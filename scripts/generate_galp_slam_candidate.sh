#!/usr/bin/env bash
# Generate a candidate SLAM map for the Galp warehouse world.
#
# This script writes to /tmp by default. It does not replace the tracked
# production map under src/rbot/mapping/rlai_mapping/maps/.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS_DIR="${ROBO_AMR_WS:-$(cd "$SCRIPT_DIR/.." && pwd)}"

RUN_DIR="${RUN_DIR:-/tmp/robo_amr_slam}"
OUT_DIR="${OUT_DIR:-$RUN_DIR/maps}"
OUT_NAME="${OUT_NAME:-galp_amr_slam_candidate}"
WORLD="${WORLD:-galp_amr}"
START_X="${START_X:-1.0}"
START_Y="${START_Y:-1.0}"
START_YAW="${START_YAW:-0.0}"
RENDER_BACKEND="${RENDER_BACKEND:-nvidia}"
CLEANUP_ON_EXIT="${CLEANUP_ON_EXIT:-true}"
DRIVE_PATTERN="${DRIVE_PATTERN:-central_sweep}"

SIM_LOG="$RUN_DIR/sim.log"
DRIVE_LOG="$RUN_DIR/explore.log"
MAP_LOG="$RUN_DIR/map_saver.log"

mkdir -p "$RUN_DIR" "$OUT_DIR"

source_ros() {
  set +u
  source /opt/ros/jazzy/setup.bash
  source "$WS_DIR/install/setup.bash"
  set -u
  export RMW_IMPLEMENTATION="${RMW_IMPLEMENTATION:-rmw_cyclonedds_cpp}"
}

setup_render_env() {
  case "$RENDER_BACKEND" in
    nvidia)
      unset LIBGL_ALWAYS_SOFTWARE GALLIUM_DRIVER MESA_GL_VERSION_OVERRIDE
      if [ -f /usr/share/glvnd/egl_vendor.d/10_nvidia.json ]; then
        export __EGL_VENDOR_LIBRARY_FILENAMES=/usr/share/glvnd/egl_vendor.d/10_nvidia.json
      fi
      export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/tmp/runtime-$(id -u)}"
      mkdir -p "$XDG_RUNTIME_DIR" && chmod 700 "$XDG_RUNTIME_DIR"
      export OGRE_RTT_MODE="${OGRE_RTT_MODE:-Copy}"
      ;;
    software)
      export LIBGL_ALWAYS_SOFTWARE=1
      export GALLIUM_DRIVER=llvmpipe
      ;;
    none)
      ;;
    *)
      echo "Unknown RENDER_BACKEND=$RENDER_BACKEND (use nvidia, software, or none)" >&2
      exit 2
      ;;
  esac
}

cleanup_stack() {
  pkill -f '[r]os2 launch rlai_bringup simulation.launch.py' 2>/dev/null || true
  pkill -f '[a]sync_slam_toolbox_node' 2>/dev/null || true
  pkill -f '[m]ap_saver_server' 2>/dev/null || true
  pkill -f '[g]z sim' 2>/dev/null || true
  pkill -f '[s]pawner diff_drive_controller' 2>/dev/null || true
  pkill -f '[v]elocity_smoother' 2>/dev/null || true
}

wait_for_slam() {
  local timeout="${1:-90}"
  for _ in $(seq 1 "$timeout"); do
    local topics nodes
    topics="$(ros2 topic list 2>/dev/null || true)"
    nodes="$(ros2 node list 2>/dev/null || true)"
    if printf '%s\n' "$topics" | grep -qx '/scan' \
      && printf '%s\n' "$topics" | grep -qx '/map' \
      && printf '%s\n' "$nodes" | grep -qx '/slam_toolbox'; then
      return 0
    fi
    sleep 1
  done

  echo "Timed out waiting for /scan, /map, and /slam_toolbox." >&2
  tail -120 "$SIM_LOG" >&2 || true
  return 1
}

pub_twist() {
  local vx="$1" wz="$2" times="$3" label="$4"
  echo "[$(date +%H:%M:%S)] $label vx=$vx wz=$wz times=$times" | tee -a "$DRIVE_LOG"
  ros2 topic pub --rate 10 --times "$times" /cmd_vel geometry_msgs/msg/TwistStamped \
    "{header: {frame_id: base_link}, twist: {linear: {x: $vx}, angular: {z: $wz}}}" \
    >> "$DRIVE_LOG" 2>&1
  sleep 0.5
}

stop_robot() {
  ros2 topic pub --once /cmd_vel geometry_msgs/msg/TwistStamped \
    "{header: {frame_id: base_link}, twist: {linear: {x: 0.0}, angular: {z: 0.0}}}" \
    >> "$DRIVE_LOG" 2>&1 || true
  sleep 1
}

drive_central_sweep() {
  : > "$DRIVE_LOG"
  echo "Controllers:" | tee -a "$DRIVE_LOG"
  ros2 control list_controllers | tee -a "$DRIVE_LOG" || true

  pub_twist 0.0 0.6 70 "spin 360deg"
  stop_robot
  pub_twist 0.22 0.0 35 "short forward east"
  stop_robot
  pub_twist -0.20 0.0 35 "reverse to center"
  stop_robot
  pub_twist 0.0 0.6 27 "turn north-ish"
  stop_robot
  pub_twist 0.18 0.0 20 "short forward north-ish"
  stop_robot
  pub_twist -0.18 0.0 20 "reverse back"
  stop_robot
  pub_twist 0.0 -0.6 54 "turn south-ish"
  stop_robot
  pub_twist 0.18 0.0 20 "short forward south-ish"
  stop_robot
  pub_twist -0.18 0.0 20 "reverse back"
  stop_robot
  pub_twist 0.0 0.6 27 "return approximate heading"
  stop_robot
}

main() {
  if [ ! -f "$WS_DIR/install/setup.bash" ]; then
    echo "Missing $WS_DIR/install/setup.bash. Build the workspace first." >&2
    exit 1
  fi

  cleanup_stack
  if [ "$CLEANUP_ON_EXIT" = "true" ]; then
    trap cleanup_stack EXIT
  fi

  : > "$SIM_LOG"
  (
    cd "$WS_DIR"
    source_ros
    setup_render_env
    exec ros2 launch rlai_bringup simulation.launch.py \
      world:="$WORLD" \
      headless:=true \
      x:="$START_X" y:="$START_Y" yaw:="$START_YAW" \
      localization_enabled:=true \
      mapping_enabled:=true \
      use_amcl:=false \
      slam_rviz_enabled:=false \
      camera_processing_enabled:=false \
      depth_camera_enabled:=false \
      stereo_camera_enabled:=false \
      lidar_2d_enabled:=true \
      lidar_3d_enabled:=false \
      imu_enabled:=true \
      gps_enabled:=false
  ) > "$SIM_LOG" 2>&1 &

  echo "$!" > "$RUN_DIR/sim.pid"
  echo "Started SLAM simulation pid $(cat "$RUN_DIR/sim.pid")"

  source_ros
  wait_for_slam 90
  sleep 8

  case "$DRIVE_PATTERN" in
    central_sweep) drive_central_sweep ;;
    none) echo "Skipping drive pattern." ;;
    *)
      echo "Unknown DRIVE_PATTERN=$DRIVE_PATTERN (use central_sweep or none)" >&2
      exit 2
      ;;
  esac

  local out_prefix="$OUT_DIR/$OUT_NAME"
  rm -f "$out_prefix.pgm" "$out_prefix.yaml"
  ros2 run nav2_map_server map_saver_cli -f "$out_prefix" \
    --ros-args -p save_map_timeout:=10.0 | tee "$MAP_LOG"

  echo
  echo "Candidate map:"
  ls -lh "$out_prefix.pgm" "$out_prefix.yaml"
  echo
  sed -n '1,40p' "$out_prefix.yaml"
}

main "$@"
