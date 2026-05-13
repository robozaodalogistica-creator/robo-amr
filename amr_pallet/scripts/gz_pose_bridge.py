#!/usr/bin/env python3
"""Bridge: /odom (ROS) → /world/<world>/set_pose (Gazebo Harmonic).

The amr_pallet stack uses a loopback `robot_sim` node as the source of truth for
the robot pose. This script mirrors that pose into a visualization-only model
spawned in Gazebo, so the user can see the AMR moving inside the warehouse.

Implementation: subprocess call to `gz service` per update. Throttled to ~15 Hz.
"""
import math
import shutil
import subprocess
import time

import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry


class GzPoseBridge(Node):
    def __init__(self):
        super().__init__('gz_pose_bridge')
        self.declare_parameter('world', 'galp_amr')
        self.declare_parameter('model', 'amr_viz')
        self.declare_parameter('rate_hz', 15.0)
        self.declare_parameter('z_offset', 0.0)

        self.world = self.get_parameter('world').value
        self.model = self.get_parameter('model').value
        self.z_off = float(self.get_parameter('z_offset').value)
        self.min_dt = 1.0 / float(self.get_parameter('rate_hz').value)

        self.service = f'/world/{self.world}/set_pose'
        self.gz = shutil.which('gz') or '/opt/ros/jazzy/opt/gz_tools_vendor/bin/gz'

        self._last_sent = 0.0
        self._sub = self.create_subscription(Odometry, '/odom', self._on_odom, 10)
        self.get_logger().info(
            f'gz_pose_bridge: /odom → {self.service} (model={self.model}, '
            f'max_rate={1.0/self.min_dt:.1f} Hz)'
        )

    def _on_odom(self, msg: Odometry) -> None:
        now = time.monotonic()
        if now - self._last_sent < self.min_dt:
            return
        self._last_sent = now

        p = msg.pose.pose.position
        q = msg.pose.pose.orientation
        req = (
            f"name: '{self.model}', "
            f"position: {{x: {p.x:.4f}, y: {p.y:.4f}, z: {p.z + self.z_off:.4f}}}, "
            f"orientation: {{x: {q.x:.6f}, y: {q.y:.6f}, z: {q.z:.6f}, w: {q.w:.6f}}}"
        )
        try:
            subprocess.run(
                [self.gz, 'service', '-s', self.service,
                 '--reqtype', 'gz.msgs.Pose',
                 '--reptype', 'gz.msgs.Boolean',
                 '--timeout', '200',
                 '--req', req],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
                timeout=1.0,
            )
        except subprocess.TimeoutExpired:
            self.get_logger().warn('gz service timed out — Gazebo not responding?')


def main():
    rclpy.init()
    node = GzPoseBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
