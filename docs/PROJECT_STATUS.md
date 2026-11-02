# VisionPick project status

- **Project:** VisionPick — Autonomous Camera-Guided Robotic Manipulation.
- **Checkpoint date:** 2026-11-02, Europe/Prague.
- **Verified milestone:** Milestone 1 COMPLETE locally. Remote publication pending.
- **Previous externally verified checkpoint:** Milestone 0 on 2026-10-31.
- **Source revision:** no previous verified pushed commit. This document belongs
  to the initial local foundation commit; use `git rev-parse HEAD` for its exact
  resulting SHA, reported after commit creation. No self-referential SHA is invented.
- **Canonical workspace:** `~/visionpick_ws` in WSL Ubuntu-24.04.
- **Intended remote:** `https://github.com/jalal006/visionpick-robotic-manipulation.git`.

## Completed and verified

Official apt-installed UR5e simulation in Gazebo Harmonic, ROS 2 Jazzy feedback,
active controllers, live TF/clock, simulation time configuration, measured
controller A/B/home motion, automatic MoveIt A/B/home execution, one actual RViz
Plan & Execute, conservative return-home utility, passive GUI recorder, audit and
idempotent setup scripts, pure-logic tests, documentation and compact real evidence.

Verification commands (after `source scripts/common.sh`):

```bash
bash scripts/check_environment.sh
bash scripts/setup_dependencies.sh
python3 -m pytest -q
bash scripts/launch_simulation.sh                 # terminal 1
bash scripts/check_ros_interfaces.sh             # terminal 2
python3 scripts/verify_motion.py --mode direct
python3 scripts/verify_motion.py --mode moveit
python3 scripts/verify_motion.py --mode direct --return-home
```

**Test outcomes:** 15 pure-logic tests passed; Python and shell syntax checks passed.
Direct and MoveIt full sequences passed twice across separate launches. Worst
automatic MoveIt final error was 0.00491170 rad (rounded upward) against 0.02 rad.
One GUI execution passed; the second attempted GUI observer timed out without a
GUI execution and is not counted. Final direct return-home max error:
1.7164e-13 rad. Gazebo shoulder-link state independently confirmed movement.

See [verification](MILESTONE_01_VERIFICATION.md) for all observed vectors and exact
GUI steps. Raw logs/screenshots are local and ignored; compact evidence is tracked.

## Limitations and blockers

Software rendering; upstream URDF/SRDF name and sensor warnings; Gazebo
mesh-collision warnings; unverified physical contacts; upstream shutdown
segfault/leftover-process behavior. Fresh restart and runtime motion passed after
targeted cleanup. No camera, gripper, perception or autonomous sorting yet.

GitHub connector metadata lookup returned **404** for the intended repository.
The connector can identify the account, but that does not establish repository
existence/access or local Git authentication. GitHub CLI reports no login.
No repository creation or successful push is claimed.

## Publish the already verified local commit

In Ubuntu-24.04:

```bash
cd ~/visionpick_ws
git status --short
git log -1 --oneline
git remote -v
gh auth login --hostname github.com --git-protocol https --web
gh auth setup-git
gh repo view jalal006/visionpick-robotic-manipulation
```

If authenticated inspection confirms the intended repository truly does not exist,
create exactly that repository (the example uses public portfolio visibility):

```bash
gh repo create jalal006/visionpick-robotic-manipulation --public
git push -u origin main
git rev-parse HEAD
git ls-remote origin refs/heads/main
```

The two SHAs must match. If a remote already exists, inspect its branches/history
with `git fetch origin` before pushing; do not overwrite it or force-push.
SSH authentication or a suitably scoped PAT via the credential manager are
alternatives. Never use or send a GitHub account password.

## Next milestone and CV readiness

Next required implementation milestone: **Milestone 2**, workcell/gripper/object
foundation, after publishing this checkpoint and reviewing shutdown/contact issues.
Milestones 2–8 remain planned.

CV-ready wording is limited to the foundation: “Built and verified a simulated
UR5e ROS 2 Jazzy/Gazebo Harmonic workcell with MoveIt trajectory execution and
joint-feedback validation.” Do not claim autonomous vision, grasping, sorting,
physical hardware performance, or a published GitHub demo yet.
