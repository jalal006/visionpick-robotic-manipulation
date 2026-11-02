#!/usr/bin/env bash
# Never adds repositories, removes packages, or compiles upstream stacks.
set -eo pipefail
source /etc/os-release
[[ "$ID" == ubuntu && "$VERSION_ID" == 24.04 ]] || { echo "Ubuntu 24.04 required"; exit 1; }
[[ -z "${WSL_DISTRO_NAME:-}" || "$WSL_DISTRO_NAME" == Ubuntu-24.04 ]] || exit 1
packages=(ros-jazzy-moveit ros-jazzy-ur-simulation-gz ros-jazzy-ur-robot-driver
 ros-jazzy-gz-ros2-control ros-jazzy-ros2controlcli ros-jazzy-joint-state-broadcaster
 ros-jazzy-joint-trajectory-controller ros-jazzy-ros-gz ros-jazzy-rviz2
 python3-colcon-common-extensions python3-rosdep python3-pytest git)
missing=()
for p in "${packages[@]}"; do
  if [[ "$(dpkg-query -W -f='${Status}' "$p" 2>/dev/null || true)" != "install ok installed" ]]; then missing+=("$p"); fi
done
if (( ${#missing[@]} == 0 )); then echo "All required binary packages already installed."; exit 0; fi
sudo apt-get update
for p in "${missing[@]}"; do
  apt-cache policy "$p"
  candidate=$(apt-cache policy "$p" | awk '/Candidate:/ {print $2}')
  [[ -n "$candidate" && "$candidate" != "(none)" ]] || { echo "No candidate for $p; stop and review ROS apt sources."; exit 1; }
done
sudo apt-get install --no-remove -y "${missing[@]}"
# No local ROS package yet: rosdep install/colcon build are intentionally unnecessary.
