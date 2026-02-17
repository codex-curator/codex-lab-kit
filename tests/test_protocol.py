"""
tests/test_protocol.py — Comprehensive test suite for codex-lab-kit.

Tests the standalone capabilities of the validation toolkit:
  - Experiment protocol generation (4-phase structure, trial counts)
  - Data collection and CSV/JSON serialization
  - Statistical analysis (robustness, grasp correlation, convergence, latency)

All tests use simulated data and pytest fixtures — no external hardware,
images, or the gcp-robotics SDK required.

Run:
    python -m pytest tests/ -v
"""

import csv
import json
import math

import pytest

from codex_lab_kit.experiment_protocol import (
    ExperimentProtocol,
    PhaseConfig,
    STANDARD_YCB_OBJECTS,
    VIEWPOINTS_PER_OBJECT,
    LIGHTING_CONDITIONS,
    GRASPS_PER_OBJECT,
    NOVEL_OBJECTS_FOR_CLOSURE,
    CLOSURE_TRIALS_PER_OBJECT,
)
from codex_lab_kit.data_collector import DataCollector, TrialResult
from codex_lab_kit.analysis import (
    ResultsAnalyzer,
    _hamming,
    _mean,
    _std,
    _percentile,
)


# =========================================================================
#  Protocol Generation
# =========================================================================


class TestExperimentProtocol:
    """Tests for ExperimentProtocol and PhaseConfig."""

    def test_default_objects(self, protocol):
        """Default protocol uses first 10 standard YCB objects."""
        assert len(protocol.object_ids) == 10
        assert protocol.object_ids == STANDARD_YCB_OBJECTS[:10]

    def test_novel_objects_default(self, protocol):
        """Default novel objects are items 11-15 for loop closure."""
        assert len(protocol.novel_object_ids) == 5
        assert protocol.novel_object_ids == STANDARD_YCB_OBJECTS[10:15]

    def test_custom_objects(self):
        """Custom object lists override defaults."""
        custom = ["my_bolt", "my_washer"]
        p = ExperimentProtocol(
            lab_name="Custom", lab_contact="x", robot_model="x",
            gripper_model="x", camera_model="x", object_ids=custom,
        )
        assert p.object_ids == custom

    def test_phase_a_trial_count(self, protocol):
        """Phase A: objects x viewpoints x lighting conditions."""
        phase = protocol.generate_phase_a()
        expected = VIEWPOINTS_PER_OBJECT * len(LIGHTING_CONDITIONS)
        assert phase.trials_per_object == expected
        assert phase.phase_id == "A"
        assert phase.requires_hardware is False

    def test_phase_b_trial_count(self, protocol):
        """Phase B: each object gets GRASPS_PER_OBJECT trials."""
        phase = protocol.generate_phase_b()
        assert phase.trials_per_object == GRASPS_PER_OBJECT
        assert phase.phase_id == "B"
        assert phase.requires_hardware is True

    def test_phase_c_trial_count(self, protocol):
        """Phase C: novel objects x closure trials per object."""
        phase = protocol.generate_phase_c()
        assert phase.trials_per_object == CLOSURE_TRIALS_PER_OBJECT
        assert phase.phase_id == "C"
        assert len(phase.object_ids) == NOVEL_OBJECTS_FOR_CLOSURE

    def test_phase_d_trial_count(self, protocol):
        """Phase D: latency profiling with 50 trials per object."""
        phase = protocol.generate_phase_d()
        assert phase.trials_per_object == 50
        assert phase.phase_id == "D"
        assert "timing_components" in phase.parameters

    def test_full_protocol_total_trials(self, protocol):
        """Full protocol total should match the sum of all phase trials."""
        full = protocol.generate_full_protocol()

        # Manually compute expected total
        phases = [
            protocol.generate_phase_a(),
            protocol.generate_phase_b(),
            protocol.generate_phase_c(),
            protocol.generate_phase_d(),
        ]
        expected = sum(p.trials_per_object * len(p.object_ids) for p in phases)

        assert full["summary"]["total_trials"] == expected
        assert full["summary"]["total_phases"] == 4

    def test_full_protocol_960_trials(self, protocol):
        """With default 10 objects, the standard protocol is 960 trials.

        Phase A: 10 objects x 12 viewpoints x 3 lighting = 360
        Phase B: 10 objects x 10 grasps = 100
        Phase C: 5 novel objects x 50 trials = 250
        Phase D: 5 objects x 50 trials = 250
        Total = 960
        """
        full = protocol.generate_full_protocol()
        assert full["summary"]["total_trials"] == 960

    def test_acceptance_criteria_present(self, protocol):
        """Acceptance criteria are defined for all four phases."""
        full = protocol.generate_full_protocol()
        criteria = full["acceptance_criteria"]
        assert "phase_a" in criteria
        assert "phase_b" in criteria
        assert "phase_c" in criteria
        assert "phase_d" in criteria
        # Spot-check specific thresholds
        assert criteria["phase_a"]["intra_class_hamming_mean_lt"] == 6
        assert criteria["phase_d"]["hash_lookup_p99_ms_lt"] == 1.0

    def test_lab_info_in_protocol(self, protocol):
        """Lab metadata is correctly embedded in the protocol."""
        full = protocol.generate_full_protocol()
        info = full["lab_info"]
        assert info["lab_name"] == "Test Lab"
        assert info["robot_model"] == "UR5e"
        assert info["camera_model"] == "RealSense D435"

    def test_export_protocol_json(self, protocol, tmp_path):
        """Protocol exports to a valid JSON file."""
        filepath = str(tmp_path / "protocol.json")
        result = protocol.export_protocol(filepath)
        assert result == filepath

        with open(filepath) as f:
            data = json.load(f)
        assert data["summary"]["total_trials"] == 960
        assert len(data["phases"]) == 4


# =========================================================================
#  Data Collection
# =========================================================================


class TestDataCollector:
    """Tests for DataCollector and TrialResult."""

    def test_record_trial(self, collector):
        """Recording a trial stores it internally."""
        trial = TrialResult(
            phase_id="A", trial_index=0, object_id="obj_a",
            match_type="EXACT", hamming_distance=0,
        )
        collector.record(trial)
        assert len(collector.get_trials()) == 1

    def test_record_from_kwargs(self, collector):
        """Recording via keyword arguments constructs a TrialResult."""
        collector.record(
            phase_id="A", trial_index=0, object_id="obj_a",
            match_type="FUZZY", hamming_distance=3,
        )
        trials = collector.get_trials()
        assert len(trials) == 1
        assert trials[0].match_type == "FUZZY"

    def test_filter_by_phase(self, collector):
        """get_trials(phase_id=...) filters correctly."""
        collector.record(phase_id="A", trial_index=0, object_id="x")
        collector.record(phase_id="B", trial_index=1, object_id="x")
        collector.record(phase_id="A", trial_index=2, object_id="y")

        assert len(collector.get_trials("A")) == 2
        assert len(collector.get_trials("B")) == 1

    def test_export_csv(self, collector, tmp_path):
        """CSV export writes valid headers and data rows."""
        for i in range(5):
            collector.record(
                phase_id="A", trial_index=i, object_id=f"obj_{i}",
                match_type="EXACT", hamming_distance=i,
                hash_computation_ms=0.5,
            )

        filepath = str(tmp_path / "trials.csv")
        result = collector.export_csv(filepath)
        assert result == filepath

        with open(filepath, newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 5
        assert "phase_id" in rows[0]
        assert "hamming_distance" in rows[0]
        assert rows[2]["object_id"] == "obj_2"

    def test_export_csv_empty(self, collector, tmp_path):
        """CSV export with no trials creates no rows but doesn't crash."""
        filepath = str(tmp_path / "empty.csv")
        collector.export_csv(filepath)
        # File should exist (even if empty or just a path)

    def test_flush_json(self, collector, tmp_path):
        """flush() writes a valid JSON file with trial data."""
        collector.record(
            phase_id="A", trial_index=0, object_id="obj_a",
            match_type="EXACT", hamming_distance=0,
        )
        filepath = collector.flush()

        with open(filepath) as f:
            data = json.load(f)
        assert data["trial_count"] == 1
        assert data["lab_name"] == "test_lab"
        assert len(data["trials"]) == 1

    def test_summary_statistics(self, collector):
        """summary() computes correct aggregate counts."""
        for i in range(3):
            collector.record(
                phase_id="A", trial_index=i, object_id="obj_a",
                match_type="EXACT",
            )
        collector.record(
            phase_id="B", trial_index=0, object_id="obj_a",
            match_type="MISS", grasp_success=True,
        )

        s = collector.summary()
        assert s["total_trials"] == 4
        assert s["phases"]["A"]["trial_count"] == 3
        assert s["phases"]["A"]["exact_hits"] == 3
        assert s["phases"]["B"]["grasp_successes"] == 1

    def test_csv_roundtrip(self, collector, tmp_path):
        """Data survives a CSV write-then-read roundtrip."""
        collector.record(
            phase_id="A", trial_index=7, object_id="test_obj",
            match_type="FUZZY", hamming_distance=4,
            query_dhash="0xABCD", hash_computation_ms=0.42,
        )
        filepath = str(tmp_path / "roundtrip.csv")
        collector.export_csv(filepath)

        analyzer = ResultsAnalyzer(filepath)
        assert len(analyzer._trials) == 1
        t = analyzer._trials[0]
        assert t.phase_id == "A"
        assert t.trial_index == 7
        assert t.hamming_distance == 4
        assert t.query_dhash == "0xABCD"
        assert abs(t.hash_computation_ms - 0.42) < 1e-6


# =========================================================================
#  Analysis Helpers
# =========================================================================


class TestAnalysisHelpers:
    """Tests for the internal math utility functions."""

    def test_hamming_identical(self):
        """Identical hashes have distance 0."""
        assert _hamming("0xFFFF", "0xFFFF") == 0

    def test_hamming_one_bit(self):
        """One bit flip gives distance 1."""
        assert _hamming("0xFFFE", "0xFFFF") == 1

    def test_hamming_all_bits(self):
        """0x0000 vs 0xFFFF = 16 bits different."""
        assert _hamming("0x0000", "0xFFFF") == 16

    def test_hamming_length_mismatch(self):
        """Mismatched lengths return max distance (64)."""
        assert _hamming("0xFF", "0xFFFF") == 64

    def test_mean(self):
        assert _mean([1.0, 2.0, 3.0]) == 2.0

    def test_mean_empty(self):
        assert _mean([]) == 0.0

    def test_std(self):
        """Standard deviation of [2, 4, 4, 4, 5, 5, 7, 9] ≈ 2.138."""
        values = [2, 4, 4, 4, 5, 5, 7, 9]
        result = _std(values)
        assert abs(result - 2.138) < 0.01

    def test_std_single_value(self):
        assert _std([5.0]) == 0.0

    def test_percentile_median(self):
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        assert _percentile(values, 50) == 3.0

    def test_percentile_p99(self):
        values = list(range(1, 101))
        result = _percentile([float(v) for v in values], 99)
        assert result == pytest.approx(99.01, abs=0.1)

    def test_percentile_empty(self):
        assert _percentile([], 50) == 0.0


# =========================================================================
#  Phase A: Hash Robustness Analysis
# =========================================================================


class TestHashRobustnessAnalysis:
    """Tests for ResultsAnalyzer.analyze_hash_robustness()."""

    def test_intra_class_distance_low(self, phase_a_trials):
        """Intra-class Hamming distance should be small for similar hashes."""
        analyzer = ResultsAnalyzer(phase_a_trials)
        report = analyzer.analyze_hash_robustness()
        # Our simulated hashes are very similar within each object
        assert report["intra_class_hamming_mean"] < 6

    def test_inter_class_distance_high(self, phase_a_trials):
        """Inter-class Hamming distance should be large for different objects."""
        analyzer = ResultsAnalyzer(phase_a_trials)
        report = analyzer.analyze_hash_robustness()
        assert report["inter_class_hamming_mean"] > 10

    def test_roc_thresholds_present(self, phase_a_trials):
        """ROC data at thresholds 0-19 should be computed."""
        analyzer = ResultsAnalyzer(phase_a_trials)
        report = analyzer.analyze_hash_robustness()
        assert len(report["recall_at_threshold"]) == 20
        assert len(report["fpr_at_threshold"]) == 20

    def test_per_object_stats(self, phase_a_trials):
        """Per-object stats should be computed for each object."""
        analyzer = ResultsAnalyzer(phase_a_trials)
        report = analyzer.analyze_hash_robustness()
        assert "obj_a" in report["per_object"]
        assert "obj_b" in report["per_object"]
        assert "obj_c" in report["per_object"]
        assert report["per_object"]["obj_a"]["image_count"] == 4

    def test_no_phase_a_raises(self):
        """Analyzing with no Phase A data raises ValueError."""
        analyzer = ResultsAnalyzer([
            TrialResult(phase_id="B", trial_index=0, object_id="x"),
        ])
        with pytest.raises(ValueError, match="No Phase A"):
            analyzer.analyze_hash_robustness()


# =========================================================================
#  Phase B: Grasp Correlation Analysis
# =========================================================================


class TestGraspCorrelationAnalysis:
    """Tests for ResultsAnalyzer.analyze_grasp_correlation()."""

    def test_overall_success_rate(self, phase_b_trials):
        """Overall success rate matches our simulated data."""
        analyzer = ResultsAnalyzer(phase_b_trials)
        report = analyzer.analyze_grasp_correlation()
        # 9/10 + 7/10 + 1/5 = 17/25 = 0.68
        assert abs(report.overall_success_rate - 0.68) < 0.01

    def test_success_by_hamming_band(self, phase_b_trials):
        """Success rates decrease with Hamming distance."""
        analyzer = ResultsAnalyzer(phase_b_trials)
        report = analyzer.analyze_grasp_correlation()
        bands = report.success_by_hamming_band
        assert bands["0-2"] > bands["9+"]

    def test_success_by_match_type(self, phase_b_trials):
        """EXACT matches have higher success than FUZZY."""
        analyzer = ResultsAnalyzer(phase_b_trials)
        report = analyzer.analyze_grasp_correlation()
        types = report.success_by_match_type
        assert "EXACT" in types
        assert "FUZZY" in types
        assert types["EXACT"] > types["FUZZY"]

    def test_force_deviation(self, phase_b_trials):
        """Mean force deviation is computed correctly."""
        analyzer = ResultsAnalyzer(phase_b_trials)
        report = analyzer.analyze_grasp_correlation()
        assert report.mean_force_deviation_N > 0

    def test_no_phase_b_raises(self):
        """Analyzing with no Phase B grasp data raises ValueError."""
        analyzer = ResultsAnalyzer([
            TrialResult(phase_id="A", trial_index=0, object_id="x"),
        ])
        with pytest.raises(ValueError, match="No Phase B"):
            analyzer.analyze_grasp_correlation()


# =========================================================================
#  Phase C: Convergence Analysis
# =========================================================================


class TestConvergenceAnalysis:
    """Tests for ResultsAnalyzer.analyze_convergence()."""

    def test_first_success_detected(self, phase_c_trials):
        """First success trial is correctly identified."""
        analyzer = ResultsAnalyzer(phase_c_trials)
        report = analyzer.analyze_convergence()
        # Trial index 3 is the first success (1-indexed = 4)
        assert report.per_object_trials_to_first_success["novel_obj_1"] == 4

    def test_convergence_to_90pct(self, phase_c_trials):
        """90% success rate is eventually reached."""
        analyzer = ResultsAnalyzer(phase_c_trials)
        report = analyzer.analyze_convergence()
        assert report.per_object_trials_to_90pct["novel_obj_1"] is not None

    def test_llm_vs_hash_counts(self, phase_c_trials):
        """LLM calls are counted for misses, hash lookups for hits."""
        analyzer = ResultsAnalyzer(phase_c_trials)
        report = analyzer.analyze_convergence()
        assert report.total_llm_calls == 3    # First 3 trials are MISS
        assert report.total_hash_lookups == 17  # Remaining 17 are hits

    def test_convergence_curve_length(self, phase_c_trials):
        """Convergence curve has one entry per trial."""
        analyzer = ResultsAnalyzer(phase_c_trials)
        report = analyzer.analyze_convergence()
        curve = report.convergence_curves["novel_obj_1"]
        assert len(curve) == 20

    def test_convergence_curve_increases(self, phase_c_trials):
        """Rolling success rate generally increases after promotion."""
        analyzer = ResultsAnalyzer(phase_c_trials)
        report = analyzer.analyze_convergence()
        curve = report.convergence_curves["novel_obj_1"]
        # First point should be 0 (miss), last point should be near 1.0
        assert curve[0] == 0.0
        assert curve[-1] > 0.9

    def test_no_phase_c_raises(self):
        """Analyzing with no Phase C data raises ValueError."""
        analyzer = ResultsAnalyzer([
            TrialResult(phase_id="A", trial_index=0, object_id="x"),
        ])
        with pytest.raises(ValueError, match="No Phase C"):
            analyzer.analyze_convergence()


# =========================================================================
#  Phase D: Latency Analysis
# =========================================================================


class TestLatencyAnalysis:
    """Tests for ResultsAnalyzer.analyze_latency()."""

    def test_p50_reasonable(self, phase_d_trials):
        """P50 latency values are close to the simulated means."""
        analyzer = ResultsAnalyzer(phase_d_trials)
        report = analyzer.analyze_latency()
        # image_capture mean = 2.0 ms, hash_computation mean = 0.5 ms
        assert abs(report.component_p50_ms["image_capture"] - 2.0) < 0.5
        assert abs(report.component_p50_ms["hash_computation"] - 0.5) < 0.2

    def test_p99_higher_than_p50(self, phase_d_trials):
        """P99 should be >= P50 for all components."""
        analyzer = ResultsAnalyzer(phase_d_trials)
        report = analyzer.analyze_latency()
        for key in report.component_p50_ms:
            assert report.component_p99_ms[key] >= report.component_p50_ms[key]

    def test_fast_path_total(self, phase_d_trials):
        """Fast path total = capture + hash + lookup, should be < 20 ms."""
        analyzer = ResultsAnalyzer(phase_d_trials)
        report = analyzer.analyze_latency()
        # capture ~2 + hash ~0.5 + lookup ~0.03 ≈ 2.5 ms
        assert report.total_fast_path_p50_ms < 20.0
        assert report.total_fast_path_p99_ms < 20.0

    def test_registry_lookup_sub_millisecond(self, phase_d_trials):
        """Registry lookup P99 should be well under 1 ms in simulation."""
        analyzer = ResultsAnalyzer(phase_d_trials)
        report = analyzer.analyze_latency()
        assert report.component_p99_ms["registry_lookup"] < 1.0

    def test_no_phase_d_raises(self):
        """Analyzing with no Phase D data raises ValueError."""
        analyzer = ResultsAnalyzer([
            TrialResult(phase_id="A", trial_index=0, object_id="x"),
        ])
        with pytest.raises(ValueError, match="No Phase D"):
            analyzer.analyze_latency()


# =========================================================================
#  Full Report Export
# =========================================================================


class TestReportExport:
    """Tests for the combined report export pipeline."""

    def test_export_report_all_phases(
        self, phase_a_trials, phase_b_trials, phase_c_trials, phase_d_trials,
        tmp_path,
    ):
        """export_report() includes all phases when data is present."""
        all_trials = phase_a_trials + phase_b_trials + phase_c_trials + phase_d_trials
        analyzer = ResultsAnalyzer(all_trials)
        filepath = str(tmp_path / "report.json")
        report = analyzer.export_report(filepath)

        assert "phase_a_hash_robustness" in report
        assert "phase_b_grasp_correlation" in report
        assert "phase_c_convergence" in report
        assert "phase_d_latency" in report

        # Verify JSON file was written
        with open(filepath) as f:
            on_disk = json.load(f)
        assert on_disk["framework"] == "Golden Codex Lab Kit v1.0"

    def test_export_report_partial(self, phase_a_trials, tmp_path):
        """export_report() only includes phases with available data."""
        analyzer = ResultsAnalyzer(phase_a_trials)
        filepath = str(tmp_path / "partial.json")
        report = analyzer.export_report(filepath)

        assert "phase_a_hash_robustness" in report
        assert "phase_b_grasp_correlation" not in report
