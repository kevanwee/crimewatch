# CrimeWatch

<div align="center">
  <img src="./readme/crimewatch.jpg" alt="CrimeWatch banner" />
</div>

CrimeWatch scrapes Singapore criminal judgments from eLitigation, infers likely incident locations from judgment text, and serves a weighted hotspot heatmap to a frontend.

## What is implemented

- Criminal-case scraper for eLitigation judgment pages
- Mention-level location scoring (not just raw string matching)
- Institution-context filtering (for example prison/hospital/court mentions)
- Weighted heatpoint generation from case-level location scores
- API + frontend map (Leaflet + leaflet.heat)
- Standalone HTML heatmap generation
- Automated tests for extraction, heatpoint aggregation, and API behavior

## Project structure

- `crimewatcher.py`: scraper + location extraction/scoring pipeline
- `heatmap.py`: validated heatpoint builder + standalone heatmap outputs
- `location_catalog.py`: Singapore location coordinates and extraction rules
- `app.py`: Flask API + static frontend server
- `frontend/`: map UI
- `tests/`: validation suite

## Methodology (research-backed tuning)

The hotspot extraction now follows an event-geography approach:

- Start with gazetteer matching for Singapore locations.
- Score each location mention at sentence/window level instead of document-wide.
- Increase score when offence/event language appears in the same sentence.
- Decrease or suppress score when context is institutional/procedural (prison, hospital, court, sentencing/remand).
- Aggregate only retained signals into weighted hotspot points.

This directly addresses the earlier false-positive issue where locations like `Changi` were overcounted due to `Changi Prison` mentions that are not the offence scene.

### Research used for tuning

- ACLED codebook (event geography and location precision guidance):  
  https://acleddata.com/knowledge-base/codebook/
- Mordecai 3 (event geolocation from text, event-location focus):  
  https://github.com/openeventdata/mordecai3
- Topo-BERT (context-aware toponym disambiguation):  
  https://arxiv.org/abs/2408.08435
- Leaflet.heat weighted intensity behavior:  
  https://leaflet.github.io/Leaflet.heat/

Notes:
- The current implementation is a transparent rule-based scorer, not a transformer model.
- Coordinates are planning-area centroids, not exact incident addresses.

## Installation

```bash
python -m pip install -r requirements.txt
```

## Usage

### 1) Scrape judgments

```bash
python crimewatcher.py --start-year 2023 --end-year 2025 --output cases_2023_2025.csv
```

Optional for quick smoke runs:

```bash
python crimewatcher.py --start-year 2025 --end-year 2025 --max-pages-per-year 5 --output sample.csv
```

### 2) Generate standalone heatmap artifacts

```bash
python heatmap.py --input cases_2023_2025.csv --output-map crime_heatmap.html --output-points heatmap_points.json
```

### 3) Serve frontend + API

```bash
set CRIMEWATCH_DATA_FILE=cases_2023_2025.csv
python app.py
```

Open:

- `http://127.0.0.1:8000/` frontend
- `http://127.0.0.1:8000/api/health`
- `http://127.0.0.1:8000/api/heatmap`
- `http://127.0.0.1:8000/api/cases?limit=100`

## Deploy (Render, free)

`render.yaml` is a Render blueprint for a free web service: in the Render dashboard choose
**New → Blueprint** and pick this repository. It installs `requirements.txt`, runs
`gunicorn app:app`, and checks `/api/health`. With no scraped CSV and no `CRIMEWATCH_DATA_FILE`, the app
serves the committed snapshot `data/cases_latest.csv` (174 judgments, 2023–2025). Free services sleep
after 15 idle minutes and take about a minute to wake.

## API query parameters

`/api/heatmap`

- `year_from` (int, optional)
- `year_to` (int, optional)
- `min_weight` (float, optional, default `0.2`)
- `data_file` (optional path override)

`/api/cases`

- `year_from` (int, optional)
- `year_to` (int, optional)
- `limit` (int, optional, default `100`, max `1000`)
- `data_file` (optional path override)

## Output schema (scraper CSV)

- `CaseIdentifier`
- `Charges`
- `Locations`
- `LocationScores` (JSON object of normalized location weights)
- `LocationEvidence` (JSON list with reason tags and sentence snippets)
- `KeywordAfterOffences`
- `Year`
- `URL`

## Validation

Run the test suite:

```bash
python -m pytest -q
```

Current status: all tests pass locally.

## Limitations

- Gazetteer coverage is finite; uncommon micro-locations may be missed.
- Legal judgments may omit or obfuscate exact offence locations.
- Weighting is heuristic and should be calibrated further if ground-truth labels become available.

## License

MIT License. See [LICENSE](LICENSE).
