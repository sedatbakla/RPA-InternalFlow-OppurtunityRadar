"""Tests for scored and marketplace CSV exports."""

from __future__ import annotations

import unittest

import pandas as pd

from export import (
    MARKETPLACE_EXPORT_COLUMNS,
    build_marketplace_export,
    build_scored_export,
    dataframe_to_csv_bytes,
)


def build_export_scores() -> pd.DataFrame:
    """Return a minimal valid marketplace export fixture."""
    return pd.DataFrame(
        {
            "Flow ID": [1, 2],
            "Flow Name": ["Flow A", "Flow B"],
            "Customer": ["Alpha", "Beta"],
            "Department": ["IT", "Finance"],
            "Predicted Department": ["Finance", "Planning"],
            "Capability": ["IT", "Finance"],
            "Run Count": [100, 50],
            "Transaction Volume": [200, 100],
            "Customer Count": [2, 1],
            "Resell Score": [100, 50],
            "Product Score": [90, 40],
            "Opportunity Score": [80, 20],
            "Opportunity Level": ["High", "Low"],
            "Risk Level": ["Low", "Critical"],
            "Priority Level": ["High", "Critical"],
        }
    )


class ExportTests(unittest.TestCase):
    """Verify ordering, marketplace mapping, and CSV encoding."""

    def test_scored_export_is_sorted_by_opportunity(self) -> None:
        scores = build_export_scores().iloc[::-1]
        result = build_scored_export(scores)
        self.assertListEqual(result["Flow ID"].tolist(), [1, 2])

    def test_marketplace_export_maps_status_and_columns(self) -> None:
        result = build_marketplace_export(build_export_scores())

        self.assertEqual(tuple(result.columns), MARKETPLACE_EXPORT_COLUMNS)
        self.assertListEqual(
            result["Marketplace Status"].tolist(),
            ["Ready", "Risk Review"],
        )
        self.assertListEqual(
            result["Department"].tolist(),
            ["Finance", "Planning"],
        )

    def test_csv_export_uses_utf8_bom(self) -> None:
        payload = dataframe_to_csv_bytes(
            build_marketplace_export(build_export_scores())
        )
        self.assertTrue(payload.startswith(b"\xef\xbb\xbf"))


if __name__ == "__main__":
    unittest.main()
