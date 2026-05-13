"""
Full demo launch: Gazebo Harmonic + TurtleBot3 Burger + Nav2 + 5-waypoint navigator.

Usage:
  ros2 launch tb3_waypoint_nav demo.launch.py
  ros2 launch tb3_waypoint_nav demo.launch.py use_sim_time:=true world:=turtlebot3_world
"""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument, IncludeLaunchDescription,
    TimerAction, SetEnvironmentVariable,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    pkg_tb3_nav  = get_package_share_directory('tb3_waypoint_nav')
    pkg_tb3_gz   = get_package_share_directory('turtlebot3_gazebo')
    pkg_tb3_nav2 = get_package_share_directory('turtlebot3_navigation2')
    pkg_nav2     = get_package_share_directory('nav2_bringup')

    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    world        = LaunchConfiguration('world',        default='turtlebot3_world')
    map_file     = LaunchConfiguration('map', default=os.path.join(pkg_tb3_nav, 'maps', 'tb3_world.yaml'))
    params_file  = LaunchConfiguration('params_file', default=os.path.join(pkg_tb3_nav, 'config', 'nav2_params.yaml'))

    # ── Declarations ─────────────────────────────────────────
    declare_sim_time  = DeclareLaunchArgument('use_sim_time', default_value='true')
    declare_world     = DeclareLaunchArgument('world',        default_value='turtlebot3_world')
    declare_map       = DeclareLaunchArgument('map',          default_value=os.path.join(pkg_tb3_nav, 'maps', 'tb3_world.yaml'))
    declare_params    = DeclareLaunchArgument('params_file',  default_value=os.path.join(pkg_tb3_nav, 'config', 'nav2_params.yaml'))

    env_tb3_model = SetEnvironmentVariable('TURTLEBOT3_MODEL', 'burger')
    env_rmw       = SetEnvironmentVariable('RMW_IMPLEMENTATION', 'rmw_cyclonedds_cpp')

    # ── Gazebo + robot ────────────────────────────────────────
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_tb3_gz, 'launch', 'turtlebot3_world.launch.py')
        ),
        launch_arguments={'use_sim_time': use_sim_time}.items(),
    )

    # ── Nav2 ──────────────────────────────────────────────────
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

    # ── Waypoint navigator (delayed 15 s to let Nav2 activate) ─
    waypoint_navigator = TimerAction(
        period=15.0,
        actions=[
            Node(
                package='tb3_waypoint_nav',
                executable='waypoint_navigator',
                name='waypoint_navigator',
                output='screen',
                parameters=[{'use_sim_time': use_sim_time}],
            )
        ],
    )

    # ── Live monitor ──────────────────────────────────────────
    monitor = TimerAction(
        period=16.0,
        actions=[
            Node(
                package='tb3_waypoint_nav',
                executable='waypoint_monitor',
                name='waypoint_monitor',
                output='screen',
                parameters=[{'use_sim_time': use_sim_time}],
            )
        ],
    )

    return LaunchDescription([
        env_tb3_model,
        env_rmw,
        declare_sim_time,
        declare_world,
        declare_map,
        declare_params,
        gazebo,
        nav2,
        waypoint_navigator,
        monitor,
    ])
