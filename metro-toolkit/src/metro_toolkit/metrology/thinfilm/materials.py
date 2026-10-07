"""Optical dispersion models for thin-film metrology.

Every material returns its complex refractive index N = n + i*k as a function
of wavelength in nanometres. Convention: k >= 0 means absorption (physics sign
convention, fields ~ exp(i(kz - wt))).

Models
------
Constant      n, k fixed (ambient, quick what-ifs)
Cauchy        n = A + B/lambda^2 + C/lambda^4 (lambda in um), optional Urbach k tail
Sellmeier     n^2 = 1 + sum B_i lambda^2 / (lambda^2 - C_i)  (lambda in um, C_i in um^2)
TaucLorentz   Jellison-Modine eps2 with eps1 from a numerical Kramers-Kronig integral
Tabulated     n, k interpolated from a CSV table (wavelength_nm, n, k)

Bundled reference data
----------------------
Si (crystalline, 300 K): M. A. Green, Sol. Energ. Mat. Sol. Cells 92, 1305 (2008),
via refractiveindex.info (CC0). Valid 250-1000 nm here.

For production work, replace the "typical" coefficients in config/films.yaml with
the material files your metrology tool's recipe actually uses.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import numpy as np
from scipy import integrate

_DATA_DIR = Path(__file__).parent / "data"
_HC_EV_NM = 1239.841984  # photon energy E[eV] = 1239.84 / lambda[nm]


class Material:
    """Base class: subclasses implement ``nk(wavelength_nm) -> complex ndarray``."""

    name: str = "material"

    def nk(self, wavelength_nm: np.ndarray) -> np.ndarray:  # pragma: no cover - abstract
        raise NotImplementedError

    def n(self, wavelength_nm) -> np.ndarray:
        return self.nk(np.atleast_1d(np.asarray(wavelength_nm, float))).real

    def k(self, wavelength_nm) -> np.ndarray:
        return self.nk(np.atleast_1d(np.asarray(wavelength_nm, float))).imag

    def with_params(self, **params) -> Material:
        """Return a copy with some model parameters replaced (used by the fitter)."""
        import copy

        new = copy.copy(self)
        for key, value in params.items():
            if not hasattr(new, key):
                raise AttributeError(f"{type(self).__name__} has no parameter '{key}'")
            setattr(new, key, value)
        return new


@dataclass
class Constant(Material):
    name: str = "constant"
    n0: float = 1.0
    k0: float = 0.0

    def nk(self, wavelength_nm):
        w = np.atleast_1d(np.asarray(wavelength_nm, float))
        return np.full(w.shape, complex(self.n0, self.k0))


@dataclass
class Cauchy(Material):
    """Cauchy dispersion with optional Urbach absorption tail.

    k = urbach_amp * exp(urbach_exp * (E - urbach_edge_ev)), E in eV.
    Leave ``urbach_amp = 0`` for a transparent dielectric.
    """

    name: str = "cauchy"
    A: float = 1.45
    B: float = 0.0
    C: float = 0.0
    urbach_amp: float = 0.0
    urbach_exp: float = 1.5
    urbach_edge_ev: float = 3.1

    def nk(self, wavelength_nm):
        w_um = np.atleast_1d(np.asarray(wavelength_nm, float)) / 1000.0
        n = self.A + self.B / w_um**2 + self.C / w_um**4
        k = np.zeros_like(n)
        if self.urbach_amp:
            energy = _HC_EV_NM / (w_um * 1000.0)
            k = self.urbach_amp * np.exp(self.urbach_exp * (energy - self.urbach_edge_ev))
        return n + 1j * k


@dataclass
class Sellmeier(Material):
    name: str = "sellmeier"
    B: tuple[float, ...] = ()
    C: tuple[float, ...] = ()  # um^2

    def nk(self, wavelength_nm):
        w2 = (np.atleast_1d(np.asarray(wavelength_nm, float)) / 1000.0) ** 2
        n2 = np.ones_like(w2)
        for b, c in zip(self.B, self.C):
            n2 += b * w2 / (w2 - c)
        return np.sqrt(n2).astype(complex)


@dataclass
class TaucLorentz(Material):
    """Tauc-Lorentz oscillator (Jellison & Modine, APL 69, 371 (1996)).

    eps2(E) = A*E0*C*(E-Eg)^2 / ((E^2-E0^2)^2 + C^2 E^2) / E   for E > Eg, else 0
    eps1(E) = eps_inf + (2/pi) P int_Eg^inf  xi*eps2(xi) / (xi^2 - E^2) dxi

    eps1 is evaluated numerically (principal value via QUADPACK's Cauchy weight),
    which avoids transcription errors in the long closed-form expression.
    """

    name: str = "tauc_lorentz"
    A: float = 100.0  # eV
    E0: float = 3.5  # eV
    C: float = 2.5  # eV
    Eg: float = 1.5  # eV
    eps_inf: float = 1.0
    _e_max: float = field(default=200.0, repr=False)

    def eps2(self, energy: np.ndarray) -> np.ndarray:
        e = np.asarray(energy, float)
        out = np.zeros_like(e)
        m = e > self.Eg
        em = e[m]
        out[m] = (
            self.A * self.E0 * self.C * (em - self.Eg) ** 2
            / ((em**2 - self.E0**2) ** 2 + self.C**2 * em**2)
            / em
        )
        return out

    def eps1(self, energy: np.ndarray) -> np.ndarray:
        return _kk_eps1(
            tuple(np.round(np.atleast_1d(energy), 9)),
            self.A, self.E0, self.C, self.Eg, self.eps_inf, self._e_max,
        )

    def nk(self, wavelength_nm):
        energy = _HC_EV_NM / np.atleast_1d(np.asarray(wavelength_nm, float))
        eps = self.eps1(energy) + 1j * self.eps2(energy)
        N = np.sqrt(eps)
        return np.where(N.imag < 0, -N, N)


@lru_cache(maxsize=256)
def _kk_eps1(energies, A, E0, C, Eg, eps_inf, e_max):
    tl = TaucLorentz(A=A, E0=E0, C=C, Eg=Eg, eps_inf=eps_inf)
    return np.array([kramers_kronig_eps1(tl.eps2, e, Eg, e_max) + eps_inf for e in energies])


def kramers_kronig_eps1(eps2_func, energy: float, e_lo: float, e_hi: float) -> float:
    """(2/pi) P int_{e_lo}^{e_hi} xi*eps2(xi)/(xi^2 - E^2) dxi  (without eps_inf)."""

    def f(xi):
        return xi * float(eps2_func(np.array([xi]))[0]) / (xi + energy)

    if e_lo < energy < e_hi:
        # P int f(xi)/(xi - E) dxi
        val, _ = integrate.quad(f, e_lo, e_hi, weight="cauchy", wvar=energy, limit=400)
    else:
        val, _ = integrate.quad(lambda xi: f(xi) / (xi - energy), e_lo, e_hi, limit=400)
    return 2.0 / np.pi * val


@dataclass
class Tabulated(Material):
    name: str = "tabulated"
    wavelength_nm: np.ndarray = field(default_factory=lambda: np.array([]))
    n_table: np.ndarray = field(default_factory=lambda: np.array([]))
    k_table: np.ndarray = field(default_factory=lambda: np.array([]))

    @classmethod
    def from_csv(cls, path: str | Path, name: str | None = None) -> Tabulated:
        data = np.genfromtxt(path, delimiter=",", names=True)
        return cls(
            name=name or Path(path).stem,
            wavelength_nm=np.asarray(data["wavelength_nm"], float),
            n_table=np.asarray(data["n"], float),
            k_table=np.asarray(data["k"], float),
        )

    def nk(self, wavelength_nm):
        w = np.atleast_1d(np.asarray(wavelength_nm, float))
        lo, hi = self.wavelength_nm.min(), self.wavelength_nm.max()
        if w.min() < lo - 1e-9 or w.max() > hi + 1e-9:
            raise ValueError(
                f"{self.name}: wavelength {w.min():.0f}-{w.max():.0f} nm outside table "
                f"range {lo:.0f}-{hi:.0f} nm"
            )
        n = np.interp(w, self.wavelength_nm, self.n_table)
        k = np.interp(w, self.wavelength_nm, self.k_table)
        return n + 1j * k


# --------------------------------------------------------------------------- #
# Built-in library                                                            #
# --------------------------------------------------------------------------- #


def builtin_library() -> dict[str, Material]:
    """Default materials. Literature-sourced where cited, otherwise 'typical'."""
    return {
        "air": Constant(name="air", n0=1.0),
        # Green 2008, crystalline Si at 300 K (tabulated, CC0 via refractiveindex.info)
        "Si": Tabulated.from_csv(_DATA_DIR / "si_green2008.csv", name="Si"),
        # Malitson 1965, fused silica (close to thermal oxide)
        "SiO2": Sellmeier(
            name="SiO2", B=(0.6961663, 0.4079426, 0.8974794), C=(0.0684043**2, 0.1162414**2, 9.896161**2)
        ),
        # Luke et al. 2015, stoichiometric LPCVD Si3N4
        "Si3N4": Sellmeier(name="Si3N4", B=(3.0249, 40314.0), C=(0.1353406**2, 1239.842**2)),
        # Typical ALD films - REPLACE with your recipe's fitted values
        "Al2O3": Cauchy(name="Al2O3", A=1.632, B=0.0058),
        "HfO2": Cauchy(name="HfO2", A=1.920, B=0.0125),
        "ZrO2": Cauchy(name="ZrO2", A=2.060, B=0.0160),
        # Amorphous Si, Jellison-Modine 1996 typical parameters
        "a-Si": TaucLorentz(name="a-Si", A=122.0, E0=3.45, C=2.54, Eg=1.20, eps_inf=1.15),
    }


def material_from_dict(name: str, spec: dict, base_dir: Path | None = None) -> Material:
    """Build a material from a config entry, e.g. ``{model: cauchy, A: 1.46, B: 0.004}``."""
    spec = dict(spec)
    model = spec.pop("model").lower()
    if model == "constant":
        return Constant(name=name, n0=spec.get("n", 1.0), k0=spec.get("k", 0.0))
    if model == "cauchy":
        return Cauchy(name=name, **spec)
    if model == "sellmeier":
        return Sellmeier(name=name, B=tuple(spec["B"]), C=tuple(spec["C"]))
    if model in ("tauc_lorentz", "tl"):
        return TaucLorentz(name=name, **spec)
    if model in ("tabulated", "table", "csv"):
        path = Path(spec["file"])
        if not path.is_absolute():
            candidates = [(base_dir or Path.cwd()) / path, _DATA_DIR / path]
            path = next((c for c in candidates if c.exists()), candidates[0])
        return Tabulated.from_csv(path, name=name)
    raise ValueError(f"Unknown material model '{model}' for '{name}'")
