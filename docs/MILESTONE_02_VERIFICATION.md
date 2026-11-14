# Milestone 2 verification — 2026-11-14

**Result: COMPLETE.** The acceptance gate passed in real Gazebo Harmonic and MoveIt
Jazzy. Final GUI-enabled run ended at 10:42:18 UTC / 11:42:18 Europe/Prague.
A separate headless run also passed. No physical robot or hardware was used.

## Baseline and preserved state

Initial local main and remote main:
`3586f036b765835145b11c70b849123a913b8455`. Working tree clean, no simulation active.
Original 21 tests, interface audit, direct A/B/home, MoveIt A/B/home and return-home
all passed before implementation. No unpushed local work was found.
Original scripts and historical Milestone 1 evidence are preserved.

Workspace is `/home/ahadd/visionpick_ws` in Ubuntu-24.04 as ahadd, not the separate
Ubuntu/jalal home. ROS_DOMAIN_ID=73; GZ_PARTITION=visionpick_m1.
No packages, global settings or shared upstream configurations were changed.

## Geometry and installed APIs

The live official UR5e URDF/SRDF, FK service, controller joint order and limits were
inspected. Startup tool position in world is approximately
[0.000810, 0.232900, 1.079400] m. World and base_link coincide; base_link_inertia
contains the upstream pi yaw rotation and must not be confused with base_link.

| Object | Dimensions XYZ (m) | Center XYZ (m) | Rotation |
|---|---|---|---|
| visionpick_table | [0.8, 1.2, 0.3] | [0.7, 0, 0.15] | identity |
| visionpick_fixture | [0.18, 0.24, 0.6] | [0.6, 0.13, 0.6] | identity |

This is a low solid worktable/plinth beside the floor-mounted robot. Its near edge
is x=0.3 m and top z=0.3 m. The fixture bottom is z=0.3 m. The robot base is not
embedded in the table. Both are static boxes with matching visual/collision geometry.
Configuration is canonical in `config/workcell.json`, reused for generated world
and MoveIt objects. Gazebo live poses plus expanded live SDF collision dimensions
and MoveIt readback all matched. Repeated ADD operations retained exactly the same IDs.

The installed official combined launch does not forward a custom world explicitly.
The wrapper includes supported `ur_sim_control.launch.py world_file:=...` and
`ur_moveit.launch.py use_sim_time:=true` once each. One controller manager,
one Gazebo robot and one move_group share the same clock.

Discovered interfaces:

- /apply_planning_scene: moveit_msgs/srv/ApplyPlanningScene
- /get_planning_scene: moveit_msgs/srv/GetPlanningScene
- /check_state_validity: moveit_msgs/srv/GetStateValidity
- /compute_fk: moveit_msgs/srv/GetPositionFK
- /move_action: moveit_msgs/action/MoveGroup
- /execute_trajectory: moveit_msgs/action/ExecuteTrajectory
- /scaled_joint_trajectory_controller/follow_joint_trajectory:
  control_msgs/action/FollowJointTrajectory

Live group: ur_manipulator; tip: tool0; planning frame: world. The controller was
active and the joint-state broadcaster supplied fresh increasing simulated stamps.
The live hardware plugin was gz_ros2_control/GazeboSimSystem.

## Actual targets and execution

Joint order: shoulder_pan, shoulder_lift, elbow, wrist_1, wrist_2, wrist_3,
each suffixed _joint. All values below are radians.

| State | Requested vector | State-validity result |
|---|---|---|
| home | [0, -1.57, 0, -1.57, 0, 0] | valid |
| safe_a | [0.5, -1.1, 0.3, -1.57, 0, 0] | valid |
| safe_b | [-0.6, -1.1, 0.3, -1.57, 0, 0] | valid |
| blocked | [0, -0.8, 0, -1.57, 0, 0] | fixture collision |

The verifier planned first with MoveGroup plan_only=True, at 5% velocity and
acceleration scaling, then checked derivatives, limits and sampled validity of
the returned trajectory before executing that exact trajectory through MoveIt.
Goal joint tolerance was 0.001 rad; final tracking tolerance was 0.02 rad.
No invalid trajectory was sent directly to a controller.

| Executed target | Plan points | Checked path states | Measured states checked | Feedback samples | Wall execution (s) | Maximum tracking error (rad) |
|---|---:|---:|---:|---:|---:|---:|
| safe_a | 40 | 110 | 51 | 2011 | 4.3280 | 3.233117107370731e-10 |
| safe_b | 216 | 639 | 325 | 10695 | 23.4294 | 6.615790904473604e-10 |
| home | 46 | 128 | 61 | 2313 | 4.9652 | 8.82245577808749e-10 |

Each executed action returned status 4 (SUCCEEDED), MoveIt code 1 (SUCCESS).
Measurements confirmed motion and at least three new settled samples spanning
0.2 simulated seconds. Exact planned endpoints, measured vectors, excursions,
planning durations and simulation durations are in the compact JSON.
Tracking error is measured against the plan, whose endpoint can differ from the
requested vector within the goal tolerance. Small errors reflect ideal simulation.

Thirteen of 21 samples on the direct joint interpolation between safe A and B
were invalid. The accepted MoveIt trajectory avoided those collisions. OMPL is
not deterministic here; future valid paths, point counts and durations may differ.

## Negative case and causal control

The blocked target is inside the actual joint limits. State validity reported
fixture contacts with forearm_link, wrist_1_link, wrist_2_link and wrist_3_link,
with penetration depths about 0.0387, 0.0295, 0.0935 and 0.0989 m.

With the fixture, the planning action aborted (status 6), returned generic OMPL
FAILURE 99999 and an empty trajectory. The server explicitly logged a fixture/
forearm collision and inability to sample valid goal states. This installed API
does not return GOAL_IN_COLLISION for this case; the report does not pretend it does.

For the control, only the fixture was removed from MoveIt while the robot remained
at home and Gazebo retained the fixture. The same target then became valid and
planned with status 4/code 1 and 57 points. This plan was never executed. A finally
block restored the fixture, geometry was read back, and the goal was invalid again.
This combination distinguishes collision rejection from a missing controller,
invalid joint limit, unavailable service or timeout. No collision exceptions were added.

## Tests, launches and observed development failures

All **61 tests passed**: 21 existing, 30 configuration/geometry/scene/joint guards,
and 10 real-report integrity regression tests. The latter check recorded evidence;
they do not replace live integration. Python compilation and shell syntax passed.
Duplicate launch returned exit 1 with the existing-launch message.

The original Milestone 1 direct, MoveIt and return-home checks passed again with
the workcell installed. The final GUI launch passed the original interface audit.
Both headless and GUI runs used real physics/controller feedback. A final direct
nominal-home command was also run before shutdown.

Development failures are retained under ignored logs:
initial scene setup raced controller activation (fixed by waiting);
the visual scene message omitted collision/static data (fixed by expanded SDF);
the first taller table clipped the proposed safe B state (geometry corrected before
execution); the initial contact monitor incorrectly expected empty heartbeat messages
(fixed against Harmonic source/topics); synchronous Gazebo queries conflicted with
Python subscriptions (isolated in a helper); the blocked action returned generic
FAILURE instead of a collision-specific code (handled with independent causal evidence).
No failed attempt is represented as a passing integration run.

## Collision and shutdown limitations

No robot/workcell contact messages occurred during accepted trajectories.
Publisher presence and an advancing physics clock were checked. Harmonic only
publishes nonempty contacts, so silence alone is not proof: matching geometry,
planned-path checks, measured-state checks and real executed feedback are also used.
Collision checks are sampled, not mathematically continuous, and this milestone does
not calibrate friction, grasp force, contact fidelity or payload behavior.

DART's initial mesh-construction debug warnings were investigated in the matching
Gazebo source: meshes are subsequently attached through AttachMeshShape.
No final mesh-ignore/load-failure warning was found in the final launch log.
Official robot meshes remain unchanged. See ENVIRONMENT.md for source links.
The upstream URDF/SRDF robot-name warning and missing perception/octomap notices
also remain. No perception capability is claimed.

WSLg uses software rendering. The historical move_group shutdown crash is not fixed.
The new supervisor limits cleanup to its private launch session, avoiding unrelated
ROS/Gazebo processes. Test simulations are closed after verification.

## Reproduction and scope

Follow the complete two-terminal instructions in README.md. Main commands:

```bash
source scripts/common.sh
python3 -m pytest -q
bash scripts/launch_workcell.sh
# Second terminal, same distribution/user/workspace:
source scripts/common.sh
python3 scripts/verify_workcell.py
```

Wait for SCENE_READY, then watch the measured robot during execution. Do not manually
execute other goals during the negative-control test. Reports and raw logs default
to ignored logs/. Stop the launcher with Ctrl+C; relaunch to reset the world.

No camera, gripper, dynamic grasp objects, recognition, sorting or AI was added.
[Gripper feasibility](GRIPPER_FEASIBILITY.md) is research only. Milestone 3 was not begun.
The final commit and remote SHA are reported after publication.

For a beginner: the planning scene is MoveIt's map of the robot and obstacles.
Collision objects give that map real shapes. State validity asks whether one robot
pose overlaps those shapes or itself. A trajectory is a timed series of joint poses;
planning finds one, execution sends it to the controller, and feedback checks what
the simulated robot actually did.

Official references:
[planning scene](https://moveit.picknik.ai/main/doc/examples/planning_scene/planning_scene_tutorial.html),
[MoveGroup](https://moveit.picknik.ai/main/doc/examples/move_group_interface/move_group_interface_tutorial.html),
[scene monitor](https://moveit.picknik.ai/main/doc/concepts/planning_scene_monitor.html),
[Jazzy gz_ros2_control](https://control.ros.org/jazzy/doc/gz_ros2_control/doc/index.html),
[UR simulation](https://github.com/UniversalRobots/Universal_Robots_ROS2_GZ_Simulation).
