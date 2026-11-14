# Gripper feasibility — research only, 2026-11-14

Nothing was installed, integrated or grasp-tested. VisionPick still has a bare
tool flange. These are future candidates, not verified VisionPick capabilities.

| Candidate | Evidence and risk |
|---|---|
| Robotiq 2F-85 | [Robotiq's repository](https://github.com/robotiq/robotiq-ros) documents Jazzy and ParallelGripperCommand. Hardware-controller support does not establish Harmonic grasp physics; simulation needs compatible gz_ros2_control, mimic joints and MoveIt limits. |
| Existing PickNik packages | [PickNik source](https://github.com/PickNikRobotics/ros2_robotiq_gripper) provides description/controller packages. A [maintainer announcement](https://discourse.openrobotics.org/t/robotiq-description-and-robotiq-controllers-releases-moving-from-ros2-robotiq-gripper-to-robotiq-ros/59562) describes release-source migration. Inspect and pin actual Jazzy versions before choosing. |
| Community UR integration | [cambel/ur3 ros2-jazzy](https://github.com/cambel/ur3/blob/ros2-jazzy/README.md) explicitly documents UR5e, Robotiq, Jazzy and Harmonic. It selects Bullet Featherstone for gripper mimic joints, unlike the current DART baseline. Its dependencies and physics changes require separate validation. |

Future acceptance must check flange/tool transforms, finger collision geometry,
actuator and mimic limits, friction, contact stability, payload retention and release.
Maintenance, licensing and version pinning also need review.

If contact-only grasps are unreliable, a separately validated attachment constraint
may be appropriate, with proximity/alignment gates, logged attach/release conditions
and matching MoveIt attached-object state. The official
[Harmonic DetachableJoint system](https://gazebosim.org/api/sim/8/detachablejoints.html)
supports detach/reattach but requires tree topology and documents DART/contact
limitations, including reattachment while touching. It is not an automatic grasp
solution. No fallback was implemented this milestone.
