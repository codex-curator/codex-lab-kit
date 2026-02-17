"""Shared fixtures for the codex-lab-kit test suite."""

import pytest

from codex_lab_kit.experiment_protocol import ExperimentProtocol
from codex_lab_kit.data_collector import DataCollector, TrialResult


@pytest.fixture
def protocol():
    """A standard experiment protocol for testing."""
    return ExperimentProtocol(
        lab_name="Test Lab",
        lab_contact="test@example.com",
        robot_model="UR5e",
        gripper_model="Robotiq 2F-85",
        camera_model="RealSense D435",
    )


@pytest.fixture
def collector(tmp_path):
    """A DataCollector writing to a temporary directory."""
    return DataCollector(
        output_dir=str(tmp_path),
        lab_name="test_lab",
        auto_flush=0,  # Manual flush only during tests
    )


@pytest.fixture
def phase_a_trials():
    """Simulated Phase A trials with known hash values.

    Three objects, each with 4 images. Intra-class hashes differ by a few
    bits; inter-class hashes differ significantly.
    """
    trials = []
    # Object A: hashes cluster tightly (low intra-class distance)
    obj_a_hashes = ["0xAAAAAAAAAAAAAAAA", "0xAAAAAAAAAAAAAAAA",
                     "0xAAAAAAAAAAAABAAA", "0xAAAAAAAAAAAABAAA"]
    for i, h in enumerate(obj_a_hashes):
        trials.append(TrialResult(
            phase_id="A", trial_index=i, object_id="obj_a",
            query_dhash=h, match_type="EXACT", hamming_distance=0,
            lighting_condition="ambient", viewpoint_index=i,
        ))

    # Object B: hashes cluster tightly but far from A
    obj_b_hashes = ["0x5555555555555555", "0x5555555555555555",
                     "0x5555555555555554", "0x5555555555555557"]
    for i, h in enumerate(obj_b_hashes):
        trials.append(TrialResult(
            phase_id="A", trial_index=i + 4, object_id="obj_b",
            query_dhash=h, match_type="EXACT", hamming_distance=0,
            lighting_condition="overhead_bright", viewpoint_index=i,
        ))

    # Object C: distinct from both A and B
    obj_c_hashes = ["0x0F0F0F0F0F0F0F0F", "0x0F0F0F0F0F0F0F0E",
                     "0x0F0F0F0F0F0F0F0D", "0x0F0F0F0F0F0F0F0F"]
    for i, h in enumerate(obj_c_hashes):
        trials.append(TrialResult(
            phase_id="A", trial_index=i + 8, object_id="obj_c",
            query_dhash=h, match_type="EXACT", hamming_distance=0,
            lighting_condition="directional_side", viewpoint_index=i,
        ))

    return trials


@pytest.fixture
def phase_b_trials():
    """Simulated Phase B trials with grasp outcomes by Hamming band."""
    trials = []
    idx = 0
    # Exact matches (hamming 0-2): mostly successful
    for i in range(10):
        trials.append(TrialResult(
            phase_id="B", trial_index=idx, object_id="obj_a",
            match_type="EXACT", hamming_distance=0,
            grasp_success=(i < 9),  # 90% success
            force_actual_N=5.0 + (i * 0.1),
            force_planned_N=5.0,
        ))
        idx += 1

    # Fuzzy matches (hamming 3-5): moderately successful
    for i in range(10):
        trials.append(TrialResult(
            phase_id="B", trial_index=idx, object_id="obj_b",
            match_type="FUZZY", hamming_distance=4,
            grasp_success=(i < 7),  # 70% success
            force_actual_N=5.5 + (i * 0.2),
            force_planned_N=5.0,
        ))
        idx += 1

    # High distance (hamming 9+): low success
    for i in range(5):
        trials.append(TrialResult(
            phase_id="B", trial_index=idx, object_id="obj_c",
            match_type="FUZZY", hamming_distance=12,
            grasp_success=(i < 1),  # 20% success
            force_actual_N=8.0,
            force_planned_N=5.0,
        ))
        idx += 1

    return trials


@pytest.fixture
def phase_c_trials():
    """Simulated Phase C trials showing convergence over time.

    Object starts with misses, then transitions to hits after promotion.
    """
    trials = []
    for i in range(20):
        if i < 3:
            # First 3 trials are misses (object unknown)
            trials.append(TrialResult(
                phase_id="C", trial_index=i, object_id="novel_obj_1",
                match_type="MISS", hamming_distance=-1,
                grasp_success=False,
                llm_calls_cumulative=i + 1,
            ))
        elif i == 3:
            # Trial 4: first success after promotion
            trials.append(TrialResult(
                phase_id="C", trial_index=i, object_id="novel_obj_1",
                match_type="EXACT", hamming_distance=0,
                grasp_success=True, promoted=True,
                llm_calls_cumulative=3,
            ))
        else:
            # Remaining: all hits
            trials.append(TrialResult(
                phase_id="C", trial_index=i, object_id="novel_obj_1",
                match_type="EXACT", hamming_distance=0,
                grasp_success=True,
                llm_calls_cumulative=3,
            ))

    return trials


@pytest.fixture
def phase_d_trials():
    """Simulated Phase D trials with known latency values."""
    import random
    random.seed(42)
    trials = []
    for i in range(50):
        trials.append(TrialResult(
            phase_id="D", trial_index=i, object_id="obj_a",
            match_type="EXACT", hamming_distance=0,
            image_capture_ms=2.0 + random.gauss(0, 0.3),
            hash_computation_ms=0.5 + random.gauss(0, 0.1),
            registry_lookup_ms=0.03 + random.gauss(0, 0.005),
            total_perception_ms=2.5 + random.gauss(0, 0.35),
            motion_planning_ms=15.0 + random.gauss(0, 2.0),
        ))
    return trials
