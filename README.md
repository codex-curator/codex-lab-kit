# Codex Lab Kit

Standardized validation toolkit for the **Golden Codex Protocol** — a patent-pending dual-path architecture for robotic manipulation.

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-green.svg)](LICENSE)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.18668110.svg)](https://doi.org/10.5281/zenodo.18668110)

`Apache 2.0` | `Python 3.9+` | `Seeking Validation Partners`

## Overview

This toolkit enables robotics labs to run standardized validation experiments testing whether **perceptual hashing** can serve as the primary recognition layer for manipulation tasks.

The underlying Golden Codex Protocol combines O(1) hash lookup for known objects with LLM-based recovery for novel encounters. This public kit provides everything needed to run experiments and collect structured data — the proprietary core engine is available separately to approved partners.

## What's Included

| Package | Description |
|---------|-------------|
| `codex_lab_kit/` | Experiment protocol generator, structured data collector (CSV), statistical analysis, hardware calibration wizard |
| `codex_mock_ros/` | Lightweight mock ROS2 framework — pub/sub, services, action servers — for testing without ROS2 installed |
| `codex_msgs/` | Standard ROS2 message, service, and action definitions for the Golden Codex pipeline |
| `docs/` | Protocol walkthrough, lab onboarding guide, data format reference |
| `examples/` | Standalone demo using only public modules (zero core dependencies) |

## Quick Start

```bash
pip install codex-lab-kit
```

```python
from codex_lab_kit import ExperimentProtocol, DataCollector, ResultsAnalyzer

# Generate the 4-phase experiment protocol
protocol = ExperimentProtocol(lab_name="My Lab", robot_model="Franka Panda")
protocol.export_protocol("experiment_protocol.json")

# Collect trial data
collector = DataCollector(lab_name="My Lab")
collector.record(
    phase_id="A", trial_index=0, object_id="001_chips_can",
    query_dhash="0xabcdef1234567890", match_type="EXACT",
    hamming_distance=0
)
collector.export_csv("results.csv")

# Analyze results
analyzer = ResultsAnalyzer("results.csv")
report = analyzer.export_report("analysis_report.json")
```

## Experiment Protocol

The validation protocol consists of four phases testing different aspects of hash-based robotic manipulation:

| Phase | Name | Trials | Hardware Required | Duration |
|-------|------|--------|-------------------|----------|
| **A** | Hash Robustness | 360 images | Camera + YCB objects | ~50 min |
| **B** | Hash-to-Grasp Correlation | 100 grasps | Robot + gripper + force sensor | ~200 min |
| **C** | Loop Closure Convergence | 250 trials | Robot + 5 novel objects | ~250 min |
| **D** | Latency Profile | timing | Full pipeline | ~30 min |

Phase A can be run with camera-only setups. Phases B-D require a manipulation platform (Franka Panda, UR5e, or similar).

See [docs/experiment_protocol.md](docs/experiment_protocol.md) for the full walkthrough.

## For Partner Labs

What you receive as a validation partner:

- Complete Python validation toolkit (pip-installable)
- Standardized experiment protocol with step-by-step instructions
- Pre-computed hash baselines for 20 YCB objects
- Structured data collector (ROS2 node or standalone)
- Automated analysis and visualization scripts
- **Co-authorship on resulting publications**
- Access to aggregated cross-lab results
- Custom dataset generation tools for novel objects

## Core Engine

The proprietary `gcp-robotics` core package — containing the composite hash engine, Spatial Kinematic Blueprint schema, O(1) registry, and LLM slow path generator — is available to approved academic partners under individual license agreements.

```bash
# For approved partners only
pip install codex-lab-kit[core]
```

Contact **research@iaeternum.ai** for access.

## Patent Notice

The Golden Codex Protocol architecture is the subject of U.S. Provisional Patent Applications No. 63/983,304, No. 63/984,299, and No. 63/985,213, assigned to Metavolve Labs, Inc.

## Citation

```bibtex
@software{codex_lab_kit,
  title    = {Codex Lab Kit: Validation Toolkit for Hash-Based Robotic Manipulation},
  author   = {MacPherson, Tad},
  year     = {2026},
  publisher = {Zenodo},
  doi      = {10.5281/zenodo.18668110},
  url      = {https://doi.org/10.5281/zenodo.18668110}
}
```

## Research Papers

| # | Paper | DOI |
|---|-------|-----|
| 1 | The Entropy of Recursion | [10.5281/zenodo.18436975](https://doi.org/10.5281/zenodo.18436975) |
| 2 | The Density Imperative | [10.5281/zenodo.18667735](https://doi.org/10.5281/zenodo.18667735) |
| 3 | Cognitive Nutrition for Foundation Models | [10.5281/zenodo.18667742](https://doi.org/10.5281/zenodo.18667742) |
| 4 | Perceptual Compute Offloading | [10.5281/zenodo.18667749](https://doi.org/10.5281/zenodo.18667749) |

## Links

- **Website:** [iaeternum.ai/robotics](https://iaeternum.ai/robotics)
- **GCP-Robotics SDK:** [github.com/codex-curator/gcp-robotics](https://github.com/codex-curator/gcp-robotics)
- **Alexandria Dataset:** [HuggingFace](https://huggingface.co/datasets/Metavolve-Labs/alexandria-aeternum-genesis) | [DOI: 10.5281/zenodo.18359131](https://doi.org/10.5281/zenodo.18359131)
- **Contact:** research@iaeternum.ai
- **License:** Apache 2.0 (this toolkit) | Proprietary (core engine)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on submitting code, running experiments, and contributing datasets.
