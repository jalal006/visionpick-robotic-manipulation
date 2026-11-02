# VisionPick roadmap

Only Milestone 1 is implemented. Each later milestone needs its own acceptance
evidence; this list is a plan, not a capability claim.

1. **Simulation foundation:** Ubuntu 24.04, Jazzy, Harmonic, UR5e, controllers,
   A/B/home motion with measured feedback, MoveIt and RViz execution.
2. **Manipulation workcell:** add a simulation-compatible gripper, table, blocks,
   collision geometry and repeatable reset. Resolve/validate physical contact
   geometry before relying on Gazebo contacts.
3. **Camera and geometry:** add a simulated camera, verify intrinsics/extrinsics,
   image transport and TF2 transformations into the robot base frame.
4. **Perception:** detect colored blocks with OpenCV; quantify pixel/pose error
   against simulator ground truth over randomized placements.
5. **Grasp and place:** produce feasible grasp poses, approach/retreat motions,
   collision-aware plans and verified simulated attachment/release.
6. **Autonomous sorting:** orchestrate detection, planning, grasping, sorting and
   visual placement verification in an explicit task state machine.
7. **Failure recovery:** detect misses, stale images, planning failures and
   placement errors; retry within bounded policies and record reasons.
8. **Benchmark and release:** seeded trials, success/time/error metrics, repeatable
   results, concise demo, installation guide and honestly scoped portfolio claims.

Milestone 0 means no verified implementation. The 2026-10-31 external check was
Milestone 0; 2026-11-02 establishes local Milestone 1 evidence. Remote publication
remains a separate unresolved checkpoint.

Next: publish the verified foundation, stabilize upstream shutdown behavior, then
begin Milestone 2. Do not advertise autonomous camera-guided sorting yet.
