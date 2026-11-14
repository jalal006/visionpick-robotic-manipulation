"""Compose installed Jazzy UR control and MoveIt launches, exactly once each."""
from pathlib import Path
import sys
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, ExecuteProcess, RegisterEventHandler
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from workcell_logic import load_config, world_xml


def generate_launch_description():
    world = ROOT / "logs/workcell.sdf"
    world.parent.mkdir(exist_ok=True)
    world.write_text(world_xml(load_config()))
    def include(package, filename, arguments):
        path = Path(get_package_share_directory(package)) / "launch" / filename
        return IncludeLaunchDescription(PythonLaunchDescriptionSource(str(path)), launch_arguments=arguments.items())
    setup = ExecuteProcess(cmd=["python3", str(ROOT / "scripts/workcell_scene.py")], output="screen")
    def checked_setup(event, context):
        if event.returncode != 0:
            raise RuntimeError('Workcell scene setup failed; see WORKCELL SCENE FAILED above')
        return []
    return LaunchDescription([
        DeclareLaunchArgument("gui", default_value="true"),
        include("ur_simulation_gz", "ur_sim_control.launch.py", {
            "ur_type": "ur5e", "world_file": str(world), "launch_rviz": "false",
            "gazebo_gui": LaunchConfiguration("gui")}),
        include("ur_moveit_config", "ur_moveit.launch.py", {
            "ur_type": "ur5e", "use_sim_time": "true", "launch_rviz": LaunchConfiguration("gui")}),
        RegisterEventHandler(OnProcessExit(target_action=setup, on_exit=checked_setup)),
        setup,
    ])
