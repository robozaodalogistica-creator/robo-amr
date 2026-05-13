#!/usr/bin/env bash
# start_gui.sh — Streaming do Gazebo GUI (headless) via navegador.
# Stack: Xvfb (GLX/llvmpipe) + fluxbox + x11vnc + noVNC/websockify + cloudflared.
#
# Uso:
#   ./start_gui.sh           # inicia tudo e imprime a URL pública
#   ./start_gui.sh stop      # mata os processos
#   ./start_gui.sh status    # mostra estado dos processos
#   ./start_gui.sh url       # reimprime a URL atual

set -euo pipefail

DISPLAY_NUM=":1"
GEOMETRY="1920x1080x24"
VNC_PORT=5901
NOVNC_PORT=6080

LOG_DIR="/tmp/gui_stream"
mkdir -p "$LOG_DIR"
XVFB_LOG="$LOG_DIR/xvfb.log"
WM_LOG="$LOG_DIR/fluxbox.log"
X11VNC_LOG="$LOG_DIR/x11vnc.log"
NOVNC_LOG="$LOG_DIR/novnc.log"
TUNNEL_LOG="$LOG_DIR/cloudflared.log"
URL_FILE="$LOG_DIR/public_url"
ENV_FILE="$LOG_DIR/env.sh"

PIDS_DIR="$LOG_DIR/pids"
mkdir -p "$PIDS_DIR"

REQ_PKGS=(xvfb x11vnc novnc websockify fluxbox xterm dbus-x11 mesa-utils libgl1-mesa-dri)

cmd_stop() {
  echo "[stop] encerrando processos..."
  for name in cloudflared websockify x11vnc fluxbox Xvfb; do
    pkill -f "$name" 2>/dev/null || true
  done
  rm -f "/tmp/.X${DISPLAY_NUM#:}-lock" "/tmp/.X11-unix/X${DISPLAY_NUM#:}" 2>/dev/null || true
  rm -f "$URL_FILE"
  echo "[stop] ok."
}

cmd_status() {
  for name in Xvfb fluxbox x11vnc websockify cloudflared; do
    if pgrep -f "$name" >/dev/null; then
      printf "  %-12s RUNNING (pid %s)\n" "$name" "$(pgrep -f "$name" | head -1)"
    else
      printf "  %-12s stopped\n" "$name"
    fi
  done
  if [ -f "$URL_FILE" ]; then
    echo
    echo "URL pública:"
    echo "  $(cat "$URL_FILE")"
  fi
}

cmd_url() {
  if [ -f "$URL_FILE" ]; then
    cat "$URL_FILE"
  else
    echo "(nenhuma URL ativa — rode ./start_gui.sh primeiro)" >&2
    exit 1
  fi
}

install_deps() {
  local missing=()
  for p in "${REQ_PKGS[@]}"; do
    dpkg -s "$p" >/dev/null 2>&1 || missing+=("$p")
  done
  if [ "${#missing[@]}" -gt 0 ]; then
    echo "[deps] instalando: ${missing[*]}"
    sudo apt-get update -qq
    sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "${missing[@]}"
  else
    echo "[deps] todos os pacotes já instalados."
  fi
  command -v cloudflared >/dev/null || {
    echo "[deps] ERRO: cloudflared não encontrado no PATH." >&2
    exit 1
  }
}

wait_for_port() {
  local port=$1 timeout=${2:-15}
  for _ in $(seq 1 "$timeout"); do
    ss -tln "( sport = :$port )" 2>/dev/null | grep -q ":$port" && return 0
    sleep 1
  done
  return 1
}

cmd_start() {
  install_deps
  cmd_stop >/dev/null 2>&1 || true
  sleep 1

  : > "$XVFB_LOG" "$WM_LOG" "$X11VNC_LOG" "$NOVNC_LOG" "$TUNNEL_LOG"

  echo "[xvfb] iniciando display $DISPLAY_NUM ($GEOMETRY)..."
  Xvfb "$DISPLAY_NUM" -screen 0 "$GEOMETRY" +extension GLX +render -noreset \
    >"$XVFB_LOG" 2>&1 &
  echo $! > "$PIDS_DIR/xvfb.pid"
  sleep 1
  if ! xdpyinfo -display "$DISPLAY_NUM" >/dev/null 2>&1; then
    echo "[xvfb] falhou — veja $XVFB_LOG" >&2; exit 1
  fi

  export DISPLAY="$DISPLAY_NUM"
  # Força Mesa/llvmpipe (renderização por software). Robusto, sem depender do driver NVIDIA no Xvfb.
  export LIBGL_ALWAYS_SOFTWARE=1
  export GALLIUM_DRIVER=llvmpipe
  # Ogre2 (Gazebo Harmonic) ocasionalmente exige GL 4.5; força o teto se necessário.
  export MESA_GL_VERSION_OVERRIDE=4.5

  echo "[wm] iniciando fluxbox..."
  fluxbox >"$WM_LOG" 2>&1 &
  echo $! > "$PIDS_DIR/fluxbox.pid"
  sleep 1

  echo "[vnc] iniciando x11vnc na porta $VNC_PORT..."
  x11vnc -display "$DISPLAY_NUM" -nopw -forever -shared -rfbport "$VNC_PORT" \
    -xkb -noxrecord -noxfixes -noxdamage -wait 5 -ncache 0 \
    >"$X11VNC_LOG" 2>&1 &
  echo $! > "$PIDS_DIR/x11vnc.pid"
  wait_for_port "$VNC_PORT" 10 || { echo "[vnc] timeout — veja $X11VNC_LOG" >&2; exit 1; }

  echo "[novnc] iniciando websockify+noVNC na porta $NOVNC_PORT..."
  websockify --web=/usr/share/novnc "$NOVNC_PORT" "localhost:$VNC_PORT" \
    >"$NOVNC_LOG" 2>&1 &
  echo $! > "$PIDS_DIR/novnc.pid"
  wait_for_port "$NOVNC_PORT" 10 || { echo "[novnc] timeout — veja $NOVNC_LOG" >&2; exit 1; }

  echo "[tunnel] iniciando cloudflared quick tunnel..."
  cloudflared tunnel --no-autoupdate --url "http://localhost:$NOVNC_PORT" \
    >"$TUNNEL_LOG" 2>&1 &
  echo $! > "$PIDS_DIR/cloudflared.pid"

  local url=""
  for _ in $(seq 1 40); do
    url=$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$TUNNEL_LOG" | head -1 || true)
    [ -n "$url" ] && break
    sleep 1
  done
  if [ -z "$url" ]; then
    echo "[tunnel] sem URL após 40s — veja $TUNNEL_LOG" >&2
    exit 1
  fi
  local full="$url/vnc.html?autoconnect=1&resize=remote"
  printf '%s\n' "$full" > "$URL_FILE"

  cat > "$ENV_FILE" <<EOF
export DISPLAY=$DISPLAY_NUM
export LIBGL_ALWAYS_SOFTWARE=1
export GALLIUM_DRIVER=llvmpipe
export MESA_GL_VERSION_OVERRIDE=4.5
EOF

  cat <<EOF

==================================================================
  ✅ Gazebo GUI Streaming pronto

  Abra no navegador:
    $full

  Variáveis para rodar GUI no mesmo display:
    source $ENV_FILE
    # exemplo:
    gz sim shapes.sdf
    # ou seu mundo:
    gz sim /workspace/amr_pallet/.../warehouse.sdf

  Logs em $LOG_DIR/
  Parar tudo:  ./start_gui.sh stop
  Status:      ./start_gui.sh status
  Ver URL:     ./start_gui.sh url
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
