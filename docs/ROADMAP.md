# VisionPick roadmap

Checkpoint: 2026-11-14. Milestones 1 and 2 are verified locally. Publication of
this checkpoint is reported after committing and matching remote main.

1. **Simulation foundation — COMPLETE:** official UR5e, Jazzy, Harmonic,
   controllers, measured A/B/home motion, MoveIt and RViz execution.
2. **Tabletop workcell — COMPLETE:** canonical table/fixture geometry shared by
   Gazebo and MoveIt, safe trajectory execution, measured settling, blocked-goal
   rejection with a successful planning-only control case. Gripper research only.
3. **Camera and geometry — PLANNED:** simulated overhead RGB camera,
   intrinsics/extrinsics, image transport, calibration and TF2 base-frame transforms.
4. **Perception — PLANNED:** OpenCV colored-block detection, randomized positions
   and orientations, pixel/pose errors against simulator ground truth.
5. **Gripper and grasp/place — PLANNED:** validate a simulated two-finger gripper,
   objects, contact or an explicitly validated attachment constraint, approach,
   retreat, collision-aware transport, release and placement checks.
6. **Autonomous sorting — PLANNED:** explicit task state machine linking perception,
   planning, grasping and visual placement verification.
7. **Failure recovery — PLANNED:** bounded retries for stale images, misses,
   failed plans and incorrect placement, with recorded outcomes.
8. **Benchmark and release — PLANNED:** at least 30 seeded randomized scenes,
   success/time/error metrics, reproducible demo and honestly scoped portfolio claims.

The owner's November 14 scope moves gripper/object integration out of Milestone 2.
The next dependency is camera geometry on the verified workcell. No Milestone 3
implementation is included. Camera-guided sorting remains the end goal.
