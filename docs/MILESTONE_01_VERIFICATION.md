# Milestone 1 verification — 2026-11-02

Latest: [November 8 recheck](MILESTONE_01_RECHECK_2026-11-08.md). The following is the preserved November 2 record.

**Result: COMPLETE locally; GitHub publication not verified.**
The acceptance gate was satisfied with the real Gazebo UR5e and a working MoveIt
execution path. One RViz GUI Plan & Execute was observed. Shutdown reliability
and physical collision fidelity are explicit limitations, not hidden successes.

## Commands actually executed

PowerShell entry: `wsl -d Ubuntu-24.04`.

```bash
cd ~/visionpick_ws
source scripts/common.sh
bash scripts/check_environment.sh
bash scripts/setup_dependencies.sh
python3 -m pytest -q
python3 -m py_compile scripts/*.py
for f in scripts/*.sh; do bash -n "$f"; done

# Terminal 1:
bash scripts/launch_simulation.sh

# Terminal 2, with common.sh sourced:
bash scripts/check_ros_interfaces.sh
python3 scripts/verify_motion.py --mode direct
python3 scripts/verify_motion.py --mode moveit
python3 scripts/verify_motion.py --mode direct --return-home
```

The first simulation used the equivalent official combined launch directly.
A second launch used the project wrapper from a newly sourced shell; interfaces,
direct A/B/home, MoveIt A/B/home, and final return-home all passed again.

## Observed acceptance evidence

| Check | Observed outcome |
|---|---|
| Ubuntu / ROS | Ubuntu-24.04 WSL2, Ubuntu 24.04.5, ROS_DISTRO=jazzy |
| Gazebo | Harmonic 8.15.0, world empty, model ur |
| Simulation backend | Live URDF names GazeboSimSystem; Gazebo logs load gz_ros2_control |
| Controllers | joint_state_broadcaster and scaled_joint_trajectory_controller active |
| Interfaces | Six position commands claimed; position/velocity feedback available |
| ROS data | /clock, /joint_states, /tf, /tf_static received |
| Time | controller manager, move_group, robot_state_publisher and rviz2_moveit use simulation time |
| Direct motion | A, B, home succeeded, each with changing joint feedback and settled endpoints |
| MoveIt action | A, B, home planned and executed; status 4, MoveIt error code 1 |
| RViz GUI | One Plan & Execute succeeded; UI showed Executed; live feedback recorded |
| Gazebo motion | Shoulder-link yaw changed -2.923890 to -3.141590 rad during return home |
| Fresh terminal | Full second launch and verification sequence passed |
| Runtime controller stability | No unexpected controller crash in either motion sequence |
| Pure logic | 15 pytest cases passed |
| Static checks | Python compilation and all shell syntax checks passed |
| Dependency idempotence | Setup reported all required packages already installed; no install |
| Duplicate launch | Wrapper refused the existing stack with exit code 1 |

The active action was
`/scaled_joint_trajectory_controller/follow_joint_trajectory`.
Direct results were action status **4 (SUCCEEDED)** and controller error code
**0 (SUCCESSFUL)**. MoveIt used **/move_action**, group **ur_manipulator**,
OMPL, 10% velocity and acceleration scaling, and **plan_only=False**.
MoveIt returned nonempty planned trajectories but empty `executed_trajectory`
arrays; the independent joint measurements and controller results establish motion.

## Real measured results

Joint order for every vector:
**[shoulder_pan, shoulder_lift, elbow, wrist_1, wrist_2, wrist_3]**, radians.

Home is the measured official startup posture, approximately
**[0, -1.57, 0, -1.57, 0, 0]**. A changes pan/wrist3 by +0.10/+0.08 rad;
B changes them by -0.10/-0.08 rad relative to home. Direct motion has a 0.2 s
initial hold followed by a 6 s segment.

Initial direct run:

| Step | Measured joints (rounded for readability) | Maximum absolute error |
|---|---|---|
| A | [0.100000, -1.570000, 0, -1.570000, 0, 0.080000] | 1.4371e-12 rad |
| B | [-0.100000, -1.570000, 0, -1.570000, 0, -0.080000] | 8.7444e-13 rad |
| Home | [0, -1.570000, 0, -1.570000, 0, 0] | 6.5312e-13 rad |

Initial automatic MoveIt run:

| Step | Measured joints | Maximum absolute error |
|---|---|---|
| A | [0.101925, -1.566728, 0.004906, -1.568836, -0.001712, 0.082135] | 0.00490614 rad |
| B | [-0.096285, -1.574057, 0.004053, -1.573967, -0.003872, -0.078587] | 0.00405691 rad |
| Home | [-0.003691, -1.573957, 0.000072, -1.566230, 0.000116, -0.003655] | 0.00395656 rad |

Fresh launch repeat:

| Test | A max error | B max error | Home max error |
|---|---|---|---|
| Direct | 5.0952e-13 | 8.6826e-13 | 3.7037e-13 |
| MoveIt | 0.00451148 | 0.00491169 | 0.00415473 |

A final direct return to the nominal home measured:
**[-6.1505e-14, -1.5699999999999803, -1.6933e-13,
-1.5699999999998284, -1.0967e-13, 9.0146e-14]**,
maximum error **1.7164e-13 rad**.

The threshold is **0.02 rad (~1.15 degrees)** for this foundation smoke test.
It accommodates MoveIt's ±0.005 rad joint goal region with margin for transient
controller residuals. It is not a grasp-accuracy specification. Three new feedback
samples spanning at least 0.2 simulation seconds must settle inside the threshold.
Recorded excursions must show actual movement for significant commanded changes.
Tiny direct errors are idealized simulated position-control results.

Full requested/measured vectors, per-joint errors, timestamps, sample counts and
action codes are preserved in [compact JSON evidence](evidence/milestone01-results.json).
Thousands of raw samples remain in ignored logs, not in the repository.

## Actual GUI test and exact reproduction procedure

1. Launch the official combined stack once. Restore the Gazebo and RViz windows.
2. In RViz's MotionPlanning panel select group `ur_manipulator`, start state
   `<current>`, velocity scaling 0.10 and acceleration scaling 0.10.
3. In **Joints**, adjust only shoulder_pan_joint slightly from its startup value.
   The observed slider displayed approximately **12 degrees**. It rounds the
   displayed value; the planned target was **0.21770710428 rad**.
4. Optionally start the passive recorder **before** executing:
   `python3 scripts/observe_gui.py --target 0.2094395102 -1.5707963268 0 -1.5707963268 0 0`.
   This nominal 12-degree target is accepted within the same 0.02 rad tolerance.
   Allow at least three seconds for it to establish the historical action baseline.
   For another target, supply its six actual radians in controller order.
5. Return to **Planning**, click **Plan & Execute**. Planning alone or RViz's
   trajectory preview does not count. Observe the Gazebo arm as well.
6. Require RViz **Executed**, a new successful action, a matching nonempty plan,
   changing measured joint positions, and final settled feedback.
7. Return safely with
   `python3 scripts/verify_motion.py --mode direct --return-home`.
   This rejects any move larger than 0.25 rad per joint. For larger deviations,
   inspect and plan a safe return rather than bypassing the check.

Observed GUI measurement: shoulder pan **0.21770709216 rad**, excursion
**0.22139809780 rad** from the preceding measured state. Tracking error against
the exact planned shoulder target was approximately **1.21e-8 rad**. The maximum
difference from the observer's nominal rounded target was **0.00826758 rad**.
The observer recorded **5,664** feedback samples and one new successful goal.

The launch log recorded the RViz Plan and Execute completion, scaled-controller
goal success, and MoveIt trajectory execution SUCCEEDED. A local screenshot shows
RViz's **Executed** label. A second intended GUI return test did **not** execute
and its passive observer timed out; it is not counted as a second GUI success.
The separately verified direct return restored home instead.

Gazebo's own state query was captured before and after that return:

```bash
gz model --list
gz model -m ur -l shoulder_link
```

Shoulder-link yaw changed from **-2.923890** to **-3.141590 rad**, consistent with
the ~0.2177 rad shoulder-joint return and the model's frame offset. This is
simulator entity-state evidence, independent of the RViz display.

## Failures and checks not run

Initial launch dependency failure, verifier development errors (rclpy graph API
and uint8 JSON serialization), and the canceled logging-error goal were retained
in local logs. Corrections preceded the successful full runs. An initial interface
audit used the wrong assumed RViz node name; discovery corrected it to
`/rviz2_moveit`, and the complete audit passed.

Shutdown triggered a move_group executor-destruction segfault and left Gazebo
children. The first restart was refused; only identified VisionPick leftovers
were stopped before the successful clean restart. See
[environment limitations](ENVIRONMENT.md). This checkpoint does not claim robust
upstream shutdown, physical collision validation, long-duration stability, camera,
gripper, grasping, sorting, hardware tests, or a benchmark.

No remote push, remote SHA check, rosdep package build, colcon build, or second
successful GUI operation is claimed. There is no custom ROS package to compile.
