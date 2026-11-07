import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from motion_logic import assess, limits_from_urdf, ordered_positions, validate_segment, make_targets

JOINTS = ["shoulder_pan_joint", "wrist_3_joint"]
LIMITS = {n: (-3.0, 3.0, 2.0) for n in JOINTS}

def test_feedback_is_reordered_by_joint_name():
    assert ordered_positions(list(reversed(JOINTS)), [.2, .1], JOINTS) == [.1, .2]

@pytest.mark.parametrize("names,positions", [(JOINTS, [0]), ([JOINTS[0]]*2,[0,0]), (JOINTS,[float("nan"),0])])
def test_bad_feedback_rejected(names, positions):
    with pytest.raises((ValueError, KeyError)):
        ordered_positions(names, positions, JOINTS)

@pytest.mark.parametrize("target,duration", [([3,0],6), ([.3,0],6), ([float("inf"),0],6), ([.1,0],1), ([.1],6)])
def test_unsafe_segment_rejected(target, duration):
    with pytest.raises(ValueError):
        validate_segment([0,0], target, JOINTS, LIMITS, duration)

def test_three_distinct_targets_return_home():
    home = [.2,.3]
    targets = make_targets(home, JOINTS)
    assert targets[-1] == ("home", home)
    assert targets[0][1] != targets[1][1]
    previous = home
    for _, target in targets:
        validate_segment(previous, target, JOINTS, LIMITS, 6)
        previous = target

def test_no_motion_does_not_pass_success():
    with pytest.raises(ValueError):
        assess([0,0], [.1,.08], [[0,0]]*10)

def test_real_feedback_passes_and_reports_error():
    errors, excursions = assess([0,0], [.1,.08], [[.02,.03],[.099,.081]])
    assert max(errors) == pytest.approx(.001)
    assert excursions == [.099,.081]

@pytest.mark.parametrize("plugin", ["mock_components/GenericSystem", "ur_robot_driver/URPositionHardwareInterface"])
def test_non_simulation_hardware_rejected(plugin):
    with pytest.raises(ValueError):
        limits_from_urdf(f"<robot><ros2_control><hardware><plugin>{plugin}</plugin></hardware></ros2_control></robot>", [])

def test_effective_soft_limits_used():
    xml = '<robot><ros2_control><hardware><plugin>gz_ros2_control/GazeboSimSystem</plugin></hardware></ros2_control><joint name="j" type="revolute"><limit lower="-3" upper="3" velocity="2"/><safety_controller soft_lower_limit="-2.8" soft_upper_limit="2.8"/></joint></robot>'
    assert limits_from_urdf(xml, ["j"]) == {"j":(-2.8,2.8,2.)}


def test_small_segment_respects_configured_acceleration():
    from motion_logic import validate_acceleration
    validate_acceleration([0,0], [.2,.16], JOINTS, dict.fromkeys(JOINTS, 5.), 6.)

@pytest.mark.parametrize("limit", [0., -1., float("nan"), float("inf")])
def test_invalid_acceleration_limit_rejected(limit):
    from motion_logic import validate_acceleration
    with pytest.raises(ValueError):
        validate_acceleration([0,0], [.2,.16], JOINTS, dict.fromkeys(JOINTS, limit), 6.)

def test_lower_configured_acceleration_limit_is_respected():
    from motion_logic import validate_acceleration
    with pytest.raises(ValueError, match="Acceleration too high"):
        validate_acceleration([0,0], [.2,.16], JOINTS, dict.fromkeys(JOINTS, .1), 6.)
