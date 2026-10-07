"""Optics: materials, TMM and ellipsometry against analytic limits and an independent implementation."""

import numpy as np
import pytest

from metro_toolkit.metrology.thinfilm import (
    Constant, Layer, Stack, TaucLorentz, builtin_library, ellipsometry, fresnel_coefficients, reflectance,
)
from metro_toolkit.metrology.thinfilm.materials import kramers_kronig_eps1

LIB = builtin_library()
WL = np.linspace(300, 900, 61)


def test_reference_optical_constants():
    assert LIB["Si"].nk(633)[0] == pytest.approx(3.8736 + 0.01614j, abs=2e-3)  # Green 2008
    assert LIB["SiO2"].n(589.3)[0] == pytest.approx(1.4585, abs=2e-4)  # Malitson 1965 n_D
    assert LIB["Si3N4"].n(633)[0] == pytest.approx(2.039, abs=5e-3)  # Luke 2015


def test_tabulated_range_is_enforced():
    with pytest.raises(ValueError):
        LIB["Si"].nk(1500)


def test_bare_substrate_matches_fresnel():
    N = LIB["Si"].nk(WL)
    expected = np.abs((1 - N) / (1 + N)) ** 2
    assert np.allclose(reflectance(Stack([], LIB["Si"]), WL), expected, rtol=1e-12)


def test_zero_thickness_film_is_invisible():
    bare = reflectance(Stack([], LIB["Si"]), WL, 65, "p")
    film = reflectance(Stack([Layer(LIB["Si3N4"], 0.0)], LIB["Si"]), WL, 65, "p")
    assert np.allclose(bare, film, atol=1e-12)


def test_quarter_wave_antireflection():
    n1, n2, wl0 = 1.6, 2.56, 600.0
    stack = Stack([Layer(Constant(n0=n1), wl0 / (4 * n1))], Constant(n0=n2))
    expected = ((n2 - n1**2) / (n2 + n1**2)) ** 2
    assert reflectance(stack, [wl0])[0] == pytest.approx(expected, abs=1e-12)


def _abeles(N, d, wl, theta0, pol):
    """Independent 2x2 characteristic-matrix implementation (Macleod, N = n + ik)."""
    n0s = N[0] * np.sin(theta0)
    cos = [np.sqrt(1 - (n0s / n) ** 2 + 0j) for n in N]
    eta = [n * c if pol == "s" else n / c for n, c in zip(N, cos)]
    M = np.eye(2, dtype=complex)
    for j in range(1, len(N) - 1):
        delta = 2 * np.pi * N[j] * cos[j] * d[j - 1] / wl
        M = M @ np.array([[np.cos(delta), -1j * np.sin(delta) / eta[j]], [-1j * eta[j] * np.sin(delta), np.cos(delta)]])
    B, C = M @ np.array([1, eta[-1]])
    return (eta[0] * B - C) / (eta[0] * B + C)


@pytest.mark.parametrize("aoi", [0.0, 45.0, 70.0])
def test_matches_independent_characteristic_matrix(aoi):
    stack = Stack([Layer(LIB["SiO2"], 5.0), Layer(LIB["Si3N4"], 12.0), Layer(LIB["a-Si"], 20.0)], LIB["Si"])
    r_s, r_p = fresnel_coefficients(stack, WL, aoi)
    for i, wl in enumerate(WL):
        N = [1.0 + 0j] + [l.material.nk(wl)[0] for l in stack.layers] + [LIB["Si"].nk(wl)[0]]
        rs = _abeles(N, stack.thicknesses, wl, np.deg2rad(aoi), "s")
        rp = _abeles(N, stack.thicknesses, wl, np.deg2rad(aoi), "p")
        assert abs(r_s[i]) ** 2 == pytest.approx(abs(rs) ** 2, abs=1e-10)
        assert abs(r_p[i]) ** 2 == pytest.approx(abs(rp) ** 2, abs=1e-10)


def test_brewster_angle_psi_zero():
    sub = Constant(n0=1.5)
    psi, _ = ellipsometry(Stack([], sub), [500.0], np.degrees(np.arctan(1.5)))
    assert psi[0] < 1e-6


def test_delta_convention_at_normal_incidence():
    _, delta = ellipsometry(Stack([Layer(LIB["SiO2"], 50.0)], LIB["Si"]), WL, 0.0)
    assert np.allclose(delta, 180.0, atol=1e-6)


def test_lossless_film_on_lossless_substrate_conserves_energy():
    n0, n1, n2 = 1.0, 1.8, 1.5
    stack = Stack([Layer(Constant(n0=n1), 137.0)], Constant(n0=n2))
    # transmittance via characteristic matrix
    for wl in (450.0, 650.0):
        delta = 2 * np.pi * n1 * 137.0 / wl
        B = np.cos(delta) - 1j * np.sin(delta) * n2 / n1
        C = -1j * n1 * np.sin(delta) + np.cos(delta) * n2
        T = 4 * n0 * n2 / abs(n0 * B + C) ** 2
        assert reflectance(stack, [wl])[0] + T == pytest.approx(1.0, abs=1e-12)


def test_kramers_kronig_on_lorentz_oscillator():
    A, E0, G = 10.0, 3.0, 0.5

    def eps2(E):
        E = np.asarray(E)
        return A * G * E / ((E0**2 - E**2) ** 2 + G**2 * E**2)

    for E in (1.5, 2.9, 4.5):
        exact = A * (E0**2 - E**2) / ((E0**2 - E**2) ** 2 + G**2 * E**2)
        assert kramers_kronig_eps1(eps2, E, 0.0, 5000.0) == pytest.approx(exact, abs=2e-3)


def test_tauc_lorentz_physical():
    tl = TaucLorentz(A=122.0, E0=3.45, C=2.54, Eg=1.20, eps_inf=1.15)
    assert np.all(tl.eps2(np.array([0.5, 1.0, 1.19])) == 0)
    nk = tl.nk(np.array([400.0, 633.0, 1000.0]))
    assert np.all(nk.real > 1) and np.all(nk.imag >= 0)
    assert nk.imag[0] > nk.imag[-1]  # more absorbing in the blue
