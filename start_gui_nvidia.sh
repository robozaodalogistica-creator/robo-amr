#!/usr/bin/env bash
# start_gui_nvidia.sh — Xorg + NVIDIA + fluxbox + x11vnc + noVNC + cloudflared.
#
# Diferenças vs start_gui.sh (Xvfb):
#   * Roda Xorg real com driver NVIDIA (libglxserver_nvidia) — GLX/3D acelerado por hardware
#   * Tela virtual 1920x1080, sem monitor físico
#   * Permite que a janela gz-sim-gui desenhe direto na A5000
#
# Fallback automático:
#   Se Xorg :1 não subir em 8 s, a função `start` cai para Xvfb (start_gui.sh)
#   e segue normalmente — exit code 0, mas com aviso.

set -euo pipefail

DISPLAY_NUM=":1"
VNC_PORT=5901
NOVNC_PORT=6080

LOG_DIR="/tmp/gui_stream"
mkdir -p "$LOG_DIR" "$LOG_DIR/pids"
XORG_LOG="$LOG_DIR/xorg.log"
WM_LOG="$LOG_DIR/fluxbox.log"
X11VNC_LOG="$LOG_DIR/x11vnc.log"
NOVNC_LOG="$LOG_DIR/novnc.log"
TUNNEL_LOG="$LOG_DIR/cloudflared.log"
URL_FILE="$LOG_DIR/public_url"
ENV_FILE="$LOG_DIR/env.sh"
BACKEND_FILE="$LOG_DIR/backend"

XORG_CONF="/workspace/xorg-nvidia-headless.conf"

cmd_stop() {
  echo "[stop] encerrando processos GUI..."
  for name in cloudflared websockify x11vnc fluxbox; do
    pkill -f "$name" 2>/dev/null || true
  done
  sudo pkill -f "Xorg :1" 2>/dev/null || true
  pkill -f "Xvfb :1" 2>/dev/null || true
  sleep 1
  sudo rm -f "/tmp/.X${DISPLAY_NUM#:}-lock" "/tmp/.X11-unix/X${DISPLAY_NUM#:}" 2>/dev/null || true
  rm -f "$URL_FILE" "$BACKEND_FILE"
  echo "[stop] ok."
}

cmd_status() {
  if pgrep -af "Xorg :1" >/dev/null; then
    printf "  %-12s RUNNING (pid %s, NVIDIA)\n" "Xorg" "$(pgrep -f 'Xorg :1' | tail -1)"
  elif pgrep -af "Xvfb :1" >/dev/null; then
    printf "  %-12s RUNNING (pid %s, software fallback)\n" "Xvfb" "$(pgrep -f 'Xvfb :1' | head -1)"
  else
    printf "  %-12s stopped\n" "X server"
  fi
  for name in fluxbox x11vnc websockify cloudflared; do
    if pgrep -f "$name" >/dev/null; then
      printf "  %-12s RUNNING (pid %s)\n" "$name" "$(pgrep -f "$name" | head -1)"
    else
      printf "  %-12s stopped\n" "$name"
    fi
  done
  [ -f "$URL_FILE" ] && { echo; echo "URL pública: $(cat "$URL_FILE")"; }
  [ -f "$BACKEND_FILE" ] && echo "Backend GL : $(cat "$BACKEND_FILE")"
}

cmd_url() {
  [ -f "$URL_FILE" ] && cat "$URL_FILE" || { echo "(sem URL)" >&2; exit 1; }
}

wait_for_port() {
  local port=$1 timeout=${2:-15}
  for _ in $(seq 1 "$timeout"); do
    ss -tln "( sport = :$port )" 2>/dev/null | grep -q ":$port" && return 0
    sleep 1
  done
  return 1
}

start_xorg_nvidia() {
  sudo nohup Xorg "$DISPLAY_NUM" -config "$XORG_CONF" \
    -noreset -novtswitch -nolisten tcp +extension GLX +extension RANDR \
    >"$XORG_LOG" 2>&1 &
  echo $! > "$LOG_DIR/pids/xorg.pid"
  for _ in $(seq 1 8); do
    [ -S "/tmp/.X11-unix/X${DISPLAY_NUM#:}" ] && break
    sleep 1
  done
  if ! command -v glxinfo >/dev/null; then
    DISPLAY="$DISPLAY_NUM" xdpyinfo >/dev/null 2>&1 || return 1
    return 0
  fi
  local renderer
  renderer=$(DISPLAY="$DISPLAY_NUM" XDG_RUNTIME_DIR=/tmp glxinfo 2>/dev/null | grep -m1 "OpenGL renderer string" || true)
  echo "[xorg] $renderer"
  case "$renderer" in
    *NVIDIA*) return 0 ;;
    *)        return 1 ;;
  esac
}

start_xvfb_fallback() {
  echo "[fallback] usando Xvfb (sem aceleração)..."
  bash /workspace/start_gui.sh start
}

start_compositor_and_vnc() {
  export DISPLAY="$DISPLAY_NUM"

  # Xorg roda como root → libera acesso para o uid corrente.  fluxbox e gz-sim
  # falham se a ACL do X bloquear.
  sudo -E DISPLAY="$DISPLAY_NUM" xhost "+SI:localuser:$(id -un)" >/dev/null 2>&1 || true

  # Fluxbox aborta neste Xorg minimal (sem fontes/dbus completos).
  # WM é opcional — gz-sim-gui desenha sua própria janela.  Tentamos best-effort.
  echo "[wm] tentando fluxbox (opcional)..."
  if nohup fluxbox >"$WM_LOG" 2>&1 & then
    echo $! > "$LOG_DIR/pids/fluxbox.pid"
    sleep 1
    if ! pgrep -f "^fluxbox$" >/dev/null 2>&1; then
      echo "[wm] fluxbox abortou — seguindo sem WM (gz-sim usa decoração nativa Qt)"
      rm -f "$LOG_DIR/pids/fluxbox.pid"
    fi
  fi

  echo "[vnc] iniciando x11vnc na porta $VNC_PORT..."
  # -noshm: MIT-SHM falha pois Xorg roda como root.  -nolookup: evita reverse DNS lento.
  # Sem -auth: confiamos no xhost ACL já liberado acima.
  nohup x11vnc -display "$DISPLAY_NUM" -nopw -forever -shared -rfbport "$VNC_PORT" \
    -xkb -noxrecord -noxfixes -noxdamage -noshm -nolookup -wait 5 -ncache 0 \
    >"$X11VNC_LOG" 2>&1 &
  echo $! > "$LOG_DIR/pids/x11vnc.pid"
  # Aceita IPv4 ou IPv6, espera até 20 s
  local ok=0
  for _ in $(seq 1 20); do
    if ss -tln 2>/dev/null | grep -qE "[:.]${VNC_PORT}\b"; then ok=1; break; fi
    sleep 1
  done
  [ "$ok" = "1" ] || { echo "[vnc] timeout"; return 1; }

  echo "[novnc] iniciando websockify+noVNC na porta $NOVNC_PORT..."
  nohup websockify --web=/usr/share/novnc "$NOVNC_PORT" "localhost:$VNC_PORT" \
    >"$NOVNC_LOG" 2>&1 &
  echo $! > "$LOG_DIR/pids/novnc.pid"
  wait_for_port "$NOVNC_PORT" 10 || { echo "[novnc] timeout"; return 1; }

  echo "[tunnel] iniciando cloudflared quick tunnel..."
  nohup cloudflared tunnel --no-autoupdate --url "http://localhost:$NOVNC_PORT" \
    >"$TUNNEL_LOG" 2>&1 &
  echo $! > "$LOG_DIR/pids/cloudflared.pid"

  local url=""
  for _ in $(seq 1 40); do
    url=$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$TUNNEL_LOG" | head -1 || true)
    [ -n "$url" ] && break
    sleep 1
  done
  [ -z "$url" ] && { echo "[tunnel] sem URL após 40s"; return 1; }

  printf '%s/vnc.html?autoconnect=1&resize=remote\n' "$url" > "$URL_FILE"
  cat > "$ENV_FILE" <<EOF
export DISPLAY=$DISPLAY_NUM
export XDG_RUNTIME_DIR=/tmp/runtime-\$(id -u)
EOF
}

cmd_start() {
  cmd_stop >/dev/null 2>&1 || true
  sleep 1
  : > "$XORG_LOG" "$WM_LOG" "$X11VNC_LOG" "$NOVNC_LOG" "$TUNNEL_LOG"

  echo "[xorg] iniciando Xorg :1 com driver NVIDIA..."
  if start_xorg_nvidia; then
    echo "NVIDIA" > "$BACKEND_FILE"
    echo "[xorg] OK — GLX acelerado por A5000"
  else
    echo "[xorg] FALHOU — caindo para Xvfb"
    sudo pkill -f "Xorg :1" 2>/dev/null || true
    sleep 1
    start_xvfb_fallback
    echo "Xvfb (fallback)" > "$BACKEND_FILE"
    echo "Backend: Xvfb (fallback).  URL: $(cat "$URL_FILE" 2>/dev/null || echo '???')"
    return 0
  fi

  if ! start_compositor_and_vnc; then
    echo "[error] compositor/vnc falhou; revertendo para Xvfb"
    sudo pkill -f "Xorg :1" 2>/dev/null
    start_xvfb_fallback
    echo "Xvfb (fallback)" > "$BACKEND_FILE"
    return 0
  fi

  echo
  echo "=================================================================="
  echo "  GUI Streaming pronto (backend: $(cat "$BACKEND_FILE"))"
  echo "  Abrir: $(cat "$URL_FILE")"
  echo "  Logs : $LOG_DIR/"
  echo "=================================================================="
}

case "${1:-start}" in
  start)  cmd_start  ;;
  stop)   cmd_stop   ;;
  status) cmd_status ;;
  url)    cmd_url    ;;
  *) echo "uso: $0 [start|stop|status|url]" >&2; exit 2 ;;
esac
