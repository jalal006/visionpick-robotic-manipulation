#!/usr/bin/env bash
set -eo pipefail
cd -- "$(dirname -- "$0")/.."
source scripts/common.sh
mkdir -p logs
exec 9>logs/launch.lock
flock -n 9 || { echo "VisionPick launch is already running" >&2; exit 1; }
nodes=$(timeout 10 ros2 node list --no-daemon --spin-time 3)
if grep -Eq '(^|/)(controller_manager|move_group|robot_state_publisher)$' <<< "$nodes"; then
  echo "A robot stack already exists in ROS_DOMAIN_ID=$ROS_DOMAIN_ID; inspect it first." >&2
  exit 1
fi
# A Gazebo server without its ROS nodes is also a conflict in this partition.
services=$(timeout 10 gz service -l)
if grep -Eq '^/world/.*/(control|scene/info)$' <<< "$services"; then
  echo "A Gazebo world already exists in GZ_PARTITION=$GZ_PARTITION; inspect it first." >&2
  exit 1
fi
exec python3 scripts/workcell_process.py "$@"
