#!/usr/bin/env bash
set -eo pipefail
cd -- "$(dirname -- "$0")/.."
source scripts/common.sh
mkdir -p logs
exec 9>logs/launch.lock
flock -n 9 || { echo "VisionPick launch is already running"; exit 1; }
nodes=$(timeout 10 ros2 node list --no-daemon --spin-time 3)
if grep -Eq '(^|/)(controller_manager|move_group|robot_state_publisher)$' <<< "$nodes"; then
  echo "A robot stack already exists in ROS_DOMAIN_ID=$ROS_DOMAIN_ID; inspect it first."; exit 1
fi
ros2 launch ur_simulation_gz ur_sim_moveit.launch.py --show-args > logs/moveit-launch-args.txt
ros2 launch ur_simulation_gz ur_sim_control.launch.py --show-args > logs/control-launch-args.txt
# Official combined launch starts both Gazebo and MoveIt. Do not start control launch too.
exec ros2 launch ur_simulation_gz ur_sim_moveit.launch.py ur_type:=ur5e "$@"
