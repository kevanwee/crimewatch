from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import pandas as pd
from flask import Flask, jsonify, request, send_from_directory

from heatmap import build_heatmap_points, load_case_data


REPO_ROOT = Path(__file__).resolve().parent
FRONTEND_DIR = REPO_ROOT / "frontend"
DEFAULT_DATA_ENV = "CRIMEWATCH_DATA_FILE"

app = Flask(__name__, static_folder=str(FRONTEND_DIR), static_url_path="/static")


def resolve_data_file(explicit_path: Optional[str]) -> Path:
    if explicit_path:
        candidate = Path(explicit_path)
        if not candidate.is_absolute():
            candidate = REPO_ROOT / candidate
        if not candidate.exists():
            raise FileNotFoundError(f"Data file not found: {candidate}")
        return candidate

    env_path = os.getenv(DEFAULT_DATA_ENV, "").strip()
    if env_path:
        return resolve_data_file(env_path)

    candidates = sorted(REPO_ROOT.glob("elitigation_criminal_cases_*_to_*.csv"))
    if candidates:
        return candidates[-1]

    raise FileNotFoundError(
        "No case CSV found. Run crimewatcher.py first or set CRIMEWATCH_DATA_FILE."
    )


def _parse_int_query(name: str, raw_value: Optional[str]) -> Optional[int]:
    if raw_value is None or raw_value == "":
        return None
    try:
        return int(raw_value)
    except ValueError as exc:
        raise ValueError(f"Query parameter '{name}' must be an integer.") from exc


def _parse_float_query(name: str, raw_value: Optional[str], default: float) -> float:
    if raw_value is None or raw_value == "":
        return default
    try:
        value = float(raw_value)
    except ValueError as exc:
        raise ValueError(f"Query parameter '{name}' must be a number.") from exc
    if value < 0:
        raise ValueError(f"Query parameter '{name}' must be >= 0.")
    return value


def _apply_year_filter(df: pd.DataFrame, year_from: Optional[int], year_to: Optional[int]) -> pd.DataFrame:
    filtered = df
    if year_from is not None:
        filtered = filtered[filtered["Year"] >= year_from]
    if year_to is not None:
        filtered = filtered[filtered["Year"] <= year_to]
    return filtered


@app.get("/")
def index():
    return send_from_directory(str(FRONTEND_DIR), "index.html")


@app.get("/api/health")
def health():
    return jsonify({"status": "ok"})


@app.get("/api/heatmap")
def api_heatmap():
    try:
        data_file = resolve_data_file(request.args.get("data_file"))
        min_weight = _parse_float_query("min_weight", request.args.get("min_weight"), default=0.2)
        year_from = _parse_int_query("year_from", request.args.get("year_from"))
        year_to = _parse_int_query("year_to", request.args.get("year_to"))
        if year_from is not None and year_to is not None and year_from > year_to:
            raise ValueError("year_from must be <= year_to")

        df = load_case_data(str(data_file))
        df = _apply_year_filter(df, year_from=year_from, year_to=year_to)
        points = build_heatmap_points(df=df, min_weight=min_weight, aggregate=True)

        year_bounds = None
        if not df.empty:
            year_bounds = {"min": int(df["Year"].min()), "max": int(df["Year"].max())}

        return jsonify(
            {
                "data_file": str(data_file.name),
                "case_count": int(len(df)),
                "point_count": int(len(points)),
                "min_weight": float(min_weight),
                "year_bounds": year_bounds,
                "points": points,
            }
        )
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": str(exc)}), 400


@app.get("/api/cases")
def api_cases():
    try:
        data_file = resolve_data_file(request.args.get("data_file"))
        limit = _parse_int_query("limit", request.args.get("limit")) or 100
        if limit <= 0 or limit > 1000:
            raise ValueError("limit must be in range 1..1000")

        year_from = _parse_int_query("year_from", request.args.get("year_from"))
        year_to = _parse_int_query("year_to", request.args.get("year_to"))
        if year_from is not None and year_to is not None and year_from > year_to:
            raise ValueError("year_from must be <= year_to")

        df = load_case_data(str(data_file))
        df = _apply_year_filter(df, year_from=year_from, year_to=year_to)
        subset = df[
            ["CaseIdentifier", "Year", "Locations", "LocationScores", "KeywordAfterOffences", "URL"]
        ].head(limit)
        return jsonify({"cases": subset.to_dict(orient="records"), "count": int(len(subset))})
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": str(exc)}), 400


if __name__ == "__main__":
    host = os.getenv("CRIMEWATCH_HOST", "127.0.0.1")
    port = int(os.getenv("CRIMEWATCH_PORT", "8000"))
    app.run(host=host, port=port, debug=False)
