#!/usr/bin/env python3
"""Passively verify one manual RViz movement against an explicit six-joint target."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import time
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import JointState
from action_msgs.msg import GoalStatusArray
from moveit_msgs.msg import DisplayTrajectory
from motion_logic import ordered_positions, assess

JOINTS = ["shoulder_pan_joint", "shoulder_lift_joint", "elbow_joint",
          "wrist_1_joint", "wrist_2_joint", "wrist_3_joint"]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=float, nargs=6, required=True, help="Controller joint order, radians")
    parser.add_argument("--seconds", type=float, default=180)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    path = root / "logs" / ("gui-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".jsonl")
    path.parent.mkdir(exist_ok=True)
    rclpy.init()
    node = Node("visionpick_gui_observer")
    rows, plans, outcomes = [], [], []
    baseline_goals = set()
    start_wall = time.monotonic()
    with path.open("x") as log:
        def emit(event, **data):
            row = dict(utc=datetime.now(timezone.utc).isoformat(), event=event, **data)
            log.write(json.dumps(row, allow_nan=False)+"\n")
            log.flush()
            if event != "feedback":
                print(json.dumps(row), flush=True)
        def feedback(msg):
            q = ordered_positions(msg.name, msg.position, JOINTS)
            stamp = msg.header.stamp.sec + msg.header.stamp.nanosec*1e-9
            if rows and stamp <= rows[-1][0]:
                return
            rows.append((stamp,q))
            emit("feedback", stamp=stamp, measured=q)
        def plan(msg):
            if msg.trajectory and msg.trajectory[-1].joint_trajectory.points:
                trajectory=msg.trajectory[-1].joint_trajectory
                final=ordered_positions(trajectory.joint_names, trajectory.points[-1].positions, JOINTS)
                plans.append(final)
                emit("plan", target=final, points=len(trajectory.points))
        def status(msg):
            # Historical action results must not count as this GUI execution.
            for s in msg.status_list:
                goal=tuple(int(v) for v in s.goal_info.goal_id.uuid)
                if time.monotonic()-start_wall < 3:
                    baseline_goals.add(goal)
                elif goal not in baseline_goals and s.status == 4:
                    outcomes.append(goal)
        subs = [
            node.create_subscription(JointState, "/joint_states", feedback, qos_profile_sensor_data),
            node.create_subscription(DisplayTrajectory, "/display_planned_path", plan, 10),
            node.create_subscription(GoalStatusArray, "/move_action/_action/status", status, 10),
            node.create_subscription(GoalStatusArray, "/execute_trajectory/_action/status", status, 10)]
        emit("waiting", target=args.target, joints=JOINTS, timeout_s=args.seconds)
        try:
            end = time.monotonic()+args.seconds
            while time.monotonic() < end:
                rclpy.spin_once(node, timeout_sec=.1)
                if len(rows) < 3 or not plans or not outcomes:
                    continue
                recent=[q for t,q in rows if rows[-1][0]-t <= .5]
                if rows[-1][0]-rows[0][0] < 1 or len(recent)<3:
                    continue
                if max(abs(a-b) for a,b in zip(plans[-1],args.target)) > .02:
                    continue
                if any(max(abs(a-b) for a,b in zip(q,args.target)) > .02 for q in recent):
                    continue
                errors, excursion=assess(rows[0][1],args.target,[q for _,q in rows])
                if max(excursion) < .05:
                    continue
                emit("PASS", start=rows[0][1], requested=args.target, measured=rows[-1][1],
                     absolute_error=errors, max_error=max(errors), excursion=excursion,
                     planned_target=plans[-1], samples=len(rows), new_successful_goals=len(set(outcomes)))
                return 0
            emit("FAIL", reason="No new successful GUI execution with matching plan and measured motion")
            return 1
        finally:
            node.destroy_node()
            rclpy.shutdown()
            print("Evidence:", path)

if __name__ == "__main__":
    raise SystemExit(main())
