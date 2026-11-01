import sys
from datetime import date, datetime
from io import BytesIO
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services import analytics, reports  # noqa: E402
from utils import exporters  # noqa: E402


def sample_df():
    rows = [
        (1, date(2026, 3, 1), "Income", "Salary", 3200.5, "March pay, bonus", datetime(2026, 3, 1, 9, 30)),
        (2, date(2026, 3, 15), "Expense", "Food", 45.25, 'Dinner "out"', datetime(2026, 3, 15, 20, 5)),
    ]
    return pd.DataFrame(rows, columns=analytics.TX_COLUMNS)


def test_export_columns_are_readable():
    out = exporters.transactions_for_export(sample_df())
    assert list(out.columns) == ["Transaction ID", "Date", "Type", "Category", "Amount",
                                 "Description", "Created At"]


def test_csv_values_dates_and_quoting():
    data = exporters.to_csv_bytes(exporters.transactions_for_export(sample_df()))
    back = pd.read_csv(BytesIO(data), encoding="utf-8-sig")
    assert list(back["Date"]) == ["2026-03-01", "2026-03-15"]
    assert list(back["Amount"]) == [3200.5, 45.25]
    assert back.loc[0, "Description"] == "March pay, bonus"
    assert back.loc[1, "Description"] == 'Dinner "out"'


def test_excel_values_dates_and_numbers():
    data = exporters.to_excel_bytes(exporters.transactions_for_export(sample_df()), "Transactions")
    ws = load_workbook(BytesIO(data))["Transactions"]
    assert [c.value for c in ws[1]][:5] == ["Transaction ID", "Date", "Type", "Category", "Amount"]
    assert ws["A2"].value == 1
    assert ws["B2"].value.date() == date(2026, 3, 1)
    assert ws["B2"].number_format == "yyyy-mm-dd"
    assert ws["E2"].value == 3200.5 and isinstance(ws["E2"].value, float)
    assert ws["E3"].value == 45.25


def test_multi_sheet_report_export():
    df = sample_df()
    tables = reports.export_tables(reports.build_report(df), df)
    wb = load_workbook(BytesIO(exporters.to_excel_bytes(tables)))
    assert set(wb.sheetnames) == {"Summary", "Monthly", "Expenses by Category",
                                  "Income by Category", "Transactions"}
    summary = {r[0].value: r[1].value for r in wb["Summary"].iter_rows(min_row=2)}
    assert summary["Total Income"] == 3200.5 and summary["Total Expenses"] == 45.25


def test_empty_export_does_not_fail():
    empty = exporters.transactions_for_export(analytics.empty_transactions())
    assert len(exporters.to_csv_bytes(empty)) > 0
    assert len(exporters.to_excel_bytes(empty)) > 0
