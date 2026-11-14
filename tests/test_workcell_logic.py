"""Pure acceptance guards; these tests do not claim Gazebo motion."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from workcell_logic import load_config, expected_boxes, verify_boxes, validate_target, world_xml


@pytest.fixture
def config():
    return load_config()


@pytest.mark.parametrize('bad', [0, -1, float('nan'), float('inf'), True])
def test_invalid_dimensions_rejected(config, tmp_path, bad):
    config['objects'][0]['dimensions'][0] = bad
    path = tmp_path/'bad.json'
    path.write_text(json.dumps(config))
    with pytest.raises(ValueError):
        load_config(path)


@pytest.mark.parametrize('key,value', [('frame','base'), ('base_frame','tool0'),
    ('base_pose',[.1,0,0,0,0,0]), ('world','bad/name')])
def test_frame_contract_rejected(config, tmp_path, key, value):
    config[key] = value
    path = tmp_path/'bad.json'
    path.write_text(json.dumps(config))
    with pytest.raises(ValueError):
        load_config(path)


def test_duplicate_ids_rejected(config, tmp_path):
    config['objects'][1]['id'] = config['objects'][0]['id']
    path = tmp_path/'bad.json'
    path.write_text(json.dumps(config))
    with pytest.raises(ValueError):
        load_config(path)


def test_generated_world_has_matching_collision_and_visual_boxes(config):
    sdf = ET.fromstring(world_xml(config))
    world = sdf.find('world')
    assert world.get('name') == config['world']
    for expected in config['objects']:
        model = world.find(f"model[@name='{expected['id']}']")
        assert model.findtext('static') == 'true'
        assert list(map(float,model.findtext('pose').split())) == expected['pose']
        for kind in ['collision','visual']:
            assert list(map(float,model.findtext(f'link/{kind}/geometry/box/size').split())) == expected['dimensions']
        assert model.findtext('link/sensor/contact/collision') == 'collision'


def test_table_clear_of_base_and_fixture_supported(config):
    table, fixture = config['objects']
    assert table['pose'][0]-table['dimensions'][0]/2 >= .25
    top = table['pose'][2]+table['dimensions'][2]/2
    bottom = fixture['pose'][2]-fixture['dimensions'][2]/2
    assert top == pytest.approx(bottom)
    assert fixture['pose'][0] > table['pose'][0]-table['dimensions'][0]/2


def test_scene_readback_is_order_independent_and_repeatable(config):
    expected = expected_boxes(config)
    actual = deepcopy(expected[::-1])
    assert verify_boxes(expected, actual)
    assert verify_boxes(expected, actual)
    assert actual == expected[::-1]


@pytest.mark.parametrize('change', ['missing','duplicate','frame','type','dimension','pose','orientation','nan'])
def test_scene_mismatch_rejected(config, change):
    expected = expected_boxes(config)
    actual = deepcopy(expected)
    if change == 'missing': actual.pop()
    elif change == 'duplicate': actual.append(deepcopy(actual[0]))
    elif change == 'frame': actual[0]['frame'] = 'base'
    elif change == 'type': actual[0]['type'] = 2
    elif change == 'dimension': actual[0]['dimensions'][0] += .01
    elif change == 'pose': actual[0]['position'][0] += .01
    elif change == 'orientation': actual[0]['orientation'] = [0,0,1,0]
    elif change == 'nan': actual[0]['position'][0] = float('nan')
    with pytest.raises(ValueError): verify_boxes(expected, actual)


@pytest.mark.parametrize('age', [-1, 2.01, float('inf'), float('nan')])
def test_stale_scene_rejected(config, age):
    boxes = expected_boxes(config)
    with pytest.raises(ValueError): verify_boxes(boxes, boxes, age)


def test_joint_targets_use_limits_not_collision_labels(config):
    limits = {j:(-3.,3.,1.) for j in config['joint_names']}
    for target in config['targets'].values():
        validate_target(target, config['joint_names'], limits)
    # Deliberately blocked remains inside limits: collision is checked by real MoveIt.
    assert config['targets']['blocked'] != config['targets']['safe_a']


@pytest.mark.parametrize('bad', [[], [0]*5, [4]*6, [float('nan')]*6])
def test_invalid_joint_targets_rejected(config, bad):
    with pytest.raises(ValueError):
        validate_target(bad, config['joint_names'], {j:(-3,3,1) for j in config['joint_names']})
