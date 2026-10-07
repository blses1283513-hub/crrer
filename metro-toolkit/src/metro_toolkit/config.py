"""Configuration loading. Nothing site-specific is hard-coded in the analysis code.

Environment variables (keep real data and recipes outside the repository):
    METRO_CONFIG_PATH   directory holding films.yaml / sampling.yaml / limits.yaml
    METRO_DATA_PATH     directory with measurement CSVs (default: data/sample)
    METRO_REPORT_PATH   output directory for generated reports (default: reports)
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[2]


def config_dir() -> Path:
    return Path(os.environ.get("METRO_CONFIG_PATH", ROOT / "config"))


def data_dir() -> Path:
    return Path(os.environ.get("METRO_DATA_PATH", ROOT / "data" / "sample"))


def report_dir() -> Path:
    path = Path(os.environ.get("METRO_REPORT_PATH", ROOT / "reports"))
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_yaml(name: str) -> dict:
    with open(config_dir() / name, encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def wavelengths(films_cfg: dict | None = None) -> np.ndarray:
    cfg = (films_cfg or load_yaml("films.yaml")).get("wavelength_nm", {})
    return np.linspace(cfg.get("start", 250), cfg.get("stop", 1000), cfg.get("points", 301))


def material_library(films_cfg: dict | None = None) -> dict:
    from .metrology.thinfilm.materials import builtin_library, material_from_dict

    cfg = films_cfg or load_yaml("films.yaml")
    lib = builtin_library()
    for name, spec in (cfg.get("materials") or {}).items():
        lib[name] = material_from_dict(name, spec, base_dir=config_dir())
    return lib


def load_stack(name: str, films_cfg: dict | None = None):
    """Return (Stack, recipe dict) for a stack defined in films.yaml."""
    from .metrology.thinfilm import FitParameter, Layer, Stack

    cfg = films_cfg or load_yaml("films.yaml")
    lib = material_library(cfg)
    spec = cfg["stacks"][name]
    layers = [Layer(lib[l["material"]], float(l["thickness_nm"])) for l in spec["layers"]]
    stack = Stack(layers=layers, substrate=lib[spec["substrate"]], ambient=lib.get(spec.get("ambient", "air")), name=name)
    recipe = dict(spec)
    recipe["fit_params"] = [FitParameter(layer=f["layer"], bounds=tuple(f["bounds"])) for f in spec.get("fit", [])]
    return stack, recipe
