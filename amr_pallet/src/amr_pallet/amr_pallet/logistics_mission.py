#!/usr/bin/env python3
"""
AMR Pallet Logistics Mission
Ciclo: busca 4 pallets e entrega em Expedição / Doca alternando.

Mapa do galpão (20m × 15m, centro em (0,0)):

  ┌──────────────────────────┐
  │  [DOCA]       [EXPED.]   │  y≈+6
  │   ◎               ◎      │
  │                          │
  │ ╔══════╗     ╔══════╗    │  y=+3  (prateleira topo)
  │  [P2]         [P4]       │  y≈+1.5 (corredor)
  │ ╚══════╝     ╚══════╝    │  y=+2.5
  │                          │
  │ ╔══════╗     ╔══════╗    │  y=-2.5 (prateleira base)
  │  [P1]         [P3]       │  y≈-1.5 (corredor)
  │ ╚══════╝     ╚══════╝    │  y=-3.5
  └──────────────────────────┘
    x≈-6         x≈+6
"""
import math, time, threading
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import NavigateToPose
from action_msgs.msg import GoalStatus
from std_msgs.msg import String
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy

# ── Warehouse waypoints (x, y, yaw_rad) ──────────────────────────────
LOCATIONS = {
    'home':      ( 0.0,  0.0,  0.0),
    'P1':        (-6.5, -1.5,  0.0),
    'P2':        (-6.5,  1.5,  0.0),
    'P3':        ( 6.5, -1.5,  math.pi),
    'P4':        ( 6.5,  1.5,  math.pi),
    'expedicao': ( 7.5,  6.0,  math.pi / 2),
    'doca':      (-7.5,  6.0,  math.pi / 2),
}

TASKS = [
    ('P1', 'expedicao', 'Pallet 1  →  Expedição'),
    ('P2', 'doca',      'Pallet 2  →  Doca'),
    ('P3', 'expedicao', 'Pallet 3  →  Expedição'),
    ('P4', 'doca',      'Pallet 4  →  Doca'),
]
PICKUP_PAUSE   = 2.0
DELIVERY_PAUSE = 2.0


def _pose(x, y, yaw):
    p = PoseStamped()
    p.header.frame_id = 'map'
    p.pose.position.x = x
    p.pose.position.y = y
    p.pose.orientation.z = math.sin(yaw / 2)
    p.pose.orientation.w = math.cos(yaw / 2)
    return p


class LogisticsMission(Node):
    def __init__(self):
        super().__init__('logistics_mission')
        self._ac = ActionClient(self, NavigateToPose, 'navigate_to_pose')
        qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            depth=1,
        )
        self._status_pub = self.create_publisher(String, '~/mission_status', qos)
        self._t0 = time.monotonic()

        self.get_logger().info('=' * 60)
        self.get_logger().info('  AMR Pallet Logistics Mission — Galpão')
        self.get_logger().info('  4 pallets  |  Expedição + Doca  |  ciclo completo')
        self.get_logger().info('=' * 60)
        for loc, (x, y, _) in LOCATIONS.items():
            self.get_logger().info(f'  {loc:12s}  ({x:+6.1f}, {y:+6.1f})')
        self.get_logger().info('=' * 60)
        self.get_logger().info('Aguardando servidor NavigateToPose...')
        self._ac.wait_for_server()
        self.get_logger().info('Servidor pronto. Iniciando missão!')

        # Mission runs in a background thread; rclpy.spin() stays on the main thread
        self._thread = threading.Thread(target=self._run_mission, daemon=True)
        self._thread.start()

    # ── Mission loop ──────────────────────────────────────────────────
    def _run_mission(self):
        total = len(TASKS)
        success = 0

        for i, (pickup, delivery, label) in enumerate(TASKS, 1):
            self.get_logger().info(f'\n[Tarefa {i}/{total}] {label}')
            self._pub(f'TASK {i}/{total}: {label}')

            self.get_logger().info(f'  → Indo buscar em {pickup}...')
            if not self._nav_to(pickup):
                self.get_logger().warn(f'  ✗ Falha ao chegar em {pickup}')
                continue

            elapsed = time.monotonic() - self._t0
            self.get_logger().info(
                f'  ✓ Chegou em {pickup} [{elapsed:.1f}s] — coletando ({PICKUP_PAUSE:.0f}s)...')
            self._pub(f'PICKING at {pickup}')
            time.sleep(PICKUP_PAUSE)

            self.get_logger().info(f'  → Indo entregar em {delivery}...')
            if not self._nav_to(delivery):
                self.get_logger().warn(f'  ✗ Falha ao chegar em {delivery}')
                continue

            elapsed = time.monotonic() - self._t0
            self.get_logger().info(
                f'  ✓ Entregue em {delivery} [{elapsed:.1f}s]')
            self._pub(f'DELIVERED at {delivery}')
            time.sleep(DELIVERY_PAUSE)
            success += 1

        self.get_logger().info('\n  → Retornando para Home...')
        self._nav_to('home')

        elapsed = time.monotonic() - self._t0
        self.get_logger().info('=' * 60)
        if success == total:
            self.get_logger().info(
                f'  MISSAO CONCLUIDA — {success}/{total} pallets entregues em {elapsed:.1f}s')
            self._pub(f'SUCCESS — {success}/{total} em {elapsed:.1f}s')
        else:
            self.get_logger().warn(
                f'  MISSAO PARCIAL — {success}/{total} pallets  t={elapsed:.1f}s')
            self._pub(f'PARTIAL — {success}/{total} em {elapsed:.1f}s')
        self.get_logger().info('=' * 60)

    # ── Navigate to a named location ──────────────────────────────────
    def _nav_to(self, location_name: str) -> bool:
        """Blocking navigation call — safe from background thread."""
        x, y, yaw = LOCATIONS[location_name]
        goal = NavigateToPose.Goal()
        goal.pose = _pose(x, y, yaw)
        goal.pose.header.stamp = self.get_clock().now().to_msg()

        event  = threading.Event()
        result = [False]

        def on_response(fut):
            handle = fut.result()
            if not handle.accepted:
                self.get_logger().error('Goal rejeitado!')
                event.set()
                return
            handle.get_result_async().add_done_callback(on_result)

        def on_result(fut):
            result[0] = (fut.result().status == GoalStatus.STATUS_SUCCEEDED)
            event.set()

        send_fut = self._ac.send_goal_async(goal)
        send_fut.add_done_callback(on_response)

        event.wait(timeout=300.0)   # wait up to 5 min per waypoint
        return result[0]

    def _pub(self, text: str):
        msg = String()
        msg.data = text
        self._status_pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = LogisticsMission()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('Interrompido.')
    finally:
        node.destroy_node()
