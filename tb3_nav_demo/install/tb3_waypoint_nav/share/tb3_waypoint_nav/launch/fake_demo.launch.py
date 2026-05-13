"""
Fake demo launch: TurtleBot3 fake node (no Gazebo) + Nav2 + 5-waypoint navigator.
Ideal for CI, headless environments, or quick validation without a GPU.

Usage:
  ros2 launch tb3_waypoint_nav fake_demo.launch.py
"""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument, IncludeLaunchDescription,
    TimerAction, SetEnvironmentVariable,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_self      = get_package_share_directory('tb3_waypoint_nav')
    pkg_nav2      = get_package_share_directory('nav2_bringup')
    pkg_fake      = get_package_share_directory('turtlebot3_fake_node')

    use_sim_time = LaunchConfiguration('use_sim_time', default='false')
    map_file     = os.path.join(pkg_self, 'maps', 'tb3_world.yaml')
    params_file  = os.path.join(pkg_self, 'config', 'nav2_params.yaml')

    env_tb3  = SetEnvironmentVariable('TURTLEBOT3_MODEL', 'burger')
    env_rmw  = SetEnvironmentVariable('RMW_IMPLEMENTATION', 'rmw_cyclonedds_cpp')

    declare_sim = DeclareLaunchArgument('use_sim_time', default_value='false')

    # Fake TB3 node (publishes /odom, /scan, /tf without Gazebo)
    fake_robot = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_fake, 'launch', 'turtlebot3_fake_node.launch.py')
        ),
        launch_arguments={'use_sim_time': use_sim_time}.items(),
    )

    # Nav2 full stack
    nav2 = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_nav2, 'launch', 'bringup_launch.py')
        ),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'map':          map_file,
            'params_file':  params_file,
        }.items(),
    )

    # Waypoint navigator — delayed to let Nav2 activate
    navigator = TimerAction(
        period=12.0,
        actions=[Node(
            package='tb3_waypoint_nav',
            executable='waypoint_navigator',
            name='waypoint_navigator',
            output='screen',
            parameters=[{'use_sim_time': use_sim_time}],
        )],
    )

    # Live pose/status monitor
    monitor = TimerAction(
        period=13.0,
        actions=[Node(
            package='tb3_waypoint_nav',
            executable='waypoint_monitor',
            name='waypoint_monitor',
            output='screen',
            parameters=[{'use_sim_time': use_sim_time}],
        )],
    )

    return LaunchDescription([
        env_tb3, env_rmw,
        declare_sim,
        fake_robot,
        nav2,
        navigator,
        monitor,
    ])
