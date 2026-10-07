"""Synthetic data generators."""

from .thickness import (
    Excursion,
    ThicknessSimConfig,
    grr_study,
    matching_study,
    repeatability_study,
    simulate_thickness,
    stability_series,
)

__all__ = [
    "Excursion", "ThicknessSimConfig", "simulate_thickness", "grr_study",
    "repeatability_study", "stability_series", "matching_study",
]
