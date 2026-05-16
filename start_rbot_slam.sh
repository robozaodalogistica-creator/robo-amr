#!/usr/bin/env bash
# start_rbot_slam.sh — sobe a stack rbot em modo SLAM (mapping online_async).
#
# Cenário: robô não sabe nada do galpão; SLAM Toolbox constrói o mapa em
# tempo real enquanto o Nav2 navega no mapa gerado.
#
# Componentes:
#   1. Xvfb + fluxbox + x11vnc + noVNC + cloudflared  (via start_gui.sh)
#   2. Gazebo Harmonic (small_warehouse) + robô + sensores + EKF
#   3. SLAM Toolbox (async, mapping)                     -> /map, map->odom
#   4. Nav2 (planner + controller + bt + recoveries)     -> /cmd_vel
#   5. foxglove_bridge                                   -> ws://host:8765
#
# Uso:
#   /workspace/start_rbot_slam.sh           # sobe tudo
#   /workspace/start_rbot_slam.sh stop      # encerra
#   /workspace/start_rbot_slam.sh status    # estado dos componentes
#   /workspace/start_rbot_slam.sh url       # imprime URL do VNC

set -euo pipefail

LOG_DIR="/tmp/rbot_slam"
mkdir -p "$LOG_DIR" "$LOG_DIR/pids"
SIM_LOG="$LOG_DIR/sim_mapping.log"
NAV_LOG="$LOG_DIR/nav2.log"
FOX_LOG="$LOG_DIR/foxglove.log"

GUI_STREAM_ENV="/tmp/gui_stream/env.sh"
WORLD="small_warehouse"

MAPS_DIR="/workspace/maps"
mkdir -p "$MAPS_DIR"

source_env() {
  set +u
  source /opt/ros/jazzy/setup.bash
  source /workspace/rbot/install/setup.bash
  if [ -f "$GUI_STREAM_ENV" ]; then
    source "$GUI_STREAM_ENV"
  fi
  set -u

  export GZ_SIM_RESOURCE_PATH="/workspace/rbot/install/rlai_gazebo/share/rlai_gazebo:/workspace/rbot/install/rlai_meshes/share${GZ_SIM_RESOURCE_PATH:+:$GZ_SIM_RESOURCE_PATH}"
  export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
  # GPU rendering: Ogre2 uses EGL surfaceless on the NVIDIA A5000 via --headless-rendering.
  # Software-rendering env vars (LIBGL_ALWAYS_SOFTWARE, GALLIUM_DRIVER, MESA_GL_VERSION_OVERRIDE)
  # are intentionally NOT exported so the NVIDIA EGL vendor is selected.
  unset LIBGL_ALWAYS_SOFTWARE GALLIUM_DRIVER MESA_GL_VERSION_OVERRIDE
  export __EGL_VENDOR_LIBRARY_FILENAMES=/usr/share/glvnd/egl_vendor.d/10_nvidia.json
  export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/tmp/runtime-$(id -u)}"
  mkdir -p "$XDG_RUNTIME_DIR" && chmod 700 "$XDG_RUNTIME_DIR"
  export OGRE_RTT_MODE=Copy
}

cmd_stop() {
  echo "[stop] encerrando stack SLAM..."
  for pat in "foxglove_bridge" "ros2 launch rlai_navigation" "ros2 launch rlai_bringup" \
             "rlai_bringup" "rlai_navigation" "rlai_mapping" \
             "slam_toolbox" "lifecycle_manager" \
             "controller_server" "planner_server" "behavior_server" "bt_navigator" \
             "waypoint_follower" "smoother_server" "map_saver_server" \
             "ekf_node" "robot_state_publisher" "ros_gz_bridge" "ros_gz_image" \
             "ros2 run rviz2" "rviz2" \
             "gz sim" "ruby.*gz sim" "gz-sim-server" "gz-sim-gui"; do
    pkill -f "$pat" 2>/dev/null || true
  done
  sleep 1
  echo "[stop] ok."
}

cmd_status() {
  for pat in "Xvfb :1" "x11vnc" "cloudflared" "gz sim" \
             "rlai_bringup" "slam_toolbox" "controller_server" \
             "planner_server" "bt_navigator" "foxglove_bridge"; do
    if pgrep -af "$pat" >/dev/null 2>&1; then
      printf "  %-24s RUNNING (%s)\n" "$pat" "$(pgrep -f "$pat" | head -1)"
    else
      printf "  %-24s stopped\n" "$pat"
    fi
  done
  echo
  echo "Logs em $LOG_DIR/"
  [ -f /tmp/gui_stream/public_url ] && echo "VNC URL: $(cat /tmp/gui_stream/public_url)"
}

cmd_url() {
  if [ -f /tmp/gui_stream/public_url ]; then
    cat /tmp/gui_stream/public_url
  else
    echo "(VNC ainda não pronto)" >&2
    exit 1
  fi
}

wait_topic() {
  local topic="$1" timeout="${2:-60}"
  for _ in $(seq 1 "$timeout"); do
    if ros2 topic list 2>/dev/null | grep -q "^${topic}\$"; then
      return 0
    fi
    sleep 1
  done
  return 1
}

cmd_start() {
  # 1) VNC (idempotente — só sobe se não estiver no ar).  Prefere Xorg+NVIDIA;
  #    cai para Xvfb se Xorg falhar.
  if ! pgrep -f "Xorg :1" >/dev/null 2>&1 && ! pgrep -f "Xvfb :1" >/dev/null 2>&1; then
    echo "[vnc] subindo Xorg+NVIDIA (com fallback Xvfb)..."
    /workspace/start_gui_nvidia.sh start
  else
    echo "[vnc] já está rodando."
  fi

  source_env

  # 2) Garante que o robô apareça no Gazebo headless.  O simulation.launch.py
  #    com mapping_enabled:=true sobe gazebo + EKF + SLAM (online_async).
  echo "[sim] subindo Gazebo + EKF + SLAM Toolbox (mapping)..."
  cmd_stop >/dev/null 2>&1 || true
  : > "$SIM_LOG" "$NAV_LOG" "$FOX_LOG"

  (
    set +u
    source /opt/ros/jazzy/setup.bash
    source /workspace/rbot/install/setup.bash
    source "$GUI_STREAM_ENV"
    set -u
    export GZ_SIM_RESOURCE_PATH="/workspace/rbot/install/rlai_gazebo/share/rlai_gazebo:/workspace/rbot/install/rlai_meshes/share"
    export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
    unset LIBGL_ALWAYS_SOFTWARE GALLIUM_DRIVER MESA_GL_VERSION_OVERRIDE
    export __EGL_VENDOR_LIBRARY_FILENAMES=/usr/share/glvnd/egl_vendor.d/10_nvidia.json
    export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/tmp/runtime-$(id -u)}"
    mkdir -p "$XDG_RUNTIME_DIR" && chmod 700 "$XDG_RUNTIME_DIR"
    export OGRE_RTT_MODE=Copy
    exec ros2 launch rlai_bringup simulation.launch.py \
      world:="$WORLD" \
      x:=1.0 y:=1.0 yaw:=0.0 \
      headless:=false \
      lidar_2d_enabled:=true \
      lidar_3d_enabled:=false \
      depth_camera_enabled:=true \
      stereo_camera_enabled:=false \
      imu_enabled:=true \
      gps_enabled:=false \
      localization_enabled:=true \
      mapping_enabled:=true \
      slam_rviz_enabled:=false \
      use_amcl:=false
  ) >"$SIM_LOG" 2>&1 &
  echo $! > "$LOG_DIR/pids/sim.pid"

  echo "[sim] aguardando /scan e /map..."
  if ! wait_topic "/scan" 90; then
    echo "[sim] TIMEOUT esperando /scan; veja $SIM_LOG" >&2
    tail -40 "$SIM_LOG" >&2 || true
    exit 1
  fi
  echo "[sim] /scan OK."
  if ! wait_topic "/map" 60; then
    echo "[sim] AVISO: /map ainda não publicado; continuando (SLAM publica no primeiro scan-match)."
  else
    echo "[sim] /map OK."
  fi

  # 3) Nav2
  echo "[nav2] subindo Nav2 (planner/controller/bt + recoveries)..."
  (
    set +u
    source /opt/ros/jazzy/setup.bash
    source /workspace/rbot/install/setup.bash
    set -u
    export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
    exec ros2 launch rlai_navigation navigation.launch.py use_sim_time:=true
  ) >"$NAV_LOG" 2>&1 &
  echo $! > "$LOG_DIR/pids/nav2.pid"

  # 4) foxglove_bridge
  echo "[foxglove] subindo foxglove_bridge na porta 8765..."
  (
    set +u
    source /opt/ros/jazzy/setup.bash
    source /workspace/rbot/install/setup.bash
    set -u
    export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
    exec ros2 launch foxglove_bridge foxglove_bridge_launch.xml \
      port:=8765 address:=0.0.0.0 use_sim_time:=true
  ) >"$FOX_LOG" 2>&1 &
  echo $! > "$LOG_DIR/pids/foxglove.pid"

  sleep 4

  cat <<EOF

==================================================================
  ✅ rbot SLAM stack no ar (world=$WORLD)
==================================================================
  VNC URL (cloudflare):
    $(cat /tmp/gui_stream/public_url 2>/dev/null || echo '(VNC ainda não pronto — rode '"\$0"' url)')

  Foxglove WebSocket:
    ws://localhost:8765    (use cloudflared/ngrok p/ acesso remoto)

  Logs:
    sim  : $SIM_LOG
    nav2 : $NAV_LOG
    fox  : $FOX_LOG

  Comandos:
    $0 status
    $0 stop

  Enviar goal manual (ros2 topic, frame=map):
    ros2 topic pub -1 /goal_pose geometry_msgs/msg/PoseStamped \\
      "{header: {frame_id: 'map'}, pose: {position: {x: 3.0, y: 2.0, z: 0.0}, \\
        orientation: {w: 1.0}}}"

  Salvar o mapa quando terminar de explorar:
    ros2 run nav2_map_server map_saver_cli -f /workspace/maps/galpao_explorado
==================================================================
EOF
}

case "${1:-start}" in
  start)  cmd_start  ;;
  stop)   cmd_stop   ;;
  status) cmd_status ;;
  url)    cmd_url    ;;
  *) echo "uso: $0 [start|stop|status|url]" >&2; exit 2 ;;
esac
