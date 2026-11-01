"""CSV and Excel exporters. Pure functions returning bytes."""
from __future__ import annotations

from datetime import date, datetime
from io import BytesIO

import pandas as pd
from openpyxl.utils import get_column_letter

EXPORT_COLUMNS = {
    "id": "Transaction ID", "date": "Date", "type": "Type", "category": "Category",
    "amount": "Amount", "description": "Description", "created_at": "Created At",
}


def transactions_for_export(df: pd.DataFrame) -> pd.DataFrame:
    """Rename columns to readable names and normalise date types."""
    cols = list(EXPORT_COLUMNS)
    if df is None or len(df) == 0:
        return pd.DataFrame(columns=list(EXPORT_COLUMNS.values()))
    out = df[cols].copy()
    out["date"] = pd.to_datetime(out["date"]).dt.date
    out["amount"] = pd.to_numeric(out["amount"]).astype(float)
    out["created_at"] = pd.to_datetime(out["created_at"])
    return out.rename(columns=EXPORT_COLUMNS)


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    """UTF-8 (with BOM so Excel opens it correctly), ISO dates, plain numbers."""
    out = df.copy()
    for col in out.columns:
        if out[col].dtype == object and len(out) and isinstance(out[col].iloc[0], date) \
                and not isinstance(out[col].iloc[0], datetime):
            out[col] = out[col].map(lambda v: v.isoformat() if isinstance(v, date) else v)
    return out.to_csv(index=False).encode("utf-8-sig")


def to_excel_bytes(sheets: dict[str, pd.DataFrame] | pd.DataFrame, sheet_name: str = "Report") -> bytes:
    """Write one or more DataFrames to an XLSX workbook with dates/numbers preserved."""
    if isinstance(sheets, pd.DataFrame):
        sheets = {sheet_name: sheets}
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for name, frame in sheets.items():
            safe = name[:31]
            frame.to_excel(writer, sheet_name=safe, index=False)
            ws = writer.sheets[safe]
            for idx, col in enumerate(frame.columns, start=1):
                letter = get_column_letter(idx)
                series = frame[col]
                width = max([len(str(col))] + [len(str(v)) for v in series.head(200)]) + 2
                ws.column_dimensions[letter].width = min(width, 60)
                for cell in ws[letter][1:]:
                    if isinstance(cell.value, datetime):
                        cell.number_format = "yyyy-mm-dd hh:mm" if (
                            cell.value.hour or cell.value.minute) else "yyyy-mm-dd"
                    elif isinstance(cell.value, date):
                        cell.number_format = "yyyy-mm-dd"
                    elif isinstance(cell.value, float) and ("Amount" in str(col) or str(col) in (
                            "Income", "Expenses", "Net", "Value", "saved")):
                        cell.number_format = "#,##0.00"
            ws.freeze_panes = "A2"
    return buffer.getvalue()
