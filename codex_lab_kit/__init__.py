"""
codex_lab_kit — Standardized validation toolkit for the Golden Codex
Robotics dual-path architecture.

Provides experiment protocols, data collection, and analysis tools for
partner labs validating perceptual-hash-based robot manipulation.
"""

__version__ = "0.1.0"

from .experiment_protocol import ExperimentProtocol, PhaseConfig
from .data_collector import DataCollector, TrialResult
from .analysis import ResultsAnalyzer
from .calibration_wizard import CalibrationWizard
