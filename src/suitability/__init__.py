"""A reference implementation of a MiFID II client risk-profiling and
suitability-mapping framework.

Public surface:

    from suitability import load_config, assess, ClientCase, render_report
"""

from .config import Config, ConfigError, load_config
from .engine import assess
from .models import ClientCase, ControlHit, DimensionResult, Outcome, Recommendation
from .report import render as render_report

__version__ = "1.0.0"

__all__ = [
    "Config",
    "ConfigError",
    "load_config",
    "assess",
    "ClientCase",
    "ControlHit",
    "DimensionResult",
    "Outcome",
    "Recommendation",
    "render_report",
]
