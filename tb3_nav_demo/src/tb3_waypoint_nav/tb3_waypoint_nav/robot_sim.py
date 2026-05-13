#!/usr/bin/env python3
"""
Minimal TurtleBot3 loopback simulator.

Subscribes to /cmd_vel (Twist), integrates velocity, and publishes:
  - /odom              (nav_msgs/Odometry)
  - /scan              (sensor_msgs/LaserScan)  – max-range circle
  - TF:  map → odom → base_footprint
  - TF:  base_footprint → base_link → base_scan  (static, from URDF)

Designed for headless Nav2 demos; no physics, no collisions.
"""
import math
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from geometry_msgs.msg import Twist, TransformStamped
from nav_msgs.msg import Odometry
from sensor_msgs.msg import LaserScan
from tf2_ros import TransformBroadcaster, StaticTransformBroadcaster
import numpy as np


def _quat_from_yaw(yaw):
    return (0.0, 0.0, math.sin(yaw / 2.0), math.cos(yaw / 2.0))


class RobotSim(Node):
    def __init__(self):
        super().__init__('robot_sim')

        # Robot state in map frame (map = odom for this sim)
        self._x = 0.0
        self._y = 0.0
        self._yaw = 0.0
        self._vx = 0.0
        self._wz = 0.0
        self._last_t = self.get_clock().now()

        self._tf_pub    = TransformBroadcaster(self)
        self._stf_pub   = StaticTransformBroadcaster(self)

        self._odom_pub = self.create_publisher(Odometry, '/odom', 10)
        self._scan_pub = self.create_publisher(LaserScan, '/scan', 10)

        self.create_subscription(Twist, '/cmd_vel', self._cmd_cb, 10)
        self.create_timer(0.05, self._timer_cb)  # 20 Hz

        self._publish_static_tfs()
        self.get_logger().info('RobotSim started at origin (0, 0, 0°)')

    # ------------------------------------------------------------------
    def _publish_static_tfs(self):
        """Publish fixed TFs from URDF: base_footprint→base_link→base_scan."""
        tfs = []
        # base_footprint → base_link  (z offset from URDF)
        t1 = TransformStamped()
        t1.header.stamp        = self.get_clock().now().to_msg()
        t1.header.frame_id     = 'base_footprint'
        t1.child_frame_id      = 'base_link'
        t1.transform.translation.x = 0.0
        t1.transform.translation.y = 0.0
        t1.transform.translation.z = 0.010
        t1.transform.rotation.w    = 1.0
        tfs.append(t1)
        # base_link → base_scan  (from TB3 burger URDF)
        t2 = TransformStamped()
        t2.header.stamp        = self.get_clock().now().to_msg()
        t2.header.frame_id     = 'base_link'
        t2.child_frame_id      = 'base_scan'
        t2.transform.translation.x = -0.032
        t2.transform.translation.z =  0.172
        t2.transform.rotation.w    = 1.0
        tfs.append(t2)
        self._stf_pub.sendTransform(tfs)

    # ------------------------------------------------------------------
    def _cmd_cb(self, msg: Twist):
        self._vx = msg.linear.x
        self._wz = msg.angular.z

    # ------------------------------------------------------------------
    def _timer_cb(self):
        now  = self.get_clock().now()
        dt   = (now - self._last_t).nanoseconds * 1e-9
        self._last_t = now

        # Integrate velocity
        self._yaw += self._wz * dt
        self._x   += self._vx * math.cos(self._yaw) * dt
        self._y   += self._vx * math.sin(self._yaw) * dt

        qx, qy, qz, qw = _quat_from_yaw(self._yaw)
        stamp = now.to_msg()

        # map → odom  (identity — no localization error in sim)
        t_mo = TransformStamped()
        t_mo.header.stamp    = stamp
        t_mo.header.frame_id = 'map'
        t_mo.child_frame_id  = 'odom'
        t_mo.transform.rotation.w = 1.0
        self._tf_pub.sendTransform(t_mo)

        # odom → base_footprint
        t_ob = TransformStamped()
        t_ob.header.stamp    = stamp
        t_ob.header.frame_id = 'odom'
        t_ob.child_frame_id  = 'base_footprint'
        t_ob.transform.translation.x = self._x
        t_ob.transform.translation.y = self._y
        t_ob.transform.rotation.x    = qx
        t_ob.transform.rotation.y    = qy
        t_ob.transform.rotation.z    = qz
        t_ob.transform.rotation.w    = qw
        self._tf_pub.sendTransform(t_ob)

        # /odom message
        odom = Odometry()
        odom.header.stamp    = stamp
        odom.header.frame_id = 'odom'
        odom.child_frame_id  = 'base_footprint'
        odom.pose.pose.position.x    = self._x
        odom.pose.pose.position.y    = self._y
        odom.pose.pose.orientation.x = qx
        odom.pose.pose.orientation.y = qy
        odom.pose.pose.orientation.z = qz
        odom.pose.pose.orientation.w = qw
        odom.twist.twist.linear.x  = self._vx
        odom.twist.twist.angular.z = self._wz
        self._odom_pub.publish(odom)

        # Fake /scan — max-range circle (no obstacles)
        scan = LaserScan()
        scan.header.stamp    = stamp
        scan.header.frame_id = 'base_scan'
        scan.angle_min       = -math.pi
        scan.angle_max       =  math.pi
        scan.angle_increment = 2 * math.pi / 360
        scan.range_min       = 0.12
        scan.range_max       = 3.5
        scan.time_increment  = 0.0
        n = 360
        scan.ranges = [float('inf')] * n
        self._scan_pub.publish(scan)


def main(args=None):
    rclpy.init(args=args)
    node = RobotSim()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()


if __name__ == '__main__':
    main()
