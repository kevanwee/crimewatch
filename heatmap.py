from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

import folium
import pandas as pd
from folium.plugins import HeatMap

from location_catalog import SINGAPORE_LOCATION_COORDS


REQUIRED_COLUMNS = {"CaseIdentifier", "Year", "URL"}


def load_case_data(file_name: str) -> pd.DataFrame:
    file_path = Path(file_name)
    if not file_path.exists():
        raise FileNotFoundError(f"Input file does not exist: {file_name}")

    suffix = file_path.suffix.lower()
    if suffix == ".csv":
        df = pd.read_csv(file_path)
    elif suffix in {".xlsx", ".xls"}:
        df = pd.read_excel(file_path)
    else:
        raise ValueError("Invalid file type. Please provide a CSV or XLSX file.")

    missing_columns = REQUIRED_COLUMNS.difference(df.columns)
    if missing_columns:
        missing_list = ", ".join(sorted(missing_columns))
        raise ValueError(f"Input file missing required columns: {missing_list}")

    return df


def _parse_location_scores(raw_scores: object, raw_locations: object) -> Dict[str, float]:
    if isinstance(raw_scores, str) and raw_scores.strip():
        try:
            parsed = json.loads(raw_scores)
            if isinstance(parsed, dict):
                return {
                    str(location): float(score)
                    for location, score in parsed.items()
                    if isinstance(location, str)
                }
        except json.JSONDecodeError:
            pass

    if isinstance(raw_locations, str) and raw_locations.strip():
        return {location.strip(): 1.0 for location in raw_locations.split(";") if location.strip()}

    return {}


def build_heatmap_points(
    df: pd.DataFrame,
    min_weight: float = 0.2,
    aggregate: bool = True,
) -> List[Dict[str, float]]:
    points: List[Dict[str, float]] = []
    aggregate_map: Dict[str, Dict[str, float]] = defaultdict(
        lambda: {
            "latitude": 0.0,
            "longitude": 0.0,
            "weight": 0.0,
            "case_count": 0.0,
            "location": "",
        }
    )

    for _, row in df.iterrows():
        location_scores = _parse_location_scores(row.get("LocationScores"), row.get("Locations"))
        case_locations = set()
        for location, score in location_scores.items():
            canonical_location = location.strip()
            coords = SINGAPORE_LOCATION_COORDS.get(canonical_location)
            if coords is None:
                continue
            weight = float(score)
            if weight < min_weight:
                continue
            case_locations.add(canonical_location)

            point = {
                "latitude": float(coords[0]),
                "longitude": float(coords[1]),
                "weight": weight,
                "location": canonical_location,
                "year": int(row["Year"]),
            }
            points.append(point)

            key = canonical_location
            aggregate_entry = aggregate_map[key]
            aggregate_entry["latitude"] = point["latitude"]
            aggregate_entry["longitude"] = point["longitude"]
            aggregate_entry["weight"] += weight
            aggregate_entry["location"] = canonical_location

        for location in case_locations:
            aggregate_map[location]["case_count"] += 1.0

    if not aggregate:
        return points

    aggregated = list(aggregate_map.values())
    aggregated.sort(key=lambda item: item["weight"], reverse=True)
    return aggregated


def create_crime_heatmap(
    file_name: str,
    map_filename: str = "crime_heatmap.html",
    min_weight: float = 0.2,
) -> str:
    df = load_case_data(file_name)
    points = build_heatmap_points(df=df, min_weight=min_weight, aggregate=False)
    if not points:
        raise ValueError("No valid heatmap points were produced from input data.")

    crime_map = folium.Map(location=[1.3521, 103.8198], zoom_start=11, control_scale=True)
    heat_data = [[point["latitude"], point["longitude"], point["weight"]] for point in points]
    HeatMap(
        heat_data,
        radius=20,
        blur=16,
        min_opacity=0.3,
        max_zoom=14,
    ).add_to(crime_map)

    crime_map.save(map_filename)
    return map_filename


def export_heatmap_points_json(
    file_name: str,
    output_json: str = "heatmap_points.json",
    min_weight: float = 0.2,
) -> str:
    df = load_case_data(file_name)
    points = build_heatmap_points(df=df, min_weight=min_weight, aggregate=True)
    with open(output_json, "w", encoding="utf-8") as file:
        json.dump(points, file, ensure_ascii=True, indent=2)
    return output_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate heatmap outputs from scraped case data.")
    parser.add_argument("--input", required=True, help="Input CSV/XLSX file from crimewatcher.py")
    parser.add_argument(
        "--output-map",
        default="crime_heatmap.html",
        help="Output HTML map path. Defaults to crime_heatmap.html",
    )
    parser.add_argument(
        "--output-points",
        default="heatmap_points.json",
        help="Output JSON points path. Defaults to heatmap_points.json",
    )
    parser.add_argument(
        "--min-weight",
        type=float,
        default=0.2,
        help="Minimum normalized score to keep as heatpoint.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    map_path = create_crime_heatmap(args.input, args.output_map, min_weight=args.min_weight)
    points_path = export_heatmap_points_json(
        args.input,
        output_json=args.output_points,
        min_weight=args.min_weight,
    )
    print(f"Heatmap HTML: {map_path}")
    print(f"Heatmap points JSON: {points_path}")
