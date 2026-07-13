"""End-to-end tests for automatic SQLite pipeline preparation."""

from __future__ import annotations

import unittest
from unittest.mock import patch
from uuid import uuid4

import pandas as pd

import database
import pipeline


READY_COLUMNS = (
    "Flow ID",
    "Flow Name",
    "Customer",
    "Capability",
    "Opportunity Score",
    "Risk Level",
)


class PipelineTests(unittest.TestCase):
    """Verify clean builds, reuse, and recovery without touching production data."""

    def setUp(self) -> None:
        database.DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.original_database_path = database.DATABASE_PATH
        self.test_database_path = database.DATABASE_PATH.parent / (
            f"pipeline-test-{uuid4().hex}.db"
        )
        database.DATABASE_PATH = self.test_database_path

    def tearDown(self) -> None:
        database.DATABASE_PATH = self.original_database_path
        if self.test_database_path.exists():
            self.test_database_path.unlink()

    def test_clean_pipeline_builds_all_tables_and_reuses_scores(self) -> None:
        scores = pipeline.load_or_build_scores(READY_COLUMNS)

        self.assertEqual(len(scores), 110)
        self.assertTrue(database.DATABASE_PATH.is_file())

        connection = database.get_connection()
        try:
            tables = pd.read_sql_query(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name",
                connection,
            )["name"].tolist()
        finally:
            connection.close()

        self.assertListEqual(
            tables,
            ["flow_classification", "flow_scores", "flows", "taxonomy"],
        )

        with patch(
            "pipeline.run_pipeline",
            side_effect=AssertionError("Unexpected pipeline rebuild"),
        ):
            stored_scores = pipeline.load_or_build_scores(READY_COLUMNS)
        self.assertEqual(len(stored_scores), 110)

    def test_incomplete_score_table_is_rebuilt(self) -> None:
        pipeline.run_pipeline()
        connection = database.get_connection()
        try:
            pd.DataFrame({"invalid": [1]}).to_sql(
                "flow_scores",
                connection,
                if_exists="replace",
                index=False,
            )
        finally:
            connection.close()

        recovered_scores = pipeline.load_or_build_scores(READY_COLUMNS)
        self.assertEqual(len(recovered_scores), 110)
        self.assertFalse(set(READY_COLUMNS) - set(recovered_scores.columns))


if __name__ == "__main__":
    unittest.main()
