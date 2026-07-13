"""Streamlit interaction tests for the complete dashboard."""

from __future__ import annotations

import unittest

from streamlit.testing.v1 import AppTest


class DashboardTests(unittest.TestCase):
    """Verify the primary dashboard views, filters, and downloads."""

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
            [(10, 8), (29, 8), (24, 11), (110, 14)],
        )
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
        self.assertEqual(app.dataframe[3].value.shape, (12, 14))

    def test_empty_filter_state_disables_flow_exports(self) -> None:
        app = AppTest.from_file("app.py", default_timeout=20)
        app.run()

        app.multiselect[0].set_value(["Finance"])
        app.multiselect[1].set_value(["HR"])
        app.run()

        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, "0")
        self.assertEqual(
            [message.value for message in app.info],
            ["No flows match this view."] * 3,
        )
        self.assertListEqual(
            [table.value.shape for table in app.dataframe],
            [(24, 11)],
        )
        self.assertTrue(
            all(button.disabled for button in app.get("download_button"))
        )


if __name__ == "__main__":
    unittest.main()
