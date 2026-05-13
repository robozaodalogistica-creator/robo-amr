"""
Headless TurtleBot3 5-waypoint navigation demo.
Uses our own robot_sim node (no nav2_loopback_sim dependency).
No Gazebo, no display required.

Stack:
  robot_sim         — integrates /cmd_vel, publishes /odom /scan /tf
  map_server        — our pre-built map
  Nav2 full stack   — bt_navigator, DWB controller, NavFn planner, …
  waypoint_navigator — sends 5 waypoints via FollowWaypoints
  waypoint_monitor  — live pose/status to stdout
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument, GroupAction,
    IncludeLaunchDescription, SetEnvironmentVariable, TimerAction,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, SetParameter


def generate_launch_description():
    pkg_self         = get_package_share_directory('tb3_waypoint_nav')
    pkg_nav2_bringup = get_package_share_directory('nav2_bringup')

    map_file    = os.path.join(pkg_self, 'maps',   'tb3_world.yaml')
    params_file = os.path.join(pkg_self, 'config', 'nav2_params_loopback.yaml')

    autostart   = LaunchConfiguration('autostart',   default='true')
    use_respawn = LaunchConfiguration('use_respawn', default='false')

    # 1. Our robot sim — publishes TFs, /odom, /scan from wall clock
    robot_sim = Node(
        package='tb3_waypoint_nav',
        executable='robot_sim',
        name='robot_sim',
        output='screen',
        parameters=[{'use_sim_time': False}],
    )

    # 2. map_server + lifecycle — wall time
    map_stack = GroupAction([
        SetParameter('use_sim_time', False),
        Node(
            package='nav2_map_server',
            executable='map_server',
            name='map_server',
            output='screen',
            parameters=[params_file, {'yaml_filename': map_file}],
        ),
        Node(
            package='nav2_lifecycle_manager',
            executable='lifecycle_manager',
            name='lifecycle_manager_map',
            output='screen',
            parameters=[params_file,
                        {'autostart': True},
                        {'node_names': ['map_server']}],
        ),
    ])

    # 3. Nav2 navigation stack — wall time, no composition
    nav2 = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_nav2_bringup, 'launch', 'navigation_launch.py')
        ),
        launch_arguments={
            'use_sim_time':    'False',
            'params_file':     params_file,
            'autostart':       'True',
            'use_composition': 'False',
            'use_respawn':     'False',
        }.items(),
    )

    # 4. waypoint_navigator  (delayed 30s — Nav2 lifecycle can take ~20-25s)
    navigator = TimerAction(
        period=30.0,
        actions=[Node(
            package='tb3_waypoint_nav',
            executable='waypoint_navigator',
            name='waypoint_navigator',
            output='screen',
            parameters=[{'use_sim_time': False}],
        )],
    )

    # 5. live pose/status monitor
    monitor = TimerAction(
        period=31.0,
        actions=[Node(
            package='tb3_waypoint_nav',
            executable='waypoint_monitor',
            name='waypoint_monitor',
            output='screen',
            parameters=[{'use_sim_time': False}],
        )],
    )

    return LaunchDescription([
        SetEnvironmentVariable('TURTLEBOT3_MODEL', 'burger'),
        SetEnvironmentVariable('RMW_IMPLEMENTATION', 'rmw_cyclonedds_cpp'),
        SetEnvironmentVariable(
            'CYCLONEDDS_URI',
            '<CycloneDDS><Domain id="any">'
            '<General><AllowMulticast>spdp</AllowMulticast></General>'
            '</Domain></CycloneDDS>'),
        DeclareLaunchArgument('autostart',    default_value='true'),
        DeclareLaunchArgument('use_respawn',  default_value='false'),

        robot_sim,
        map_stack,
        nav2,
        navigator,
        monitor,
    ])
