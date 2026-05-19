"""Launch the Galp pallet logistics mission node."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    pkg = FindPackageShare("rlai_logistics")

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
        DeclareLaunchArgument(
            "waypoints_file",
            default_value=PathJoinSubstitution([pkg, "config", "galp_waypoints.yaml"]),
            description="YAML file with mission locations and task sequence",
        ),
        DeclareLaunchArgument(
            "goal_timeout",
            default_value="900.0",
            description="Maximum seconds to wait for each Nav2 goal before continuing",
        ),
        DeclareLaunchArgument(
            "enable_gazebo_attach",
            default_value="false",
            description="Publish Gazebo detachable-joint attach/detach commands for pallets",
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
                "waypoints_file": LaunchConfiguration("waypoints_file"),
                "goal_timeout": LaunchConfiguration("goal_timeout"),
                "enable_gazebo_attach": LaunchConfiguration("enable_gazebo_attach"),
            }
        ],
    )

    return LaunchDescription(declared_args + [mission_node])
