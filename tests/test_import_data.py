"""Tests for CSV validation and derived import fields."""

from __future__ import annotations

import unittest
from pathlib import Path

import pandas as pd
from pandas.testing import assert_series_equal

from import_data import FLOW_CATALOG_PATH, load_flows, load_taxonomy


FIXTURE_DIRECTORY = Path(__file__).resolve().parent / "fixtures"


class ImportDataTests(unittest.TestCase):
    """Verify project CSV loading and validation behavior."""

    def test_project_catalog_derives_customer_count(self) -> None:
        source_columns = pd.read_csv(FLOW_CATALOG_PATH, nrows=0).columns
        flows = load_flows()

        self.assertNotIn("Customer Count", source_columns)
        self.assertIn("Customer Count", flows.columns)

        expected = flows.groupby("Capability")["Customer"].nunique().sort_index()
        actual = (
            flows.groupby("Capability")["Customer Count"].first().sort_index()
        )
        assert_series_equal(actual, expected.astype(int), check_names=False)

    def test_missing_flow_file_is_rejected(self) -> None:
        missing_path = Path("missing-flow-catalog.csv")
        with self.assertRaises(FileNotFoundError):
            load_flows(missing_path)

    def test_missing_flow_columns_are_rejected(self) -> None:
        path = FIXTURE_DIRECTORY / "flows_missing_columns.csv"
        with self.assertRaisesRegex(ValueError, "missing required columns"):
            load_flows(path)

    def test_duplicate_taxonomy_keywords_are_rejected(self) -> None:
        path = FIXTURE_DIRECTORY / "taxonomy_duplicate_keywords.csv"
        with self.assertRaisesRegex(ValueError, "must be unique"):
            load_taxonomy(path)


if __name__ == "__main__":
    unittest.main()
