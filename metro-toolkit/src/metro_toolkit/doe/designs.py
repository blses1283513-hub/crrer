"""Experimental designs in coded units (-1 = low, +1 = high, 0 = centre).

full_factorial      2^k or 3^k
fractional          2^(k-p) from generators such as "D=ABC"; reports aliases and resolution
central_composite   factorial + axial (face-centred alpha=1, or rotatable alpha=(2^k)^(1/4)) + centre
box_behnken         all pairs of factors at +-1, others at 0, + centre (3-5 factors; never uses corners)
run_sheet           coded -> real settings, replicates, randomised run order
"""

from __future__ import annotations

import itertools
import string

import numpy as np
import pandas as pd

LETTERS = string.ascii_uppercase
DEFAULT_GENERATORS = {3: ["C=AB"], 4: ["D=ABC"], 5: ["E=ABCD"], 6: ["E=ABC", "F=BCD"], 7: ["E=ABC", "F=BCD", "G=ACD"]}


def full_factorial(k: int, levels: int = 2) -> np.ndarray:
    vals = [-1.0, 1.0] if levels == 2 else [-1.0, 0.0, 1.0]
    return np.array(list(itertools.product(vals, repeat=k)))[:, ::-1]  # standard (Yates) order: A changes fastest


def _word_product(a: str, b: str) -> str:
    return "".join(sorted(set(a) ^ set(b)))


def defining_relation(generators: list[str]) -> list[str]:
    """All words of the defining relation I = ... (e.g. D=ABC -> ABCD)."""
    base = ["".join(sorted(g.split("=")[0].strip() + g.split("=")[1].strip())) for g in generators]
    words = set()
    for r in range(1, len(base) + 1):
        for combo in itertools.combinations(base, r):
            w = ""
            for c in combo:
                w = _word_product(w, c)
            words.add(w)
    return sorted(words, key=lambda w: (len(w), w))


def fractional(k: int, generators: list[str] | None = None) -> tuple[np.ndarray, dict]:
    """2^(k-p) fractional factorial. Returns (design, info) with resolution and main-effect / 2FI aliases."""
    generators = generators or DEFAULT_GENERATORS.get(k)
    if not generators:
        return full_factorial(k), {"resolution": None, "aliases": {}, "generators": []}
    p = len(generators)
    base = full_factorial(k - p)
    cols = {LETTERS[i]: base[:, i] for i in range(k - p)}
    for g in generators:
        new, expr = (s.strip() for s in g.split("="))
        cols[new] = np.prod([cols[c] for c in expr], axis=0)
    design = np.column_stack([cols[LETTERS[i]] for i in range(k)])
    words = defining_relation(generators)
    effects = list(LETTERS[:k]) + ["".join(c) for c in itertools.combinations(LETTERS[:k], 2)]
    aliases = {}
    for e in effects:
        al = sorted({_word_product(e, w) for w in words if len(_word_product(e, w)) <= 2} - {e})
        if al:
            aliases[e] = al
    return design, {"resolution": min(len(w) for w in words), "aliases": aliases, "generators": generators,
                    "defining_relation": "I = " + " = ".join(words)}


def central_composite(k: int, alpha: str | float = "face", center: int = 4) -> np.ndarray:
    fact = full_factorial(k) if k <= 4 else fractional(k)[0]
    a = 1.0 if alpha == "face" else (len(fact) ** 0.25 if alpha == "rotatable" else float(alpha))
    axial = np.zeros((2 * k, k))
    for i in range(k):
        axial[2 * i, i], axial[2 * i + 1, i] = -a, a
    return np.vstack([fact, axial, np.zeros((center, k))])


def box_behnken(k: int, center: int = 3) -> np.ndarray:
    if not 3 <= k <= 5:
        raise ValueError("Box-Behnken needs 3-5 factors")
    rows = []
    for i, j in itertools.combinations(range(k), 2):
        for a, b in itertools.product([-1.0, 1.0], repeat=2):
            r = np.zeros(k)
            r[i], r[j] = a, b
            rows.append(r)
    return np.vstack([np.array(rows), np.zeros((center, k))])


def add_center(design: np.ndarray, n: int) -> np.ndarray:
    return np.vstack([design, np.zeros((n, design.shape[1]))]) if n else design


def make_design(kind: str, k: int, center: int = 3, alpha: str = "face", generators=None) -> tuple[np.ndarray, dict]:
    """One entry point for the dashboard. kind: full2, full3, fractional, ccd, bbd."""
    info: dict = {}
    if kind == "full2":
        d = add_center(full_factorial(k, 2), center)
    elif kind == "full3":
        d = full_factorial(k, 3)
    elif kind == "fractional":
        d, info = fractional(k, generators)
        d = add_center(d, center)
    elif kind == "ccd":
        d = central_composite(k, alpha, center)
    elif kind == "bbd":
        d = box_behnken(k, center)
    else:
        raise ValueError(f"unknown design {kind}")
    return d, info


def to_real(coded: np.ndarray, factors: dict) -> np.ndarray:
    """factors: {name: {low, high}} in the same order as the coded columns."""
    lo = np.array([f["low"] for f in factors.values()], float)
    hi = np.array([f["high"] for f in factors.values()], float)
    return (lo + hi) / 2 + coded * (hi - lo) / 2


def to_coded(real: np.ndarray, factors: dict) -> np.ndarray:
    lo = np.array([f["low"] for f in factors.values()], float)
    hi = np.array([f["high"] for f in factors.values()], float)
    return (np.asarray(real, float) - (lo + hi) / 2) / ((hi - lo) / 2)


def run_sheet(coded: np.ndarray, factors: dict, replicates: int = 1, seed: int = 1) -> pd.DataFrame:
    """Run sheet with standard order, randomised run order, real settings (and coded, for the analysis)."""
    coded = np.vstack([coded] * replicates)
    real = to_real(coded, factors)
    names = list(factors)
    df = pd.DataFrame(real, columns=names)
    for i, n in enumerate(names):
        df[f"{n}__coded"] = coded[:, i]
    df.insert(0, "std_order", np.arange(1, len(df) + 1))
    order = np.random.default_rng(seed).permutation(len(df)) + 1
    df.insert(0, "run_order", order)
    df["point"] = np.where((coded == 0).all(axis=1), "center",
                           np.where((np.abs(coded) == 1).all(axis=1), "corner", "axial/edge"))
    return df.sort_values("run_order").reset_index(drop=True)
