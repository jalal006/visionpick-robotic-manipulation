#!/usr/bin/env python3
"""Install and read back the canonical planning scene. No robot motion."""
import fcntl
import rclpy
from workcell_logic import ROOT, load_config
from workcell_runtime import WorkcellClient, GazeboScene


def main():
    (ROOT/'logs').mkdir(exist_ok=True)
    with (ROOT/'logs/motion.lock').open('w') as lock, (ROOT/'logs/workcell-scene.jsonl').open('w') as log:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        rclpy.init()
        node = None
        try:
            config = load_config()
            node = WorkcellClient(config, log, setup=True)
            node.prepare()
            gazebo = GazeboScene(config)
            node.event('gazebo_geometry', objects=gazebo.read())
            first = node.setup_scene()
            second = node.setup_scene()
            if first != second:
                raise RuntimeError('Scene setup is not idempotent')
            valid = node.validity(node.fresh())
            if not valid['valid']:
                raise RuntimeError(f'Start in collision: {valid}')
            node.event('SCENE_READY', objects=second, state_validity=valid, idempotent=True)
            return 0
        except Exception as exc:
            print(f'WORKCELL SCENE FAILED: {exc}', flush=True)
            return 1
        finally:
            if node:
                node.destroy_node()
            rclpy.shutdown()


if __name__ == '__main__':
    raise SystemExit(main())
