"""Tests for in-memory CSV and XLSX flow dataset uploads."""

from __future__ import annotations

import csv
import unittest
from io import BytesIO, StringIO

from openpyxl import Workbook

from data_contract import FLOW_REQUIRED_COLUMNS
from dataset_upload import load_uploaded_dataset, safe_export_stem
from export import build_marketplace_export, build_scored_export
from pipeline import process_flow_dataset


FLOW_ROWS = [
    [1, "Invoice Processing", "Alpha", "Finance", "Finance", 100, 1, 30, 1000],
    [2, "Recruitment Processing", "Beta", "HR", "HR", 80, 2, 20, 800],
    [3, "Campaign Flow", "Gamma", "Sales", "Sales", 60, 3, 10, 600],
]


def build_csv_bytes(
    rows: list[list[object]] | None = None,
    headers: list[str] | tuple[str, ...] = FLOW_REQUIRED_COLUMNS,
    delimiter: str = ",",
    include_bom: bool = False,
) -> bytes:
    """Return a small valid flow catalog as CSV bytes."""
    output = StringIO(newline="")
    writer = csv.writer(output, delimiter=delimiter)
    writer.writerow(headers)
    writer.writerows(FLOW_ROWS if rows is None else rows)
    payload = output.getvalue().encode("utf-8")
    return b"\xef\xbb\xbf" + payload if include_bom else payload


def build_xlsx_bytes(rows: list[list[object]] | None = None) -> bytes:
    """Return a small flow catalog in the first XLSX worksheet."""
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Flows"
    worksheet.append(list(FLOW_REQUIRED_COLUMNS))
    for row in FLOW_ROWS if rows is None else rows:
        worksheet.append(row)
    workbook.create_sheet("Ignored")

    output = BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()


class DatasetUploadTests(unittest.TestCase):
    """Verify upload parsing, validation, scoring, and export behavior."""

    def test_valid_csv_upload(self) -> None:
        result = load_uploaded_dataset("company_flows.csv", build_csv_bytes())

        self.assertEqual(result.file_format, "CSV")
        self.assertEqual(result.row_count, 3)
        self.assertEqual(result.column_count, len(FLOW_REQUIRED_COLUMNS))
        self.assertEqual(len(result.flows), 3)
        self.assertIn("Customer Count", result.flows.columns)

    def test_valid_xlsx_upload_uses_first_sheet(self) -> None:
        result = load_uploaded_dataset("company_flows.xlsx", build_xlsx_bytes())

        self.assertEqual(result.file_format, "XLSX")
        self.assertEqual(result.row_count, 3)
        self.assertEqual(result.flows["Flow ID"].tolist(), [1, 2, 3])

    def test_missing_required_column_is_rejected(self) -> None:
        headers = [column for column in FLOW_REQUIRED_COLUMNS if column != "Department"]
        rows = [[value for index, value in enumerate(row) if index != 3] for row in FLOW_ROWS]

        with self.assertRaisesRegex(ValueError, "missing required columns: Department"):
            load_uploaded_dataset("missing.csv", build_csv_bytes(rows, headers))

    def test_empty_file_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Uploaded file is empty"):
            load_uploaded_dataset("empty.csv", b"")

    def test_invalid_numeric_value_reports_column(self) -> None:
        rows = [row.copy() for row in FLOW_ROWS]
        rows[1][5] = "many"

        with self.assertRaisesRegex(ValueError, "Column 'Run Count'"):
            load_uploaded_dataset("invalid.csv", build_csv_bytes(rows))

    def test_infinite_numeric_value_is_rejected(self) -> None:
        rows = [row.copy() for row in FLOW_ROWS]
        rows[0][8] = "inf"

        with self.assertRaisesRegex(ValueError, "Column 'Transaction Volume'"):
            load_uploaded_dataset("infinite.csv", build_csv_bytes(rows))

    def test_known_headers_are_case_and_underscore_insensitive(self) -> None:
        headers = [column.upper().replace(" ", "_") for column in FLOW_REQUIRED_COLUMNS]
        result = load_uploaded_dataset(
            "normalized.csv",
            build_csv_bytes(headers=headers, include_bom=True),
        )

        self.assertTrue(set(FLOW_REQUIRED_COLUMNS).issubset(result.flows.columns))

    def test_semicolon_delimited_csv_is_supported(self) -> None:
        result = load_uploaded_dataset(
            "semicolon.csv",
            build_csv_bytes(delimiter=";"),
        )

        self.assertEqual(len(result.flows), 3)
        self.assertEqual(result.flows["Department"].tolist()[0], "Finance")

    def test_duplicate_normalized_headers_are_rejected(self) -> None:
        headers = list(FLOW_REQUIRED_COLUMNS) + ["flow_id"]
        rows = [row + [row[0]] for row in FLOW_ROWS]

        with self.assertRaisesRegex(ValueError, "duplicate column names"):
            load_uploaded_dataset("duplicate.csv", build_csv_bytes(rows, headers))

    def test_uploaded_data_runs_through_scoring_and_department_matching(self) -> None:
        uploaded = load_uploaded_dataset("company_flows.csv", build_csv_bytes())
        scores = process_flow_dataset(uploaded.flows)

        self.assertEqual(len(scores), 3)
        self.assertListEqual(
            scores["Predicted Department"].tolist(),
            ["Finance", "HR", "Sales"],
        )
        self.assertTrue(scores["Department Match"].eq("Matched").all())
        self.assertTrue(scores["Opportunity Score"].between(0, 100).all())

    def test_uploaded_data_drives_both_exports(self) -> None:
        uploaded = load_uploaded_dataset("company_flows.csv", build_csv_bytes())
        scores = process_flow_dataset(uploaded.flows)
        scored_export = build_scored_export(scores)
        marketplace_export = build_marketplace_export(scores)

        self.assertSetEqual(set(scored_export["Flow ID"]), {1, 2, 3})
        self.assertSetEqual(set(marketplace_export["Task ID"]), {1, 2, 3})
        self.assertListEqual(
            marketplace_export["Department"].tolist(),
            scored_export["Predicted Department"].tolist(),
        )

    def test_export_stem_removes_paths_and_special_characters(self) -> None:
        self.assertEqual(
            safe_export_stem("../../Company Flows (Final).csv"),
            "company_flows_final",
        )


if __name__ == "__main__":
    unittest.main()
