# VisionPick project status

- **Project:** VisionPick — Autonomous Camera-Guided Robotic Manipulation.
- **Checkpoint date:** 2026-11-08, Europe/Prague.
- **Verified milestone:** Milestone 1 COMPLETE; published to the intended public GitHub repository.
- **Latest independent external checkpoint supplied by the owner:** November 7
  repository lookup returned 404/inaccessible. Local work was inspected and preserved.
- **Existing source preserved:** foundation commit
  `835645eabab6675aa453f36f920804aca19742ff`, plus all ignored raw logs.
- **Verified pushed implementation commit:** c76e2f3cb669b06f8432b1d5a5e7851976ee9d13.
  GitHub main and the local SHA matched after publication. This documentation-only
  follow-up records that already-known SHA; the final follow-up SHA is reported
  after committing/pushing and can be read with git rev-parse HEAD.
- **Workspace:** `~/visionpick_ws` in WSL distribution `Ubuntu-24.04`.
- **Intended remote:** `https://github.com/jalal006/visionpick-robotic-manipulation.git`.

## Current verification

A fresh official UR5e launch passed the ROS interface audit, direct A/B/home motion,
automatic MoveIt A/B/home execution, an actual RViz **Plan & Execute**, and a final
measured return home. **21 pure-logic tests passed**, including six acceleration
checks. Python compilation and shell syntax checks passed.

The new guard reads each joint's live MoveIt acceleration setting (5 rad/s² here),
checks peak quintic acceleration, and caps direct motion at
min(0.1 rad/s², 10% of the configured limit). Targets and durations are unchanged.
No dependency installation or source build was needed.

Worst automatic MoveIt error: **0.004996993 rad** (rounded upward).
GUI nominal-target maximum error: **0.008326365 rad** (rounded upward).
Final home maximum error: **1.59355e-12 rad**. All are below **0.02 rad**.
Gazebo shoulder-link yaw independently confirmed the GUI movement and return.

Details: [November 8 recheck](MILESTONE_01_RECHECK_2026-11-08.md) and
[evidence JSON](evidence/milestone01-recheck-2026-11-08.json).
The original [November 2 verification](MILESTONE_01_VERIFICATION.md) is preserved.

## Reproduce

In **Windows PowerShell**:

~~~powershell
wsl -d Ubuntu-24.04 --cd '~'
~~~

In the Ubuntu-24.04 shell it opens:

~~~bash
cd ~/visionpick_ws
source scripts/common.sh
bash scripts/check_environment.sh
bash scripts/setup_dependencies.sh
python3 -m pytest -q
bash scripts/launch_simulation.sh
~~~

Leave that terminal open. Open a second PowerShell, enter Ubuntu-24.04 with the
same wsl command, then run this complete block:

~~~bash
cd ~/visionpick_ws
source scripts/common.sh
bash scripts/check_ros_interfaces.sh
python3 scripts/verify_motion.py --mode direct
python3 scripts/verify_motion.py --mode moveit
python3 scripts/verify_motion.py --mode direct --return-home
~~~

The plain Ubuntu app is a separate distribution. From its Bash terminal use
`wsl.exe -d Ubuntu-24.04 --cd '~'`. Every new terminal needs the project
directory and environment sourcing.

## Publication

GitHub browser authentication was completed by the owner and verified as jalal006.
The intended repository was created as public, main was pushed, and its remote
SHA was verified against the local implementation commit above. No credential or
token is stored in the repository; raw logs/screenshots remain ignored.

Repository: [jalal006/visionpick-robotic-manipulation](https://github.com/jalal006/visionpick-robotic-manipulation).

Verify future checkpoints with:

~~~bash
git rev-parse HEAD
git ls-remote origin refs/heads/main
~~~

The two SHAs must match. GitHub publication is now verified; an external reviewer
can independently inspect the evidence and reproduce the procedure.

## Limitations and next work

WSLg uses llvmpipe software graphics. Known upstream robot-name, missing perception
plugin and Gazebo mesh-collision warnings remain. Physical contact fidelity,
camera, gripper, perception, sorting and 30-scene benchmarks remain unverified.

The November 2 shutdown test exposed a move_group exit-time segfault and leftover
Gazebo processes. That historical issue is documented, not claimed fixed.
Today's execution checks showed no controller crash. The simulation was left
running at home after verification.

Milestone 1 is the only completed implementation milestone. Stop here this week.
Milestone 2 (workcell/gripper/objects) is next, after review of contact/shutdown limitations.

CV wording can describe a **simulated UR5e workcell with ROS 2 Jazzy, Gazebo Harmonic,
MoveIt trajectory execution and measured joint-feedback validation**. Autonomous
vision, grasping, sorting and physical-robot performance remain future work.
