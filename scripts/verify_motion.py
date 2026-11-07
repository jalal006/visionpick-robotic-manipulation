#!/usr/bin/env python3
"""Verify small motions in the official Gazebo UR5e. Never for physical hardware."""
import argparse
from datetime import datetime, timezone
import fcntl
import json
from pathlib import Path
import time

import rclpy
from rclpy.action import ActionClient, get_action_names_and_types
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.parameter_client import AsyncParameterClient
from rclpy.qos import QoSProfile, DurabilityPolicy, qos_profile_sensor_data
from action_msgs.msg import GoalStatus
from builtin_interfaces.msg import Duration
from control_msgs.action import FollowJointTrajectory
from control_msgs.msg import JointTolerance
from controller_manager_msgs.srv import ListControllers
from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import Constraints, JointConstraint
from moveit_msgs.srv import GetStateValidity
from sensor_msgs.msg import JointState
from std_msgs.msg import String
from trajectory_msgs.msg import JointTrajectoryPoint
from motion_logic import limits_from_urdf, ordered_positions, validate_segment, make_targets, assess, validate_acceleration


class Verifier(Node):
    def __init__(self, args, log):
        super().__init__("visionpick_motion_verifier",
                         parameter_overrides=[Parameter("use_sim_time", value=True)])
        self.args, self.log = args, log
        self.joints, self.latest, self.samples = [], None, []
        self.urdf, self.feedback_error, self.goal = None, None, None
        self.last_stamp = -1
        self.sub = self.create_subscription(JointState, args.joint_states, self.on_state,
                                            qos_profile_sensor_data)
        self.description_sub = self.create_subscription(
            String, args.description_topic, self.on_description,
            QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL))

    def event(self, kind, **data):
        row = {"utc": datetime.now(timezone.utc).isoformat(),
               "sim_ns": self.get_clock().now().nanoseconds, "event": kind, **data}
        self.log.write(json.dumps(row, allow_nan=False) + "\n")
        self.log.flush()
        if kind != "feedback":
            print(json.dumps(row, allow_nan=False), flush=True)

    def on_description(self, message):
        self.urdf = message.data

    def on_state(self, message):
        if not self.joints:
            return
        try:
            positions = ordered_positions(message.name, message.position, self.joints)
            stamp = message.header.stamp.sec * 10**9 + message.header.stamp.nanosec
            if stamp <= self.last_stamp:
                return
            self.last_stamp = stamp
            self.latest = (time.monotonic(), stamp, positions)
            self.samples.append(positions)
            self.event("feedback", stamp_ns=stamp, measured=positions)
        except (ValueError, KeyError) as exc:
            self.feedback_error = str(exc)

    def wait(self, condition, timeout, label):
        end = time.monotonic() + timeout
        while rclpy.ok() and time.monotonic() < end:
            rclpy.spin_once(self, timeout_sec=.05)
            if self.feedback_error:
                raise RuntimeError(self.feedback_error)
            if condition():
                return
        raise TimeoutError(label)

    def result(self, future, timeout=20):
        self.wait(future.done, timeout, "ROS response timeout")
        return future.result()

    def service(self, kind, name, request):
        client = self.create_client(kind, name)
        try:
            if not client.wait_for_service(timeout_sec=20):
                raise RuntimeError(f"Missing service: {name}")
            return self.result(client.call_async(request))
        finally:
            self.destroy_client(client)

    def fresh(self):
        after = self.last_stamp
        self.wait(lambda: self.latest is not None and self.last_stamp > after,
                  10, "No fresh, increasing joint timestamp")
        if time.monotonic() - self.latest[0] > 1:
            raise RuntimeError("Stale feedback")
        if abs(self.get_clock().now().nanoseconds - self.latest[1]) > 2e9:
            raise RuntimeError("Joint feedback and simulation clock disagree")
        return list(self.latest[2])

    def prepare(self):
        response = self.service(ListControllers, self.args.manager + "/list_controllers",
                                ListControllers.Request())
        active = [c for c in response.controller if c.state == "active"]
        if not any("JointStateBroadcaster" in c.type for c in active):
            raise RuntimeError("No active joint state broadcaster")
        candidates = [c for c in active if "JointTrajectoryController" in c.type]
        if self.args.controller:
            candidates = [c for c in candidates if c.name == self.args.controller]
        if len(candidates) != 1:
            raise RuntimeError(f"Ambiguous/missing active controller: {[c.name for c in candidates]}")
        controller = candidates[0]
        namespace = self.args.manager.rsplit("/", 1)[0]
        controller_path = namespace + "/" + controller.name
        params = AsyncParameterClient(self, controller_path)
        if not params.wait_for_services(timeout_sec=20):
            raise RuntimeError("Controller parameter service missing")
        self.joints = list(self.result(params.get_parameters(["joints"])).values[0].string_array_value)
        if len(self.joints) != 6 or len(set(self.joints)) != 6:
            raise RuntimeError("Expected six unique controller joints")
        self.wait(lambda: self.urdf is not None and self.latest is not None and
                  self.get_clock().now().nanoseconds > 0, 20, "Missing description/clock/joint states")
        self.limits = limits_from_urdf(self.urdf, self.joints)
        planning_params = AsyncParameterClient(self, self.args.move_group_node)
        if not planning_params.wait_for_services(timeout_sec=20):
            raise RuntimeError("MoveIt parameter service missing")
        names = [f"robot_description_planning.joint_limits.{j}.{field}"
                 for j in self.joints for field in
                 ("has_acceleration_limits", "max_acceleration")]
        values = self.result(planning_params.get_parameters(names)).values
        self.acceleration_limits = {}
        for i, joint in enumerate(self.joints):
            enabled, limit = values[2*i:2*i+2]
            if enabled.type != 1 or not enabled.bool_value or limit.type != 3:
                raise RuntimeError(f"Missing configured acceleration limit: {joint}")
            self.acceleration_limits[joint] = limit.double_value
        self.home = self.fresh()
        # This verifier deliberately covers only the inspected official initial 'up' posture.
        expected = dict(shoulder_pan_joint=0., shoulder_lift_joint=-1.57, elbow_joint=0.,
                        wrist_1_joint=-1.57, wrist_2_joint=0., wrist_3_joint=0.)
        if not self.args.return_home and any(abs(q-expected[j]) > .03 for j, q in zip(self.joints, self.home)):
            raise RuntimeError("Not at documented startup home; restore the official initial pose first")
        if self.args.return_home:
            self.home = [expected[j] for j in self.joints]
        self.action_name = controller_path + "/follow_joint_trajectory"
        wanted = "control_msgs/action/FollowJointTrajectory"
        self.wait(lambda: any(n == self.action_name and wanted in types
                             for n, types in get_action_names_and_types(self)), 20,
                  "Active controller action is absent")
        self.direct = ActionClient(self, FollowJointTrajectory, self.action_name)
        if not self.direct.wait_for_server(timeout_sec=20):
            raise RuntimeError("Trajectory action not ready")
        self.event("ready", mode=self.args.mode, controller=controller.name,
                   controller_type=controller.type, action=self.action_name,
                   joints=self.joints, home=self.home, effective_limits=self.limits,
                   tolerance_rad=self.args.tolerance, duration_s=self.args.duration,
                   configured_acceleration_limits=self.acceleration_limits,
                   verifier_acceleration_cap_rad_s2=.1)
        if self.args.mode == "moveit":
            self.moveit = ActionClient(self, MoveGroup, self.args.moveit_action)
            if not self.moveit.wait_for_server(timeout_sec=20):
                raise RuntimeError("MoveIt action not ready")

    def check_path(self, start, target):
        # Sampled collision check of this small joint-space segment; not a general planner.
        for i in range(21):
            q = [a+(b-a)*i/20 for a,b in zip(start,target)]
            req = GetStateValidity.Request()
            req.group_name = self.args.group
            req.robot_state.joint_state.name = self.joints
            req.robot_state.joint_state.position = q
            req.robot_state.is_diff = True
            if not self.service(GetStateValidity, self.args.validity_service, req).valid:
                raise RuntimeError(f"Collision/invalid state at segment sample {i}/20")

    def direct_goal(self, start, target):
        goal = FollowJointTrajectory.Goal()
        goal.trajectory.joint_names = self.joints
        for q, seconds in [(start, .2), (target, self.args.duration + .2)]:
            point = JointTrajectoryPoint()
            point.positions, point.velocities, point.accelerations = q, [0.]*6, [0.]*6
            point.time_from_start = Duration(sec=int(seconds), nanosec=round((seconds % 1)*1e9))
            goal.trajectory.points.append(point)
        goal.goal_time_tolerance = Duration(sec=3)
        goal.goal_tolerance = [JointTolerance(name=j, position=self.args.tolerance) for j in self.joints]
        return self.direct, goal

    def moveit_goal(self, start, target):
        goal = MoveGroup.Goal()
        req = goal.request
        req.group_name = self.args.group
        req.pipeline_id = "ompl"
        req.num_planning_attempts = 3
        req.allowed_planning_time = 10.
        req.max_velocity_scaling_factor = .1
        req.max_acceleration_scaling_factor = .1
        req.start_state.is_diff = True
        req.start_state.joint_state.name = self.joints
        req.start_state.joint_state.position = start
        constraints = Constraints(name="visionpick_small_joint_target")
        constraints.joint_constraints = [
            JointConstraint(joint_name=j, position=q, tolerance_above=.005,
                            tolerance_below=.005, weight=1.)
            for j, q in zip(self.joints, target)]
        req.goal_constraints = [constraints]
        goal.planning_options.plan_only = False
        goal.planning_options.planning_scene_diff.is_diff = True
        goal.planning_options.planning_scene_diff.robot_state.is_diff = True
        return self.moveit, goal

    def move(self, label, target):
        start = self.fresh()
        validate_segment(start, target, self.joints, self.limits, self.args.duration)
        validate_acceleration(start, target, self.joints,
                              self.acceleration_limits, self.args.duration)
        self.check_path(start, target)
        # Reject unexpected drift during validation before issuing the goal.
        current = self.fresh()
        if max(abs(a-b) for a,b in zip(start,current)) > .005:
            raise RuntimeError("Robot moved during preflight")
        self.samples = []
        self.event("goal", label=label, requested=target, start=start)
        client, goal = (self.direct_goal if self.args.mode == "direct" else self.moveit_goal)(start, target)
        send = client.send_goal_async(goal)
        try:
            self.goal = self.result(send)
        except BaseException:
            # If acceptance arrives after our deadline, cancel this exact goal then.
            def cancel_late(future):
                handle = future.result()
                if handle is not None and handle.accepted:
                    handle.cancel_goal_async()
            send.add_done_callback(cancel_late)
            raise
        if not self.goal.accepted:
            raise RuntimeError("Action goal rejected")
        self.event("accepted", label=label, goal_id=[int(v) for v in self.goal.goal_id.uuid])
        outcome = self.result(self.goal.get_result_async(), self.args.timeout)
        code = (outcome.result.error_code if self.args.mode == "direct"
                else outcome.result.error_code.val)
        self.event("action_result", label=label, status=outcome.status, error_code=code)
        self.goal = None
        if outcome.status != GoalStatus.STATUS_SUCCEEDED or code != (0 if self.args.mode == "direct" else 1):
            raise RuntimeError(f"Action failed: status={outcome.status}, code={code}")
        if self.args.mode == "moveit":
            self.event("moveit_execution", label=label,
                       planned_points=len(outcome.result.planned_trajectory.joint_trajectory.points),
                       executed_points=len(outcome.result.executed_trajectory.joint_trajectory.points),
                       planning_time=outcome.result.planning_time)
            if not outcome.result.planned_trajectory.joint_trajectory.points:
                raise RuntimeError("MoveIt returned an empty plan")
        # Three NEW samples spanning >=0.2 simulation seconds after the action result.
        stable, first_stamp = 0, None
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            q = self.fresh()
            if max(abs(a-b) for a,b in zip(q,target)) <= self.args.tolerance:
                stable += 1
                if first_stamp is None:
                    first_stamp = self.latest[1]
                if stable >= 3 and self.latest[1] - first_stamp >= 200_000_000:
                    break
            else:
                stable, first_stamp = 0, None
        else:
            raise RuntimeError("Final pose did not settle")
        errors, excursion = assess(start, target, self.samples, self.args.tolerance)
        self.event("verified", label=label, requested=target, measured=self.latest[2],
                   absolute_error=errors, max_error=max(errors), excursion=excursion,
                   sample_count=len(self.samples))

    def cancel(self):
        if self.goal is not None and self.goal.accepted:
            result = self.result(self.goal.cancel_goal_async(), 5)
            self.event("cancel", goals_canceling=len(result.goals_canceling))
            self.goal = None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--return-home", action="store_true", help="Return only to documented startup pose; still rejects steps over .25 rad")
    parser.add_argument("--mode", choices=["direct", "moveit"], default="direct")
    parser.add_argument("--manager", default="/controller_manager")
    parser.add_argument("--controller", default=None)
    parser.add_argument("--joint-states", default="/joint_states")
    parser.add_argument("--description-topic", default="/robot_description")
    parser.add_argument("--group", default="ur_manipulator")
    parser.add_argument("--move-group-node", default="/move_group")
    parser.add_argument("--moveit-action", default="/move_action")
    parser.add_argument("--validity-service", default="/check_state_validity")
    parser.add_argument("--duration", type=float, default=6.)
    parser.add_argument("--timeout", type=float, default=90.)
    parser.add_argument("--tolerance", type=float, default=.02)
    args = parser.parse_args()
    import math
    if not all(map(math.isfinite, (args.duration, args.timeout, args.tolerance))) or not (
            4 <= args.duration <= 30 and args.timeout >= args.duration+10 and 0 < args.tolerance <= .02):
        parser.error("Use duration 4..30, timeout >= duration+10, tolerance (0,.02]")
    root = Path(__file__).resolve().parents[1]
    (root / "logs").mkdir(exist_ok=True)
    lock = (root / "logs/motion.lock").open("w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        parser.error("Another VisionPick motion verifier is running")
    path = root / "logs" / (args.mode + "-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".jsonl")
    rclpy.init()
    node = None
    with path.open("x") as log:
        try:
            node = Verifier(args, log)
            node.prepare()
            targets = [("home", node.home)] if args.return_home else make_targets(node.home, node.joints)
            for label, target in targets:
                node.move(label, target)
            node.event("PASS", mode=args.mode)
            return 0
        except (Exception, KeyboardInterrupt) as exc:
            if node:
                node.event("FAIL", reason=str(exc), home_return="not guaranteed; no blind recovery")
                try:
                    node.cancel()
                except Exception as cancel_error:
                    node.event("cancel_failed", reason=str(cancel_error))
            else:
                print(f"FAIL: {exc}")
            return 1
        finally:
            if node:
                node.destroy_node()
            rclpy.shutdown()
            print(f"Evidence: {path}")


if __name__ == "__main__":
    raise SystemExit(main())
