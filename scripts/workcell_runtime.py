"""ROS/Gazebo adapters for the canonical Milestone 2 workcell."""
import argparse
import math
import json
from pathlib import Path
import subprocess
import sys
import threading
import time
import xml.etree.ElementTree as ET

from gz.transport13 import Node as GazeboNode
from gz.msgs10.empty_pb2 import Empty
from gz.msgs10.scene_pb2 import Scene
from gz.msgs10.contacts_pb2 import Contacts
from gz.msgs10.clock_pb2 import Clock
from gz.msgs10.sdf_generator_config_pb2 import SdfGeneratorConfig
from gz.msgs10.stringmsg_pb2 import StringMsg
from controller_manager_msgs.srv import ListControllers
from geometry_msgs.msg import Pose
from moveit_msgs.msg import CollisionObject, PlanningSceneComponents
from moveit_msgs.srv import ApplyPlanningScene, GetPlanningScene, GetPositionFK, GetStateValidity
from rclpy.parameter_client import AsyncParameterClient
from shape_msgs.msg import SolidPrimitive

from verify_motion import Verifier
from workcell_logic import expected_boxes, verify_boxes


def arguments():
    return argparse.Namespace(joint_states='/joint_states', description_topic='/robot_description',
        manager='/controller_manager', controller=None, move_group_node='/move_group',
        return_home=False, mode='moveit', moveit_action='/move_action', group=None,
        validity_service='/check_state_validity', tolerance=.02, duration=6., timeout=90.)


def xyz(value):
    return [float(getattr(value, axis)) for axis in 'xyz']


def quaternion(value):
    return [float(getattr(value, axis)) for axis in 'xyzw']


def collision_objects(config):
    objects = []
    for box in expected_boxes(config):
        obj = CollisionObject(id=box['id'], operation=CollisionObject.ADD)
        obj.header.frame_id = box['frame']
        obj.pose.orientation.w = 1.
        obj.primitives = [SolidPrimitive(type=SolidPrimitive.BOX, dimensions=list(map(float, box['dimensions'])))]
        pose = Pose()
        pose.position.x, pose.position.y, pose.position.z = map(float, box['position'])
        pose.orientation.w = 1.
        obj.primitive_poses = [pose]
        objects.append(obj)
    return objects


class GazeboScene:
    def __init__(self, config, monitor=True):
        self.config = config
        self.monitor = monitor
        self.node = GazeboNode()
        if not monitor:
            return
        self.lock = threading.Lock()
        self.counts = {o['id']: 0 for o in config['objects']}
        self.last = {}
        self.robot_contacts = []
        self.clock_count = 0
        self.clock_last = 0.
        self.clock_stamp = -1
        self.callbacks = []
        def clock(message):
            stamp = message.sim.sec*10**9 + message.sim.nsec
            with self.lock:
                if stamp > self.clock_stamp:
                    self.clock_stamp = stamp
                    self.clock_count += 1
                    self.clock_last = time.monotonic()
        self.callbacks.append(clock)
        if not self.node.subscribe(Clock, f"/world/{config['world']}/clock", clock):
            raise RuntimeError('Cannot monitor Gazebo clock')
        for obj in config['objects']:
            key = obj['id']
            def callback(message, key=key):
                with self.lock:
                    self.counts[key] += 1
                    self.last[key] = time.monotonic()
                    for c in message.contact:
                        names = [c.collision1.name, c.collision2.name]
                        # Workcell-to-workcell contacts at the fixture support are intentional.
                        if any('ur::' in name or '_link' in name for name in names):
                            self.robot_contacts.append(names)
            self.callbacks.append(callback)
            topic = f"/world/{config['world']}/model/{key}/link/body/sensor/contacts/contact"
            if not self.node.subscribe(Contacts, topic, callback):
                raise RuntimeError(f'Cannot subscribe to Gazebo contacts: {key}')

    def read(self):
        if self.monitor:
            # transport13 synchronous requests can block Python subscription
            # callbacks on the same interpreter. Isolate readback, not physics.
            result = subprocess.run([sys.executable, str(Path(__file__).resolve()), '--gazebo-query'],
                input=json.dumps(self.config), text=True, capture_output=True, timeout=15, check=True)
            return json.loads(result.stdout)
        before = time.monotonic()
        ok, scene = self.node.request(f"/world/{self.config['world']}/scene/info", Empty(), Empty, Scene, 5000)
        if not ok:
            raise RuntimeError('Gazebo scene query failed')
        request = SdfGeneratorConfig()
        request.global_entity_gen_config.expand_include_tags.data = True
        ok, exported = self.node.request(f"/world/{self.config['world']}/generate_world_sdf",
            request, SdfGeneratorConfig, StringMsg, 5000)
        if not ok:
            raise RuntimeError('Gazebo collision geometry export failed')
        sdf = ET.fromstring(exported.data)
        actual = []
        wanted = {o['id'] for o in self.config['objects']}
        robot = [m for m in scene.model if m.name == 'ur']
        if len(robot) != 1 or max(map(abs, xyz(robot[0].pose.position))) > 1e-6:
            raise RuntimeError('Missing or displaced Gazebo UR model')
        if max(abs(a-b) for a,b in zip(quaternion(robot[0].pose.orientation), [0,0,0,1])) > 1e-6:
            raise RuntimeError('Rotated Gazebo UR model')
        for model in scene.model:
            if model.name not in wanted:
                continue
            model_sdf = sdf.find(f"./world/model[@name='{model.name}']")
            if model_sdf is None or model_sdf.findtext('static') != 'true' or len(model.link) != 1:
                raise RuntimeError('Workcell model is not a single static body')
            link = model.link[0]
            if max(map(abs, xyz(link.pose.position))) > 1e-6 or max(
                abs(a-b) for a,b in zip(quaternion(link.pose.orientation), [0,0,0,1])) > 1e-6:
                raise RuntimeError('Unexpected Gazebo link offset')
            shapes = model_sdf.findall('./link/collision') if model_sdf is not None else []
            if len(shapes) != 1:
                raise RuntimeError('Missing/duplicate Gazebo box collision')
            shape = shapes[0]
            if shape.find('geometry/box/size') is None or any(float(x) != 0 for x in shape.findtext('pose', '0 0 0 0 0 0').split()):
                raise RuntimeError('Unexpected Gazebo collision geometry')
            actual.append(dict(id=model.name, frame=self.config['frame'], type=1,
                dimensions=list(map(float, shape.findtext('geometry/box/size').split())), position=xyz(model.pose.position),
                orientation=quaternion(model.pose.orientation)))
        verify_boxes(expected_boxes(self.config), actual, time.monotonic()-before)
        return actual

    def contact_snapshot(self):
        with self.lock:
            return dict(self.counts), dict(self.last), list(self.robot_contacts)

    def check_contacts(self):
        counts, last, contacts = self.contact_snapshot()
        # Harmonic Contact publishes only nonempty contact sets, not heartbeats.
        # Clock + actual publisher discovery establish liveness; sampled MoveIt
        # states supply independent geometry checks. Silence alone is not proof.
        if self.clock_count == 0 or time.monotonic()-self.clock_last > 2:
            raise RuntimeError('Missing/stale Gazebo physics clock')
        if contacts:
            raise RuntimeError(f'Robot contacted the workcell: {contacts[:5]}')
        return counts

    def check_publishers(self):
        topics = self.node.topic_list()
        for key in self.counts:
            topic = f"/world/{self.config['world']}/model/{key}/link/body/sensor/contacts/contact"
            if topic not in topics:
                raise RuntimeError(f'Contact publisher missing: {topic}')


class WorkcellClient(Verifier):
    def __init__(self, config, log, setup=False):
        args = arguments()
        args.return_home = setup
        super().__init__(args, log)
        self.config = config

    def prepare(self):
        # Services appear before controller activation during a fresh launch.
        deadline = time.monotonic()+60
        while True:
            response = self.service(ListControllers, '/controller_manager/list_controllers', ListControllers.Request())
            active = [c for c in response.controller if c.state == 'active']
            if any('JointStateBroadcaster' in c.type for c in active) and any('JointTrajectoryController' in c.type for c in active):
                break
            if time.monotonic() >= deadline:
                raise RuntimeError('Controllers did not activate')
            time.sleep(.25)
        super().prepare()
        if set(self.joints) != set(self.config['joint_names']):
            raise RuntimeError('Configured and live joints differ')
        params = AsyncParameterClient(self, '/move_group')
        if not params.wait_for_services(timeout_sec=20):
            raise RuntimeError('MoveIt model parameters unavailable')
        values = self.result(params.get_parameters(['robot_description_semantic'])).values
        if len(values) != 1 or not values[0].string_value:
            raise RuntimeError('Missing live SRDF')
        srdf = ET.fromstring(values[0].string_value)
        groups = [g for g in srdf.findall('group') if g.find('chain') is not None
                  and g.find('chain').get('base_link') == self.config['base_frame']]
        if len(groups) != 1:
            raise RuntimeError('Cannot discover one arm planning group')
        self.args.group = groups[0].get('name')
        self.tip = groups[0].find('chain').get('tip_link')
        scene = self.scene()
        self.frame = scene.robot_state.multi_dof_joint_state.header.frame_id
        if self.frame != self.config['frame']:
            raise RuntimeError(f'Unexpected planning frame: {self.frame}')
        pose = self.fk(self.fresh(), [self.config['base_frame']])[0].pose
        if max(map(abs, xyz(pose.position))) > 1e-6 or max(
            abs(a-b) for a,b in zip(quaternion(pose.orientation), [0,0,0,1])) > 1e-6:
            raise RuntimeError('World-to-base transform is not identity')
        self.event('model', group=self.args.group, frame=self.frame, tip=self.tip,
                   base_frame=self.config['base_frame'], base_position=xyz(pose.position))

    def target(self, label):
        by_name = dict(zip(self.config['joint_names'], self.config['targets'][label]))
        return [float(by_name[j]) for j in self.joints]

    def scene(self):
        req = GetPlanningScene.Request()
        req.components.components = (PlanningSceneComponents.ROBOT_STATE |
            PlanningSceneComponents.WORLD_OBJECT_GEOMETRY | PlanningSceneComponents.ALLOWED_COLLISION_MATRIX)
        return self.service(GetPlanningScene, '/get_planning_scene', req).scene

    def scene_boxes(self, expected=None):
        start = time.monotonic()
        scene = self.scene()
        actual = []
        for obj in scene.world.collision_objects:
            if not obj.id.startswith('visionpick_'):
                continue
            if len(obj.primitives) != 1 or len(obj.primitive_poses) != 1 or obj.meshes or obj.planes:
                raise RuntimeError('Expected one box per workcell object')
            if max(abs(a-b) for a,b in zip(quaternion(obj.pose.orientation), [0,0,0,1])) > 1e-6:
                raise RuntimeError('Unexpected object rotation')
            actual.append(dict(id=obj.id, frame=obj.header.frame_id, type=obj.primitives[0].type,
                dimensions=list(obj.primitives[0].dimensions),
                position=[a+b for a,b in zip(xyz(obj.pose.position),xyz(obj.primitive_poses[0].position))],
                orientation=quaternion(obj.primitive_poses[0].orientation)))
        verify_boxes(expected if expected is not None else expected_boxes(self.config), actual,
                     time.monotonic()-start)
        # No workcell exceptions may be hidden in the collision matrix.
        acm = scene.allowed_collision_matrix
        for i, name in enumerate(acm.entry_names):
            if name.startswith('visionpick_') and any(acm.entry_values[i].enabled):
                raise RuntimeError('Workcell collisions disabled in ACM')
        if any(enabled for enabled in acm.default_entry_values):
            raise RuntimeError('Unexpected default allowed collisions')
        return actual

    def apply(self, objects):
        req = ApplyPlanningScene.Request()
        req.scene.is_diff = True
        req.scene.robot_state.is_diff = True
        req.scene.world.collision_objects = objects
        if not self.service(ApplyPlanningScene, '/apply_planning_scene', req).success:
            raise RuntimeError('Planning scene update rejected')

    def setup_scene(self):
        self.apply(collision_objects(self.config))
        return self.scene_boxes()

    def validity(self, q):
        req = GetStateValidity.Request()
        req.group_name = self.args.group
        req.robot_state.joint_state.name = self.joints
        req.robot_state.joint_state.position = list(q)
        req.robot_state.is_diff = True
        response = self.service(GetStateValidity, self.args.validity_service, req)
        return dict(valid=response.valid, contacts=[dict(body_1=c.contact_body_1,
            body_2=c.contact_body_2, depth=c.depth) for c in response.contacts])

    def fk(self, q, links=None):
        req = GetPositionFK.Request()
        req.header.frame_id = self.config['frame']
        req.fk_link_names = links or [self.tip]
        req.robot_state.joint_state.name = self.joints
        req.robot_state.joint_state.position = list(q)
        req.robot_state.is_diff = True
        result = self.service(GetPositionFK, '/compute_fk', req)
        if result.error_code.val != 1:
            raise RuntimeError('Forward kinematics failed')
        return result.pose_stamped


if __name__ == '__main__' and sys.argv[1:] == ['--gazebo-query']:
    print(json.dumps(GazeboScene(json.load(sys.stdin), monitor=False).read()))
