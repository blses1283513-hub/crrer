"""Thin-film optics: Fresnel coefficients for an arbitrary planar stack.

Geometry (top to bottom)::

    ambient (semi-infinite, usually air)
    layer 1   thickness d1        <- top film, what the light sees first
    layer 2   thickness d2
    ...
    substrate (semi-infinite, usually Si)

Method: recursive Airy summation from the substrate upward, vectorised over
wavelength. Mathematically identical to the 2x2 characteristic-matrix (Abeles)
method for isotropic layers, but easier to read.

Ellipsometry convention (Azzam & Bashara / "Nebraska" convention):
    rho = r_p / r_s = tan(Psi) * exp(i*Delta)
With this sign choice Delta = 180 deg at normal incidence, and for a bare
transparent substrate Psi -> 0 at the Brewster angle.
Psi in [0, 90] deg, Delta reported in [0, 360) deg.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .materials import Material


@dataclass
class Layer:
    material: Material
    thickness_nm: float
    name: str = ""

    def __post_init__(self):
        if not self.name:
            self.name = self.material.name


@dataclass
class Stack:
    """A planar film stack. ``layers`` are listed top (ambient side) to bottom."""

    layers: list[Layer]
    substrate: Material
    ambient: Material = field(default=None)  # type: ignore[assignment]
    name: str = "stack"

    def __post_init__(self):
        if self.ambient is None:
            from .materials import Constant

            self.ambient = Constant(name="air", n0=1.0)

    @property
    def thicknesses(self) -> np.ndarray:
        return np.array([layer.thickness_nm for layer in self.layers], float)

    def total_thickness(self) -> float:
        return float(self.thicknesses.sum())

    def describe(self) -> str:
        films = " / ".join(f"{l.name} {l.thickness_nm:.2f} nm" for l in self.layers)
        return f"{self.ambient.name} | {films} | {self.substrate.name}"

    def copy_with(self, thicknesses=None, materials=None) -> Stack:
        new_layers = []
        for i, layer in enumerate(self.layers):
            t = layer.thickness_nm if thicknesses is None else float(thicknesses[i])
            m = layer.material if materials is None or materials[i] is None else materials[i]
            new_layers.append(Layer(material=m, thickness_nm=t, name=layer.name))
        return Stack(layers=new_layers, substrate=self.substrate, ambient=self.ambient, name=self.name)


def _cos_theta(N: np.ndarray, n0_sin0: np.ndarray) -> np.ndarray:
    """cos(theta_j) from Snell's law, choosing the physical (decaying) branch."""
    cos_t = np.sqrt(1.0 - (n0_sin0 / N) ** 2 + 0j)
    # N*cos(theta) must have Im >= 0 (decay into the medium) and Re >= 0 (forward)
    Ncos = N * cos_t
    flip = (Ncos.imag < 0) | ((np.abs(Ncos.imag) < 1e-14) & (Ncos.real < 0))
    return np.where(flip, -cos_t, cos_t)


def fresnel_coefficients(
    stack: Stack, wavelength_nm, aoi_deg: float = 0.0
) -> tuple[np.ndarray, np.ndarray]:
    """Return complex (r_s, r_p) of the whole stack at each wavelength."""
    wl = np.atleast_1d(np.asarray(wavelength_nm, float))
    theta0 = np.deg2rad(aoi_deg)

    media = [stack.ambient] + [l.material for l in stack.layers] + [stack.substrate]
    N = [m.nk(wl).astype(complex) for m in media]
    n0_sin0 = N[0] * np.sin(theta0)
    cos = [_cos_theta(Nj, n0_sin0) for Nj in N]

    def r_interface(i, j):
        a_s, b_s = N[i] * cos[i], N[j] * cos[j]
        a_p, b_p = N[j] * cos[i], N[i] * cos[j]
        return (a_s - b_s) / (a_s + b_s), (a_p - b_p) / (a_p + b_p)

    # start at the bottom interface (last film / substrate)
    last = len(media) - 1
    r_s, r_p = r_interface(last - 1, last)
    for j in range(last - 1, 0, -1):  # film j sits between media j-1 and j+1
        beta = 2.0 * np.pi * stack.layers[j - 1].thickness_nm * N[j] * cos[j] / wl
        phase = np.exp(2j * beta)
        rs_top, rp_top = r_interface(j - 1, j)
        r_s = (rs_top + r_s * phase) / (1.0 + rs_top * r_s * phase)
        r_p = (rp_top + r_p * phase) / (1.0 + rp_top * r_p * phase)
    return r_s, r_p


def reflectance(stack: Stack, wavelength_nm, aoi_deg: float = 0.0, polarization: str = "u"):
    """Reflectance (0-1). polarization: 's', 'p' or 'u' (unpolarised average)."""
    r_s, r_p = fresnel_coefficients(stack, wavelength_nm, aoi_deg)
    R_s, R_p = np.abs(r_s) ** 2, np.abs(r_p) ** 2
    return {"s": R_s, "p": R_p, "u": 0.5 * (R_s + R_p)}[polarization]


def ellipsometry(stack: Stack, wavelength_nm, aoi_deg: float = 70.0):
    """Return (Psi_deg, Delta_deg) with rho = r_p / r_s = tan(Psi) exp(i Delta)."""
    r_s, r_p = fresnel_coefficients(stack, wavelength_nm, aoi_deg)
    rho = r_p / r_s
    psi = np.degrees(np.arctan(np.abs(rho)))
    delta = np.degrees(np.angle(rho)) % 360.0
    return psi, delta


def ncs(psi_deg, delta_deg):
    """Ellipsometric N, C, S = cos2Psi, sin2Psi cosDelta, sin2Psi sinDelta.

    Fitting in N/C/S space avoids the 0/360 deg wrap of Delta and weights the
    data the way a rotating-compensator ellipsometer actually measures it.
    """
    psi, delta = np.deg2rad(psi_deg), np.deg2rad(delta_deg)
    return np.cos(2 * psi), np.sin(2 * psi) * np.cos(delta), np.sin(2 * psi) * np.sin(delta)
