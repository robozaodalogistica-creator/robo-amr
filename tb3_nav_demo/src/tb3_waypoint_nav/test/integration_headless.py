#!/usr/bin/env python3
"""
Headless integration test: spins a mock FollowWaypoints action server
in one thread and the WaypointNavigator in another, then verifies
the entire mission completes with 0 missed waypoints — no Gazebo needed.
"""
import math
import sys
import threading
import time

import rclpy
from rclpy.executors import MultiThreadedExecutor
from rclpy.action import ActionServer
from rclpy.node import Node
from nav2_msgs.action import FollowWaypoints


WAYPOINTS_EXPECTED = 5
FAKE_WP_DELAY = 0.3   # seconds per simulated waypoint


class MockFollowWaypointsServer(Node):
    """Simulates Nav2 FollowWaypoints: accepts goal, steps through waypoints."""

    def __init__(self):
        super().__init__("mock_follow_waypoints_server")
        self._server = ActionServer(
            self,
            FollowWaypoints,
            "follow_waypoints",
            self._execute_cb,
        )
        self.get_logger().info("Mock FollowWaypoints server started.")

    def _execute_cb(self, goal_handle):
        poses = goal_handle.request.poses
        n = len(poses)
        self.get_logger().info(f"  [MOCK] Received {n} waypoints — executing...")

        for i in range(n):
            time.sleep(FAKE_WP_DELAY)
            feedback = FollowWaypoints.Feedback()
            feedback.current_waypoint = i
            goal_handle.publish_feedback(feedback)
            self.get_logger().info(f"  [MOCK] Waypoint {i+1}/{n} reached")

        goal_handle.succeed()
        result = FollowWaypoints.Result()
        result.missed_waypoints = []
        self.get_logger().info("  [MOCK] Mission complete — 0 missed.")
        return result


def main():
    rclpy.init()

    # Shared state
    mission_result = {"done": False, "success": False, "missed": None,
                      "elapsed": 0.0}

    # Patch WaypointNavigator._on_result to capture result
    from tb3_waypoint_nav.waypoint_navigator import WaypointNavigator, WAYPOINTS

    _orig_on_result = WaypointNavigator._on_result

    def _patched_on_result(self, future):
        result = future.result().result
        elapsed = time.monotonic() - self._start_time
        missed = list(result.missed_waypoints)
        mission_result["done"] = True
        mission_result["success"] = len(missed) == 0
        mission_result["missed"] = missed
        mission_result["elapsed"] = elapsed
        _orig_on_result(self, future)   # also logs + shuts down

    WaypointNavigator._on_result = _patched_on_result

    executor = MultiThreadedExecutor(num_threads=4)
    server_node = MockFollowWaypointsServer()
    executor.add_node(server_node)

    # Run executor in background thread
    spin_thread = threading.Thread(target=executor.spin, daemon=True)
    spin_thread.start()

    # Give server time to register
    time.sleep(0.5)

    # Start navigator (blocks on wait_for_server, then sends goal)
    nav_node = WaypointNavigator()
    executor.add_node(nav_node)

    # Wait for mission to complete (max 30s)
    deadline = time.monotonic() + 30.0
    while not mission_result["done"] and time.monotonic() < deadline:
        time.sleep(0.1)

    executor.shutdown(timeout_sec=2)

    print()
    print("=" * 60)
    print("  RESULTADO DO TESTE DE INTEGRACAO HEADLESS")
    print("=" * 60)
    if not mission_result["done"]:
        print("  FALHA: timeout — missão não concluída em 30s")
        sys.exit(1)

    missed = mission_result["missed"]
    elapsed = mission_result["elapsed"]
    total = WAYPOINTS_EXPECTED

    if mission_result["success"]:
        print(f"  STATUS : SUCESSO")
        print(f"  Waypoints: {total}/{total} atingidos")
        print(f"  Perdidos : 0")
        print(f"  Tempo    : {elapsed:.2f}s")
    else:
        print(f"  STATUS : PARCIAL ({len(missed)} perdido(s))")
        print(f"  Perdidos: {missed}")
        print(f"  Tempo   : {elapsed:.2f}s")

    print()
    print("  Waypoints percorridos:")
    from tb3_waypoint_nav.waypoint_navigator import WAYPOINTS
    for i, wp in enumerate(WAYPOINTS):
        ok = "OK" if i not in (mission_result["missed"] or []) else "XX"
        print(f"    [{ok}] WP{i+1}: {wp['name']:20s}  "
              f"x={wp['x']:+.1f}  y={wp['y']:+.1f}  yaw={math.degrees(wp['yaw']):+.0f}°")
    print("=" * 60)

    sys.exit(0 if mission_result["success"] else 1)


if __name__ == "__main__":
    main()
