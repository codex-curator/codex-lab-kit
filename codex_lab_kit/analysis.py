"""
analysis.py — Statistical analysis and visualization of validation results.

Computes hash robustness metrics, grasp correlation curves, loop closure
convergence, and latency profiles from collected trial data.
"""

from __future__ import annotations

import csv
import json
import logging
import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from .data_collector import TrialResult

logger = logging.getLogger(__name__)


@dataclass
class HashRobustnessReport:
    """Results from Phase A analysis."""
    intra_class_hamming_mean: float
    intra_class_hamming_std: float
    inter_class_hamming_mean: float
    inter_class_hamming_std: float
    recall_at_threshold: Dict[int, float]  # threshold → recall
    fpr_at_threshold: Dict[int, float]     # threshold → false positive rate
    per_object: Dict[str, Dict[str, float]]


@dataclass
class GraspCorrelationReport:
    """Results from Phase B analysis."""
    overall_success_rate: float
    success_by_hamming_band: Dict[str, float]  # "0-2" → rate, "3-5" → rate, etc.
    success_by_match_type: Dict[str, float]    # EXACT → rate, FUZZY → rate
    mean_force_deviation_N: float
    per_object: Dict[str, Dict[str, float]]


@dataclass
class ConvergenceReport:
    """Results from Phase C analysis."""
    per_object_trials_to_first_success: Dict[str, int]
    per_object_trials_to_90pct: Dict[str, Optional[int]]
    total_llm_calls: int
    total_hash_lookups: int
    convergence_curves: Dict[str, List[float]]  # object → rolling success rates


@dataclass
class LatencyReport:
    """Results from Phase D analysis."""
    component_p50_ms: Dict[str, float]
    component_p99_ms: Dict[str, float]
    total_fast_path_p50_ms: float
    total_fast_path_p99_ms: float


def _percentile(values: List[float], pct: float) -> float:
    """Simple percentile calculation without numpy dependency."""
    if not values:
        return 0.0
    sorted_v = sorted(values)
    idx = (pct / 100.0) * (len(sorted_v) - 1)
    lo = int(math.floor(idx))
    hi = int(math.ceil(idx))
    if lo == hi:
        return sorted_v[lo]
    frac = idx - lo
    return sorted_v[lo] * (1 - frac) + sorted_v[hi] * frac


def _mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _std(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0
    m = _mean(values)
    return math.sqrt(sum((x - m) ** 2 for x in values) / (len(values) - 1))


class ResultsAnalyzer:
    """Analyzes collected trial data and generates reports.

    Parameters
    ----------
    trials_or_path : list of TrialResult, or str/Path
        Collected trial data, or path to a CSV file exported by DataCollector.
    """

    def __init__(self, trials_or_path: Union[List[TrialResult], str, Path]) -> None:
        if isinstance(trials_or_path, (str, Path)):
            self._trials = self._load_csv(str(trials_or_path))
        else:
            self._trials = trials_or_path

    @staticmethod
    def _load_csv(filepath: str) -> List[TrialResult]:
        """Load trials from a CSV file exported by DataCollector."""
        trials = []
        with open(filepath, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                kwargs = {}
                for k, v in row.items():
                    if k not in TrialResult.__dataclass_fields__:
                        continue
                    if v == "" or v is None:
                        kwargs[k] = v if isinstance(v, str) else ""
                    elif k in ("trial_index", "hamming_distance", "post_action_hash_shift",
                               "llm_calls_cumulative", "viewpoint_index"):
                        kwargs[k] = int(v)
                    elif k in ("timestamp", "image_capture_ms", "hash_computation_ms",
                               "registry_lookup_ms", "total_perception_ms", "llm_generation_ms",
                               "motion_planning_ms", "force_actual_N", "force_planned_N",
                               "execution_time_ms"):
                        kwargs[k] = float(v)
                    elif k == "grasp_success":
                        kwargs[k] = v.lower() in ("true", "1", "yes") if v else None
                    elif k == "promoted":
                        kwargs[k] = v.lower() in ("true", "1", "yes")
                    else:
                        kwargs[k] = v
                trials.append(TrialResult(**kwargs))
        return trials

    @classmethod
    def from_json(cls, filepath: str) -> "ResultsAnalyzer":
        """Load trials from a JSON file exported by DataCollector."""
        with open(filepath) as f:
            data = json.load(f)

        trials = []
        for t in data.get("trials", []):
            trials.append(TrialResult(**{
                k: v for k, v in t.items()
                if k in TrialResult.__dataclass_fields__
            }))
        return cls(trials)

    @classmethod
    def from_directory(cls, dirpath: str) -> "ResultsAnalyzer":
        """Load and merge all trial JSON files in a directory."""
        all_trials = []
        for path in sorted(Path(dirpath).glob("trials_*.json")):
            with open(path) as f:
                data = json.load(f)
            for t in data.get("trials", []):
                all_trials.append(TrialResult(**{
                    k: v for k, v in t.items()
                    if k in TrialResult.__dataclass_fields__
                }))
        logger.info("Loaded %d trials from %s", len(all_trials), dirpath)
        return cls(all_trials)

    def analyze_hash_robustness(self) -> dict:
        """Analyze Phase A: hash robustness across viewpoints and lighting."""
        phase_a = [t for t in self._trials if t.phase_id == "A"]
        if not phase_a:
            raise ValueError("No Phase A trials found.")

        # Group by object for intra-class distances
        by_object: Dict[str, List[str]] = defaultdict(list)
        for t in phase_a:
            if t.query_dhash:
                by_object[t.object_id].append(t.query_dhash)

        intra_distances = []
        per_object = {}
        for obj_id, hashes in by_object.items():
            obj_dists = []
            for i in range(len(hashes)):
                for j in range(i + 1, len(hashes)):
                    d = _hamming(hashes[i], hashes[j])
                    obj_dists.append(d)
                    intra_distances.append(d)
            per_object[obj_id] = {
                "hamming_mean": _mean(obj_dists),
                "hamming_std": _std(obj_dists),
                "image_count": len(hashes),
            }

        # Inter-class: pick one representative hash per object
        obj_ids = list(by_object.keys())
        inter_distances = []
        for i in range(len(obj_ids)):
            for j in range(i + 1, len(obj_ids)):
                h1 = by_object[obj_ids[i]][0]
                h2 = by_object[obj_ids[j]][0]
                inter_distances.append(_hamming(h1, h2))

        # ROC at various thresholds
        recall = {}
        fpr = {}
        for threshold in range(0, 20):
            tp = sum(1 for d in intra_distances if d <= threshold)
            fn = sum(1 for d in intra_distances if d > threshold)
            fp = sum(1 for d in inter_distances if d <= threshold)
            tn = sum(1 for d in inter_distances if d > threshold)
            recall[threshold] = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            fpr[threshold] = fp / (fp + tn) if (fp + tn) > 0 else 0.0

        # Compute simple overall metrics for convenience
        hamming_values = [t.hamming_distance for t in phase_a if t.hamming_distance >= 0]
        exact_count = sum(1 for t in phase_a if t.match_type == "EXACT")

        return {
            "overall_hamming_mean": _mean([float(v) for v in hamming_values]) if hamming_values else 0.0,
            "exact_match_rate": exact_count / len(phase_a) if phase_a else 0.0,
            "intra_class_hamming_mean": _mean(intra_distances),
            "intra_class_hamming_std": _std(intra_distances),
            "inter_class_hamming_mean": _mean(inter_distances),
            "inter_class_hamming_std": _std(inter_distances),
            "recall_at_threshold": recall,
            "fpr_at_threshold": fpr,
            "per_object": per_object,
        }

    def analyze_grasp_correlation(self) -> GraspCorrelationReport:
        """Analyze Phase B: hash distance vs. grasp success."""
        phase_b = [t for t in self._trials if t.phase_id == "B" and t.grasp_success is not None]
        if not phase_b:
            raise ValueError("No Phase B trials with grasp outcomes found.")

        total_success = sum(1 for t in phase_b if t.grasp_success)
        overall_rate = total_success / len(phase_b)

        # By Hamming band
        bands = {"0-2": [], "3-5": [], "6-8": [], "9+": []}
        for t in phase_b:
            d = t.hamming_distance
            if d <= 2:
                bands["0-2"].append(t.grasp_success)
            elif d <= 5:
                bands["3-5"].append(t.grasp_success)
            elif d <= 8:
                bands["6-8"].append(t.grasp_success)
            else:
                bands["9+"].append(t.grasp_success)

        success_by_band = {
            k: (sum(v) / len(v) if v else 0.0) for k, v in bands.items()
        }

        # By match type
        by_type: Dict[str, List[bool]] = defaultdict(list)
        for t in phase_b:
            by_type[t.match_type].append(t.grasp_success)
        success_by_type = {
            k: (sum(v) / len(v) if v else 0.0) for k, v in by_type.items()
        }

        # Force deviation
        force_devs = [
            abs(t.force_actual_N - t.force_planned_N)
            for t in phase_b
            if t.force_actual_N > 0 and t.force_planned_N > 0
        ]

        # Per object
        by_obj: Dict[str, List[bool]] = defaultdict(list)
        for t in phase_b:
            by_obj[t.object_id].append(t.grasp_success)
        per_object = {
            k: {"success_rate": sum(v) / len(v), "trials": len(v)}
            for k, v in by_obj.items()
        }

        return GraspCorrelationReport(
            overall_success_rate=overall_rate,
            success_by_hamming_band=success_by_band,
            success_by_match_type=success_by_type,
            mean_force_deviation_N=_mean(force_devs),
            per_object=per_object,
        )

    def analyze_convergence(self) -> ConvergenceReport:
        """Analyze Phase C: loop closure convergence dynamics."""
        phase_c = [t for t in self._trials if t.phase_id == "C"]
        if not phase_c:
            raise ValueError("No Phase C trials found.")

        by_obj: Dict[str, List[TrialResult]] = defaultdict(list)
        for t in sorted(phase_c, key=lambda x: x.trial_index):
            by_obj[t.object_id].append(t)

        first_success = {}
        to_90pct = {}
        curves = {}
        total_llm = 0
        total_hash = 0

        for obj_id, trials in by_obj.items():
            first_success[obj_id] = -1
            to_90pct[obj_id] = None

            successes = []
            rolling = []
            for i, t in enumerate(trials):
                s = t.grasp_success if t.grasp_success is not None else (t.match_type != "MISS")
                successes.append(s)

                if s and first_success[obj_id] == -1:
                    first_success[obj_id] = i + 1

                # Rolling success rate (window of 10)
                window = successes[max(0, i - 9):]
                rate = sum(window) / len(window)
                rolling.append(rate)

                if rate >= 0.9 and to_90pct[obj_id] is None:
                    to_90pct[obj_id] = i + 1

                if t.match_type == "MISS":
                    total_llm += 1
                else:
                    total_hash += 1

            curves[obj_id] = rolling

        return ConvergenceReport(
            per_object_trials_to_first_success=first_success,
            per_object_trials_to_90pct=to_90pct,
            total_llm_calls=total_llm,
            total_hash_lookups=total_hash,
            convergence_curves=curves,
        )

    def analyze_latency(self) -> LatencyReport:
        """Analyze Phase D: latency profiling."""
        phase_d = [t for t in self._trials if t.phase_id == "D"]
        if not phase_d:
            raise ValueError("No Phase D trials found.")

        components = {
            "image_capture": [t.image_capture_ms for t in phase_d if t.image_capture_ms > 0],
            "hash_computation": [t.hash_computation_ms for t in phase_d if t.hash_computation_ms > 0],
            "registry_lookup": [t.registry_lookup_ms for t in phase_d if t.registry_lookup_ms > 0],
            "total_perception": [t.total_perception_ms for t in phase_d if t.total_perception_ms > 0],
            "motion_planning": [t.motion_planning_ms for t in phase_d if t.motion_planning_ms > 0],
        }

        p50 = {k: _percentile(v, 50) for k, v in components.items()}
        p99 = {k: _percentile(v, 99) for k, v in components.items()}

        fast_path_total = [
            t.image_capture_ms + t.hash_computation_ms + t.registry_lookup_ms
            for t in phase_d
            if t.match_type in ("EXACT", "FUZZY")
        ]

        return LatencyReport(
            component_p50_ms=p50,
            component_p99_ms=p99,
            total_fast_path_p50_ms=_percentile(fast_path_total, 50),
            total_fast_path_p99_ms=_percentile(fast_path_total, 99),
        )

    def export_report(self, filepath: str = "validation_report.json") -> dict:
        """Export all available analysis reports to a single JSON file."""
        report: Dict[str, Any] = {"framework": "Golden Codex Lab Kit v1.0"}

        phases_present = set(t.phase_id for t in self._trials)

        if "A" in phases_present:
            r = self.analyze_hash_robustness()
            report["phase_a_hash_robustness"] = {
                "overall_hamming_mean": r["overall_hamming_mean"],
                "exact_match_rate": r["exact_match_rate"],
                "intra_class_hamming_mean": r["intra_class_hamming_mean"],
                "intra_class_hamming_std": r["intra_class_hamming_std"],
                "inter_class_hamming_mean": r["inter_class_hamming_mean"],
                "inter_class_hamming_std": r["inter_class_hamming_std"],
                "recall_at_threshold_5": r["recall_at_threshold"].get(5, 0.0),
                "fpr_at_threshold_5": r["fpr_at_threshold"].get(5, 0.0),
                "per_object": r["per_object"],
            }

        if "B" in phases_present:
            r = self.analyze_grasp_correlation()
            report["phase_b_grasp_correlation"] = {
                "overall_success_rate": r.overall_success_rate,
                "success_by_hamming_band": r.success_by_hamming_band,
                "success_by_match_type": r.success_by_match_type,
                "mean_force_deviation_N": r.mean_force_deviation_N,
                "per_object": r.per_object,
            }

        if "C" in phases_present:
            r = self.analyze_convergence()
            report["phase_c_convergence"] = {
                "trials_to_first_success": r.per_object_trials_to_first_success,
                "trials_to_90pct": r.per_object_trials_to_90pct,
                "total_llm_calls": r.total_llm_calls,
                "total_hash_lookups": r.total_hash_lookups,
            }

        if "D" in phases_present:
            r = self.analyze_latency()
            report["phase_d_latency"] = {
                "component_p50_ms": r.component_p50_ms,
                "component_p99_ms": r.component_p99_ms,
                "total_fast_path_p50_ms": r.total_fast_path_p50_ms,
                "total_fast_path_p99_ms": r.total_fast_path_p99_ms,
            }

        with open(filepath, "w") as f:
            json.dump(report, f, indent=2)

        logger.info("Exported validation report to %s", filepath)
        return report


def _hamming(h1: str, h2: str) -> int:
    """Hamming distance between two 0x-prefixed hex hashes."""
    a = h1.lower().removeprefix("0x")
    b = h2.lower().removeprefix("0x")
    if len(a) != len(b):
        return 64  # Max distance for mismatched hashes
    xor = int(a, 16) ^ int(b, 16)
    return bin(xor).count("1")
