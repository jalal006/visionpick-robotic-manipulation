# VisionPick project status

- **Project:** VisionPick — Autonomous Camera-Guided Robotic Manipulation.
- **Checkpoint:** 2026-11-14, Europe/Prague.
- **Verified milestone:** Milestone 2 COMPLETE locally; Milestone 1 remains functional.
- **Verified previous local and remote main commit:**
  `3586f036b765835145b11c70b849123a913b8455`.
- **Workspace:** `/home/ahadd/visionpick_ws`, WSL Ubuntu-24.04, user `ahadd`.
- **Repository:** https://github.com/jalal006/visionpick-robotic-manipulation
- The new final commit SHA and matching remote SHA are reported after publication,
  avoiding a self-referential commit in this file.

## Current verification

A fresh GUI-enabled workcell launch passed geometry readback, idempotent planning
scene setup, collision-free home, safe A/B/home planning and execution, measured
settling and blocked-goal rejection. Both headless and GUI-enabled integration runs
passed. These were actual Gazebo physics/controller runs, not mocks.

**61 tests pass:** 21 existing tests and 40 new tests. Python compilation and shell
syntax checks pass. The original interface audit passed on the baseline and final
GUI workcell. Direct, MoveIt and return-home Milestone 1 smoke tests passed both in
the original empty world and with the workcell present.

Final run worst tracking error relative to the planned endpoint:
**8.82245577808749e-10 rad**, below 0.02 rad. These tiny errors reflect ideal simulated
position control, not real-robot accuracy. The planner's requested-target tolerance
is 0.001 rad. Thirteen of 21 straight-line samples between safe A and B collided;
the checked MoveIt detour executed successfully.

The blocked target collided with the fixture in explicit forearm/wrist contacts.
MoveIt returned action status 6 and generic OMPL FAILURE 99999, with zero trajectory
points. The same target was collision-free and planned successfully after removing
only the fixture from MoveIt. That control plan was never executed. The fixture
was restored and verified before motion.

Details: [verification](MILESTONE_02_VERIFICATION.md),
[compact evidence](evidence/milestone02-results.json),
[gripper research only](GRIPPER_FEASIBILITY.md).
Historical Milestone 1 reports and evidence are unchanged.

## Reproduce

In Windows PowerShell:

```powershell
wsl -d Ubuntu-24.04 -u ahadd --cd /home/ahadd/visionpick_ws
```

In the resulting Ubuntu terminal:

```bash
source scripts/common.sh
python3 -m pytest -q
bash scripts/launch_workcell.sh
```

Wait for SCENE_READY. In a second terminal entered through the same WSL command:

```bash
source scripts/common.sh
python3 scripts/verify_workcell.py
```

Use `gui:=false` on the launcher for headless physics. Stop the launch with Ctrl+C.
The plain Ubuntu app opens a different distribution/user; from that Bash shell,
use `wsl.exe` in place of PowerShell's `wsl`. Never run both milestone launchers.

## Scope and limitations

One solid worktable and one fixture, no camera, gripper, blocks, recognition,
sorting or AI. Collision sampling is discrete. Contact topics reported no
robot/workcell contacts; their silence alone is not the acceptance evidence.
WSLg software rendering and existing upstream name/sensor/shutdown warnings remain.
The supervisor contains its own leftover processes; it does not fix MoveIt's
destruction-time crash. No new dependency or global configuration was introduced.
No unrelated project was modified.

The verified test stack is shut down at the end of this task. Milestone 3 is next,
but no implementation was started. Portfolio claims can now include a simulated
UR5e tabletop workcell with collision-aware MoveIt execution, measured joint
feedback, and demonstrated blocked-goal rejection.
