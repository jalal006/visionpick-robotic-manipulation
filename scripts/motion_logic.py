"""Pure validation for the simulation-only motion verifier (radians, seconds)."""
import math
import xml.etree.ElementTree as ET


def limits_from_urdf(xml, joints):
    root = ET.fromstring(xml)
    plugins = [p.text for p in root.findall("./ros2_control/hardware/plugin")]
    if plugins != ["gz_ros2_control/GazeboSimSystem"]:
        raise ValueError("Refusing non-Gazebo or ambiguous hardware")
    result = {}
    for name in joints:
        elements = [j for j in root.findall("joint") if j.get("name") == name]
        if len(elements) != 1 or elements[0].get("type") != "revolute":
            raise ValueError(f"Expected one bounded revolute joint: {name}")
        joint = elements[0]
        limit = joint.find("limit")
        lo, hi, velocity = (float(limit.get(k)) for k in ("lower", "upper", "velocity"))
        safety = joint.find("safety_controller")
        if safety is not None:
            lo = max(lo, float(safety.get("soft_lower_limit", lo)))
            hi = min(hi, float(safety.get("soft_upper_limit", hi)))
        if not all(map(math.isfinite, (lo, hi, velocity))) or lo >= hi or velocity <= 0:
            raise ValueError(f"Invalid limits: {name}")
        result[name] = (lo, hi, velocity)
    return result


def ordered_positions(names, positions, joints):
    if len(names) != len(positions) or len(set(names)) != len(names):
        raise ValueError("Malformed or duplicate joint feedback")
    values = dict(zip(names, positions))
    ordered = [float(values[j]) for j in joints]
    if not all(map(math.isfinite, ordered)):
        raise ValueError("Nonfinite joint feedback")
    return ordered


def validate_segment(start, target, joints, limits, duration):
    if len(start) != len(joints) or len(target) != len(joints):
        raise ValueError("Joint vector length mismatch")
    if not math.isfinite(duration) or duration < 4.0:
        raise ValueError("At least four seconds per movement required")
    for name, a, b in zip(joints, start, target):
        lo, hi, velocity = limits[name]
        if not all(map(math.isfinite, (a, b))) or not lo + .01 <= a <= hi - .01 or not lo + .01 <= b <= hi - .01:
            raise ValueError(f"Position outside limits/margin: {name}")
        if abs(b - a) > .25:
            raise ValueError(f"Refusing large direct movement: {name}")
        # Quintic interpolation with zero endpoint velocity/acceleration.
        if 1.875 * abs(b - a) / duration > min(.15, velocity * .1):
            raise ValueError(f"Velocity too high: {name}")


def make_targets(home, joints):
    a, b = list(home), list(home)
    pan = joints.index("shoulder_pan_joint")
    wrist = joints.index("wrist_3_joint")
    a[pan] += .10
    a[wrist] += .08
    b[pan] -= .10
    b[wrist] -= .08
    return [("pose_a", a), ("pose_b", b), ("home", list(home))]


def assess(start, target, samples, tolerance=.02):
    if not samples or len(start) != len(target):
        raise ValueError("Missing feedback")
    if not 0 < tolerance <= .02 or not math.isfinite(tolerance):
        raise ValueError("Invalid tolerance")
    for sample in samples:
        if len(sample) != len(target) or not all(map(math.isfinite, sample)):
            raise ValueError("Invalid feedback sample")
    error = [abs(a - b) for a, b in zip(samples[-1], target)]
    excursion = [max(abs(s[i] - start[i]) for s in samples) for i in range(len(start))]
    if max(error) > tolerance:
        raise ValueError(f"Final joint error exceeds tolerance: {error}")
    for i, (a, b) in enumerate(zip(start, target)):
        if abs(b-a) > 2*tolerance and excursion[i] < abs(b-a)*.5:
            raise ValueError("Action succeeded without measured movement")
    return error, excursion


def validate_acceleration(start, target, joints, limits, duration):
    """Bound peak quintic acceleration against live MoveIt planning limits."""
    if len(start) != len(joints) or len(target) != len(joints):
        raise ValueError("Joint vector length mismatch")
    if not math.isfinite(duration) or duration < 4.0:
        raise ValueError("At least four seconds per movement required")
    for name, a, b in zip(joints, start, target):
        limit = limits[name]
        if not all(map(math.isfinite, (a, b, limit))) or limit <= 0:
            raise ValueError(f"Invalid acceleration input: {name}")
        # max |d2/dt2 (10u^3 - 15u^4 + 6u^5)| = 10/sqrt(3) / T^2.
        peak = (10 / math.sqrt(3)) * abs(b - a) / duration**2
        if peak > min(.1, limit * .1):
            raise ValueError(f"Acceleration too high: {name}")
