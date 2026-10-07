"""Measurement System Analysis (MSA) for metrology tools.

Before trusting any SPC chart or tool comparison, show the gauge is capable:
repeatability (static / dynamic), reproducibility (GR&R), long-term stability,
and tool-to-tool matching.
"""

from .grr import gauge_rr
from .matching import deming_regression, fleet_matching, tool_matching
from .repeatability import dynamic_repeatability, long_term_stability, static_repeatability

__all__ = [
    "gauge_rr", "static_repeatability", "dynamic_repeatability", "long_term_stability",
    "tool_matching", "fleet_matching", "deming_regression",
]
