import time
import re
import pandas as pd
import requests
from bs4 import BeautifulSoup
from ftfy import fix_text
import spacy

# nlp = spacy.load("en_core_web_sm")


class SingaporeCrimeScraper:
    def __init__(self):
        self.base_list_url = "https://www.elitigation.sg/gd/Home/Index"
        self.base_case_url = "https://www.elitigation.sg/gd/s/"
        self.singapore_locations = {
            "Ang Mo Kio": [1.3691, 103.8454],
            "Bedok": [1.3236, 103.9273],
            "Bishan": [1.3526, 103.8352],
            "Bukit Batok": [1.3590, 103.7637],
            "Bukit Merah": [1.2819, 103.8239],
            "Bukit Panjang": [1.3774, 103.7719],
            "Bukit Timah": [1.3294, 103.8021],
            "Changi": [1.3644, 103.9915],
            "Chinatown": [1.2808, 103.8442],
            "Clementi": [1.3162, 103.7649],
            "Geylang": [1.3201, 103.8918],
            "Hougang": [1.3612, 103.8863],
            "Jurong": [1.3329, 103.7436],
            "Kallang": [1.3100, 103.8714],
            "Marina Bay": [1.2815, 103.8636],
            "Novena": [1.3203, 103.8438],
            "Orchard": [1.3036, 103.8318],
            "Pasir Ris": [1.3721, 103.9474],
            "Punggol": [1.3984, 103.9072],
            "Queenstown": [1.2942, 103.7861],
            "Sembawang": [1.4491, 103.8185],
            "Sengkang": [1.3868, 103.8914],
            "Serangoon": [1.3554, 103.8679],
            "Tampines": [1.3496, 103.9568],
            "Toa Payoh": [1.3340, 103.8471],
            "Woodlands": [1.4382, 103.7891],
            "Yishun": [1.4304, 103.8354]
        }

    def scrape_elitigation_criminal_cases(self, start_year, end_year):
        all_cases = []
        output_file_name = f"elitigation_criminal_cases_{start_year}_to_{end_year}.csv"

        for year in range(start_year, end_year + 1):
            print(f"Processing cases from {year}...")
            page_num = 1

            while True:
                list_url = f"{self.base_list_url}?Filter=SUPCT&YearOfDecision={year}&SortBy=Score&CurrentPage={page_num}"
                response = requests.get(list_url)
                if response.status_code != 200:
                    print(f"Failed to retrieve page {page_num} for year {year}. Status code: {response.status_code}")
                    break

                soup = BeautifulSoup(response.text, 'html.parser')
                cards = soup.find_all('div', class_='card col-12')

                if not cards:
                    print(f"No more cases found for year {year} after page {page_num - 1}")
                    break

                for card in cards:
                    case_identifier_span = card.find('span', class_='gd-addinfo-text')
                    if case_identifier_span:
                        case_identifier = fix_text(case_identifier_span.text.strip().replace(" |", ""))

                        catchwords_links = card.find_all('a', class_='gd-cw')
                        catchwords_texts = [
                            fix_text(link.get("data-searchterm", "").strip()) for link in catchwords_links
                        ]
                        if any("Criminal Law" in text for text in catchwords_texts):
                            print(f"Found criminal law case: {case_identifier}")

                            keyword_after_offences = []
                            for text in catchwords_texts:
                                if 'Offences — ' in text:
                                    keyword_after_offences.append(text.split('Offences — ')[-1].strip().replace('"', "").replace("—", "-"))
                                if 'offences — ' in text:
                                    keyword_after_offences.append(text.split('offences — ')[-1].strip().replace('"', "").replace("—", "-"))
                                elif 'Criminal Law — ' in text:
                                    keyword_after_offences.append(text.split('Criminal Law — ')[-1].strip().replace('"', "").replace("—", "-"))
                        
                            formatted_case_identifier = (
                                case_identifier.replace(" ", "_")
                                .replace("[", "")
                                .replace("]", "")
                            )
                            case_url = f"{self.base_case_url}{formatted_case_identifier}"
                            case_details = self.scrape_case_details(case_url)
                            if case_details:
                                all_cases.append({
                                    'CaseIdentifier': case_identifier,
                                    'Charges': case_details['Charges'],
                                    'Locations': case_details['Locations'],
                                    'KeywordAfterOffences': ", ".join(keyword_after_offences) if keyword_after_offences else None,
                                    'Year': year,
                                    'URL': case_url
                                })

                page_num += 1
                time.sleep(0.5)

        pd.DataFrame(all_cases).to_csv(output_file_name, index=False)
        print(f"Saved all cases to {output_file_name}")
        return output_file_name

    def scrape_case_details(self, url):
        response = requests.get(url)
        if response.status_code != 200:
            print(f"Failed to fetch details from {url}. Status code: {response.status_code}")
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        judgment_text_divs = soup.find_all('div', class_='Judg-1')

        if not judgment_text_divs:
            print(f"No judgment text found at {url}")
            return None

        judgment_text = "\n".join(div.text for div in judgment_text_divs)
        judgment_text = fix_text(judgment_text)

        # encoding prob - still figuring out how to fix this
        judgment_text = judgment_text.replace("â€ƒ", ". ").replace("Â", "")

        charges_list = []
        locations_list = []

        # tried using spaCy to extract sentences containing 'charge' - results need some tuning
        # doc = nlp(judgment_text)
        # for sentence in doc.sents:
        #     if any(word.lower_ == 'charge' for word in sentence):
        #         charges_list.append(sentence.text.strip())


        for location in self.singapore_locations.keys():
            # match location names as whole words using word boundaries
            location_pattern = rf"\b{location.lower()}\b"
            if re.search(location_pattern, judgment_text.lower()):
                # tentatively excluding "prison", "general hospital", and "hospital" - need to think of another way to handle this
                # changi is reflected far too many times
                if not any(exclusion in judgment_text.lower() for exclusion in [f"{location.lower()} prison", "general hospital", "hospital"]):
                    locations_list.append(location)


        return {
            'Charges': "; ".join(charges_list),
            'Locations': "; ".join(locations_list)
        }


if __name__ == "__main__":
    scraper = SingaporeCrimeScraper()
    scraper.scrape_elitigation_criminal_cases(start_year=2023, end_year=2025)
