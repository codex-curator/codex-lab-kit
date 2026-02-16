# Experiment Protocol — Detailed Walkthrough

## Overview

The Golden Codex validation protocol consists of four phases testing different aspects of hash-based robotic manipulation. The protocol generates 960 total trials across 15 objects.

## Phase A: Hash Robustness (No Hardware Required)

**Objective:** Determine whether perceptual hashes are stable enough to serve as object identifiers under varying conditions.

**Setup:**
- 10 YCB objects from the standard benchmark
- Camera at fixed overhead position
- 12 viewpoints (30-degree turntable increments or manual rotation)
- 3 lighting conditions (ambient, overhead bright, directional side)

**Procedure:**
1. Place object in workspace
2. For each viewpoint (12 total):
   - Capture image
   - Compute dHash (64-bit)
   - Record hash, viewpoint index, lighting condition
3. Repeat for all 3 lighting conditions
4. Repeat for all 10 objects

**Metrics:**
- Intra-class Hamming distance (mean, std)
- Inter-class Hamming distance (mean)
- ROC curves at various thresholds
- False positive rate at threshold=5
- Recall at threshold=5

**Acceptance Criteria:**
- Intra-class Hamming mean < 6
- Inter-class Hamming mean > 15
- Recall at threshold 5 > 0.90
- False positive rate < 0.01

## Phase B: Hash-to-Grasp Correlation (Hardware Required)

**Objective:** Determine whether hash match quality predicts manipulation success.

**Setup:**
- 10 YCB objects (same as Phase A)
- Robot with gripper and force sensor
- Objects placed in randomized positions

**Procedure:**
1. Present object to camera
2. Compute hash and lookup in registry
3. Execute the SKB-prescribed grasp action
4. Record: binary success, actual force (N), planned force (N), execution time (ms)
5. Repeat 10 times per object

**Metrics:**
- Grasp success rate by Hamming distance band (0-2, 3-5, 6-8, 9+)
- Mean force deviation (actual vs planned)
- Execution time distribution
- Post-action hash shift

**Acceptance Criteria:**
- Exact match grasp success > 85%
- Fuzzy match grasp success > 70%

## Phase C: Loop Closure Convergence (Hardware Required)

**Objective:** Measure how quickly the system learns new objects via slow path recovery.

**Setup:**
- 5 novel objects NOT in the initial registry
- Same robot and camera setup as Phase B

**Procedure:**
1. Present novel object (guaranteed MISS on first encounter)
2. System triggers slow path (LLM generates manipulation plan)
3. Execute plan, record success/failure
4. If successful, promote hash-plan mapping to fast path
5. Repeat 50 times per object

**Metrics:**
- Trials to first successful grasp
- Trials to reliable (>90%) success
- Total LLM calls vs hash lookups
- Convergence curve
- Promotion count

**Acceptance Criteria:**
- Median trials to 90% success < 10
- Final success rate > 90%

## Phase D: Latency Profile (Hardware Required)

**Objective:** Measure real-world timing of each pipeline component.

**Setup:**
- 5 objects from Phase A (known objects)
- Full pipeline (camera - hash - registry - action)

**Procedure:**
1. 10 warmup iterations (discard)
2. 50 timed iterations per object
3. Measure each component separately

**Timing Components:**
- Image capture (ms)
- Hash computation (ms)
- Registry lookup (ms)
- ROS2 transport (ms)
- Motion planning (ms)
- Total perception-to-action (ms)

**Acceptance Criteria:**
- Hash lookup p99 < 1.0 ms
- Total fast-path p99 < 20.0 ms
