"""
calibration_wizard.py — Interactive calibration and workspace registration
for partner labs.

Walks through camera intrinsics, lighting baseline, workspace zone
definition, and initial hash baseline computation.
"""

from __future__ import annotations

import json
import logging
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class CameraCalibration:
    """Camera intrinsic and extrinsic parameters."""
    camera_model: str = ""
    resolution_w: int = 0
    resolution_h: int = 0
    focal_length_mm: float = 0.0
    working_distance_mm: float = 0.0
    mount_position: str = ""  # e.g., "overhead", "eye-in-hand", "fixed_side"
    notes: str = ""


@dataclass
class LightingBaseline:
    """Lighting condition characterization."""
    condition_name: str = ""
    lux_estimate: float = 0.0
    source_type: str = ""  # e.g., "overhead_fluorescent", "led_ring", "ambient"
    notes: str = ""


@dataclass
class WorkspaceConfig:
    """Workspace zone definition."""
    zone_name: str = ""
    dimensions_mm: List[float] = field(default_factory=lambda: [0, 0, 0])
    robot_model: str = ""
    gripper_model: str = ""
    has_force_sensor: bool = False
    has_turntable: bool = False
    notes: str = ""


@dataclass
class CalibrationRecord:
    """Complete calibration record for a partner lab."""
    lab_name: str
    lab_contact: str
    calibration_date: str = ""
    camera: CameraCalibration = field(default_factory=CameraCalibration)
    lighting_conditions: List[LightingBaseline] = field(default_factory=list)
    workspace: WorkspaceConfig = field(default_factory=WorkspaceConfig)
    hash_baselines: Dict[str, str] = field(default_factory=dict)


class CalibrationWizard:
    """Guides a lab through calibration and exports configuration.

    Can be used interactively (terminal prompts) or programmatically
    by setting fields directly on the record.
    """

    def __init__(self, lab_name: str, lab_contact: str) -> None:
        self.record = CalibrationRecord(
            lab_name=lab_name,
            lab_contact=lab_contact,
        )
        self._calibration = {}

    def set_camera(
        self,
        camera_model: str,
        resolution: tuple[int, int],
        focal_length_mm: float = 0.0,
        working_distance_mm: float = 500.0,
        mount_position: str = "overhead",
    ) -> None:
        self.record.camera = CameraCalibration(
            camera_model=camera_model,
            resolution_w=resolution[0],
            resolution_h=resolution[1],
            focal_length_mm=focal_length_mm,
            working_distance_mm=working_distance_mm,
            mount_position=mount_position,
        )

    def add_lighting_condition(
        self,
        name: str,
        lux_estimate: float = 0.0,
        source_type: str = "ambient",
    ) -> None:
        self.record.lighting_conditions.append(LightingBaseline(
            condition_name=name,
            lux_estimate=lux_estimate,
            source_type=source_type,
        ))

    def set_workspace(
        self,
        zone_name: str,
        robot_model: str,
        gripper_model: str,
        dimensions_mm: Optional[List[float]] = None,
        has_force_sensor: bool = False,
        has_turntable: bool = False,
    ) -> None:
        self.record.workspace = WorkspaceConfig(
            zone_name=zone_name,
            dimensions_mm=dimensions_mm or [800, 600, 400],
            robot_model=robot_model,
            gripper_model=gripper_model,
            has_force_sensor=has_force_sensor,
            has_turntable=has_turntable,
        )

    def compute_hash_baselines(
        self,
        image_dir: str,
        hasher: Any = None,
    ) -> Dict[str, str]:
        """Compute baseline dHash for calibration images in a directory.

        Parameters
        ----------
        image_dir : str
            Directory containing calibration images named like
            ``<object_id>_<variant>.png``.
        hasher : CompositeHasher, optional
            If None, imports from gcp_robotics.
        """
        if hasher is None:
            try:
                from gcp_robotics.hash_engine.hasher import CompositeHasher
                hasher = CompositeHasher()
            except ImportError:
                print("[calibration] gcp-robotics core not installed — hash baselines will use placeholder values.")
                print("[calibration] Install the core package for real hash computation: pip install gcp-robotics")
                # Return placeholder baselines
                self._calibration["hash_baselines"] = {
                    "_note": "Placeholder — install gcp-robotics for real hash baselines",
                }
                return self

        baselines = {}
        img_dir = Path(image_dir)
        for img_path in sorted(img_dir.glob("*.png")) + sorted(img_dir.glob("*.jpg")):
            try:
                dhash = hasher.compute_dhash(str(img_path))
                baselines[img_path.name] = dhash
                logger.debug("Baseline hash: %s → %s", img_path.name, dhash)
            except Exception:
                logger.exception("Failed to hash %s", img_path)

        self.record.hash_baselines = baselines
        logger.info("Computed %d hash baselines from %s", len(baselines), image_dir)
        return baselines

    def validate(self) -> tuple[bool, List[str]]:
        """Check that calibration is complete enough to run experiments."""
        errors = []

        if not self.record.camera.camera_model:
            errors.append("Camera model not set.")
        if self.record.camera.resolution_w == 0:
            errors.append("Camera resolution not set.")
        if not self.record.lighting_conditions:
            errors.append("No lighting conditions defined.")
        if not self.record.workspace.robot_model:
            errors.append("Robot model not set.")
        if not self.record.workspace.gripper_model:
            errors.append("Gripper model not set.")

        is_valid = len(errors) == 0
        if is_valid:
            logger.info("Calibration validated successfully.")
        else:
            logger.warning("Calibration incomplete: %s", errors)

        return is_valid, errors

    def export(self, filepath: Optional[str] = None) -> str:
        """Export calibration record to JSON."""
        if filepath is None:
            filepath = f"calibration_{self.record.lab_name}.json"

        import datetime
        self.record.calibration_date = datetime.datetime.now().isoformat()

        with open(filepath, "w") as f:
            json.dump(asdict(self.record), f, indent=2)

        logger.info("Exported calibration to %s", filepath)
        return filepath

    def run_interactive(self) -> None:
        """Run an interactive terminal-based calibration wizard."""
        print("\n" + "=" * 60)
        print("  Golden Codex Lab Kit — Calibration Wizard")
        print("=" * 60)
        print(f"\n  Lab: {self.record.lab_name}")
        print(f"  Contact: {self.record.lab_contact}\n")

        # Camera
        print("--- Camera Configuration ---")
        model = input("  Camera model (e.g., Intel RealSense D435): ").strip()
        res_w = int(input("  Resolution width (px): ") or "640")
        res_h = int(input("  Resolution height (px): ") or "480")
        mount = input("  Mount position [overhead/eye-in-hand/fixed_side]: ").strip() or "overhead"
        self.set_camera(model, (res_w, res_h), mount_position=mount)

        # Lighting
        print("\n--- Lighting Conditions ---")
        print("  (Enter conditions one at a time. Empty name to finish.)")
        while True:
            name = input("  Condition name: ").strip()
            if not name:
                break
            source = input("  Source type: ").strip() or "ambient"
            self.add_lighting_condition(name, source_type=source)

        if not self.record.lighting_conditions:
            self.add_lighting_condition("ambient", source_type="ambient")
            print("  Added default 'ambient' condition.")

        # Workspace
        print("\n--- Workspace Configuration ---")
        robot = input("  Robot model (e.g., Franka Emika Panda): ").strip()
        gripper = input("  Gripper model (e.g., Robotiq 2F-85): ").strip()
        zone = input("  Zone name [validation_bench]: ").strip() or "validation_bench"
        ft = input("  Has force/torque sensor? [y/N]: ").strip().lower() == "y"
        tt = input("  Has turntable? [y/N]: ").strip().lower() == "y"
        self.set_workspace(zone, robot, gripper, has_force_sensor=ft, has_turntable=tt)

        # Validate and export
        is_valid, errors = self.validate()
        if not is_valid:
            print("\n  Warnings:")
            for e in errors:
                print(f"    - {e}")

        filepath = self.export()
        print(f"\n  Calibration saved to: {filepath}")
        print("  You can now run the experiment protocol.\n")
