#!/usr/bin/env bash
set -eo pipefail
cd -- "$(dirname -- "$0")/.."
mkdir -p logs
exec > >(tee "logs/environment-$(date -u +%Y%m%dT%H%M%SZ).log") 2>&1
source scripts/common.sh
failed=0
echo "UTC: $(date -u --iso-8601=seconds)"
uname -srmo
cat /etc/os-release
echo "ROS_DISTRO=$ROS_DISTRO ROS_DOMAIN_ID=$ROS_DOMAIN_ID GZ_PARTITION=$GZ_PARTITION"
python3 --version
nproc
free -h
df -h .
echo "DISPLAY=${DISPLAY:-unset} WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-unset}"
if command -v glxinfo >/dev/null; then glxinfo -B || true; fi
gz sim --versions || failed=1
gz sim --versions | grep -q '^8\.' || { echo "Gazebo Harmonic (sim 8) required"; failed=1; }
for p in moveit_ros_move_group ur_simulation_gz ur_description ur_moveit_config ur_robot_driver gz_ros2_control ros2controlcli joint_state_broadcaster joint_trajectory_controller rviz2 ros_gz_sim; do
  echo "Package: $p"
  ros2 pkg prefix "$p" || failed=1
done
for cmd in colcon rosdep git; do command -v "$cmd" || failed=1; done
dpkg-query -W 'ros-jazzy-*' python3-colcon-common-extensions python3-rosdep 2>/dev/null || true
apt-cache policy ros-jazzy-moveit ros-jazzy-ur-simulation-gz ros-jazzy-gz-ros2-control
ps -eo pid,comm | grep -E 'gz|ruby|rviz|move_group|ros2|robot_state' || true
echo "Selected domain nodes (review before launch):"
timeout 10 ros2 node list --no-daemon --spin-time 3 || true
exit "$failed"
