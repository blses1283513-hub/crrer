"""Statistical analysis: SPC, capability."""

from .spc import control_chart, process_capability, spc_by_group, wafer_summary, western_electric

__all__ = ["control_chart", "process_capability", "spc_by_group", "wafer_summary", "western_electric"]
