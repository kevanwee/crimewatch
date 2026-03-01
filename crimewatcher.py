from __future__ import annotations

import argparse
import json
import re
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import DefaultDict, Dict, List, Optional, Sequence, Tuple

import pandas as pd
import requests
from bs4 import BeautifulSoup, Tag
from ftfy import fix_text
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

from location_catalog import (
    INCIDENT_TERMS,
    INSTITUTION_TERMS,
    LEGAL_PROCESS_TERMS,
    LOCATION_ALIASES,
    LOCATION_SPECIFIC_EXCLUSIONS,
    RESIDENTIAL_TERMS,
    SINGAPORE_LOCATION_COORDS,
)


REQUEST_TIMEOUT_SECONDS = 30
DEFAULT_REQUEST_DELAY_SECONDS = 0.4
MIN_SCORE_TO_KEEP = 0.8


@dataclass
class MentionSignal:
    location: str
    score: float
    reason: str
    sentence: str


class SingaporeCrimeScraper:
    """Scrape Singapore criminal judgments and infer incident-location signals."""

    def __init__(self, request_delay: float = DEFAULT_REQUEST_DELAY_SECONDS) -> None:
        self.base_list_url = "https://www.elitigation.sg/gd/Home/Index"
        self.base_case_root = "https://www.elitigation.sg"
        self.request_delay = request_delay
        self.session = self._build_session()
        self.singapore_locations = SINGAPORE_LOCATION_COORDS
        self.term_patterns = self._compile_location_patterns()

    @staticmethod
    def _build_session() -> requests.Session:
        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": (
                    "CrimeWatch/2.0 (+https://github.com/garma/crimewatch) "
                    "research scraper"
                )
            }
        )
        retries = Retry(
            total=3,
            backoff_factor=0.8,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        adapter = HTTPAdapter(max_retries=retries)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def _compile_location_patterns(self) -> List[Tuple[str, str, re.Pattern[str]]]:
        term_to_canonical: Dict[str, str] = {
            location.lower(): location for location in self.singapore_locations
        }
        for alias, canonical in LOCATION_ALIASES.items():
            if canonical in self.singapore_locations:
                term_to_canonical[alias.lower()] = canonical

        patterns: List[Tuple[str, str, re.Pattern[str]]] = []
        for term, canonical in term_to_canonical.items():
            escaped = re.escape(term)
            pattern = re.compile(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])", re.IGNORECASE)
            patterns.append((term, canonical, pattern))
        return patterns

    @staticmethod
    def _validate_year_range(start_year: int, end_year: int) -> None:
        current_year = datetime.now().year
        if start_year > end_year:
            raise ValueError("start_year must be <= end_year")
        if start_year < 1990 or end_year > current_year:
            raise ValueError(
                f"Year range must be between 1990 and {current_year}, got {start_year}-{end_year}"
            )

    def _get(self, url: str) -> Optional[requests.Response]:
        try:
            response = self.session.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            print(f"Request failed for {url}: {exc}")
            return None

    def scrape_elitigation_criminal_cases(
        self,
        start_year: int,
        end_year: int,
        output_file_name: Optional[str] = None,
        max_pages_per_year: Optional[int] = None,
    ) -> str:
        self._validate_year_range(start_year, end_year)
        all_cases: List[Dict[str, object]] = []

        if output_file_name is None:
            output_file_name = f"elitigation_criminal_cases_{start_year}_to_{end_year}.csv"

        for year in range(start_year, end_year + 1):
            print(f"Processing cases from {year}...")
            page_num = 1
            while True:
                if max_pages_per_year is not None and page_num > max_pages_per_year:
                    break

                list_url = (
                    f"{self.base_list_url}?Filter=SUPCT&YearOfDecision={year}"
                    f"&SortBy=Score&CurrentPage={page_num}"
                )
                response = self._get(list_url)
                if response is None:
                    break

                soup = BeautifulSoup(response.text, "html.parser")
                cards = soup.select("div.card.col-12")
                if not cards:
                    print(f"No more cases found for year {year} after page {page_num - 1}")
                    break

                for card in cards:
                    case_row = self._parse_case_card(card, year)
                    if case_row is not None:
                        all_cases.append(case_row)

                page_num += 1
                time.sleep(self.request_delay)

        df = pd.DataFrame(all_cases)
        df.to_csv(output_file_name, index=False)
        print(f"Saved {len(df)} cases to {output_file_name}")
        return output_file_name

    def _parse_case_card(self, card: Tag, year: int) -> Optional[Dict[str, object]]:
        catchword_tags = card.select("a.gd-cw")
        catchwords_texts = [fix_text(tag.get("data-searchterm", "").strip()) for tag in catchword_tags]
        if not any("Criminal Law" in text for text in catchwords_texts):
            return None

        case_identifier_span = card.select_one("span.gd-addinfo-text")
        if case_identifier_span is None:
            return None
        case_identifier = fix_text(case_identifier_span.get_text(" ", strip=True)).replace("|", "").strip()

        case_url = self._extract_case_url(card)
        if case_url is None:
            return None

        details = self.scrape_case_details(case_url)
        if details is None:
            return None

        return {
            "CaseIdentifier": case_identifier,
            "Charges": details["Charges"],
            "Locations": details["Locations"],
            "LocationScores": details["LocationScores"],
            "LocationEvidence": details["LocationEvidence"],
            "KeywordAfterOffences": self._extract_keyword_after_offences(catchwords_texts),
            "Year": year,
            "URL": case_url,
        }

    def _extract_case_url(self, card: Tag) -> Optional[str]:
        case_link = card.select_one("a[href*='/gd/s/']")
        if case_link is None:
            return None
        href = case_link.get("href", "")
        if not href:
            return None
        if href.startswith("http"):
            return href
        return f"{self.base_case_root}{href}"

    @staticmethod
    def _extract_keyword_after_offences(catchwords: Sequence[str]) -> Optional[str]:
        extracted: List[str] = []
        pattern = re.compile(r"(?:Offences|offences|Criminal Law)\s*[-\u2014]\s*(.+)$")
        for text in catchwords:
            match = pattern.search(text)
            if match:
                extracted.append(match.group(1).replace('"', "").strip())
        if not extracted:
            return None
        return ", ".join(dict.fromkeys(extracted))

    def scrape_case_details(self, url: str) -> Optional[Dict[str, str]]:
        response = self._get(url)
        if response is None:
            return None

        soup = BeautifulSoup(response.text, "html.parser")
        judgment_text_divs = soup.select("div.Judg-1")
        if not judgment_text_divs:
            print(f"No judgment text found at {url}")
            return None

        judgment_text = "\n".join(div.get_text(" ", strip=True) for div in judgment_text_divs)
        judgment_text = self._clean_text(judgment_text)

        charges = self._extract_charges(judgment_text)
        location_scores, location_signals = self._extract_location_scores(judgment_text)

        sorted_locations = sorted(
            location_scores.items(),
            key=lambda item: item[1],
            reverse=True,
        )

        evidence_payload = [
            {
                "location": signal.location,
                "score": round(signal.score, 3),
                "reason": signal.reason,
                "sentence": signal.sentence[:220],
            }
            for signal in location_signals[:25]
        ]

        return {
            "Charges": "; ".join(charges),
            "Locations": "; ".join(location for location, _ in sorted_locations),
            "LocationScores": json.dumps(
                {location: round(score, 3) for location, score in sorted_locations},
                ensure_ascii=True,
                sort_keys=True,
            ),
            "LocationEvidence": json.dumps(evidence_payload, ensure_ascii=True),
        }

    @staticmethod
    def _clean_text(text: str) -> str:
        cleaned = fix_text(text)
        cleaned = cleaned.replace("Ã¢â‚¬Æ’", ". ").replace("Ã‚", "")
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    @staticmethod
    def _split_sentences(text: str) -> List[str]:
        sentence_pattern = re.compile(r"(?<=[.!?])\s+")
        return [segment.strip() for segment in sentence_pattern.split(text) if segment.strip()]

    @staticmethod
    def _extract_charges(text: str) -> List[str]:
        charges: List[str] = []
        sentences = SingaporeCrimeScraper._split_sentences(text)
        for sentence in sentences:
            sentence_lower = sentence.lower()
            if (
                "charged with" in sentence_lower
                or "convicted of" in sentence_lower
                or "offence under section" in sentence_lower
                or "offence under s " in sentence_lower
            ):
                trimmed = sentence.strip()
                if len(trimmed) > 260:
                    trimmed = f"{trimmed[:257]}..."
                charges.append(trimmed)
                if len(charges) == 5:
                    break
        return charges

    def _extract_location_scores(self, text: str) -> Tuple[Dict[str, float], List[MentionSignal]]:
        location_scores: DefaultDict[str, float] = defaultdict(float)
        signals: List[MentionSignal] = []
        sentences = self._split_sentences(text)

        for sentence in sentences:
            sentence_lower = sentence.lower()
            mentions = self._find_mentions(sentence_lower)
            for term, canonical, start, end in mentions:
                score, reason = self._score_mention(canonical, term, sentence_lower, start, end)
                if score < MIN_SCORE_TO_KEEP:
                    continue
                location_scores[canonical] += score
                signals.append(
                    MentionSignal(
                        location=canonical,
                        score=score,
                        reason=reason,
                        sentence=sentence,
                    )
                )

        if not location_scores:
            return {}, []

        max_score = max(location_scores.values())
        normalized = {location: score / max_score for location, score in location_scores.items()}
        ordered_signals = sorted(signals, key=lambda item: item.score, reverse=True)
        return normalized, ordered_signals

    def _find_mentions(self, sentence_lower: str) -> List[Tuple[str, str, int, int]]:
        candidates: List[Tuple[str, str, int, int]] = []
        for term, canonical, pattern in self.term_patterns:
            for match in pattern.finditer(sentence_lower):
                candidates.append((term, canonical, match.start(), match.end()))

        # Keep longest non-overlapping spans first to avoid double counting nested terms.
        candidates.sort(key=lambda item: (item[3] - item[2], -item[2]), reverse=True)
        kept: List[Tuple[str, str, int, int]] = []
        occupied: List[Tuple[int, int]] = []
        for candidate in candidates:
            _, _, start, end = candidate
            if any(start < existing_end and end > existing_start for existing_start, existing_end in occupied):
                continue
            kept.append(candidate)
            occupied.append((start, end))
        kept.sort(key=lambda item: item[2])
        return kept

    @staticmethod
    def _contains_any(text: str, terms: Sequence[str]) -> bool:
        return any(term in text for term in terms)

    def _score_mention(
        self,
        canonical_location: str,
        term: str,
        sentence_lower: str,
        start_idx: int,
        end_idx: int,
    ) -> Tuple[float, str]:
        window_start = max(0, start_idx - 48)
        window_end = min(len(sentence_lower), end_idx + 48)
        local_window = sentence_lower[window_start:window_end]

        for phrase in LOCATION_SPECIFIC_EXCLUSIONS.get(canonical_location, set()):
            if phrase in sentence_lower:
                return 0.0, "location_specific_exclusion"

        score = 0.3
        reasons: List[str] = ["mention"]

        if self._contains_any(local_window, tuple(INSTITUTION_TERMS)):
            score -= 1.8
            reasons.append("institution_window")
        if self._contains_any(sentence_lower, tuple(LEGAL_PROCESS_TERMS)):
            score -= 0.7
            reasons.append("legal_process_sentence")
        if self._contains_any(sentence_lower, tuple(RESIDENTIAL_TERMS)):
            score -= 0.5
            reasons.append("residential_sentence")
        if self._contains_any(sentence_lower, tuple(INCIDENT_TERMS)):
            score += 1.8
            reasons.append("incident_sentence")

        prep_pattern = re.compile(
            rf"(?:at|in|near|along|outside|inside|around)\s+{re.escape(term)}\b"
        )
        if prep_pattern.search(sentence_lower):
            score += 0.6
            reasons.append("event_preposition")

        # If a sentence strongly references institutions and no crime action words,
        # treat the location as administrative context rather than incident location.
        if "institution_window" in reasons and "incident_sentence" not in reasons:
            score -= 0.5
            reasons.append("institution_without_incident")

        score = max(0.0, min(score, 3.0))
        return score, "+".join(reasons)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape eLitigation criminal judgments.")
    parser.add_argument("--start-year", type=int, required=True, help="Start year, inclusive.")
    parser.add_argument("--end-year", type=int, required=True, help="End year, inclusive.")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output CSV path. Default is generated from start/end years.",
    )
    parser.add_argument(
        "--max-pages-per-year",
        type=int,
        default=None,
        help="Optional page cap per year (useful for testing).",
    )
    parser.add_argument(
        "--request-delay",
        type=float,
        default=DEFAULT_REQUEST_DELAY_SECONDS,
        help="Delay in seconds between list-page requests.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    cli_args = parse_args()
    scraper = SingaporeCrimeScraper(request_delay=cli_args.request_delay)
    output_path = scraper.scrape_elitigation_criminal_cases(
        start_year=cli_args.start_year,
        end_year=cli_args.end_year,
        output_file_name=str(cli_args.output) if cli_args.output else None,
        max_pages_per_year=cli_args.max_pages_per_year,
    )
    print(f"CSV output: {output_path}")
