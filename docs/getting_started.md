# Getting Started with Codex Lab Kit

## Prerequisites

- Python 3.9 or higher
- A robotics lab with manipulation hardware (for Phases B-D)
- Camera system (Intel RealSense recommended)

## Installation

```bash
pip install codex-lab-kit
```

For analysis visualizations:
```bash
pip install codex-lab-kit[analysis]
```

## Workflow

### 1. Calibrate Your Setup

```python
from codex_lab_kit import CalibrationWizard

wizard = CalibrationWizard(lab_name="Your Lab", lab_contact="you@university.edu")
wizard.set_camera(camera_model="RealSense D435", resolution=(640, 480))
wizard.add_lighting_condition("ambient", lux_estimate=300)
wizard.set_workspace(
    zone_name="bench_1",
    dimensions_mm=(800, 600, 400),
    robot_model="Franka Panda",
    gripper_model="Robotiq 2F-85",
)
wizard.export("calibration.json")
```

### 2. Generate Your Protocol

```python
from codex_lab_kit import ExperimentProtocol

protocol = ExperimentProtocol(lab_name="Your Lab", robot_model="Franka Panda")
protocol.export_protocol("protocol.json")
```

### 3. Run Experiments & Collect Data

```python
from codex_lab_kit import DataCollector

collector = DataCollector(lab_name="Your Lab")
collector.record(
    phase_id="A", trial_index=0, object_id="001_chips_can",
    query_dhash="0x...", match_type="EXACT", hamming_distance=0,
)
collector.export_csv("results.csv")
```

### 4. Analyze Results

```python
from codex_lab_kit import ResultsAnalyzer

analyzer = ResultsAnalyzer("results.csv")
analyzer.analyze_hash_robustness()
analyzer.analyze_grasp_correlation()
analyzer.analyze_convergence()
analyzer.analyze_latency()
analyzer.export_report("report.json")
```

## Phase Overview

| Phase | Name | What You Need | Duration |
|-------|------|---------------|----------|
| A | Hash Robustness | Camera + YCB objects | ~50 min |
| B | Hash-to-Grasp | Robot + gripper + force sensor | ~200 min |
| C | Loop Closure | Robot + 5 novel objects | ~250 min |
| D | Latency Profile | Full pipeline running | ~30 min |

## Need the Core Engine?

The proprietary `gcp-robotics` package (hash engine, SKB schema, LLM slow path)
is available to approved academic partners. Contact research@iaeternum.ai.
