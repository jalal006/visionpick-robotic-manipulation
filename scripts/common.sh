#!/usr/bin/env bash
# Source in every terminal; no persistent shell or shared ROS changes.
if [[ -n "${WSL_DISTRO_NAME:-}" && "$WSL_DISTRO_NAME" != Ubuntu-24.04 ]]; then
  echo "Use wsl -d Ubuntu-24.04" >&2; return 1
fi
source /etc/os-release
[[ "$ID" == ubuntu && "$VERSION_ID" == 24.04 ]] || { echo "Ubuntu 24.04 required" >&2; return 1; }
[[ -f /opt/ros/jazzy/setup.bash ]] || { echo "ROS Jazzy is missing" >&2; return 1; }
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-73}"
export GZ_PARTITION="${GZ_PARTITION:-visionpick_m1}"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-4}"
export ROS_LOG_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)/logs/ros"
