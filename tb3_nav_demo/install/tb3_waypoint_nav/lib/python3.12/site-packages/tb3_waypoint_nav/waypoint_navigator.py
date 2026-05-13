#!/usr/bin/env python3
"""TurtleBot3 autonomous 5-waypoint navigator using Nav2 FollowWaypoints action."""
import math
import time
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from nav2_msgs.action import FollowWaypoints
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry
from std_msgs.msg import String

# 5 waypoints forming a pentagon pattern in the TB3 world (metres, radians)
WAYPOINTS = [
    {"name": "WP1 – Leste",   "x":  1.5, "y":  0.0, "yaw":  math.pi / 2},
    {"name": "WP2 – Nordeste","x":  1.0, "y":  1.5, "yaw":  math.pi},
    {"name": "WP3 – Norte",   "x":  0.0, "y":  1.8, "yaw": -math.pi / 2},
    {"name": "WP4 – Noroeste","x": -1.0, "y":  1.0, "yaw": -math.pi / 4},
    {"name": "WP5 – Origem",  "x":  0.0, "y":  0.0, "yaw":  0.0},
]


def make_pose(x: float, y: float, yaw: float) -> PoseStamped:
    p = PoseStamped()
    p.header.frame_id = "map"
    p.pose.position.x = x
    p.pose.position.y = y
    p.pose.orientation.z = math.sin(yaw / 2.0)
    p.pose.orientation.w = math.cos(yaw / 2.0)
    return p


class WaypointNavigator(Node):
    def __init__(self):
        super().__init__("waypoint_navigator")

        self._total = len(WAYPOINTS)
        self._start_time = time.monotonic()
        self._current_wp = 0

        qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            depth=1,
        )
        self._status_pub = self.create_publisher(String, "~/nav_status", qos)

        self._ac = ActionClient(self, FollowWaypoints, "follow_waypoints")

        self.get_logger().info("=" * 55)
        self.get_logger().info("  TB3 Waypoint Navigator — 5 waypoints")
        self.get_logger().info("=" * 55)
        for i, wp in enumerate(WAYPOINTS):
            self.get_logger().info(
                f"  [{i+1}] {wp['name']:20s}  x={wp['x']:+.1f}  y={wp['y']:+.1f}"
            )
        self.get_logger().info("=" * 55)
        self.get_logger().info("Aguardando servidor FollowWaypoints...")

        self._ac.wait_for_server()
        self._send_goal()

    def _send_goal(self):
        goal = FollowWaypoints.Goal()
        goal.poses = [make_pose(wp["x"], wp["y"], wp["yaw"]) for wp in WAYPOINTS]

        self.get_logger().info("Enviando missao com 5 waypoints...")
        self._publish_status("RUNNING — enviando waypoints")

        future = self._ac.send_goal_async(goal, feedback_callback=self._on_feedback)
        future.add_done_callback(self._on_goal_response)

    def _on_goal_response(self, future):
        handle = future.result()
        if not handle.accepted:
            self.get_logger().error("Goal REJEITADO pelo servidor Nav2!")
            self._publish_status("ERROR — goal rejeitado")
            rclpy.shutdown()
            return
        self.get_logger().info("Goal ACEITO. Iniciando navegacao...")
        handle.get_result_async().add_done_callback(self._on_result)

    def _on_feedback(self, feedback_msg):
        idx = feedback_msg.feedback.current_waypoint
        if idx != self._current_wp:
            self._current_wp = idx
        if idx < self._total:
            wp = WAYPOINTS[idx]
            elapsed = time.monotonic() - self._start_time
            self.get_logger().info(
                f"▶  Waypoint {idx + 1}/{self._total}: {wp['name']}  "
                f"(t={elapsed:.1f}s)"
            )
            self._publish_status(f"RUNNING — WP {idx+1}/{self._total}: {wp['name']}")

    def _on_result(self, future):
        result = future.result().result
        elapsed = time.monotonic() - self._start_time
        missed = list(result.missed_waypoints)

        self.get_logger().info("=" * 55)
        if missed:
            self.get_logger().warn(
                f"Missao concluida com {len(missed)} waypoint(s) perdido(s): {missed}"
            )
            self._publish_status(f"DONE — {len(missed)} perdido(s) em {elapsed:.1f}s")
        else:
            self.get_logger().info(
                f"  MISSAO CONCLUIDA — todos os {self._total} waypoints "
                f"atingidos em {elapsed:.1f}s"
            )
            self._publish_status(f"SUCCESS — {self._total} WPs em {elapsed:.1f}s")
        self.get_logger().info("=" * 55)
        rclpy.shutdown()

    def _publish_status(self, text: str):
        msg = String()
        msg.data = text
        self._status_pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = WaypointNavigator()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Interrompido pelo usuario.")
    finally:
        node.destroy_node()


if __name__ == "__main__":
    main()
