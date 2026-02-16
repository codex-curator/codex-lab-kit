#!/usr/bin/env python3
"""
Codex Lab Kit — Standalone Demo
================================
Demonstrates the full validation workflow using only public modules.
No gcp-robotics core installation required.

Usage:
    python examples/run_protocol.py
"""

import os
import sys
import json
import random
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from codex_lab_kit import (
    ExperimentProtocol,
    DataCollector,
    ResultsAnalyzer,
    CalibrationWizard,
)


def main():
    print("=" * 60)
    print("  Codex Lab Kit — Standalone Validation Demo")
    print("=" * 60)

    with tempfile.TemporaryDirectory(prefix="codex_demo_") as tmpdir:
        # ── Step 1: Calibration ──
        print("\n[1/4] Running calibration wizard...")
        wizard = CalibrationWizard(lab_name="Demo Lab", lab_contact="demo@example.com")
        wizard.set_camera(camera_model="RealSense D435", resolution=(640, 480))
        wizard.add_lighting_condition("ambient", lux_estimate=300, source_type="LED")
        wizard.set_workspace(
            zone_name="bench_1",
            dimensions_mm=(800, 600, 400),
            robot_model="Franka Panda",
            gripper_model="Robotiq 2F-85",
        )
        cal_path = os.path.join(tmpdir, "calibration.json")
        wizard.export(cal_path)
        print(f"  Calibration exported to {cal_path}")

        # ── Step 2: Generate Protocol ──
        print("\n[2/4] Generating experiment protocol...")
        protocol = ExperimentProtocol(
            lab_name="Demo Lab",
            robot_model="Franka Panda",
            gripper_model="Robotiq 2F-85",
            camera_model="RealSense D435",
        )
        proto_path = os.path.join(tmpdir, "protocol.json")
        protocol.export_protocol(proto_path)

        with open(proto_path) as f:
            proto = json.load(f)
        print(f"  Protocol: {proto['summary']['total_phases']} phases, "
              f"{proto['summary']['total_trials']} total trials")

        # ── Step 3: Simulate Phase A trials ──
        print("\n[3/4] Simulating Phase A (Hash Robustness) trials...")
        collector = DataCollector(lab_name="Demo Lab")

        objects = ["001_chips_can", "003_cracker_box", "005_tomato_soup_can"]

        for obj_idx, obj_id in enumerate(objects):
            for trial in range(12):
                fake_hash = f"0x{random.getrandbits(64):016x}"
                hamming = random.randint(0, 8)
                match_type = "EXACT" if hamming <= 3 else "FUZZY"

                collector.record(
                    phase_id="A",
                    trial_index=obj_idx * 12 + trial,
                    object_id=obj_id,
                    query_dhash=fake_hash,
                    match_type=match_type,
                    hamming_distance=hamming,
                    image_capture_ms=random.uniform(3, 8),
                    hash_computation_ms=random.uniform(4, 6),
                    registry_lookup_ms=random.uniform(0.01, 0.5),
                )

        csv_path = os.path.join(tmpdir, "trials.csv")
        collector.export_csv(csv_path)
        summary = collector.summary()
        print(f"  Recorded {summary['total_trials']} trials across "
              f"{summary['unique_objects']} objects")
        print(f"  CSV exported to {csv_path}")

        # ── Step 4: Analyze results ──
        print("\n[4/4] Analyzing results...")
        analyzer = ResultsAnalyzer(csv_path)

        hash_report = analyzer.analyze_hash_robustness()
        print(f"  Phase A — Mean Hamming distance: "
              f"{hash_report.get('overall_hamming_mean', 'N/A'):.2f}")
        print(f"  Phase A — Exact match rate: "
              f"{hash_report.get('exact_match_rate', 'N/A'):.1%}")

        report_path = os.path.join(tmpdir, "report.json")
        analyzer.export_report(report_path)
        print(f"  Full report exported to {report_path}")

        # ── Summary ──
        print("\n" + "=" * 60)
        print("  Demo complete!")
        print()
        print("  Next steps for real experiments:")
        print("  1. Run calibration wizard with your actual hardware")
        print("  2. Follow the generated protocol")
        print("  3. Use DataCollector to record real trial data")
        print("  4. Run ResultsAnalyzer on your CSV files")
        print()
        print("  Questions? Visit https://iaeternum.ai/robotics")
        print("  or email research@iaeternum.ai")
        print("=" * 60)


if __name__ == "__main__":
    main()
