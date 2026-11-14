# Environment audits

## Milestone 2 audit — 2026-11-14 (Europe/Prague)

The canonical Ubuntu-24.04 workspace is `/home/ahadd/visionpick_ws`, user `ahadd`.
Local and remote main initially matched `3586f036b765835145b11c70b849123a913b8455`;
the working tree was clean and no robot stack was running. Domain 73 and partition
`visionpick_m1` are unchanged. Installed Jazzy/Harmonic binaries are reused, with
no dependency installation, source rebuild, global ROS, WSL or graphics changes.
The already installed `gz.transport13` and `gz.msgs10` Python bindings work after
sourcing `scripts/common.sh`. No pip dependency or colcon package was added.

The headless option removes windows only; physics and real controller feedback
remain active. Historical audits below retain their original observations and do
not describe the current authentication or running-process state.

### Mesh and contact warnings investigated

The DART debug messages about initial SDF mesh construction describe an intermediate
stage. The installed-version [Gazebo Sim 8.15.0 source](https://github.com/gazebosim/gz-sim/blob/gz-sim8_8.15.0/src/systems/physics/Physics.cc)
subsequently loads and attaches mesh collisions with `AttachMeshShape`; the
[upstream issue](https://github.com/gazebosim/gz-physics/issues/985) explains this fallback.
Workcell objects use boxes. Official UR robot meshes are retained, tested against
MoveIt collision queries, and observed through workcell contact topics during motion.
No warning is suppressed. This does not establish grasp friction/contact fidelity.

The [Harmonic Contact system](https://github.com/gazebosim/gz-sim/blob/gz-sim8_8.15.0/src/systems/contact/Contact.cc)
publishes only nonempty contact sets. The verifier checks publisher presence and
clock liveness separately; silence is not treated as a sensor heartbeat.

## Rechecked 2026-11-08 (Europe/Prague)

The same Ubuntu-24.04 workspace and binary versions listed below were verified
again: Ubuntu 24.04.5, kernel 6.18.54.1-microsoft-standard-WSL2, Jazzy,
Gazebo 8.15.0 and Python 3.12.3. Current nproc is **4** (previously 16);
about 15 GiB RAM, 4 GiB swap and 949 GiB free disk were observed.
No CPU, graphics or global ROS settings were changed by this recheck.

GLX still reports Mesa 25.2.8 llvmpipe without hardware acceleration.
WSLg displayed RViz, and the official GUI Plan & Execute passed.
All required packages were installed already; setup made no apt changes.
Official launch arguments and live controller/MoveIt parameters were inspected.
MoveIt acceleration settings are 5 rad/s²; the verifier explicitly caps peak
direct acceleration at min(0.1 rad/s², 10% of the configured limit).

Browser GitHub authentication is now available as the intended owner. November 2
authentication and shutdown observations below are historical.

References revisited November 8:
[MoveIt binaries](https://moveit.ai/install-moveit2/binary/),
[Jazzy gz_ros2_control](https://control.ros.org/jazzy/doc/gz_ros2_control/doc/index.html),
[official UR simulation](https://github.com/UniversalRobots/Universal_Robots_ROS2_GZ_Simulation),
[UR documentation](https://docs.universal-robots.com/),
[Gazebo Harmonic](https://gazebosim.org/docs/harmonic/).
Installed versions, not moving upstream branches, define this run.

Current results: [November 8 recheck](MILESTONE_01_RECHECK_2026-11-08.md).

## Historical audit — 2026-11-02

## Observed baseline and changes

Windows PowerShell, WSL2 distribution **Ubuntu-24.04**, Ubuntu **24.04.5 LTS
(noble)**, x86_64; kernel **6.18.54.1-microsoft-standard-WSL2**.
A separate distribution named `Ubuntu` exists and was not used.

ROS Jazzy was already installed at `/opt/ros/jazzy`. ROS_DISTRO was initially
unset in the fresh shell and became `jazzy` after sourcing setup.bash.
Gazebo CLI reported **8.15.0** (Harmonic). Python **3.12.3**, Git **2.43.0**,
16 logical CPUs, about 15 GiB RAM, 4 GiB swap and 949 GiB available Linux disk
were observed. No ROS/Gazebo simulation was running at initial audit.

WSLg: DISPLAY=`:0`, WAYLAND_DISPLAY=`wayland-0`. GLX reports Mesa **25.2.8**,
**llvmpipe (LLVM 20.1.2, 256 bits)**, OpenGL **4.5**, acceleration **no**.
Gazebo and RViz rendered after restoring their minimized Windows-hosted windows.
WSL Qt screenshot calls returned black images; Windows screen capture produced
a readable RViz execution screenshot. Screenshots remain local and uncommitted.

No existing `~/visionpick_ws` was found in the home-directory search. The selected
Windows project directory was initially empty; Windows Git was not on PATH.
The new canonical repository/workspace is **~/visionpick_ws**, entirely on the
Linux filesystem. A Windows source snapshot may be supplied for review; run and
build only in the Linux workspace.

Missing binary packages were installed using apt in Ubuntu-24.04. Passwordless
sudo was unavailable; the authorized installation used WSL's root user. No
password, credential, apt-source change, distribution replacement or MoveIt source
build was needed. ReConFactory was not touched.

## Actual installed package versions

| apt package | Installed version |
|---|---|
| ros-jazzy-moveit | 2.12.4-1noble.20260921.025955 |
| ros-jazzy-ur-simulation-gz | 2.5.0-1noble.20261006.043651 |
| ros-jazzy-ur-description | 3.5.1-1noble.20260920.234208 |
| ros-jazzy-ur-moveit-config | 3.9.0-1noble.20261006.043609 |
| ros-jazzy-ur-robot-driver | 3.9.0-1noble.20261006.040539 |
| ros-jazzy-gz-ros2-control | 1.2.20-1noble.20261006.040504 |
| ros-jazzy-controller-manager | 4.48.1-1noble.20261006.035021 |
| ros-jazzy-joint-state-broadcaster | 4.42.1-1noble.20260924.190601 |
| ros-jazzy-joint-trajectory-controller | 4.42.1-1noble.20260924.190511 |
| ros-jazzy-ros-gz | 1.0.24-1noble.20261006.041805 |
| ros-jazzy-gz-sim-vendor | 0.0.13-1noble.20260905.073557 |
| ros-jazzy-rviz2 | 14.1.24-1noble.20260915.204213 |
| python3-colcon-common-extensions | 0.3.0-100 |
| python3-rosdep | 0.27.0-1 |
| python3-pytest | 7.4.4-1 |

GitHub CLI **2.45.0** was installed but is not authenticated. Optional screenshot
inspection tools `x11-utils` and `xdotool` were installed; they are not required
to launch or test the robotics stack. Apt policy confirmed compatible candidates
for MoveIt, UR simulation and gz_ros2_control before installation. Re-running
`setup_dependencies.sh` reported all packages installed and made no changes.

## Inspected official interfaces

Commands actually run:

```bash
source /opt/ros/jazzy/setup.bash
ros2 pkg prefix ur_simulation_gz
ros2 launch ur_simulation_gz ur_sim_moveit.launch.py --show-args
ros2 launch ur_simulation_gz ur_sim_control.launch.py --show-args
```

The combined launch accepts `ur_type` (including `ur5e`), `safety_limits`,
`controllers_file`, `description_file` and `moveit_launch_file`.
The control launch additionally declares `safety_pos_margin`,
`safety_k_position`, `tf_prefix`, `activate_joint_controller`,
`initial_joint_controller`, `launch_rviz`, `rviz_config_file`,
`gazebo_gui` and `world_file`. Defaults include
`scaled_joint_trajectory_controller`, `gazebo_gui=true`, `world_file=empty.sdf`.
The installed combined launch forces MoveIt's RViz on; do not assume
`launch_rviz:=false` on it disables RViz.

Read installed files, not merely current upstream branch:

- `ur_simulation_gz/config/ur_controllers.yaml`.
- `ur_moveit_config/config/moveit_controllers.yaml`.
- `ur_description/config/ur5e/joint_limits.yaml`.
- `ur_simulation_gz/urdf/ur_gz.urdf.xacro` and `ur_gz.ros2_control.xacro`.
- `ur_moveit_config/srdf/ur_macro.srdf.xacro`.

Resolved URDF soft position bounds are ±6.13318530718 rad except elbow
±2.99159265359 rad; velocity limits are pi rad/s. Our direct checks add another
0.01 rad position margin, limit each step to 0.25 rad, and enforce a conservative
peak speed no greater than min(0.15 rad/s, 10% of the model limit).

## Errors and limitations, retained honestly

- Initial WSL inspection failed with sandbox E_ACCESSDENIED; elevated tool access
  resolved it. This did not require changing WSL permissions.
- First official launch failed because `ur_robot_driver` was absent. Installing
  its Jazzy binary resolved the configuration-file dependency. No real robot
  hardware driver was launched.
- MoveIt logs a robot-name mismatch between URDF and SRDF, missing inferred
  config/ur.urdf (description is supplied from the ROS topic), and no octomap
  sensor plugin. Planning/execution nevertheless passed. No camera is intended.
- Gazebo DART logs unsupported mesh-collision construction messages. This milestone
  verifies simulated kinematics/control and MoveIt collision checks, **not**
  physical contact, grasp dynamics or collision fidelity.
- No unexpected controller crash occurred during the verified movement sequences.
  On requested shutdown, move_group segfaulted in executor destruction; RViz
  required escalation by ROS launch, and Gazebo left server/gui children running.
  The first restart was correctly refused by the duplicate-stack guard.
  Only the two identified children were stopped after checking their process
  environments for both ROS_DOMAIN_ID=73 and GZ_PARTITION=visionpick_m1.
- Stop with Ctrl+C in the launch terminal. If the next launch refuses, inspect
  `ps -eo pid,ppid,args` and the selected domain. Never use broad killall/pkill
  or delete shared ROS installations. Confirm a leftover PID belongs to this
  workspace/partition before signaling it. Shutdown robustness remains follow-up
  work; successful execution is not a claim of a clean upstream shutdown.
- DDS graph discovery can be incomplete with short CLI waits. The launcher uses
  a three-second no-daemon discovery window and an additional local flock guard.
- No rosdep build, colcon build, hardware test, camera, gripper, AI or benchmark was
  run. There is no local ROS package to build.

Full audit outputs remain under ignored `logs/`. Review/redact raw logs before
sharing; they may include local machine paths.

## Documentation checked

- [Gazebo ROS installation pairing](https://gazebosim.org/docs/latest/ros_installation/)
- [MoveIt Jazzy binary installation](https://moveit.ai/install-moveit2/binary/)
- [Jazzy gz_ros2_control](https://control.ros.org/jazzy/doc/gz_ros2_control/doc/index.html)
- [Official UR simulation usage](https://github.com/UniversalRobots/Universal_Robots_ROS2_GZ_Simulation/blob/ros2/ur_simulation_gz/doc/usage.rst)
- [ROS package index](https://index.ros.org/p/ur_simulation_gz/)

The installed apt versions above, rather than a moving ros2 branch, define the
tested baseline. No upstream repository was cloned into this workspace.
