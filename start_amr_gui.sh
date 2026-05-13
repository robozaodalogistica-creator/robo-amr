#!/usr/bin/env bash
# start_amr_gui.sh — sobe a stack completa do amr_pallet com Gazebo gráfico no DISPLAY=:1.
#
# O `warehouse.launch.py` original é headless: usa o nó `robot_sim` (loopback)
# como fonte da pose do robô. Este script:
#   1. Sobe `gz sim galp_amr.world` em modo GUI no display do VNC.
#   2. Spawna um modelo de viz (amr_viz) no Gazebo.
#   3. Sobe a stack ROS headless (warehouse.launch.py).
#   4. Sobe um pose-bridge: /odom → /world/galp_amr/set_pose, fazendo o
#      modelo no Gazebo seguir o robô do loopback.
#
# Uso:
#   ./start_amr_gui.sh           # start
#   ./start_amr_gui.sh stop      # encerra tudo
#   ./start_amr_gui.sh status    # lista processos
#   ./start_amr_gui.sh logs      # mostra os caminhos dos logs

set -euo pipefail

# ── Configuração ──────────────────────────────────────────────────────
WORLD_NAME="galp_amr"
PKG_SRC="/workspace/amr_pallet/src/amr_pallet"
WORLD_FILE="$PKG_SRC/worlds/${WORLD_NAME}.world"
MODELS_DIR="$PKG_SRC/models"
BRIDGE_PY="/workspace/amr_pallet/scripts/gz_pose_bridge.py"

GUI_STREAM_ENV="/tmp/gui_stream/env.sh"

LOG_DIR="/tmp/amr_gui"
mkdir -p "$LOG_DIR"
GZ_LOG="$LOG_DIR/gz_sim.log"
SPAWN_LOG="$LOG_DIR/spawn.log"
LAUNCH_LOG="$LOG_DIR/warehouse_launch.log"
BRIDGE_LOG="$LOG_DIR/pose_bridge.log"

PIDS_DIR="$LOG_DIR/pids"
mkdir -p "$PIDS_DIR"

# ── Helpers ───────────────────────────────────────────────────────────
have_proc() { pgrep -f "$1" >/dev/null 2>&1; }

source_env() {
  # GUI/VNC display
  if [ ! -f "$GUI_STREAM_ENV" ]; then
    echo "ERRO: $GUI_STREAM_ENV não existe — rode /workspace/start_gui.sh primeiro." >&2
    exit 1
  fi
  # Os setup.bash do ROS/colcon usam variáveis indefinidas — relaxa `set -u`.
  set +u
  # shellcheck disable=SC1090
  source "$GUI_STREAM_ENV"
  # shellcheck disable=SC1091
  source /opt/ros/jazzy/setup.bash
  # shellcheck disable=SC1091
  source /workspace/amr_pallet/install/setup.bash
  set -u

  # Gazebo Harmonic resource paths — modelos do amr_pallet
  export GZ_SIM_RESOURCE_PATH="${MODELS_DIR}${GZ_SIM_RESOURCE_PATH:+:$GZ_SIM_RESOURCE_PATH}"

  # Render: software (llvmpipe) — combina com Xvfb+VNC
  export LIBGL_ALWAYS_SOFTWARE=1
  export GALLIUM_DRIVER=llvmpipe
  export MESA_GL_VERSION_OVERRIDE=4.5
  # Ogre2 ocasionalmente quer indicar engine de render explicitamente
  export OGRE_RTT_MODE=Copy

  # RMW — bater com o que o warehouse.launch.py força para todos os nós,
  # caso contrário o pose-bridge não enxerga /odom.
  export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
  export CYCLONEDDS_URI='<CycloneDDS><Domain><General><Interfaces><NetworkInterface name="lo"/></Interfaces></General></Domain></CycloneDDS>'
}

wait_for_topic() {
  local topic=$1 timeout=${2:-30}
  for _ in $(seq 1 "$timeout"); do
    if gz topic -l 2>/dev/null | grep -q "^${topic}\$"; then
      return 0
    fi
    sleep 1
  done
  return 1
}

# ── Sub-comandos ──────────────────────────────────────────────────────
cmd_stop() {
  echo "[stop] encerrando processos..."
  for pat in "gz_pose_bridge" "ros2 launch amr_pallet" "ros2 run ros_gz_sim create" \
             "gz sim" "ruby.*gz sim" "gz-sim-server" "gz-sim-gui"; do
    pkill -f "$pat" 2>/dev/null || true
  done
  # Limpa lock-files do Gazebo
  rm -rf /tmp/gz_amr_lock 2>/dev/null || true
  sleep 1
  echo "[stop] ok."
}

cmd_status() {
  for pat in "gz sim" "gz-sim-server" "gz-sim-gui" "warehouse.launch" "gz_pose_bridge"; do
    if pgrep -af "$pat" >/dev/null 2>&1; then
      printf "  %-22s " "$pat"
      pgrep -af "$pat" | head -1 | awk '{print "pid="$1}'
    else
      printf "  %-22s stopped\n" "$pat"
    fi
  done
}

cmd_logs() {
  echo "Logs:"
  echo "  gz sim       : $GZ_LOG"
  echo "  spawn        : $SPAWN_LOG"
  echo "  warehouse    : $LAUNCH_LOG"
  echo "  pose-bridge  : $BRIDGE_LOG"
}

cmd_start() {
  source_env

  # ── Sanity ─────────────────────────────────────────────────────────
  if ! pgrep -f "Xvfb :1" >/dev/null; then
    echo "ERRO: Xvfb :1 não está rodando. Execute /workspace/start_gui.sh primeiro." >&2
    exit 1
  fi
  [ -f "$WORLD_FILE" ] || { echo "ERRO: world não encontrado: $WORLD_FILE" >&2; exit 1; }
  [ -d "$MODELS_DIR/amr_viz" ] || { echo "ERRO: modelo amr_viz ausente em $MODELS_DIR" >&2; exit 1; }
  [ -f "$BRIDGE_PY" ] || { echo "ERRO: bridge ausente: $BRIDGE_PY" >&2; exit 1; }

  # ── Limpa execução anterior ────────────────────────────────────────
  cmd_stop >/dev/null 2>&1 || true

  : > "$GZ_LOG" "$SPAWN_LOG" "$LAUNCH_LOG" "$BRIDGE_LOG"

  # ── 1. Gazebo GUI ──────────────────────────────────────────────────
  echo "[gz] iniciando 'gz sim' em DISPLAY=$DISPLAY (mundo: $WORLD_NAME)..."
  ( gz sim -r -v 3 "$WORLD_FILE" >"$GZ_LOG" 2>&1 ) &
  echo $! > "$PIDS_DIR/gz_sim.pid"

  echo "[gz] aguardando world ficar visível..."
  if ! wait_for_topic "/world/${WORLD_NAME}/clock" 60; then
    echo "[gz] ERRO: world não ficou pronto em 60s. Veja $GZ_LOG" >&2
    tail -20 "$GZ_LOG" >&2 || true
    exit 1
  fi
  echo "[gz] world publicando /clock — pronto."

  # ── 2. Spawn do robô de viz ────────────────────────────────────────
  echo "[spawn] criando entidade amr_viz em (0,0,0)..."
  ros2 run ros_gz_sim create \
       -world "$WORLD_NAME" \
       -file "$MODELS_DIR/amr_viz/model.sdf" \
       -name amr_viz \
       -x 0 -y 0 -z 0.1 -Y 0 \
       >"$SPAWN_LOG" 2>&1 \
    || { echo "[spawn] FALHOU — veja $SPAWN_LOG" >&2; tail -10 "$SPAWN_LOG" >&2; exit 1; }
  echo "[spawn] amr_viz spawned."

  # ── 3. Stack ROS headless (Nav2 + map + mission + foxglove) ────────
  echo "[ros] subindo warehouse.launch.py (Nav2 + missão + foxglove)..."
  ( ros2 launch amr_pallet warehouse.launch.py >"$LAUNCH_LOG" 2>&1 ) &
  echo $! > "$PIDS_DIR/warehouse_launch.pid"

  # ── 4. Pose bridge ─────────────────────────────────────────────────
  echo "[bridge] iniciando /odom → set_pose..."
  ( python3 "$BRIDGE_PY" --ros-args \
       -p "world:=$WORLD_NAME" -p "model:=amr_viz" -p "rate_hz:=15.0" \
       >"$BRIDGE_LOG" 2>&1 ) &
  echo $! > "$PIDS_DIR/pose_bridge.pid"

  sleep 2
  echo
  cat <<EOF
==================================================================
  ✅ Stack AMR + Gazebo gráfico no ar
==================================================================
  Abra a URL do VNC e você verá o galpão + robô no Gazebo:
    $(cat /tmp/gui_stream/public_url 2>/dev/null || echo '(rode start_gui.sh url)')

  Nav2 + missão sobem em ~35 s — o robô azul se mexerá sozinho
  pelos 4 waypoints (doca → pallets → expedição).

  Foxglove:    ws://localhost:8765   (também acessível via túnel se quiser)
  RViz local:  source /tmp/gui_stream/env.sh && rviz2

  Comandos:
    ./start_amr_gui.sh status
    ./start_amr_gui.sh logs
    ./start_amr_gui.sh stop
==================================================================
EOF
}

case "${1:-start}" in
  start)  cmd_start  ;;
  stop)   cmd_stop   ;;
  status) cmd_status ;;
  logs)   cmd_logs   ;;
  *) echo "uso: $0 [start|stop|status|logs]" >&2; exit 2 ;;
esac
