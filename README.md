# VisionPick — Autonomous Camera-Guided Robotic Manipulation

A simulation-only robotics portfolio project: a UR5e will eventually locate randomly
placed and rotated colored blocks using a rendered overhead camera, estimate grasp poses, plan
collision-aware movements, sort objects, verify placement, recover from failures,
and benchmark at least 30 seeded randomized scenes.

**Milestone 2 update, 2026-11-14:** a static worktable and fixture now share one
geometry configuration between Gazebo and MoveIt. **Milestone 2 is COMPLETE:** real
collision-aware execution, measured settling, blocked-goal rejection and fresh
headless/GUI launches passed. See [Milestone 2 verification](docs/MILESTONE_02_VERIFICATION.md).

**Preserved checkpoint, 2026-11-08: Milestone 1 verified locally.** Real Gazebo joint motion,
A/B/home feedback verification, automatic MoveIt planning/execution, and one actual
RViz MotionPlanning **Plan & Execute** operation have passed. The checkpoint is
published on [GitHub](https://github.com/jalal006/visionpick-robotic-manipulation). Read
[latest verification](docs/MILESTONE_01_RECHECK_2026-11-08.md) and
[limitations](docs/ENVIRONMENT.md) before presenting this work.

This is independent of ReConFactory. No camera, gripper, perception, AI, sorting,
or custom ROS package is implemented yet.

## Run Milestone 2

In **Windows PowerShell**:

```powershell
wsl -d Ubuntu-24.04 -u ahadd --cd /home/ahadd/visionpick_ws
```

From the plain Ubuntu app (`jalal@JalalLaptop`), use
`wsl.exe -d Ubuntu-24.04 -u ahadd --cd /home/ahadd/visionpick_ws` instead.
In the resulting `ahadd` terminal:

```bash
source scripts/common.sh
python3 -m pytest -q
bash scripts/launch_workcell.sh
```

Wait for **SCENE_READY**. Open a second terminal, enter the same WSL workspace,
then run:

```bash
source scripts/common.sh
python3 scripts/verify_workcell.py
```

Expected: `negative_test`, three `executed` records (safe A, safe B, home), then
`PASS`. Watch the normal-colored robot during execution; orange is the RViz goal
overlay. These movements are larger than the Milestone 1 smoke motions.
Do not click Plan/Execute or run another motion client during verification:
the negative control temporarily removes only the fixture from MoveIt, never
executes that control plan, and restores the fixture before any motion.

Use `bash scripts/launch_workcell.sh gui:=false` to run the same real simulation
without windows. **Do not run both milestone launchers together.** Both share a
lock; the new launcher also rejects an existing world in the Gazebo partition.
Stop with **Ctrl+C in the launch terminal**. Its supervisor cleans up only its own
launch session; the upstream shutdown crash is not claimed fixed.

The worktable is a solid 0.8 × 1.2 × 0.3 m box beside the floor-mounted robot.
A 0.18 × 0.24 × 0.6 m fixture stands on it. Coordinates, frames and targets are in
[config/workcell.json](config/workcell.json); `world` and `base_link` coincide.
Readback verifies actual collision geometry, not just colored markers.

A failed verifier exits nonzero and records the reason without blind recovery.
After inspecting a failure, stop and relaunch to recreate the world and home pose.
Milestone 1 commands below remain available and also pass in the workcell from home.

## Run Milestone 1

Open **Windows PowerShell** from the Start menu and run:

```powershell
wsl -d Ubuntu-24.04 --cd '~'
```

The plain **Ubuntu** app opens a separate distribution with a different home
directory. From inside that app, enter `wsl.exe -d Ubuntu-24.04 --cd '~'`
first. Confirm `echo "$WSL_DISTRO_NAME"` prints `Ubuntu-24.04`.
Do not paste PowerShell's `wsl` command into Bash; use `wsl.exe` there.

**In that Ubuntu-24.04 terminal**, enter the project and source its environment.
Every new terminal needs both `cd ~/visionpick_ws` and `source scripts/common.sh`.
The runnable workspace is on the Linux filesystem; the Windows folder is only
a review snapshot:

```bash
cd ~/visionpick_ws
bash scripts/setup_dependencies.sh
bash scripts/check_environment.sh
python3 -m pytest -q
source scripts/common.sh
bash scripts/launch_simulation.sh
```

Leave the simulation terminal open. Open a **second Windows PowerShell** window,
run `wsl -d Ubuntu-24.04 --cd '~'`, then paste this complete block:

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
velocity/acceleration. Peak acceleration is checked against live MoveIt limits
and capped at 0.1 rad/s² (also no more than 10% of the configured limit).
Segments undergo URDF soft-limit and sampled MoveIt collision
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
| 2 | Table, fixture, collision-aware execution and blocked-goal rejection | Locally verified |
| 3 | Simulated camera, calibration and TF2 geometry | Planned |
| 4 | OpenCV colored-block detection and pose estimation | Planned |
| 5 | Simulated gripper, objects, collision-aware grasp and place | Planned |
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

The public repository is [jalal006/visionpick-robotic-manipulation](https://github.com/jalal006/visionpick-robotic-manipulation).
Publication was verified by matching the local commit to remote main.
See [project status](docs/PROJECT_STATUS.md) for the known pushed implementation SHA.
