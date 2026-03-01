import json
import os

import pandas as pd

from app import app


def test_api_heatmap_returns_points(tmp_path):
    csv_path = tmp_path / "cases.csv"
    pd.DataFrame(
        [
            {
                "CaseIdentifier": "[2025] SGHC 1",
                "Year": 2025,
                "URL": "https://example/1",
                "Locations": "Bedok",
                "LocationScores": json.dumps({"Bedok": 1.0}),
            }
        ]
    ).to_csv(csv_path, index=False)

    os.environ["CRIMEWATCH_DATA_FILE"] = str(csv_path)
    client = app.test_client()
    response = client.get("/api/heatmap")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["case_count"] == 1
    assert payload["point_count"] == 1
