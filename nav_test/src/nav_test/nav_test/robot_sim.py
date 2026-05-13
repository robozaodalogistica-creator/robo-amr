#!/usr/bin/env python3
"""
Minimal differential-drive loopback simulator for Nav2.
Subscribes /cmd_vel (Twist), integrates velocity, publishes:
  /odom, /scan, TF: map→odom→base_footprint + static base_footprint→base_link→base_scan
"""
import math
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, TransformStamped
from nav_msgs.msg import Odometry
from sensor_msgs.msg import LaserScan
from tf2_ros import TransformBroadcaster, StaticTransformBroadcaster


def _quat_from_yaw(yaw):
    return (0.0, 0.0, math.sin(yaw / 2.0), math.cos(yaw / 2.0))


class RobotSim(Node):
    def __init__(self):
        super().__init__('robot_sim')
        self._x = self._y = self._yaw = 0.0
        self._vx = self._wz = 0.0
        self._last_t = self.get_clock().now()

        self._tf_pub  = TransformBroadcaster(self)
        self._stf_pub = StaticTransformBroadcaster(self)

        self._odom_pub = self.create_publisher(Odometry,   '/odom', 10)
        self._scan_pub = self.create_publisher(LaserScan,  '/scan', 10)
        self.create_subscription(Twist, '/cmd_vel', self._cmd_cb, 10)
        self.create_timer(0.05, self._tick)  # 20 Hz

        self._publish_static_tfs()
        self.get_logger().info('RobotSim ready — origin (0,0,0°)')

    def _publish_static_tfs(self):
        now = self.get_clock().now().to_msg()
        tfs = []
        for parent, child, tx, ty, tz in [
            ('base_footprint', 'base_link', 0.0,    0.0,   0.010),
            ('base_link',      'base_scan', -0.032, 0.0,   0.172),
        ]:
            t = TransformStamped()
            t.header.stamp       = now
            t.header.frame_id    = parent
            t.child_frame_id     = child
            t.transform.translation.x = tx
            t.transform.translation.y = ty
            t.transform.translation.z = tz
            t.transform.rotation.w    = 1.0
            tfs.append(t)
        self._stf_pub.sendTransform(tfs)

    def _cmd_cb(self, msg: Twist):
        self._vx = msg.linear.x
        self._wz = msg.angular.z

    def _tick(self):
        now = self.get_clock().now()
        dt  = (now - self._last_t).nanoseconds * 1e-9
        self._last_t = now

        self._yaw += self._wz * dt
        self._x   += self._vx * math.cos(self._yaw) * dt
        self._y   += self._vx * math.sin(self._yaw) * dt

        qx, qy, qz, qw = _quat_from_yaw(self._yaw)
        stamp = now.to_msg()

        # map → odom (identity)
        t = TransformStamped()
        t.header.stamp = stamp; t.header.frame_id = 'map'; t.child_frame_id = 'odom'
        t.transform.rotation.w = 1.0
        self._tf_pub.sendTransform(t)

        # odom → base_footprint
        t = TransformStamped()
        t.header.stamp = stamp; t.header.frame_id = 'odom'; t.child_frame_id = 'base_footprint'
        t.transform.translation.x = self._x
        t.transform.translation.y = self._y
        t.transform.rotation.x = qx; t.transform.rotation.y = qy
        t.transform.rotation.z = qz; t.transform.rotation.w = qw
        self._tf_pub.sendTransform(t)

        # /odom
        o = Odometry()
        o.header.stamp = stamp; o.header.frame_id = 'odom'; o.child_frame_id = 'base_footprint'
        o.pose.pose.position.x = self._x; o.pose.pose.position.y = self._y
        o.pose.pose.orientation.x = qx; o.pose.pose.orientation.y = qy
        o.pose.pose.orientation.z = qz; o.pose.pose.orientation.w = qw
        o.twist.twist.linear.x = self._vx; o.twist.twist.angular.z = self._wz
        self._odom_pub.publish(o)

        # /scan — 360 rays all at infinity (no obstacles)
        s = LaserScan()
        s.header.stamp = stamp; s.header.frame_id = 'base_scan'
        s.angle_min = -math.pi; s.angle_max = math.pi
        s.angle_increment = 2 * math.pi / 360
        s.range_min = 0.12; s.range_max = 3.5
        s.ranges = [float('inf')] * 360
        self._scan_pub.publish(s)


def main(args=None):
    rclpy.init(args=args)
    node = RobotSim()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
