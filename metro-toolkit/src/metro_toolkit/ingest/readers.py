"""Read measurement exports: CSV / TXT (any delimiter, UTF-8 or Big5/CP950), Excel, and UCI SECOM."""

from __future__ import annotations

import csv
import io
from pathlib import Path

import pandas as pd

EXCEL = (".xlsx", ".xlsm", ".xls")
ENCODINGS = ("utf-8-sig", "cp950", "big5", "latin-1")  # Excel on a Taiwan Windows PC often saves Big5/CP950


def _name(source, filename: str | None) -> str:
    return filename or getattr(source, "name", None) or str(source)


def _bytes(source) -> bytes:
    if isinstance(source, (str, Path)):
        return Path(source).read_bytes()
    if hasattr(source, "getvalue"):
        return source.getvalue()
    data = source.read()
    if hasattr(source, "seek"):
        source.seek(0)
    return data


def _decode(raw: bytes) -> tuple[str, str]:
    for enc in ENCODINGS:
        try:
            return raw.decode(enc), enc
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace"), "utf-8 (with replacements)"


def excel_sheets(source) -> list[str]:
    return list(pd.ExcelFile(io.BytesIO(_bytes(source))).sheet_names)


def read_table(source, filename: str | None = None, sheet: str | int | None = None) -> pd.DataFrame:
    """Read a CSV/TXT/Excel export into a DataFrame. Delimiter and text encoding are detected.

    The detected encoding and delimiter are stored in ``df.attrs`` for the check report.
    """
    name = _name(source, filename)
    ext = Path(name).suffix.lower()
    raw = _bytes(source)
    if ext in EXCEL:
        df = pd.read_excel(io.BytesIO(raw), sheet_name=sheet if sheet is not None else 0)
        df.attrs.update(source=name, encoding="excel", delimiter="excel")
        return df

    text, enc = _decode(raw)
    first = next((ln for ln in text.splitlines() if ln.strip()), "")
    if ext == ".data" or (not any(d in first for d in ",;\t|") and " " in first.strip()):
        # whitespace-separated, typically without a header row (e.g. secom.data)
        has_header = any(c.isalpha() for c in first.replace("NaN", "").replace("nan", "").replace("e", "").replace("E", ""))
        df = pd.read_csv(io.StringIO(text), sep=r"\s+", header=0 if has_header else None)
        if not has_header:
            df.columns = [f"col_{i + 1:03d}" for i in range(df.shape[1])]
        delim = "whitespace"
    else:
        try:
            delim = csv.Sniffer().sniff(text[:20000], delimiters=",;\t|").delimiter
        except csv.Error:
            delim = ","
        df = pd.read_csv(io.StringIO(text), sep=delim)
    df.columns = [str(c).strip() for c in df.columns]
    df.attrs.update(source=name, encoding=enc, delimiter={"\t": "tab"}.get(delim, delim))
    return df


def read_secom(data_source, labels_source) -> pd.DataFrame:
    """UCI SECOM (secom.data + secom_labels.data) -> one row per production unit (wide layout).

    secom.data: 590 whitespace-separated sensor values per row ("NaN" for missing).
    secom_labels.data: `-1 "19/07/2008 11:55:00"` (-1 = pass, 1 = fail) + timestamp.
    SECOM has no lot or wafer IDs, so wafer_id = row number and lot_id = production date.
    """
    x = pd.read_csv(io.StringIO(_decode(_bytes(data_source))[0]), sep=r"\s+", header=None)
    x.columns = [f"sensor_{i + 1:03d}" for i in range(x.shape[1])]
    lab = pd.read_csv(io.StringIO(_decode(_bytes(labels_source))[0]), sep=" ", header=None, quotechar='"')
    if len(lab) != len(x):
        raise ValueError(f"SECOM files do not match: {len(x)} data rows vs {len(lab)} label rows")
    ts = pd.to_datetime(lab[1], format="%d/%m/%Y %H:%M:%S", errors="coerce")
    out = pd.DataFrame({
        "timestamp": ts,
        "lot_id": ts.dt.strftime("%Y-%m-%d"),
        "wafer_id": [f"SECOM_{i + 1:04d}" for i in range(len(x))],
        "fail": (lab[0].astype(int) == 1).astype(int),
    })
    out = pd.concat([out, x], axis=1)
    out.attrs.update(source="SECOM", encoding="ascii", delimiter="whitespace")
    return out
