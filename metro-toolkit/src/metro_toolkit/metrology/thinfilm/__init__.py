"""Thin-film optical metrology: dispersion models, TMM/ellipsometry, model fitting."""

from .fitting import FitParameter, FitResult, Measurement, fit, fit_thickness, simulate_reflectometry, simulate_se
from .materials import Cauchy, Constant, Sellmeier, Tabulated, TaucLorentz, builtin_library, material_from_dict
from .pipeline import fit_sites, simulate_site_spectra
from .tmm import Layer, Stack, ellipsometry, fresnel_coefficients, ncs, reflectance

__all__ = [
    "Cauchy", "Constant", "Sellmeier", "Tabulated", "TaucLorentz", "builtin_library", "material_from_dict",
    "Layer", "Stack", "ellipsometry", "fresnel_coefficients", "ncs", "reflectance",
    "fit_sites", "simulate_site_spectra",
    "FitParameter", "FitResult", "Measurement", "fit", "fit_thickness", "simulate_reflectometry", "simulate_se",
]
