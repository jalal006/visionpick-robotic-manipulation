#!/usr/bin/env bash
set -eo pipefail
cd -- "$(dirname -- "$0")/.."
source scripts/common.sh
mkdir -p logs
exec > >(tee "logs/interfaces-$(date -u +%Y%m%dT%H%M%SZ).log") 2>&1
manager="${1:-/controller_manager}"
timeout 20 ros2 control list_controllers -c "$manager"
timeout 20 ros2 control list_hardware_components -c "$manager" -v
timeout 20 ros2 control list_hardware_interfaces -c "$manager"
ros2 action list -t
ros2 topic list -t
for topic in /clock /joint_states /tf /tf_static; do
  timeout 15 ros2 topic echo "$topic" --once
done
for node in /controller_manager /move_group /robot_state_publisher /rviz2_moveit; do
  timeout 10 ros2 param get "$node" use_sim_time
done
echo "Gazebo model evidence:"
timeout 20 gz model --list
