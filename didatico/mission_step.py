#!/usr/bin/env python3
"""
mission_step.py — Gerenciador de missão step-by-step com NavigateToPose.

Importado por control_panel.py. Não tem ponto de entrada próprio.

Fluxo:
    1. painel chama send_next() quando usuário pressiona ENTER
    2. goal é enviado ao Nav2 de forma assíncrona
    3. callbacks atualizam o estado compartilhado (NAVIGATING → WAITING/DONE)
    4. painel reflete o estado na tela
"""
import math
import threading
import time

from action_msgs.msg import GoalStatus
from geometry_msgs.msg import PoseStamped, Quaternion
from nav2_msgs.action import NavigateToPose
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.parameter import Parameter


def _make_pose(x: float, y: float, yaw: float) -> PoseStamped:
    ps = PoseStamped()
    ps.header.frame_id = 'map'
    ps.pose.position.x = x
    ps.pose.position.y = y
    q = Quaternion()
    q.z = math.sin(yaw / 2.0)
    q.w = math.cos(yaw / 2.0)
    ps.pose.orientation = q
    return ps


class MissionManager(Node):
    """Envia goals NavigateToPose um a um, só avançando quando o painel pede."""

    def __init__(self, state, waypoints):
        super().__init__(
            'mission_manager',
            parameter_overrides=[Parameter('use_sim_time', Parameter.Type.BOOL, True)],
        )
        self._state = state
        self._waypoints = waypoints
        self._handle = None          # GoalHandle atual
        self._t_feedback = 0.0       # throttle de logs de feedback
        self._send_event = threading.Event()   # sinal "envia próximo goal"

        self._client = ActionClient(self, NavigateToPose, 'navigate_to_pose')

        # Timer de 100ms para processar pedido de send sem bloquear o painel
        self.create_timer(0.1, self._tick)

    @property
    def total(self):
        return len(self._waypoints)

    def send_next(self):
        """Chamado pelo painel (thread curses) quando ENTER é pressionado."""
        self._send_event.set()

    def cancel(self):
        """Cancela o goal em andamento (se houver)."""
        if self._handle is not None:
            self._handle.cancel_goal_async()
            self._handle = None
            self._state.update(mission_state='WAITING')
            self._state.add_log("⏹  Goal cancelado")

    # ── Timer: processa pedidos de send na thread do executor ─────────────────

    def _tick(self):
        if not self._send_event.is_set():
            return
        self._send_event.clear()

        snap = self._state.snapshot()
        if snap['mission_state'] not in ('WAITING',):
            return
        wp_idx = snap['current_wp']
        if wp_idx >= len(self._waypoints):
            return

        if not self._client.server_is_ready():
            self._state.add_log("⚠️  Nav2 não está pronto. Aguarde e tente ENTER novamente.")
            return

        x, y, yaw, label = self._waypoints[wp_idx]
        self._state.update(mission_state='NAVIGATING')
        self._state.add_log(
            f"🚀 Navegando para waypoint {wp_idx + 1}/{self.total}: "
            f"{label} ({x:.1f}, {y:.1f})"
        )

        goal = NavigateToPose.Goal()
        goal.pose = _make_pose(x, y, yaw)

        future = self._client.send_goal_async(goal, feedback_callback=self._feedback_cb)
        future.add_done_callback(self._goal_response_cb)

    # ── Callbacks de action ───────────────────────────────────────────────────

    def _goal_response_cb(self, future):
        handle = future.result()
        if not handle.accepted:
            self._state.update(mission_state='WAITING')
            self._state.add_log("❌ Goal rejeitado pelo servidor Nav2")
            return
        self._handle = handle
        handle.get_result_async().add_done_callback(self._result_cb)

    def _feedback_cb(self, feedback_msg):
        now = time.monotonic()
        if now - self._t_feedback < 3.0:
            return
        self._t_feedback = now
        dist = feedback_msg.feedback.distance_remaining
        self._state.add_log(f"📡 Distância restante: {dist:.2f} m até o destino")

    def _result_cb(self, future):
        self._handle = None
        result = future.result()
        wp_idx = self._state.current_wp
        _, _, _, label = self._waypoints[wp_idx]

        if result.status == GoalStatus.STATUS_SUCCEEDED:
            new_idx = wp_idx + 1
            if new_idx >= len(self._waypoints):
                self._state.update(mission_state='DONE', current_wp=new_idx)
                self._state.add_log("🏁 MISSÃO CONCLUÍDA! Todos os waypoints visitados.")
            else:
                self._state.update(mission_state='WAITING', current_wp=new_idx)
                next_lbl = self._waypoints[new_idx][3]
                self._state.add_log(
                    f"✅ Cheguei no waypoint {wp_idx + 1}! ({label})\n"
                    f"   Próximo: {next_lbl} — pressione ENTER quando pronto."
                )
        else:
            self._state.update(mission_state='WAITING')
            self._state.add_log(
                f"⚠️  Navegação falhou (status={result.status}). "
                "Pressione ENTER para tentar novamente."
            )
