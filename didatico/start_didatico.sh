#!/usr/bin/env bash
# start_didatico.sh — Inicia a stack rbot em modo didático (slow-motion 15%).
#
# O que faz:
#   1. Instala small_warehouse_slow.sdf no pacote rlai_gazebo (sem rebuild)
#   2. Sobe Gazebo headless + robô + AMCL em background
#   3. Sobe Nav2 (planner + controller + BT) em foreground
#   Ctrl-C encerra tudo limpo.
#
# Uso:
#   Terminal 1:  bash /workspace/didatico/start_didatico.sh
#   Terminal 2:  cd /workspace/didatico && python3 control_panel.py

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORLDS_SRC="${SCRIPT_DIR}/worlds"
ROS_WS="/workspace/rbot"
MAP_YAML="${ROS_WS}/maps/small_warehouse.yaml"

INSTALLED_WORLDS="${ROS_WS}/install/rlai_gazebo/share/rlai_gazebo/worlds"
SOURCE_WORLDS="${ROS_WS}/src/simulation/rlai_gazebo/worlds"

# ── 1. Disponibiliza o mundo slow-motion ─────────────────────────────────────
for dest in "$INSTALLED_WORLDS" "$SOURCE_WORLDS"; do
    if [ -d "$dest" ] && [ ! -f "$dest/small_warehouse_slow.sdf" ]; then
        cp "${WORLDS_SRC}/small_warehouse_slow.sdf" "$dest/"
        echo "[setup] Copiado small_warehouse_slow.sdf → $dest"
    fi
done

# ── 2. Fontes ROS 2 + workspace ───────────────────────────────────────────────
# shellcheck disable=SC1091
source /opt/ros/jazzy/setup.bash
# shellcheck disable=SC1091
source "${ROS_WS}/install/setup.bash"

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║         rbot — MODO DIDÁTICO  (15% velocidade)       ║"
echo "╠══════════════════════════════════════════════════════╣"
echo "║  Mundo : small_warehouse_slow  (real_time_factor=0.15)║"
echo "║  Mapa  : small_warehouse.yaml                         ║"
echo "║  Nav2  : SMAC Hybrid-A* + MPPI + BT                  ║"
echo "╠══════════════════════════════════════════════════════╣"
echo "║  Aguarde ~15s para os lifecycles ficarem ACTIVE...    ║"
echo "║  Então abra o Terminal 2 e rode:                      ║"
echo "║    cd /workspace/didatico && python3 control_panel.py ║"
echo "║  Ctrl-C aqui encerra toda a stack.                    ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# ── 3. Simulação (Gazebo headless + EKF + AMCL) em background ────────────────
ros2 launch rlai_bringup simulation.launch.py \
    world:=small_warehouse_slow \
    headless:=true \
    use_amcl:=true \
    map_yaml_file:="${MAP_YAML}" \
    camera_processing_enabled:=false \
    &
SIM_PID=$!

# Mata a simulação quando este script terminar (Ctrl-C ou exit)
cleanup() {
    echo ""
    echo "[didatico] Encerrando stack (PID $SIM_PID)..."
    kill "$SIM_PID" 2>/dev/null || true
    # Força encerramento de processos Gazebo órfãos
    pkill -f "gz sim" 2>/dev/null || true
    exit 0
}
trap cleanup INT TERM EXIT

echo "[didatico] Simulação iniciando (PID $SIM_PID)..."
echo "[didatico] Aguardando 8s para o Gazebo estabilizar..."
sleep 8

# ── 4. Nav2 em foreground (saída aparece neste terminal) ─────────────────────
echo "[didatico] Iniciando Nav2..."
ros2 launch rlai_navigation navigation.launch.py \
    use_sim_time:=true

wait
