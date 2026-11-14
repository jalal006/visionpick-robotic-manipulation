#!/usr/bin/env python3
"""Plan, check, execute and measure the simulation-only Milestone 2 workcell."""
import argparse
from datetime import datetime, timezone
from pathlib import Path
import fcntl
import json
import math
import time

import rclpy
from rclpy.action import ActionClient
from moveit_msgs.action import ExecuteTrajectory
from moveit_msgs.msg import CollisionObject

from motion_logic import assess
from workcell_logic import ROOT, load_config, expected_boxes, validate_target, summarize_report
from workcell_runtime import WorkcellClient, GazeboScene, collision_objects, xyz


class WorkcellVerifier(WorkcellClient):
    def __init__(self, config, log):
        self.records = []
        self.monitor_execution = False
        super().__init__(config, log)

    def event(self, kind, **data):
        super().event(kind, **data)
        if kind != 'feedback':
            self.records.append(dict(event=kind, **data))

    def wait(self, condition, timeout, label):
        def checked():
            if self.monitor_execution:
                self.gazebo.check_contacts()
            return condition()
        return super().wait(checked, timeout, label)

    def plan(self, label, target, expect_success=True):
        validate_target(target, self.joints, self.limits)
        start = self.fresh()
        client, goal = self.moveit_goal(start, target)
        goal.planning_options.plan_only = True
        goal.request.max_velocity_scaling_factor = .05
        goal.request.max_acceleration_scaling_factor = .05
        goal.request.allowed_planning_time = 5.
        for c in goal.request.goal_constraints[0].joint_constraints:
            c.tolerance_above = c.tolerance_below = .001
        before = time.monotonic()
        self.goal = self.result(client.send_goal_async(goal))
        if not self.goal.accepted:
            raise RuntimeError('Planning action rejected before collision checking')
        outcome = self.result(self.goal.get_result_async(), 30)
        self.goal = None
        code = outcome.result.error_code.val
        trajectory = outcome.result.planned_trajectory
        self.event('plan', label=label, start=start, target=target, plan_only=True,
                   status=outcome.status, error_code=code, points=len(trajectory.joint_trajectory.points),
                   message=outcome.result.error_code.message, source=outcome.result.error_code.source,
                   planning_seconds=outcome.result.planning_time, wall_seconds=time.monotonic()-before)
        if expect_success:
            if outcome.status != 4 or code != 1 or not trajectory.joint_trajectory.points:
                raise RuntimeError(f'Expected a valid plan for {label}: {code}')
        elif outcome.status != 6 or code not in (-1, -12, 99999) or trajectory.joint_trajectory.points:
            raise RuntimeError(f'Unexpected blocked-plan result: status {outcome.status}, code {code}')
        if max(abs(a-b) for a,b in zip(start, self.fresh())) > .005:
            raise RuntimeError('Robot moved during a planning-only test')
        return trajectory

    def check_trajectory(self, trajectory):
        jt = trajectory.joint_trajectory
        if set(jt.joint_names) != set(self.joints) or len(jt.joint_names) != len(self.joints):
            raise RuntimeError('Trajectory joints do not match the active controller')
        order = [jt.joint_names.index(j) for j in self.joints]
        previous = self.fresh()
        last_time = -1.
        count = 0
        for point in jt.points:
            q = [point.positions[i] for i in order]
            validate_target(q, self.joints, self.limits)
            seconds = point.time_from_start.sec + point.time_from_start.nanosec*1e-9
            if seconds <= last_time:
                raise RuntimeError('Trajectory times do not increase')
            last_time = seconds
            if len(point.velocities) != len(order) or len(point.accelerations) != len(order):
                raise RuntimeError('Missing trajectory derivatives')
            for j, i in zip(self.joints, order):
                v, a = point.velocities[i], point.accelerations[i]
                if not math.isfinite(v+a) or abs(v) > self.limits[j][2]*.051 or abs(a) > self.acceleration_limits[j]*.051:
                    raise RuntimeError('Trajectory exceeds conservative derivative limits')
            steps = max(1, math.ceil(max(abs(a-b) for a,b in zip(previous,q))/.01))
            for k in range(steps+1):
                sample = [a+(b-a)*k/steps for a,b in zip(previous,q)]
                validity = self.validity(sample)
                if not validity['valid']:
                    raise RuntimeError(f'Planned path is in collision: {validity}')
                count += 1
            previous = q
        return previous, count, last_time

    def execute(self, label, target):
        self.scene_boxes()
        self.gazebo.read()
        self.gazebo.check_publishers()
        start = self.fresh()
        if not self.validity(start)['valid'] or not self.validity(target)['valid']:
            raise RuntimeError('Start or requested safe target is invalid')
        if label == 'safe_b':
            invalid = []
            for i in range(21):
                q = [a+(b-a)*i/20 for a,b in zip(start,target)]
                result = self.validity(q)
                if not result['valid']:
                    invalid.append(dict(fraction=i/20, **result))
            self.event('straight_segment_diagnostic', invalid_samples=invalid,
                       note='Diagnostic only; only the checked MoveIt trajectory is executed')
        trajectory = self.plan(label, target)
        endpoint, checked, planned_seconds = self.check_trajectory(trajectory)
        if max(abs(a-b) for a,b in zip(start, self.fresh())) > .005:
            raise RuntimeError('Robot drifted during trajectory validation')
        if max(abs(a-b) for a,b in zip(endpoint, target)) > .002:
            raise RuntimeError('Planned endpoint does not satisfy requested target')
        self.scene_boxes()
        counts = self.gazebo.check_contacts()
        clock_count = self.gazebo.clock_count
        goal = ExecuteTrajectory.Goal(trajectory=trajectory, controllers=[self.action_name.split('/')[1]])
        client = ActionClient(self, ExecuteTrajectory, '/execute_trajectory')
        if not client.wait_for_server(timeout_sec=20):
            raise RuntimeError('MoveIt execute-trajectory action missing')
        self.samples = []
        before = time.monotonic()
        start_sim = self.get_clock().now().nanoseconds
        self.monitor_execution = True
        self.goal = self.result(client.send_goal_async(goal))
        if not self.goal.accepted:
            raise RuntimeError('Execution rejected')
        outcome = self.result(self.goal.get_result_async(), max(60, planned_seconds*4))
        self.goal = None
        if outcome.status != 4 or outcome.result.error_code.val != 1:
            raise RuntimeError(f'Controller execution failed: {outcome.status}/{outcome.result.error_code.val}')
        first, stable = None, 0
        deadline = time.monotonic()+10
        while time.monotonic() < deadline:
            current = self.fresh()
            if max(abs(a-b) for a,b in zip(current, endpoint)) <= .02:
                first = self.last_stamp if first is None else first
                stable += 1
                if stable >= 3 and self.last_stamp-first >= 200_000_000:
                    break
            else:
                first, stable = None, 0
        else:
            raise RuntimeError('Executed endpoint did not settle')
        self.monitor_execution = False
        elapsed = time.monotonic()-before
        sim_elapsed = (self.get_clock().now().nanoseconds-start_sim)*1e-9
        errors, excursion = assess(start, endpoint, self.samples)
        measured = self.fresh()
        samples = list(self.samples)
        # Check measured motion too, bounded by 0.01-rad joint displacement.
        last = start
        measured_checks = 0
        for q in samples + [measured]:
            if max(abs(a-b) for a,b in zip(last,q)) >= .01 or q == measured:
                if not self.validity(q)['valid']:
                    raise RuntimeError('Measured robot state entered collision')
                last = q
                measured_checks += 1
        contact_counts = self.gazebo.check_contacts()
        if self.gazebo.clock_count <= clock_count:
            raise RuntimeError('Gazebo physics clock did not advance during execution')
        self.gazebo.check_publishers()
        self.scene_boxes()
        self.event('executed', label=label, requested=target, planned_endpoint=endpoint,
            measured=measured, max_error=max(errors), excursion=excursion, feedback_samples=len(samples),
            trajectory_checks=checked, measured_state_checks=measured_checks,
            planned_duration_seconds=planned_seconds, execution_wall_seconds=elapsed,
            execution_sim_seconds=sim_elapsed, status=outcome.status, error_code=outcome.result.error_code.val,
            contact_messages={k:contact_counts[k]-counts[k] for k in counts}, robot_workcell_contacts=0)
        client.destroy()

    def negative_test(self):
        target = self.target('blocked')
        validate_target(target, self.joints, self.limits)
        self.scene_boxes()
        blocked = self.validity(target)
        if blocked['valid'] or not any('visionpick_fixture' in (c['body_1'], c['body_2']) for c in blocked['contacts']):
            raise RuntimeError('Blocked target lacks explicit fixture collision evidence')
        self.plan('blocked_with_fixture', target, expect_success=False)
        removal = CollisionObject(id='visionpick_fixture', operation=CollisionObject.REMOVE)
        try:
            # The robot stays at home. This counterfactual plan is NEVER executed.
            self.apply([removal])
            actual = self.scene_boxes([b for b in expected_boxes(self.config) if b['id'] != removal.id])
            if any(b['id'] == removal.id for b in actual):
                raise RuntimeError('Fixture removal not observed')
            clear = self.validity(target)
            if not clear['valid']:
                raise RuntimeError('Control target is not valid without fixture')
            self.plan('same_target_without_fixture', target)
        finally:
            self.apply(collision_objects(self.config))
            self.scene_boxes()
        if self.validity(target)['valid']:
            raise RuntimeError('Restored fixture does not block target')
        self.event('negative_test', target=target, with_fixture=blocked, without_fixture=clear,
                   fixture_restored=True, control_plan_executed=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path,
                        help='Optional compact JSON report path (overwrites only this requested path)')
    options = parser.parse_args()
    config = load_config()
    (ROOT/'logs').mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    report = options.report or ROOT/f'logs/workcell-{stamp}.json'
    node = None
    success = False
    failure = None
    with (ROOT/'logs/motion.lock').open('w') as lock, (ROOT/f'logs/workcell-{stamp}.jsonl').open('x') as log:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        rclpy.init()
        try:
            node = WorkcellVerifier(config, log)
            node.prepare()
            node.gazebo = GazeboScene(config)
            node.event('gazebo_geometry', objects=node.gazebo.read())
            original = node.scene_boxes()
            if original != node.setup_scene() or original != node.setup_scene():
                raise RuntimeError('Scene setup changed canonical geometry')
            node.event('scene_verified', objects=original, idempotent=True)
            for label in ['home','safe_a','safe_b','blocked']:
                q = node.target(label)
                validate_target(q, node.joints, node.limits)
                valid = node.validity(q)
                node.event('target_validity', label=label, target=q, **valid,
                           tool_position=xyz(node.fk(q)[0].pose.position))
                if valid['valid'] != (label != 'blocked'):
                    raise RuntimeError(f'Unexpected target validity: {label}')
            node.wait(lambda: node.gazebo.clock_count > 0, 10, 'No Gazebo clock heartbeat')
            node.gazebo.check_publishers()
            node.gazebo.check_contacts()
            node.negative_test()
            for label in ['safe_a','safe_b','home']:
                node.execute(label, node.target(label))
            node.event('PASS', milestone=2)
            summarize_report(dict(schema_version=1, status='PASS', config=config, events=node.records))
            success = True
        except (Exception, KeyboardInterrupt) as exc:
            failure = str(exc)
            if node:
                node.monitor_execution = False
                node.event('FAIL', reason=failure, home_return='not guaranteed; no blind recovery')
                try:
                    node.cancel()
                except Exception as cancel_error:
                    node.event('cancel_failed', reason=str(cancel_error))
            else:
                print(f'FAIL: {failure}')
        finally:
            report.parent.mkdir(parents=True, exist_ok=True)
            report.write_text(json.dumps(dict(schema_version=1, utc=datetime.now(timezone.utc).isoformat(),
                status='PASS' if success else 'FAIL', failure=failure, config=config,
                events=node.records if node else []), indent=2, allow_nan=False)+'\n')
            if node:
                node.destroy_node()
            rclpy.shutdown()
            print(f'Report: {report}')
    return 0 if success else 1


if __name__ == '__main__':
    raise SystemExit(main())
