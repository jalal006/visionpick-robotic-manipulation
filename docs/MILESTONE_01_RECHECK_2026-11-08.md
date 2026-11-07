# Milestone 1 recheck — 2026-11-08

**Observed result: PASS, locally complete.** This recheck reuses the November 2
foundation and adds an explicit acceleration guard; it does not implement Milestone 2.

Raw timestamps are UTC. Logs beginning 2026-11-07 at 23:xx UTC correspond to
November 8 at 00:xx in Europe/Prague. No timestamps were rewritten.

## Environment and observed checks

- Ubuntu-24.04 WSL2, Ubuntu 24.04.5, ROS Jazzy, Python 3.12.3.
- Harmonic 8.15.0, official ur_simulation_gz 2.5.0, MoveIt 2.12.4,
  gz_ros2_control 1.2.20. Package versions match the prior audit.
- 4 logical CPUs, about 15 GiB RAM, 4 GiB swap and 949 GiB free Linux disk.
- WSLg DISPLAY=:0, WAYLAND_DISPLAY=wayland-0, Mesa 25.2.8 llvmpipe software rendering.
- No ROS/Gazebo stack was running at the initial audit.
- Dependency setup reported all packages installed; no apt mutation.
- 21 pytest cases passed; Python compilation and shell syntax checks passed.
- Fresh-terminal launch through scripts/launch_simulation.sh passed.
- Actual Gazebo world/model empty/ur, with live GazeboSimSystem hardware.
- Active joint_state_broadcaster and scaled_joint_trajectory_controller.
- Active action /scaled_joint_trajectory_controller/follow_joint_trajectory.
- /clock, /joint_states, /tf and /tf_static all received.
- use_sim_time=true on controller_manager, move_group, robot_state_publisher
  and the actual RViz node /rviz2_moveit.
- Controller joint order discovered and incoming feedback remapped by name.
- Live MoveIt acceleration settings: 5 rad/s² on all six joints.
- No unexpected controller crash during these movement sequences.

Full commands: [PROJECT_STATUS.md](PROJECT_STATUS.md). Both official launch files
were re-inspected with --show-args; only the combined MoveIt launch was started.

## Actual measured movement

Joint order (radians): [shoulder_pan, shoulder_lift, elbow, wrist_1, wrist_2,
wrist_3], with _joint suffixes in ROS. Direct home is [0, -1.57, 0, -1.57, 0, 0].
Full tests capture measured startup home. A offsets pan/wrist3 by +0.10/+0.08 rad;
B offsets them by -0.10/-0.08 rad relative to home.

| Run | Step | Measured joints (rounded) | Max error (rad) |
|---|---|---|---|
| direct | pose_a | [0.100000, -1.570000, 0.000000, -1.570000, -0.000000, 0.080000] | 1.30383204e-12 |
| direct | pose_b | [-0.100000, -1.570000, 0.000000, -1.570000, -0.000000, -0.080000] | 1.00987274e-12 |
| direct | home | [-0.000000, -1.570000, 0.000000, -1.570000, -0.000000, -0.000000] | 1.53040522e-12 |
| moveit | pose_a | [0.103836, -1.565003, 0.000232, -1.567599, -0.003982, 0.080626] | 0.00499699249 |
| moveit | pose_b | [-0.104668, -1.571686, 0.003450, -1.574230, -0.004190, -0.075291] | 0.0047086972 |
| moveit | home | [-0.002854, -1.566015, -0.002930, -1.572068, 0.002243, 0.001935] | 0.00398461976 |
| home | home | [-0.000000, -1.570000, -0.000000, -1.570000, 0.000000, 0.000000] | 5.37347944e-14 |
| gui | GUI | [0.217766, -1.569911, -0.000071, -1.569947, -0.000053, 0.000037] | 0.0083263641 |
| post-gui-home | home | [0.000000, -1.570000, 0.000000, -1.570000, -0.000000, 0.000000] | 1.59354848e-12 |


All results passed the 0.02 rad (~1.15°) threshold. Direct moves lasted six seconds
plus a 0.2 s initial hold. The guard bounds peak quintic speed/acceleration, uses
URDF soft position limits, and samples 21 collision-validity states. Three new
post-result feedback samples over at least 0.2 simulated seconds must settle
inside tolerance. Tiny direct errors reflect ideal position control.

MoveIt used OMPL, ur_manipulator, /move_action, plan_only=false and 10%
velocity/acceleration scaling. Action status 4 and MoveIt code 1 meant success.
Nonempty plans and measured motion were observed despite empty executed_trajectory
arrays. Direct controller success code was 0.

## Genuine RViz Plan & Execute

The official RViz Joints tab was used to set a shoulder-pan target displayed as
approximately 12°. Velocity and acceleration scaling were both 0.10.
Plan & Execute produced the **Executed** UI label. The launch log recorded RViz
completion, MoveIt execution SUCCEEDED and scaled-controller goal success.

Initial Windows focus handling missed the tab/button clicks; those were not
counted as executions. The inspected Planning tab and subsequent successful
click were followed by the passive observer's PASS result.

Exact planned shoulder target: 0.217765886117489 rad; measured:
0.217765874302213 rad. The nominal rounded 12° target differs by
0.008326364102213 rad, inside tolerance. Actual tracking error against the
planned shoulder value was about 1.18e-8 rad. The observer recorded 37,815 samples,
including the wait for the GUI click, and one new successful goal.

Independent Gazebo link queries showed shoulder-link yaw approximately:
+3.141590 at home, -2.923830 after GUI execution, and -3.141590 rad after return.
The ±pi wrap represents the same home orientation.

~~~bash
gz model --list
gz model -m ur -l shoulder_link
~~~

Final return home passed. Screenshots and raw logs stay local under ignored logs
directories. The screenshot was visually inspected for Executed; screenshots are
not committed because capture boundaries can contain unrelated desktop content.

## Limits of the evidence

This is real Gazebo execution, not mock-hardware-only or RViz-preview-only testing.
Physical contact/grasp dynamics, camera/perception, sorting, long-duration stability
and 30-scene benchmarking were not run.

Known mesh-collision and missing perception-plugin warnings remain. The historical
shutdown crash/leftover-process issue was not repaired or retested in this run;
the simulator was left at home. No colcon/source build was needed because there
is no custom ROS package.

Exact vectors, per-joint errors, action codes, timestamps, limits and Gazebo states:
[evidence JSON](evidence/milestone01-recheck-2026-11-08.json).
Previous verification/evidence files remain historical records.
