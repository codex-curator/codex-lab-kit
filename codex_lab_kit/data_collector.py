"""
data_collector.py — Structured data collection for validation experiments.

Records per-trial metrics and serializes them for analysis. Can operate
as a standalone collector or as a ROS2 node subscriber.
"""

from __future__ import annotations

import csv
import json
import logging
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class TrialResult:
    """A single trial measurement."""

    # Identification
    phase_id: str
    trial_index: int
    object_id: str
    timestamp: float = field(default_factory=time.time)

    # Hash metrics
    query_dhash: str = ""
    matched_dhash: str = ""
    match_type: str = ""          # EXACT | FUZZY | MISS
    hamming_distance: int = -1

    # Timing (ms)
    image_capture_ms: float = 0.0
    hash_computation_ms: float = 0.0
    registry_lookup_ms: float = 0.0
    total_perception_ms: float = 0.0
    llm_generation_ms: float = 0.0
    motion_planning_ms: float = 0.0

    # Manipulation outcome
    grasp_success: Optional[bool] = None
    force_actual_N: float = 0.0
    force_planned_N: float = 0.0
    execution_time_ms: float = 0.0
    post_action_hash_shift: int = -1

    # Loop closure
    promoted: bool = False
    llm_calls_cumulative: int = 0

    # Context
    lighting_condition: str = ""
    viewpoint_index: int = -1
    notes: str = ""


class DataCollector:
    """Collects, stores, and exports trial results.

    Parameters
    ----------
    output_dir : str
        Directory for result files.
    lab_name : str
        Identifier for this lab's data.
    auto_flush : int
        Write to disk every N trials (0 = manual only).
    """

    def __init__(
        self,
        output_dir: str = "./codex_validation_results",
        lab_name: str = "unnamed_lab",
        auto_flush: int = 50,
    ) -> None:
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._lab_name = lab_name
        self._auto_flush = auto_flush
        self._trials: List[TrialResult] = []
        self._flush_count = 0
        logger.info("DataCollector initialized: %s → %s", lab_name, output_dir)

    def record(self, result: TrialResult = None, **kwargs: Any) -> TrialResult:
        """Record a single trial result.

        Can be called with a TrialResult object or with keyword arguments
        that will be used to construct one.
        """
        if result is None:
            result = TrialResult(**kwargs)
        self._trials.append(result)
        logger.debug(
            "Recorded trial %s/%d/%s: %s (hamming=%d)",
            result.phase_id, result.trial_index, result.object_id,
            result.match_type, result.hamming_distance,
        )
        if self._auto_flush > 0 and len(self._trials) % self._auto_flush == 0:
            self.flush()
        return result

    def record_from_lookup(
        self,
        phase_id: str,
        trial_index: int,
        object_id: str,
        lookup_result: Any,
        **kwargs: Any,
    ) -> TrialResult:
        """Convenience: create TrialResult from a LookupResult + extras."""
        result = TrialResult(
            phase_id=phase_id,
            trial_index=trial_index,
            object_id=object_id,
            query_dhash=getattr(lookup_result, "query_hash", ""),
            matched_dhash=getattr(lookup_result, "matched_hash", "") or "",
            match_type=getattr(lookup_result, "match_type", ""),
            hamming_distance=getattr(lookup_result, "hamming_distance", -1),
            registry_lookup_ms=getattr(lookup_result, "lookup_time_ms", 0.0),
            **kwargs,
        )
        self.record(result)
        return result

    def get_trials(self, phase_id: Optional[str] = None) -> List[TrialResult]:
        """Return recorded trials, optionally filtered by phase."""
        if phase_id is None:
            return list(self._trials)
        return [t for t in self._trials if t.phase_id == phase_id]

    def flush(self) -> str:
        """Write all trials to a JSON file. Returns filepath."""
        self._flush_count += 1
        filepath = self._output_dir / f"trials_{self._lab_name}_{self._flush_count:04d}.json"

        data = {
            "lab_name": self._lab_name,
            "flush_index": self._flush_count,
            "trial_count": len(self._trials),
            "trials": [asdict(t) for t in self._trials],
        }

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

        logger.info("Flushed %d trials to %s", len(self._trials), filepath)
        return str(filepath)

    def export_csv(self, filepath: Optional[str] = None) -> str:
        """Export all trials as CSV for analysis in R/pandas."""
        if filepath is None:
            filepath = str(self._output_dir / f"trials_{self._lab_name}.csv")

        if not self._trials:
            logger.warning("No trials to export.")
            return filepath

        fields = list(asdict(self._trials[0]).keys())
        with open(filepath, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            for trial in self._trials:
                writer.writerow(asdict(trial))

        logger.info("Exported %d trials to CSV: %s", len(self._trials), filepath)
        return filepath

    def summary(self) -> Dict[str, Any]:
        """Return aggregate summary statistics."""
        if not self._trials:
            return {"total_trials": 0}

        phases = set(t.phase_id for t in self._trials)
        objects = set(t.object_id for t in self._trials)
        by_phase = {}
        for p in sorted(phases):
            phase_trials = [t for t in self._trials if t.phase_id == p]
            exact = sum(1 for t in phase_trials if t.match_type == "EXACT")
            fuzzy = sum(1 for t in phase_trials if t.match_type == "FUZZY")
            miss = sum(1 for t in phase_trials if t.match_type == "MISS")
            grasps = [t for t in phase_trials if t.grasp_success is not None]
            successes = sum(1 for t in grasps if t.grasp_success)

            by_phase[p] = {
                "trial_count": len(phase_trials),
                "exact_hits": exact,
                "fuzzy_hits": fuzzy,
                "misses": miss,
                "grasp_trials": len(grasps),
                "grasp_successes": successes,
                "grasp_success_rate": successes / len(grasps) if grasps else None,
            }

        return {
            "lab_name": self._lab_name,
            "total_trials": len(self._trials),
            "unique_objects": len(objects),
            "phases": by_phase,
        }
