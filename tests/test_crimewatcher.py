import json

from crimewatcher import SingaporeCrimeScraper


def test_extract_location_scores_filters_prison_mentions():
    scraper = SingaporeCrimeScraper()
    text = (
        "The accused assaulted the victim at Bedok town centre in the evening. "
        "After conviction, he was sent to Changi Prison Complex."
    )
    scores, signals = scraper._extract_location_scores(text)

    assert "Bedok" in scores
    assert "Changi" not in scores
    assert signals


def test_extract_location_scores_uses_aliases():
    scraper = SingaporeCrimeScraper()
    text = "The robbery took place at AMK and the accused fled by taxi."
    scores, _ = scraper._extract_location_scores(text)

    assert "Ang Mo Kio" in scores


def test_scrape_case_details_format():
    scraper = SingaporeCrimeScraper()
    fake_text = (
        "The offender was charged with theft under section 379. "
        "He committed the offence at Tampines Mall."
    )
    scores, signals = scraper._extract_location_scores(fake_text)
    payload = {
        "Locations": "; ".join(scores.keys()),
        "LocationScores": json.dumps(scores),
        "LocationEvidence": json.dumps([signal.__dict__ for signal in signals]),
    }

    assert "Tampines" in payload["Locations"]
    assert "LocationScores" in payload
