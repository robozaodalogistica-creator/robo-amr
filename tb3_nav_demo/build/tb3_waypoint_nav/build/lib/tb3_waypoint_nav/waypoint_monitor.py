#!/usr/bin/env python3
"""Live monitor: prints robot pose and navigation status to stdout."""
import math
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from nav_msgs.msg import Odometry
from std_msgs.msg import String


def yaw_from_quat(q) -> float:
    siny = 2.0 * (q.w * q.z + q.x * q.y)
    cosy = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny, cosy)


class WaypointMonitor(Node):
    def __init__(self):
        super().__init__("waypoint_monitor")
        self._last_status = "aguardando..."

        qos_tl = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            depth=1,
        )
        self.create_subscription(Odometry, "/odom", self._odom_cb, 10)
        self.create_subscription(
            String, "/waypoint_navigator/nav_status", self._status_cb, qos_tl
        )
        self.create_timer(1.0, self._print_cb)
        self._x = self._y = self._yaw = 0.0

    def _odom_cb(self, msg):
        self._x = msg.pose.pose.position.x
        self._y = msg.pose.pose.position.y
        self._yaw = math.degrees(yaw_from_quat(msg.pose.pose.orientation))

    def _status_cb(self, msg):
        self._last_status = msg.data

    def _print_cb(self):
        self.get_logger().info(
            f"pose=({self._x:+.2f},{self._y:+.2f}) yaw={self._yaw:+.1f}°  "
            f"status={self._last_status}"
        )


def main(args=None):
    rclpy.init(args=args)
    node = WaypointMonitor()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()


if __name__ == "__main__":
    main()
