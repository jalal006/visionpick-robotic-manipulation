# VisionPick — Autonomous Camera-Guided Robotic Manipulation

A simulation-only robotics portfolio project: a UR5e will eventually locate randomly
placed colored blocks in simulated camera images, estimate grasp poses, plan
collision-aware movements, sort objects, verify placement, recover from failures,
and benchmark randomized trials.

**Checkpoint, 2026-11-02: Milestone 1 verified locally.** Real Gazebo joint motion,
A/B/home feedback verification, automatic MoveIt planning/execution, and one actual
RViz MotionPlanning **Plan & Execute** operation have passed. Publication is
pending GitHub authentication/repository access. Read
[verification](docs/MILESTONE_01_VERIFICATION.md) and
[limitations](docs/ENVIRONMENT.md) before presenting this work.

This is independent of ReConFactory. No camera, gripper, perception, AI, sorting,
or custom ROS package is implemented yet.

## Run Milestone 1

From Windows PowerShell:

```powershell
wsl -d Ubuntu-24.04
```

Use the Linux filesystem workspace, not a build under `/mnt/c`:

```bash
cd ~/visionpick_ws
bash scripts/setup_dependencies.sh
bash scripts/check_environment.sh
python3 -m pytest -q
source scripts/common.sh
bash scripts/launch_simulation.sh
```

Leave that terminal open. In a second **Ubuntu-24.04** terminal:

```bash
cd ~/visionpick_ws
source scripts/common.sh
bash scripts/check_ros_interfaces.sh
python3 scripts/verify_motion.py --mode direct
python3 scripts/verify_motion.py --mode moveit
python3 scripts/verify_motion.py --mode direct --return-home
```

Expected: the UR5e moves in Gazebo; all three movements in each full verification
run emit `verified`, followed by `PASS`. Each command exits nonzero on failure.
A successful action alone is insufficient: increasing joint timestamps, measured
motion, and settled final errors no greater than **0.02 rad** are required.

The scripts use ROS domain **73** and Gazebo partition **visionpick_m1** by default.
Use identical settings in every terminal. The launcher refuses an existing robot
stack in that domain. Never also start the official control-only launch.

The exact underlying command is:

```bash
ros2 launch ur_simulation_gz ur_sim_moveit.launch.py ur_type:=ur5e
```

No colcon build is needed: official binary packages provide the robot and launch
files; our Python utilities run directly. `src/` is reserved for future packages.
When a real package is added, initialize rosdep if needed, run
`rosdep install --from-paths src --ignore-src --rosdistro jazzy -y`, then
`colcon build --symlink-install` and source `install/setup.bash`.

## Home and motion scope

Controller order is discovered, then checked against six actual joints:

`shoulder_pan, shoulder_lift, elbow, wrist_1, wrist_2, wrist_3` (each ends in `_joint`).

Documented startup home, radians: **[0, -1.57, 0, -1.57, 0, 0]**.
A full verification run captures the measured startup pose as its return target.
Pose A adds +0.10 rad to shoulder pan and +0.08 rad to wrist 3; Pose B subtracts
the same offsets from home. Direct segments last 6 seconds, with zero endpoint
velocity/acceleration, and undergo URDF soft-limit and sampled MoveIt collision
checks. This is a small empty-world smoke test, not a general manipulation planner.

The official SRDF calls its near-equivalent pose `up`. Its named `home` instead
sets wrist 1 to zero. Do not confuse these two definitions. `--return-home`
requests the documented startup pose, still rejecting any joint step over 0.25 rad.

For the RViz procedure and passive evidence recorder, see
[Milestone 1 verification](docs/MILESTONE_01_VERIFICATION.md).

## Architecture and roadmap

`MoveIt / verification client → FollowJointTrajectory → active scaled controller
→ gz_ros2_control → Gazebo UR5e → /joint_states and TF`.

| Milestone | Intended outcome | State |
|---|---|---|
| 1 | Reproducible UR5e + Gazebo + MoveIt, measured A/B/home | Locally verified |
| 2 | Manipulation workcell, simulated gripper and objects | Planned |
| 3 | Simulated camera, calibration and TF2 geometry | Planned |
| 4 | OpenCV colored-block detection and pose estimation | Planned |
| 5 | Collision-aware grasp and place planning | Planned |
| 6 | Autonomous sorting and placement verification | Planned |
| 7 | Failure detection, recovery and randomized scenarios | Planned |
| 8 | Repeatable benchmarks, demo and portfolio release | Planned |

Details: [architecture](docs/ARCHITECTURE.md), [roadmap](docs/ROADMAP.md),
[project status](docs/PROJECT_STATUS.md), [environment](docs/ENVIRONMENT.md).

## Evidence, limitations and publication

Compact observed numeric evidence is tracked in
[the evidence JSON](docs/evidence/milestone01-results.json).
Raw logs, screenshots, caches and videos are ignored. The measured tiny direct
controller errors reflect ideal simulated position control, not real-robot accuracy.

Known upstream limitations include software rendering, shutdown failures, robot-name
warnings and Gazebo mesh-collision warnings. No physical collision/contact or grasp
performance is claimed. Follow the shutdown guidance in the environment document.

No license has been selected on the owner's behalf. No LICENSE file is included;
choose a license before inviting reuse. Upstream packages keep their own licenses.

The intended remote is `https://github.com/jalal006/visionpick-robotic-manipulation.git`.
Do not describe it as published until its remote SHA is verified.
