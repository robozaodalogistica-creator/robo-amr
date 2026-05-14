#!/usr/bin/env python3
"""
friendly_logger.py — Subscreve tópicos ROS e gera mensagens em linguagem simples.

Importado por control_panel.py. Não tem ponto de entrada próprio.

Tópicos monitorados:
    /scan              → LiDAR (pontos válidos por varredura)
    /map               → Mapa AMCL (células ocupadas, publicado uma vez)
    /amcl_pose         → Localização AMCL (x, y, θ)
    /plan              → Rota calculada pelo planner (nº de waypoints)
    /cmd_vel           → Comando de velocidade (TwistStamped)
    TF map→base_footprint → Fallback de localização
"""
import math
import time

import rclpy
import rclpy.time
import tf2_ros
from geometry_msgs.msg import PoseWithCovarianceStamped, TwistStamped
from nav_msgs.msg import OccupancyGrid, Path
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import QoSDurabilityPolicy, QoSProfile, QoSReliabilityPolicy
from sensor_msgs.msg import LaserScan


def _yaw_deg(q) -> float:
    siny = 2.0 * (q.w * q.z + q.x * q.y)
    cosy = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.degrees(math.atan2(siny, cosy))


class FriendlyLogger(Node):
    """Nó ROS 2 que converte tópicos técnicos em mensagens legíveis."""

    def __init__(self, state):
        super().__init__(
            'friendly_logger',
            parameter_overrides=[Parameter('use_sim_time', Parameter.Type.BOOL, True)],
        )
        self._state = state
        self._t_lidar = 0.0   # timestamps de última vez que logamos (wall-clock)
        self._t_pose  = 0.0
        self._t_vel   = 0.0

        self.create_subscription(LaserScan, '/scan', self._lidar_cb, 10)
        self.create_subscription(
            PoseWithCovarianceStamped, '/amcl_pose', self._pose_cb, 10)
        self.create_subscription(TwistStamped, '/cmd_vel', self._vel_cb, 10)
        self.create_subscription(Path, '/plan', self._plan_cb, 10)

        # Mapa AMCL usa QoS TRANSIENT_LOCAL para receber histórico
        map_qos = QoSProfile(
            depth=1,
            durability=QoSDurabilityPolicy.TRANSIENT_LOCAL,
            reliability=QoSReliabilityPolicy.RELIABLE,
        )
        self._map_sub = self.create_subscription(
            OccupancyGrid, '/map', self._map_cb, map_qos)

        # TF: fallback quando AMCL ainda não publicou pose
        self._tf_buf = tf2_ros.Buffer()
        self._tf_listener = tf2_ros.TransformListener(self._tf_buf, self)
        self.create_timer(0.5, self._tf_poll)

    # ── Callbacks ─────────────────────────────────────────────────────────────

    def _lidar_cb(self, msg: LaserScan):
        valid = sum(1 for r in msg.ranges if msg.range_min <= r <= msg.range_max)
        self._state.update(lidar_pts=valid)
        now = time.monotonic()
        if now - self._t_lidar > 3.0:
            self._state.add_log(f"🤖 LiDAR escaneando {valid} pontos...")
            self._t_lidar = now

    def _map_cb(self, msg: OccupancyGrid):
        occupied = sum(1 for c in msg.data if c > 50)
        total = len(msg.data)
        self._state.add_log(
            f"🗺️  Mapa AMCL carregado: {occupied}/{total} células ocupadas")
        # Mapa estático — não precisa de mais callbacks
        self.destroy_subscription(self._map_sub)

    def _pose_cb(self, msg: PoseWithCovarianceStamped):
        p = msg.pose.pose
        x, y = p.position.x, p.position.y
        th = _yaw_deg(p.orientation)
        self._state.update(pose=(x, y, th))
        now = time.monotonic()
        if now - self._t_pose > 4.0:
            self._state.add_log(f"📍 Localizei: estou em ({x:.2f}, {y:.2f}), θ={th:.0f}°")
            self._t_pose = now

    def _plan_cb(self, msg: Path):
        n = len(msg.poses)
        self._state.update(plan_wps=n)
        self._state.add_log(f"🎯 Rota calculada: {n} pontos no caminho até o destino")

    def _vel_cb(self, msg: TwistStamped):
        lin = msg.twist.linear.x
        ang = msg.twist.angular.z
        self._state.update(cmd_vel=(lin, ang))
        now = time.monotonic()
        if now - self._t_vel > 2.0 and (abs(lin) > 0.01 or abs(ang) > 0.01):
            self._state.add_log(
                f"⚙️  Motor: avançar {lin:.2f} m/s, girar {ang:.2f} rad/s")
            self._t_vel = now

    def _tf_poll(self):
        """Atualiza pose via TF quando AMCL ainda não publicou."""
        if self._state.pose is not None:
            return
        try:
            t = self._tf_buf.lookup_transform(
                'map', 'base_footprint', rclpy.time.Time())
            x = t.transform.translation.x
            y = t.transform.translation.y
            th = _yaw_deg(t.transform.rotation)
            self._state.update(pose=(x, y, th))
        except Exception:
            pass
