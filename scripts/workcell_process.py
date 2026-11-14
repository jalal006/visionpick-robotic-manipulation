"""Supervise this launch's private Linux session; never signal other ROS sessions."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


def members(session):
    result = []
    for path in Path('/proc').glob('[0-9]*/stat'):
        try:
            fields = path.read_text().rsplit(')', 1)[1].split()
            if int(fields[3]) == session and fields[0] != 'Z':
                result.append((int(path.parent.name), fields[19]))
        except (OSError, ValueError, IndexError):
            pass
    return result


def signal_members(session, sig):
    for pid, start in members(session):
        try:
            fields = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
            if fields[19] == start and int(fields[3]) == session:
                os.kill(pid, sig)
        except (OSError, ValueError):
            pass


def main():
    root = Path(__file__).resolve().parents[1]
    child = subprocess.Popen(['ros2', 'launch', str(root/'launch/workcell.launch.py'), *sys.argv[1:]],
                             start_new_session=True)
    stopping = False
    def stop(signum, frame):
        nonlocal stopping
        if not stopping:
            stopping = True
            if child.poll() is None:
                child.send_signal(signal.SIGINT)
    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    try:
        while child.poll() is None and not stopping:
            time.sleep(.2)
    finally:
        stop(None, None)
        try:
            child.wait(timeout=15)
        except subprocess.TimeoutExpired:
            pass
        for sig in (signal.SIGTERM, signal.SIGKILL):
            remaining = members(child.pid)
            if remaining:
                print(f'Cleaning this launch session {child.pid}: {remaining}', flush=True)
                signal_members(child.pid, sig)
                time.sleep(1)
        child.wait(timeout=5)
    return 0 if stopping and child.returncode in (0, -2, -15) else child.returncode


if __name__ == '__main__':
    raise SystemExit(main())
