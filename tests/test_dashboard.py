"""Streamlit interaction tests for the complete dashboard."""

from __future__ import annotations

import unittest

from streamlit.testing.v1 import AppTest

from app import build_export_file_names
from tests.test_dataset_upload import build_csv_bytes


class DashboardTests(unittest.TestCase):
    """Verify dashboard views, charts, filters, uploads, and downloads."""

    def test_dashboard_workflow(self) -> None:
        app = AppTest.from_file("app.py", default_timeout=20)
        app.run()

        self.assertFalse(app.exception)
        self.assertListEqual(
            [tab.label for tab in app.tabs],
            [
                "Top opportunities",
                "Risk monitoring",
                "Customer growth",
                "All flows",
            ],
        )
        self.assertListEqual(
            [table.value.shape for table in app.dataframe],
            [(10, 12), (29, 10), (24, 11), (110, 18)],
        )
        self.assertIn("Usage Score", app.dataframe[0].value.columns)
        self.assertIn("Resell Score", app.dataframe[0].value.columns)
        self.assertEqual(len(app.metric), 5)
        self.assertEqual(len(app.get("vega_lite_chart")), 2)
        self.assertIn("Product Score =", app.code[0].value)
        self.assertListEqual(
            [button.label for button in app.get("download_button")],
            ["Scored results", "Marketplace tasks"],
        )

        app.selectbox[0].set_value("Summit Bank").run()
        self.assertFalse(app.exception)
        self.assertEqual(app.dataframe[2].value.shape, (5, 11))

        app.multiselect[0].set_value(["Finance"]).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, "12")
        self.assertEqual(app.dataframe[3].value.shape, (12, 18))

    def test_empty_filter_state_disables_flow_exports(self) -> None:
        app = AppTest.from_file("app.py", default_timeout=20)
        app.run()

        app.multiselect[0].set_value(["Finance"])
        app.multiselect[1].set_value(["HR"])
        app.run()

        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, "0")
        self.assertListEqual(
            [message.value for message in app.info],
            [
                "No portfolio signals match the active filters.",
                "No flows match this view.",
                "No flows match this view.",
                "No customer growth opportunities match this view.",
                "No flows match this view.",
            ],
        )
        self.assertFalse(app.dataframe)
        self.assertFalse(app.get("vega_lite_chart"))
        self.assertTrue(
            all(button.disabled for button in app.get("download_button"))
        )

    def test_new_upload_clears_filters_and_reset_restores_sample(self) -> None:
        app = AppTest.from_file("app.py", default_timeout=20)
        app.run()

        app.radio[0].set_value("Upload dataset").run()
        self.assertEqual(len(app.file_uploader), 1)

        app.file_uploader[0].set_value(
            ("Company Flows.csv", build_csv_bytes(), "text/csv")
        ).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, "3")
        self.assertEqual(app.dataframe[-1].value.shape, (3, 18))
        self.assertIn("File: Company Flows.csv", [item.value for item in app.caption])
        self.assertIn("Rows: 3", [item.value for item in app.caption])

        app.multiselect[0].set_value(["Finance"]).run()
        self.assertEqual(app.metric[0].value, "1")

        replacement_rows = [
            [10, "Server Backup", "Delta", "IT", "IT", 40, 1, 15, 300]
        ]
        app.file_uploader[0].set_value(
            (
                "IT Portfolio.csv",
                build_csv_bytes(rows=replacement_rows),
                "text/csv",
            )
        ).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, "1")
        self.assertListEqual(app.multiselect[0].value, [])
        self.assertEqual(app.dataframe[-1].value.shape, (1, 18))

        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.radio[0].value, "Sample dataset")
        self.assertFalse(app.file_uploader)
        self.assertEqual(app.metric[0].value, "110")

    def test_export_names_follow_the_active_source(self) -> None:
        self.assertTupleEqual(
            build_export_file_names("company_flows"),
            (
                "company_flows_scored.csv",
                "company_flows_marketplace_tasks.csv",
            ),
        )
        self.assertTupleEqual(
            build_export_file_names("internalflow"),
            (
                "internalflow_scored_results.csv",
                "internalflow_marketplace_tasks.csv",
            ),
        )


if __name__ == "__main__":
    unittest.main()
