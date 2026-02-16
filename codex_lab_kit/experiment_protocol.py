"""
experiment_protocol.py — Generates standardized validation experiments.

Four phases:
  A: Hash Robustness (perception only)
  B: Hash-to-Grasp Correlation (manipulation)
  C: Loop Closure Convergence (learning dynamics)
  D: Latency Profile (end-to-end timing)
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Default YCB objects for the standard protocol
STANDARD_YCB_OBJECTS = [
    "001_chips_can",
    "002_master_chef_can",
    "003_cracker_box",
    "004_sugar_box",
    "005_tomato_soup_can",
    "006_mustard_bottle",
    "007_tuna_fish_can",
    "008_pudding_box",
    "009_gelatin_box",
    "010_potted_meat_can",
    "011_banana",
    "019_pitcher_base",
    "021_bleach_cleanser",
    "024_bowl",
    "025_mug",
    "035_power_drill",
    "036_wood_block",
    "037_scissors",
    "040_large_marker",
    "052_extra_large_clamp",
]

LIGHTING_CONDITIONS = ["ambient", "overhead_bright", "directional_side"]
VIEWPOINTS_PER_OBJECT = 12  # 30-degree increments around turntable
GRASPS_PER_OBJECT = 10
NOVEL_OBJECTS_FOR_CLOSURE = 5
CLOSURE_TRIALS_PER_OBJECT = 50


@dataclass
class PhaseConfig:
    """Configuration for a single experiment phase."""
    phase_id: str
    name: str
    description: str
    object_ids: List[str]
    trials_per_object: int
    requires_hardware: bool
    estimated_duration_min: int
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExperimentProtocol:
    """A complete validation experiment protocol.

    Generates the full specification of trials to run, metrics to collect,
    and acceptance criteria to evaluate.
    """

    lab_name: str
    lab_contact: str
    robot_model: str
    gripper_model: str
    camera_model: str
    workspace_zone: str = "validation_bench"
    object_ids: Optional[List[str]] = None
    novel_object_ids: Optional[List[str]] = None
    output_dir: str = "./codex_validation_results"

    def __post_init__(self):
        if self.object_ids is None:
            self.object_ids = STANDARD_YCB_OBJECTS[:10]
        if self.novel_object_ids is None:
            self.novel_object_ids = STANDARD_YCB_OBJECTS[10:15]

    def generate_phase_a(self) -> PhaseConfig:
        """Phase A: Hash Robustness — perception only, no manipulation."""
        n_images = (
            len(self.object_ids)
            * VIEWPOINTS_PER_OBJECT
            * len(LIGHTING_CONDITIONS)
        )
        return PhaseConfig(
            phase_id="A",
            name="Hash Robustness",
            description=(
                f"Capture {n_images} images of {len(self.object_ids)} objects "
                f"across {VIEWPOINTS_PER_OBJECT} viewpoints and "
                f"{len(LIGHTING_CONDITIONS)} lighting conditions. "
                "Compute composite hashes and measure intra-class Hamming "
                "distance distributions, inter-class separation, and ROC curves."
            ),
            object_ids=self.object_ids,
            trials_per_object=VIEWPOINTS_PER_OBJECT * len(LIGHTING_CONDITIONS),
            requires_hardware=False,  # Camera only, no manipulation
            estimated_duration_min=len(self.object_ids) * 5,
            parameters={
                "viewpoints": VIEWPOINTS_PER_OBJECT,
                "lighting_conditions": LIGHTING_CONDITIONS,
                "turntable_increment_deg": 360 / VIEWPOINTS_PER_OBJECT,
                "capture_format": "PNG",
                "resolution_min": "640x480",
                "metrics": [
                    "intra_class_hamming_mean",
                    "intra_class_hamming_std",
                    "inter_class_hamming_mean",
                    "roc_auc_exact_threshold",
                    "roc_auc_fuzzy_threshold",
                    "false_positive_rate_at_threshold_5",
                    "recall_at_threshold_5",
                ],
            },
        )

    def generate_phase_b(self) -> PhaseConfig:
        """Phase B: Hash-to-Grasp Correlation — manipulation required."""
        return PhaseConfig(
            phase_id="B",
            name="Hash-to-Grasp Correlation",
            description=(
                f"For each of {len(self.object_ids)} objects, execute the "
                f"SKB-prescribed action {GRASPS_PER_OBJECT} times. Record "
                "binary grasp success, actual force profile, and execution time. "
                "Correlate hash distance at lookup time with grasp success."
            ),
            object_ids=self.object_ids,
            trials_per_object=GRASPS_PER_OBJECT,
            requires_hardware=True,
            estimated_duration_min=len(self.object_ids) * GRASPS_PER_OBJECT * 2,
            parameters={
                "grasps_per_object": GRASPS_PER_OBJECT,
                "max_hamming_distance": 10,
                "force_sensor_required": True,
                "metrics": [
                    "grasp_success_rate_by_hamming_band",
                    "mean_force_deviation_N",
                    "execution_time_ms",
                    "post_action_hash_shift",
                ],
            },
        )

    def generate_phase_c(self) -> PhaseConfig:
        """Phase C: Loop Closure Convergence — learning dynamics."""
        return PhaseConfig(
            phase_id="C",
            name="Loop Closure Convergence",
            description=(
                f"Present {NOVEL_OBJECTS_FOR_CLOSURE} novel objects (not in "
                f"initial registry). Run {CLOSURE_TRIALS_PER_OBJECT} "
                "consecutive attempts per object. Measure trials until first "
                "success, trials until reliable (>90%) success, and total LLM "
                "calls vs. hash lookups."
            ),
            object_ids=self.novel_object_ids[:NOVEL_OBJECTS_FOR_CLOSURE],
            trials_per_object=CLOSURE_TRIALS_PER_OBJECT,
            requires_hardware=True,
            estimated_duration_min=NOVEL_OBJECTS_FOR_CLOSURE * CLOSURE_TRIALS_PER_OBJECT,
            parameters={
                "llm_provider": "anthropic_claude",
                "auto_promote": True,
                "metrics": [
                    "trials_to_first_success",
                    "trials_to_90pct_success",
                    "total_llm_calls",
                    "total_hash_lookups",
                    "convergence_curve",
                    "promotion_count",
                ],
            },
        )

    def generate_phase_d(self) -> PhaseConfig:
        """Phase D: Latency Profile — end-to-end timing."""
        return PhaseConfig(
            phase_id="D",
            name="Latency Profile",
            description=(
                "Measure end-to-end timing: image capture, hash computation, "
                "registry lookup, action execution start. Compare against a "
                "baseline neural-network-only pipeline if available."
            ),
            object_ids=self.object_ids[:5],
            trials_per_object=50,
            requires_hardware=True,
            estimated_duration_min=30,
            parameters={
                "timing_components": [
                    "image_capture_ms",
                    "hash_computation_ms",
                    "registry_lookup_ms",
                    "ros2_transport_ms",
                    "motion_planning_ms",
                    "total_perception_to_action_ms",
                ],
                "baseline_comparison": "clip_feature_matching",
                "warmup_iterations": 10,
                "measurement_iterations": 50,
            },
        )

    def generate_full_protocol(self) -> Dict[str, Any]:
        """Generate the complete experiment protocol as a dict."""
        phases = [
            self.generate_phase_a(),
            self.generate_phase_b(),
            self.generate_phase_c(),
            self.generate_phase_d(),
        ]

        total_trials = sum(
            p.trials_per_object * len(p.object_ids) for p in phases
        )
        total_duration = sum(p.estimated_duration_min for p in phases)

        protocol = {
            "protocol_version": "1.0",
            "framework": "Golden Codex Protocol 2.0-GCP-ROBOTICS",
            "lab_info": {
                "lab_name": self.lab_name,
                "lab_contact": self.lab_contact,
                "robot_model": self.robot_model,
                "gripper_model": self.gripper_model,
                "camera_model": self.camera_model,
                "workspace_zone": self.workspace_zone,
            },
            "summary": {
                "total_phases": len(phases),
                "total_trials": total_trials,
                "estimated_duration_min": total_duration,
                "requires_hardware": any(p.requires_hardware for p in phases),
            },
            "phases": [asdict(p) for p in phases],
            "acceptance_criteria": {
                "phase_a": {
                    "intra_class_hamming_mean_lt": 6,
                    "inter_class_hamming_mean_gt": 15,
                    "recall_at_threshold_5_gt": 0.90,
                    "false_positive_rate_lt": 0.01,
                },
                "phase_b": {
                    "exact_match_grasp_success_gt": 0.85,
                    "fuzzy_match_grasp_success_gt": 0.70,
                },
                "phase_c": {
                    "trials_to_90pct_median_lt": 10,
                    "final_success_rate_gt": 0.90,
                },
                "phase_d": {
                    "hash_lookup_p99_ms_lt": 1.0,
                    "total_fast_path_p99_ms_lt": 20.0,
                },
            },
        }

        return protocol

    def export_protocol(self, filepath: Optional[str] = None) -> str:
        """Export protocol to JSON file. Returns filepath."""
        protocol = self.generate_full_protocol()
        if filepath is None:
            out_dir = Path(self.output_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            filepath = str(out_dir / "experiment_protocol.json")

        with open(filepath, "w") as f:
            json.dump(protocol, f, indent=2)

        logger.info("Exported protocol to %s (%d trials)", filepath, protocol["summary"]["total_trials"])
        return filepath
