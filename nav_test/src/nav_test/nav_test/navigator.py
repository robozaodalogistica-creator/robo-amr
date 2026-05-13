#!/usr/bin/env python3
"""
Sends 3 waypoints via FollowWaypoints and reports results.
Waypoints (map frame):
  WP1 (1.5, 0.0)  — East
  WP2 (0.0, 1.5)  — North
  WP3 (0.0, 0.0)  — Origin
"""
import math, time
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import FollowWaypoints

WAYPOINTS = [
    ('WP1 — East',   1.5,  0.0, 0.0),
    ('WP2 — North',  0.0,  1.5, math.pi / 2),
    ('WP3 — Origin', 0.0,  0.0, 0.0),
]


def _pose(x, y, yaw):
    p = PoseStamped()
    p.header.frame_id = 'map'
    p.pose.position.x = x
    p.pose.position.y = y
    p.pose.orientation.z = math.sin(yaw / 2.0)
    p.pose.orientation.w = math.cos(yaw / 2.0)
    return p


class Navigator(Node):
    def __init__(self):
        super().__init__('navigator')
        self._ac = ActionClient(self, FollowWaypoints, 'follow_waypoints')
        self._t0 = time.monotonic()
        self._current = 0

        self.get_logger().info('=' * 50)
        self.get_logger().info('  Nav2 3-Waypoint Demo')
        for i, (name, x, y, _) in enumerate(WAYPOINTS):
            self.get_logger().info(f'  [{i+1}] {name:20s}  ({x:+.1f}, {y:+.1f})')
        self.get_logger().info('=' * 50)
        self.get_logger().info('Waiting for FollowWaypoints server...')

        self._ac.wait_for_server()
        self._send()

    def _send(self):
        goal = FollowWaypoints.Goal()
        goal.poses = [_pose(x, y, yaw) for _, x, y, yaw in WAYPOINTS]
        self.get_logger().info('Goal sent — navigating...')
        f = self._ac.send_goal_async(goal, feedback_callback=self._feedback)
        f.add_done_callback(self._accepted)

    def _accepted(self, future):
        h = future.result()
        if not h.accepted:
            self.get_logger().error('Goal REJECTED')
            rclpy.shutdown(); return
        self.get_logger().info('Goal ACCEPTED')
        h.get_result_async().add_done_callback(self._done)

    def _feedback(self, fb):
        idx = fb.feedback.current_waypoint
        if idx != self._current:
            self._current = idx
        if idx < len(WAYPOINTS):
            name = WAYPOINTS[idx][0]
            t = time.monotonic() - self._t0
            self.get_logger().info(f'  >> Waypoint {idx+1}/3: {name}  t={t:.1f}s')

    def _done(self, future):
        res = future.result().result
        t   = time.monotonic() - self._t0
        missed = list(res.missed_waypoints)
        self.get_logger().info('=' * 50)
        if not missed:
            self.get_logger().info(f'  SUCCESS — all 3 waypoints reached in {t:.1f}s')
        else:
            self.get_logger().warn(f'  DONE — {len(missed)} missed: {missed}  t={t:.1f}s')
        self.get_logger().info('=' * 50)
        rclpy.shutdown()


def main(args=None):
    rclpy.init(args=args)
    node = Navigator()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
