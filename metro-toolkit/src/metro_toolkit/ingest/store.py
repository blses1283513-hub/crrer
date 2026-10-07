"""Save / load imported datasets and reusable mapping profiles (only on this PC, under import_dir()).

<import_dir>/
    <name>.csv            standard long table (one row per measurement)
    <name>_wafer.csv      one row per wafer (used by the SemiYield launcher)
    <name>_specs.json     spec limits carried by the export, per parameter (if any)
    profiles/<name>.yaml  column mapping + parameter table, reusable for the next export
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd
import yaml

from ..config import import_dir
from .convert import ImportSpec, spec_table, wafer_table


def safe_name(name: str) -> str:
    s = re.sub(r"[^\w\-]+", "_", str(name).strip(), flags=re.UNICODE).strip("_")
    if not s:
        raise ValueError("名稱不可空白")
    return s[:80]


def save_dataset(name: str, long_df: pd.DataFrame, folder: Path | None = None) -> dict[str, Path]:
    folder = folder or import_dir()
    n = safe_name(name)
    paths = {"long": folder / f"{n}.csv", "wafer": folder / f"{n}_wafer.csv", "specs": folder / f"{n}_specs.json"}
    long_df.to_csv(paths["long"], index=False)
    wafer_table(long_df).to_csv(paths["wafer"], index=False)
    paths["specs"].write_text(json.dumps(spec_table(long_df), ensure_ascii=False, indent=2), encoding="utf-8")
    return paths


def list_datasets(folder: Path | None = None) -> list[str]:
    folder = folder or import_dir()
    # a dataset is <name>.csv with its <name>_wafer.csv companion (answer-key files are not datasets)
    return sorted(p.stem for p in folder.glob("*.csv")
                  if not p.stem.endswith("_wafer") and (folder / f"{p.stem}_wafer.csv").exists())


def load_dataset(name: str, folder: Path | None = None) -> pd.DataFrame:
    folder = folder or import_dir()
    df = pd.read_csv(folder / f"{safe_name(name)}.csv")
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    for c in ("lot_id", "wafer_id", "parameter"):
        df[c] = df[c].astype(str)
    return df


def save_profile(name: str, spec: ImportSpec, folder: Path | None = None) -> Path:
    folder = (folder or import_dir()) / "profiles"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{safe_name(name)}.yaml"
    path.write_text(yaml.safe_dump(spec.to_dict(), allow_unicode=True, sort_keys=False), encoding="utf-8")
    return path


def list_profiles(folder: Path | None = None) -> list[str]:
    folder = (folder or import_dir()) / "profiles"
    return sorted(p.stem for p in folder.glob("*.yaml")) if folder.exists() else []


def load_profile(name: str, folder: Path | None = None) -> ImportSpec:
    folder = (folder or import_dir()) / "profiles"
    return ImportSpec.from_dict(yaml.safe_load((folder / f"{safe_name(name)}.yaml").read_text(encoding="utf-8")))
