"""
3-waypoint Nav2 headless demo.
  robot_sim   — loopback simulator (cmd_vel→odom/scan/tf)
  map_server  — pre-built free-space map
  Nav2 stack  — navigation_launch.py (bt_navigator, DWB, NavFn, ...)
  navigator   — sends 3 waypoints via FollowWaypoints (after 30s)
"""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    IncludeLaunchDescription,
    SetEnvironmentVariable, TimerAction,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node


def generate_launch_description():
    pkg         = get_package_share_directory('nav_test')
    pkg_nav2    = get_package_share_directory('nav2_bringup')

    # Absolute path so map_server finds the file (no relative-path ambiguity)
    map_file    = os.path.join(pkg, 'maps', 'free_space.yaml')
    params_file = os.path.join(pkg, 'config', 'nav2_params.yaml')

    # ── robot loopback simulator ──────────────────────────────────────────
    robot_sim = Node(
        package='nav_test',
        executable='robot_sim',
        name='robot_sim',
        output='screen',
        parameters=[{'use_sim_time': False}],
    )

    # ── map_server ────────────────────────────────────────────────────────
    # IMPORTANT: yaml_filename set directly as dict — NOT via params_file
    # override, which was previously read as empty string.
    map_server = Node(
        package='nav2_map_server',
        executable='map_server',
        name='map_server',
        output='screen',
        parameters=[{'yaml_filename': map_file, 'use_sim_time': False}],
    )

    # Delay the lifecycle manager so map_server has time to register its
    # lifecycle service before the manager tries to transition it.
    map_lc = TimerAction(
        period=3.0,
        actions=[Node(
            package='nav2_lifecycle_manager',
            executable='lifecycle_manager',
            name='lifecycle_manager_map',
            output='screen',
            parameters=[{
                'use_sim_time': False,
                'autostart': True,
                'node_names': ['map_server'],
            }],
        )],
    )

    # ── Nav2 navigation stack (bt_navigator, DWB, NavFn, …) ───────────────
    nav2 = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_nav2, 'launch', 'navigation_launch.py')
        ),
        launch_arguments={
            'use_sim_time':    'False',
            'params_file':     params_file,
            'autostart':       'True',
            'use_composition': 'False',
            'use_respawn':     'False',
        }.items(),
    )

    # ── navigator — delayed 30 s so Nav2 lifecycle finishes ───────────────
    navigator = TimerAction(
        period=30.0,
        actions=[Node(
            package='nav_test',
            executable='navigator',
            name='navigator',
            output='screen',
            parameters=[{'use_sim_time': False}],
        )],
    )

    return LaunchDescription([
        # CycloneDDS on loopback — no multicast needed for single-host demo
        SetEnvironmentVariable('RMW_IMPLEMENTATION', 'rmw_cyclonedds_cpp'),
        SetEnvironmentVariable(
            'CYCLONEDDS_URI',
            '<CycloneDDS><Domain>'
            '<General><NetworkInterfaceAddress>lo</NetworkInterfaceAddress></General>'
            '</Domain></CycloneDDS>'),

        robot_sim,
        map_server,
        map_lc,
        nav2,
        navigator,
    ])
