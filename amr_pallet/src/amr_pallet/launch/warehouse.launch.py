"""
AMR Pallet — Galpão logístico headless.

Stack:
  robot_sim        — loopback diferencial (cmd_vel → odom/scan/tf)
  map_server       — mapa do galpão 20×15 m
  Nav2 full stack  — bt_navigator, DWB, NavFn, ...
  foxglove_bridge  — WebSocket na porta 8765 para visualização
  logistics_mission — missão de 4 pallets (delay 35 s)
"""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, SetEnvironmentVariable, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node


def generate_launch_description():
    pkg      = get_package_share_directory('amr_pallet')
    pkg_nav2 = get_package_share_directory('nav2_bringup')

    map_file    = os.path.join(pkg, 'maps',   'warehouse.yaml')
    params_file = os.path.join(pkg, 'config', 'nav2_params.yaml')

    # ── 1. Loopback robot simulator ───────────────────────────────────
    robot_sim = Node(
        package='amr_pallet',
        executable='robot_sim',
        name='robot_sim',
        output='screen',
        parameters=[{'use_sim_time': False}],
    )

    # ── 2. Map server (params directly as dict — avoids yaml_filename bug) ──
    map_server = Node(
        package='nav2_map_server',
        executable='map_server',
        name='map_server',
        output='screen',
        parameters=[{'yaml_filename': map_file, 'use_sim_time': False}],
    )

    # Delay lifecycle manager so map_server registers its service first
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

    # ── 3. Nav2 navigation stack ──────────────────────────────────────
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

    # ── 4. Foxglove Bridge — WebSocket porta 8765 ─────────────────────
    foxglove = Node(
        package='foxglove_bridge',
        executable='foxglove_bridge',
        name='foxglove_bridge',
        output='screen',
        parameters=[{
            'port':              8765,
            'address':           '0.0.0.0',
            'tls':               False,
            'send_buffer_limit': 10000000,
            'use_sim_time':      False,
        }],
    )

    # ── 5. Logistics mission (delay 35 s — Nav2 lifecycle ~25 s) ─────
    mission = TimerAction(
        period=35.0,
        actions=[Node(
            package='amr_pallet',
            executable='logistics_mission',
            name='logistics_mission',
            output='screen',
            parameters=[{'use_sim_time': False}],
        )],
    )

    return LaunchDescription([
        # CycloneDDS on loopback — reliable single-host discovery
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
        foxglove,
        mission,
    ])
