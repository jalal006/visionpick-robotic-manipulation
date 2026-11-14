"""Canonical box geometry and fail-closed checks; no ROS/Gazebo imports."""
import json
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/workcell.json"


def vector(value, size):
    if not isinstance(value, list) or len(value) != size or any(
        isinstance(x, bool) or not isinstance(x, (float, int)) or not math.isfinite(x)
        for x in value
    ):
        raise ValueError(f"Expected {size} finite numbers")
    return value


def load_config(path=CONFIG):
    data = json.loads(Path(path).read_text())
    if data["schema_version"] != 1 or data["frame"] != "world" or data["base_frame"] != "base_link":
        raise ValueError("Unsupported schema or reference frame")
    if vector(data["base_pose"], 6) != [0]*6:
        raise ValueError("Official UR spawn requires identity world-to-base transform")
    if not re.fullmatch(r"[a-z][a-z0-9_]*", data["world"]):
        raise ValueError("Invalid world name")
    ids = [obj["id"] for obj in data["objects"]]
    if sorted(ids) != ["visionpick_fixture", "visionpick_table"]:
        raise ValueError("Expected exactly one table and one fixture")
    for obj in data["objects"]:
        if min(vector(obj["dimensions"], 3)) <= 0:
            raise ValueError("Dimensions must be positive")
        if vector(obj["pose"], 6)[3:] != [0]*3:
            raise ValueError("This workcell supports axis-aligned boxes only")
        if any(not 0 <= x <= 1 for x in vector(obj["color"], 4)):
            raise ValueError("Invalid color")
    joints = data["joint_names"]
    if len(joints) != 6 or len(set(joints)) != 6:
        raise ValueError("Expected six unique joints")
    if set(data["targets"]) != {"home", "safe_a", "safe_b", "blocked"}:
        raise ValueError("Missing workcell targets")
    for q in data["targets"].values():
        vector(q, 6)
    return data


def validate_target(q, joints, limits):
    vector(q, len(joints))
    for j, x in zip(joints, q):
        lo, hi, velocity = limits[j]
        if not all(map(math.isfinite, (lo, hi, velocity))) or velocity <= 0 or not lo+.01 <= x <= hi-.01:
            raise ValueError(f"Invalid target/limits for {j}")


def expected_boxes(config):
    return [{"id": o["id"], "frame": config["frame"], "type": 1,
             "dimensions": o["dimensions"], "position": o["pose"][:3],
             "orientation": [0., 0., 0., 1.]} for o in config["objects"]]


def verify_boxes(expected, actual, age_seconds=0.):
    if not math.isfinite(age_seconds) or not 0 <= age_seconds <= 2:
        raise ValueError("Stale scene query")
    if len(actual) != len({x["id"] for x in actual}):
        raise ValueError("Duplicate collision IDs")
    by_id = {x["id"]: x for x in actual}
    for want in expected:
        got = by_id.get(want["id"])
        if got is None:
            raise ValueError(f"Missing collision object: {want['id']}")
        if got["frame"] != want["frame"] or got["type"] != 1:
            raise ValueError("Collision frame/type mismatch")
        for key, size in [("dimensions", 3), ("position", 3), ("orientation", 4)]:
            value = vector(got[key], size)
            if max(abs(a-b) for a,b in zip(value, want[key])) > 1e-6:
                raise ValueError(f"Collision geometry mismatch: {want['id']} {key}")
    return True


def world_xml(config):
    root = ET.Element("sdf", version="1.9")
    world = ET.SubElement(root, "world", name=config["world"])
    physics = ET.SubElement(world, "physics", name="1ms", type="ignored")
    ET.SubElement(physics, "max_step_size").text = "0.001"
    ET.SubElement(physics, "real_time_factor").text = "1"
    for filename, name in [("physics", "Physics"), ("user-commands", "UserCommands"),
                           ("scene-broadcaster", "SceneBroadcaster"), ("contact", "Contact")]:
        ET.SubElement(world, "plugin", filename=f"gz-sim-{filename}-system", name=f"gz::sim::systems::{name}")
    light = ET.SubElement(world, "light", type="directional", name="sun")
    ET.SubElement(light, "pose").text = "0 0 10 0 0 0"
    ET.SubElement(light, "diffuse").text = "0.8 0.8 0.8 1"
    ET.SubElement(light, "direction").text = "-0.5 0.1 -0.9"
    for obj in config["objects"]:
        model = ET.SubElement(world, "model", name=obj["id"])
        ET.SubElement(model, "static").text = "true"
        ET.SubElement(model, "pose").text = " ".join(map(str, obj["pose"]))
        link = ET.SubElement(model, "link", name="body")
        for kind in ("collision", "visual"):
            shape = ET.SubElement(link, kind, name=kind)
            box = ET.SubElement(ET.SubElement(shape, "geometry"), "box")
            ET.SubElement(box, "size").text = " ".join(map(str, obj["dimensions"]))
            if kind == "visual":
                material = ET.SubElement(shape, "material")
                for tag in ("ambient", "diffuse"):
                    ET.SubElement(material, tag).text = " ".join(map(str, obj["color"]))
        sensor = ET.SubElement(link, "sensor", name="contacts", type="contact")
        ET.SubElement(sensor, "always_on").text = "true"
        ET.SubElement(sensor, "update_rate").text = "50"
        ET.SubElement(ET.SubElement(sensor, "contact"), "collision").text = "collision"
    ET.indent(root)
    return ET.tostring(root, encoding="unicode")


def summarize_report(report):
    """Validate compact acceptance evidence; never infer PASS from action success alone."""
    if report.get('status') != 'PASS' or report.get('schema_version') != 1:
        raise ValueError('Report is not a successful workcell run')
    rows = report['events']
    def one(kind, label=None):
        found = [r for r in rows if r['event'] == kind and (label is None or r.get('label') == label)]
        if len(found) != 1:
            raise ValueError(f'Missing/duplicate evidence: {kind} {label}')
        return found[0]
    one('PASS')
    boxes = expected_boxes(report['config'])
    verify_boxes(boxes, one('gazebo_geometry')['objects'])
    scene = one('scene_verified')
    verify_boxes(boxes, scene['objects'])
    if not scene['idempotent']:
        raise ValueError('Scene idempotence not verified')
    negative = one('negative_test')
    if (negative['with_fixture']['valid'] or not negative['without_fixture']['valid'] or
        not negative['fixture_restored'] or negative['control_plan_executed'] or not any(
            'visionpick_fixture' in (c['body_1'],c['body_2']) for c in negative['with_fixture']['contacts'])):
        raise ValueError('Collision/control comparison is incomplete')
    blocked, control = one('plan','blocked_with_fixture'), one('plan','same_target_without_fixture')
    if blocked['status'] != 6 or blocked['error_code'] not in (-1,-12,99999) or blocked['points'] != 0:
        raise ValueError('Blocked plan was not rejected')
    if control['status'] != 4 or control['error_code'] != 1 or control['points'] < 2:
        raise ValueError('No successful corresponding control plan')
    executions = [one('executed',label) for label in ('safe_a','safe_b','home')]
    for row in executions:
        error = row['max_error']
        if (not math.isfinite(error) or not 0 <= error <= .02 or row['status'] != 4 or
            row['error_code'] != 1 or row['feedback_samples'] < 3 or row['trajectory_checks'] < 2 or
            row['measured_state_checks'] < 2 or row['robot_workcell_contacts'] != 0):
            raise ValueError('Insufficient successful execution evidence')
    return dict(executions=len(executions), worst_joint_error=max(r['max_error'] for r in executions),
                blocked_error_code=blocked['error_code'])


if __name__ == "__main__":
    config = load_config()
    output = ROOT / "logs/workcell.sdf"
    output.parent.mkdir(exist_ok=True)
    output.write_text(world_xml(config))
    print(output)
