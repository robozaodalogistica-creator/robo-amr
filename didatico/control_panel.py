#!/usr/bin/env python3
"""
control_panel.py — Painel curses do modo didático do rbot.

Uso:
    cd /workspace/didatico && python3 control_panel.py

Controles:
    SPACE  — pausa / retoma simulação
    +      — aumenta velocidade em 5%
    -      — diminui velocidade em 5%
    ENTER  — envia próximo waypoint ao Nav2
    Q      — sai
"""

import curses
import os
import subprocess
import sys
import threading
import time
from collections import deque

import rclpy
from rclpy.executors import MultiThreadedExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from friendly_logger import FriendlyLogger
from mission_step import MissionManager

# ── Waypoints: (x, y, yaw_rad, label) ──────────────────────────────────────
WAYPOINTS = [
    ( 4.0,  4.0, 0.0,  "Setor A — Nordeste"),
    ( 4.0, -4.0, 0.0,  "Setor B — Sudeste"),
    (-4.0, -4.0, 3.14, "Setor C — Sudoeste"),
    ( 0.0,  0.0, 0.0,  "Origem"),
]

SIM_WORLD     = "small_warehouse"
SPEED_STEP    = 0.05
SPEED_MIN     = 0.05
SPEED_MAX     = 1.00
SPEED_DEFAULT = 0.15
LOG_MAXLINES  = 200
LOG_DISPLAY   = 8


# ── Estado compartilhado ─────────────────────────────────────────────────────

class RobotState:
    """Thread-safe shared state: ROS callbacks escrevem, curses lê."""

    def __init__(self):
        self._lock         = threading.Lock()
        self.pose          = None          # (x, y, theta_deg) | None
        self.lidar_pts     = 0
        self.cmd_vel       = (0.0, 0.0)    # (linear m/s, angular rad/s)
        self.plan_wps      = 0
        self.mission_state = 'WAITING'
        self.current_wp    = 0
        self._log          = deque(maxlen=LOG_MAXLINES)

    def update(self, **kwargs):
        with self._lock:
            for k, v in kwargs.items():
                setattr(self, k, v)

    def add_log(self, msg: str):
        ts = time.strftime('%H:%M:%S')
        with self._lock:
            for line in msg.splitlines():
                self._log.appendleft(f"[{ts}] {line}")

    def snapshot(self) -> dict:
        with self._lock:
            return {
                'pose':          self.pose,
                'lidar_pts':     self.lidar_pts,
                'cmd_vel':       self.cmd_vel,
                'plan_wps':      self.plan_wps,
                'mission_state': self.mission_state,
                'current_wp':    self.current_wp,
                'log':           list(self._log)[:LOG_DISPLAY],
            }


# ── Controle do simulador via gz service ─────────────────────────────────────

def _gz_call(args: list):
    try:
        subprocess.run(
            ['gz', 'service', '--timeout', '500'] + args,
            capture_output=True, timeout=1.5,
        )
    except Exception:
        pass


def set_sim_paused(paused: bool):
    flag = 'true' if paused else 'false'
    threading.Thread(
        target=_gz_call,
        args=([
            '-s', f'/world/{SIM_WORLD}/control',
            '--reqtype', 'gz.msgs.WorldControl',
            '--reptype', 'gz.msgs.Boolean',
            '--req', f'pause: {flag}',
        ],),
        daemon=True,
    ).start()


def set_sim_speed(factor: float):
    threading.Thread(
        target=_gz_call,
        args=([
            '-s', f'/world/{SIM_WORLD}/set_physics',
            '--reqtype', 'gz.msgs.Physics',
            '--reptype', 'gz.msgs.Boolean',
            '--req', f'real_time_factor: {factor:.2f}',
        ],),
        daemon=True,
    ).start()


# ── Curses helper ─────────────────────────────────────────────────────────────

def _put(win, y, x, text, attr=0):
    try:
        win.addstr(y, x, text[:win.getmaxyx()[1] - x - 1], attr)
    except curses.error:
        pass


# ── Painel principal ──────────────────────────────────────────────────────────

def run_panel(stdscr, state: RobotState, mission: MissionManager):
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.timeout(200)

    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_GREEN,  -1)   # OK / rodando
    curses.init_pair(2, curses.COLOR_YELLOW, -1)   # aviso / pausado
    curses.init_pair(3, curses.COLOR_RED,    -1)   # erro
    curses.init_pair(4, curses.COLOR_CYAN,   -1)   # info
    curses.init_pair(5, curses.COLOR_WHITE,  -1)   # dim

    C_OK   = curses.color_pair(1) | curses.A_BOLD
    C_WARN = curses.color_pair(2) | curses.A_BOLD
    C_INFO = curses.color_pair(4)
    C_DIM  = curses.color_pair(5) | curses.A_DIM

    paused    = False
    sim_speed = SPEED_DEFAULT

    while True:
        key = stdscr.getch()

        if key in (ord('q'), ord('Q')):
            mission.cancel()
            break

        elif key == ord(' '):
            paused = not paused
            set_sim_paused(paused)
            state.add_log("⏸  Simulação pausada" if paused else "▶  Simulação retomada")

        elif key in (ord('+'), ord('=')):
            sim_speed = min(SPEED_MAX, round(sim_speed + SPEED_STEP, 2))
            set_sim_speed(sim_speed)
            state.add_log(f"⚡ Velocidade: {sim_speed * 100:.0f}%")

        elif key in (ord('-'), ord('_')):
            sim_speed = max(SPEED_MIN, round(sim_speed - SPEED_STEP, 2))
            set_sim_speed(sim_speed)
            state.add_log(f"⚡ Velocidade: {sim_speed * 100:.0f}%")

        elif key in (curses.KEY_ENTER, 10, 13):
            snap = state.snapshot()
            ms = snap['mission_state']
            if ms == 'DONE':
                state.add_log("🏁 Missão já concluída.")
            elif ms == 'NAVIGATING':
                state.add_log("⏳ Aguarde o robô chegar ao waypoint atual.")
            else:
                mission.send_next()

        # ── Renderização ──────────────────────────────────────────────────
        snap = state.snapshot()
        stdscr.erase()
        h, w = stdscr.getmaxyx()

        wp_idx = snap['current_wp']
        total  = mission.total
        mstate = snap['mission_state']

        # Cabeçalho
        status = "[ PAUSADO ]" if paused else "[ RODANDO ]"
        s_col  = C_WARN if paused else C_OK
        _put(stdscr, 0, 0, " rbot — MODO DIDÁTICO  ", curses.A_BOLD)
        _put(stdscr, 0, 23, status, s_col)
        _put(stdscr, 1, 0, "─" * (w - 1), C_DIM)

        # Missão
        m_col = C_OK if mstate == 'NAVIGATING' else (C_INFO if mstate == 'DONE' else C_WARN)
        done_pct = int(wp_idx / total * 100) if total else 0
        _put(stdscr, 2, 0, "  Missão: ", curses.A_BOLD)
        _put(stdscr, 2, 10, f"{mstate:<12}", m_col)
        _put(stdscr, 2, 23, f"Waypoint: {wp_idx}/{total}  ({done_pct}%)")

        if mstate == 'WAITING' and wp_idx < total:
            hint = f"  Próximo: {WAYPOINTS[wp_idx][3]}  →  pressione ENTER"
            _put(stdscr, 3, 0, hint, C_INFO)
        elif mstate == 'NAVIGATING' and wp_idx < total:
            _put(stdscr, 3, 0, f"  Indo para: {WAYPOINTS[wp_idx][3]}", C_INFO)
        elif mstate == 'DONE':
            _put(stdscr, 3, 0, "  Todos os waypoints visitados!", C_OK)

        _put(stdscr, 4, 0, "─" * (w - 1), C_DIM)

        # Sensores
        pose = snap['pose']
        if pose:
            _put(stdscr, 5, 0, f"  Pose    x={pose[0]:+.2f}  y={pose[1]:+.2f}  θ={pose[2]:+.0f}°")
        else:
            _put(stdscr, 5, 0, "  Pose    aguardando AMCL...", C_WARN)

        _put(stdscr, 6, 0, f"  LiDAR   {snap['lidar_pts']} pontos válidos")

        lin, ang = snap['cmd_vel']
        _put(stdscr, 7, 0, f"  Motor   lin={lin:+.2f} m/s   ang={ang:+.2f} rad/s")
        _put(stdscr, 8, 0, f"  Rota    {snap['plan_wps']} pontos no plano global")

        bar  = "█" * int(sim_speed * 20) + "░" * (20 - int(sim_speed * 20))
        s_c  = C_WARN if sim_speed < 0.25 else 0
        _put(stdscr, 9, 0, f"  Veloc.  {sim_speed * 100:.0f}%  [{bar}]", s_c)

        _put(stdscr, 10, 0, "─" * (w - 1), C_DIM)

        # Log
        _put(stdscr, 11, 0, "  LOG", curses.A_BOLD)
        for i, line in enumerate(snap['log']):
            row = 12 + i
            if row >= h - 2:
                break
            _put(stdscr, row, 2, line, C_DIM)

        # Rodapé
        footer = " SPACE=pausa  ENTER=próximo  +/-=velocidade  Q=sair "
        _put(stdscr, h - 2, 0, "─" * (w - 1), C_DIM)
        _put(stdscr, h - 1, 0, footer, curses.A_REVERSE)

        stdscr.refresh()


# ── Ponto de entrada ──────────────────────────────────────────────────────────

def main():
    rclpy.init()
    state = RobotState()
    state.add_log("🟢 Painel iniciado — aguardando ROS 2...")

    logger  = FriendlyLogger(state)
    mission = MissionManager(state, WAYPOINTS)

    executor = MultiThreadedExecutor()
    executor.add_node(logger)
    executor.add_node(mission)

    ros_thread = threading.Thread(target=executor.spin, daemon=True)
    ros_thread.start()

    state.add_log("📡 Nós ROS 2 ativos. Pressione ENTER para iniciar a missão.")

    try:
        curses.wrapper(run_panel, state, mission)
    except KeyboardInterrupt:
        pass
    finally:
        mission.cancel()
        executor.shutdown(timeout_sec=1.0)
        rclpy.shutdown()
        ros_thread.join(timeout=2.0)


if __name__ == '__main__':
    main()
