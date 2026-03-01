import json

import pandas as pd
import pytest

from heatmap import build_heatmap_points, load_case_data


def test_build_heatmap_points_aggregates_by_location():
    df = pd.DataFrame(
        [
            {
                "CaseIdentifier": "[2025] SGHC 1",
                "Year": 2025,
                "URL": "https://example/1",
                "Locations": "Bedok;Changi",
                "LocationScores": json.dumps({"Bedok": 1.0, "Changi": 0.1}),
            },
            {
                "CaseIdentifier": "[2025] SGHC 2",
                "Year": 2025,
                "URL": "https://example/2",
                "Locations": "Bedok",
                "LocationScores": json.dumps({"Bedok": 0.8}),
            },
        ]
    )

    points = build_heatmap_points(df=df, min_weight=0.2, aggregate=True)

    assert len(points) == 1
    assert points[0]["location"] == "Bedok"
    assert points[0]["case_count"] == 2.0
    assert points[0]["weight"] == pytest.approx(1.8)


def test_load_case_data_requires_columns(tmp_path):
    path = tmp_path / "cases.csv"
    pd.DataFrame([{"CaseIdentifier": "x"}]).to_csv(path, index=False)

    with pytest.raises(ValueError):
        load_case_data(str(path))
