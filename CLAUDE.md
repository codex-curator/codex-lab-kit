# CLAUDE.md -- Codex Lab Kit

**What this is**: The public validation toolkit for the Golden Codex Protocol (GCP-Robotics). Standardized 4-phase experiment protocol for partner labs testing hash-based robotic manipulation. Published to `codex-curator/codex-lab-kit` on GitHub. DOI: 10.5281/zenodo.18668110.

**Local path**: `/mnt/d/NeuralNet/codex-lab-kit/`

---

## Workspace Map

| Directory | What It Is | Local Path |
|-----------|-----------|------------|
| **This repo** (Lab Kit) | Validation toolkit, experiment protocol | `/mnt/d/NeuralNet/codex-lab-kit/` |
| **GCP-Robotics SDK** | Core SDK (hasher, registry, SKB schema) | `/mnt/d/NeuralNet/golden-codex-core/` |
| **Robotics Research LAIR** | Research strategy, open questions | `/mnt/d/NeuralNet/LABS/robotics-research/` |
| **NeuralNet root** | D: drive session initialization | `/mnt/d/NeuralNet/START_HERE.md` |

---

## Package Structure

```
codex_lab_kit/           Experiment protocol, data collector, analysis
codex_mock_ros/          Mock ROS2 framework (test without rclpy)
codex_msgs/              ROS2 message/service/action definitions
docs/                    Protocol walkthrough, onboarding guide
examples/                Standalone demo (no core dependencies)
tests/                   Test suite (54 tests)
```

---

## Key Commands

```bash
# Install
pip install codex-lab-kit

# Run tests
python3 -m pytest tests/ -v

# Generate experiment protocol
python -c "
from codex_lab_kit import ExperimentProtocol
p = ExperimentProtocol(lab_name='Test', robot_model='Franka')
p.export_protocol('protocol.json')
"
```

---

## 4-Phase Experiment Protocol

| Phase | Name | Trials | What It Tests |
|-------|------|--------|--------------|
| A | Hash Robustness | 360 images | Perceptual hash stability under transforms |
| B | Hash-to-Grasp | 100 grasps | Does hash match predict grasp success? |
| C | Loop Closure | 250 trials | Can novel objects be learned and recognized? |
| D | Latency Profile | timing | End-to-end pipeline speed |

---

## Related Repos

- **GCP-Robotics SDK**: `/mnt/d/NeuralNet/golden-codex-core/CLAUDE.md`
- **Robotics START HERE**: `/mnt/d/NeuralNet/LABS/robotics-research/ROBOT_LAB_START_HERE.md`
- **NeuralNet root**: `/mnt/d/NeuralNet/START_HERE.md`
