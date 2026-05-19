"""Launch the Galp pallet logistics mission node."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    declared_args = [
        DeclareLaunchArgument(
            "use_sim_time",
            default_value="true",
            description="Use simulation (Gazebo) clock",
        ),
        DeclareLaunchArgument(
            "autostart",
            default_value="true",
            description="Start the mission immediately after Nav2 is available",
        ),
    ]

    mission_node = Node(
        package="rlai_logistics",
        executable="logistics_mission",
        name="logistics_mission",
        output="screen",
        parameters=[
            {
                "use_sim_time": LaunchConfiguration("use_sim_time"),
                "autostart": LaunchConfiguration("autostart"),
            }
        ],
    )

    return LaunchDescription(declared_args + [mission_node])
