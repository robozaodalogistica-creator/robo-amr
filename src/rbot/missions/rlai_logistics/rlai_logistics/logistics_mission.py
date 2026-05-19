#!/usr/bin/env python3
"""Galp pallet mission state machine on top of Nav2.

This first mission layer uses fixed map-frame poses. AprilTag docking and
Gazebo attach/detach come later; the useful milestone here is proving that
Nav2 and the fork controller can be sequenced as one pallet workflow.
"""

import math
from pathlib import Path
import threading
import time

from action_msgs.msg import GoalStatus
from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import NavigateToPose
import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import Empty, Float64MultiArray, String
import yaml


DEFAULT_LOCATIONS = {
    "home": (1.0, 1.0, 0.0),
    "pallet_1": (-2.0, 1.0, math.pi / 2.0),
    "pallet_2": (-2.0, -1.0, -math.pi / 2.0),
    "pallet_3": (2.0, 1.0, math.pi / 2.0),
    "pallet_4": (2.0, -1.0, -math.pi / 2.0),
    "expedicao": (2.6, -0.6, 0.0),
    "doca": (-0.7, -0.8, math.pi),
}

DEFAULT_TASKS = [
    ("pallet_1", "expedicao", "Pallet 1 -> Expedicao"),
    ("pallet_2", "doca", "Pallet 2 -> Doca"),
    ("pallet_3", "expedicao", "Pallet 3 -> Expedicao"),
    ("pallet_4", "doca", "Pallet 4 -> Doca"),
]


def _pose(x: float, y: float, yaw: float) -> PoseStamped:
    pose = PoseStamped()
    pose.header.frame_id = "map"
    pose.pose.position.x = x
    pose.pose.position.y = y
    pose.pose.orientation.z = math.sin(yaw / 2.0)
    pose.pose.orientation.w = math.cos(yaw / 2.0)
    return pose


def _param_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).lower() in ("1", "true", "yes", "on")


def _load_waypoint_config(path: str):
    if not path:
        return DEFAULT_LOCATIONS, DEFAULT_TASKS

    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Waypoint config not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as stream:
        data = yaml.safe_load(stream) or {}

    locations = {}
    for name, pose in data.get("locations", {}).items():
        if len(pose) != 3:
            raise ValueError(f"Location '{name}' must be [x, y, yaw]")
        locations[name] = tuple(float(value) for value in pose)

    tasks = []
    for item in data.get("tasks", []):
        if len(item) != 3:
            raise ValueError("Each task must be [pickup, delivery, label]")
        pickup, delivery, label = item
        tasks.append((str(pickup), str(delivery), str(label)))

    if not locations:
        locations = DEFAULT_LOCATIONS
    if not tasks:
        tasks = DEFAULT_TASKS

    missing = {
        name
        for task in tasks
        for name in (task[0], task[1])
        if name not in locations
    }
    if missing:
        raise ValueError(f"Waypoint config references unknown locations: {sorted(missing)}")

    return locations, tasks


class LogisticsMission(Node):
    def __init__(self):
        super().__init__("logistics_mission")

        self.declare_parameter("autostart", True)
        self.declare_parameter("waypoints_file", "")
        self.declare_parameter("navigate_action", "navigate_to_pose")
        self.declare_parameter("fork_command_topic", "/fork_lift_controller/commands")
        self.declare_parameter("fork_raise_velocity", 0.06)
        self.declare_parameter("fork_lower_velocity", -0.06)
        self.declare_parameter("fork_raise_time", 3.0)
        self.declare_parameter("fork_lower_time", 3.0)
        self.declare_parameter("pickup_pause", 1.0)
        self.declare_parameter("delivery_pause", 1.0)
        self.declare_parameter("goal_timeout", 900.0)
        self.declare_parameter("enable_gazebo_attach", False)
        self.declare_parameter("attach_topic_template", "/{pallet}/attach")
        self.declare_parameter("detach_topic_template", "/{pallet}/detach")

        action_name = self.get_parameter("navigate_action").value
        fork_topic = self.get_parameter("fork_command_topic").value
        waypoints_file = self.get_parameter("waypoints_file").value

        self._locations, self._tasks = _load_waypoint_config(waypoints_file)

        self._nav_client = ActionClient(self, NavigateToPose, action_name)
        self._fork_pub = self.create_publisher(Float64MultiArray, fork_topic, 10)
        self._attach_pubs = {}
        self._detach_pubs = {}

        qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            depth=1,
        )
        self._status_pub = self.create_publisher(String, "~/mission_status", qos)

        self._thread = None
        self._start_time = time.monotonic()
        self._waiting_logged = False

        self.get_logger().info("Galp logistics mission ready.")
        if waypoints_file:
            self.get_logger().info(f"Loaded waypoints from {waypoints_file}")
        for name, (x, y, yaw) in self._locations.items():
            self.get_logger().info(f"  {name:10s} x={x:+.2f} y={y:+.2f} yaw={yaw:+.2f}")

        self._start_timer = None
        if _param_bool(self.get_parameter("autostart").value):
            self._start_timer = self.create_timer(1.0, self._start_when_nav2_ready)
        else:
            self.get_logger().info("autostart is false; mission node will idle.")

    def _start_when_nav2_ready(self):
        if self._thread is not None:
            return
        if not self._nav_client.server_is_ready():
            if not self._waiting_logged:
                self.get_logger().info("Waiting for NavigateToPose action server...")
                self._waiting_logged = True
            return

        self._thread = threading.Thread(target=self._run_mission, daemon=True)
        self._thread.start()

    def _run_mission(self):
        self._publish_status("MISSION_STARTED")
        self._stop_fork()

        delivered = 0
        for index, (pickup, delivery, label) in enumerate(self._tasks, start=1):
            self.get_logger().info(f"[Task {index}/{len(self._tasks)}] {label}")
            self._publish_status(f"TASK_STARTED {label}")

            if not self._navigate_to(pickup):
                self.get_logger().warn(f"Navigation failed at pickup {pickup}")
                self._publish_status(f"TASK_FAILED pickup={pickup}")
                continue

            self._publish_status(f"PICKUP_REACHED {pickup}")
            time.sleep(self._pickup_pause())
            self._attach_pallet(pickup)
            self._raise_fork()
            self._publish_status(f"PALLET_LIFTED {pickup}")

            if not self._navigate_to(delivery):
                self.get_logger().warn(f"Navigation failed at delivery {delivery}")
                self._publish_status(f"TASK_FAILED delivery={delivery}")
                self._lower_fork()
                self._detach_pallet(pickup)
                continue

            self._publish_status(f"DELIVERY_REACHED {delivery}")
            time.sleep(self._delivery_pause())
            self._lower_fork()
            self._detach_pallet(pickup)
            self._publish_status(f"PALLET_DROPPED {delivery}")
            delivered += 1

        self.get_logger().info("Returning home.")
        self._navigate_to("home")

        elapsed = time.monotonic() - self._start_time
        if delivered == len(self._tasks):
            final = f"MISSION_SUCCESS delivered={delivered}/{len(self._tasks)} t={elapsed:.1f}s"
            self.get_logger().info(final)
        else:
            final = f"MISSION_PARTIAL delivered={delivered}/{len(self._tasks)} t={elapsed:.1f}s"
            self.get_logger().warn(final)
        self._publish_status(final)

    def _navigate_to(self, location_name: str) -> bool:
        x, y, yaw = self._locations[location_name]
        goal = NavigateToPose.Goal()
        goal.pose = _pose(x, y, yaw)
        goal.pose.header.stamp = self.get_clock().now().to_msg()

        event = threading.Event()
        result = [False]

        def on_result(future):
            try:
                result[0] = future.result().status == GoalStatus.STATUS_SUCCEEDED
            except Exception as exc:  # pragma: no cover - defensive ROS callback guard
                self.get_logger().error(f"NavigateToPose result error: {exc}")
            event.set()

        def on_response(future):
            try:
                handle = future.result()
            except Exception as exc:  # pragma: no cover - defensive ROS callback guard
                self.get_logger().error(f"NavigateToPose response error: {exc}")
                event.set()
                return
            if not handle.accepted:
                self.get_logger().error(f"Goal rejected for {location_name}")
                event.set()
                return
            handle.get_result_async().add_done_callback(on_result)

        self.get_logger().info(f"Navigating to {location_name}: x={x:+.2f} y={y:+.2f}")
        self._nav_client.send_goal_async(goal).add_done_callback(on_response)
        event.wait(timeout=self._goal_timeout())
        return result[0]

    def _raise_fork(self):
        self._command_fork_velocity(self._fork_raise_velocity(), self._fork_raise_time())
        self._stop_fork()

    def _lower_fork(self):
        self._command_fork_velocity(self._fork_lower_velocity(), self._fork_lower_time())
        self._stop_fork()

    def _stop_fork(self):
        self._command_fork_velocity(0.0, 0.2)

    def _command_fork_velocity(self, velocity: float, duration: float):
        clamped = max(-0.08, min(0.08, velocity))
        msg = Float64MultiArray()
        msg.data = [clamped]

        self.get_logger().info(f"Commanding fork velocity {clamped:.3f} m/s")
        deadline = time.monotonic() + max(0.0, duration)
        while time.monotonic() < deadline:
            self._fork_pub.publish(msg)
            time.sleep(0.1)

    def _attach_pallet(self, pallet: str):
        if not self._gazebo_attach_enabled():
            return
        self._publish_empty_command(
            pallet,
            self.get_parameter("attach_topic_template").value,
            self._attach_pubs,
            "attach",
        )
        self._publish_status(f"PALLET_ATTACHED {pallet}")

    def _detach_pallet(self, pallet: str):
        if not self._gazebo_attach_enabled():
            return
        self._publish_empty_command(
            pallet,
            self.get_parameter("detach_topic_template").value,
            self._detach_pubs,
            "detach",
        )
        self._publish_status(f"PALLET_DETACHED {pallet}")

    def _publish_empty_command(self, pallet: str, template: str, publishers: dict, action: str):
        topic = str(template).format(pallet=pallet)
        publisher = publishers.get(topic)
        if publisher is None:
            publisher = self.create_publisher(Empty, topic, 10)
            publishers[topic] = publisher

        self.get_logger().info(f"Gazebo pallet {action}: {pallet} via {topic}")
        msg = Empty()
        for _ in range(3):
            publisher.publish(msg)
            time.sleep(0.05)

    def _publish_status(self, text: str):
        msg = String()
        msg.data = text
        self._status_pub.publish(msg)

    def _fork_raise_velocity(self) -> float:
        return float(self.get_parameter("fork_raise_velocity").value)

    def _fork_lower_velocity(self) -> float:
        return float(self.get_parameter("fork_lower_velocity").value)

    def _fork_raise_time(self) -> float:
        return float(self.get_parameter("fork_raise_time").value)

    def _fork_lower_time(self) -> float:
        return float(self.get_parameter("fork_lower_time").value)

    def _pickup_pause(self) -> float:
        return float(self.get_parameter("pickup_pause").value)

    def _delivery_pause(self) -> float:
        return float(self.get_parameter("delivery_pause").value)

    def _goal_timeout(self) -> float:
        return float(self.get_parameter("goal_timeout").value)

    def _gazebo_attach_enabled(self) -> bool:
        return _param_bool(self.get_parameter("enable_gazebo_attach").value)


def main(args=None):
    rclpy.init(args=args)
    node = LogisticsMission()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Interrupted.")
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
