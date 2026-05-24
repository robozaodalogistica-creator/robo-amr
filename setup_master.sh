#!/usr/bin/env bash
# =============================================================================
# setup_master.sh — Idempotent provisioning for ROS 2 Jazzy dev container
# =============================================================================
# Installs / configures:
#   1. ROS 2 Jazzy + Gazebo Harmonic + Nav2 + SLAM Toolbox + foxglove_bridge
#   2. cloudflared
#   3. Node.js 22 + Claude Code (global)
#   4. User `dev` with sudo NOPASSWD (password: dev123)
#   5. /home/dev/.bashrc: `claude` alias with --dangerously-skip-permissions,
#      auto-source ROS 2
#   6. colcon build of /workspace/{amr_pallet,nav_test,tb3_nav_demo}
#   7. Final verification
#
# Safe to re-run: each step detects existing state and skips if already done.
# =============================================================================
set -euo pipefail

LOG=/workspace/setup_master.log
mkdir -p /workspace
# Tee everything to log (append) and stdout
exec > >(tee -a "$LOG") 2>&1

DEV_USER=dev
DEV_PASS=dev123
WORKSPACES=(amr_pallet nav_test tb3_nav_demo)

# ── Re-exec as root if needed ────────────────────────────────────────────────
if [[ $EUID -ne 0 ]]; then
    echo "[setup_master] Not root — re-executing under sudo..."
    exec sudo -E bash "$0" "$@"
fi

export DEBIAN_FRONTEND=noninteractive

log()    { echo -e "\n\033[1;34m[$(date +%H:%M:%S)] $*\033[0m"; }
ok()     { echo -e "  \033[1;32m✓\033[0m $*"; }
skip()   { echo -e "  \033[1;33m↷\033[0m $* (already present, skipping)"; }
warn()   { echo -e "  \033[1;33m!\033[0m $*"; }

pkg_installed() {
    dpkg-query -W -f='${Status}' "$1" 2>/dev/null | grep -q "install ok installed"
}

apt_install_missing() {
    # Args: list of package names. Installs only the ones not yet installed.
    local missing=()
    for p in "$@"; do
        if pkg_installed "$p"; then
            skip "$p"
        else
            missing+=("$p")
        fi
    done
    if [[ ${#missing[@]} -gt 0 ]]; then
        echo "  → apt-get install: ${missing[*]}"
        apt-get install -y -qq --no-install-recommends "${missing[@]}"
    fi
}

echo "============================================================"
echo "  setup_master.sh — $(date)"
echo "============================================================"

# ── Step 0: base tools + repositories ────────────────────────────────────────
log "[0/7] Base tools and APT repositories"
apt-get update -qq
apt_install_missing curl gnupg2 ca-certificates lsb-release software-properties-common \
                    locales build-essential git wget sudo

# Locale
if ! locale -a 2>/dev/null | grep -q '^en_US\.utf8$'; then
    locale-gen en_US.UTF-8
    update-locale LANG=en_US.UTF-8
    ok "locale en_US.UTF-8 generated"
else
    skip "locale en_US.UTF-8"
fi

if ! grep -q '^deb.*packages.ros.org' /etc/apt/sources.list.d/ros2.list 2>/dev/null; then
    add-apt-repository -y universe
    curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
        -o /usr/share/keyrings/ros-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] \
http://packages.ros.org/ros2/ubuntu $(lsb_release -cs) main" \
        > /etc/apt/sources.list.d/ros2.list
    ok "ROS 2 apt repo added"
else
    skip "ROS 2 apt repo"
fi

if ! grep -q '^deb.*packages.osrfoundation.org' /etc/apt/sources.list.d/gazebo-stable.list 2>/dev/null; then
    curl -sSL https://packages.osrfoundation.org/gazebo.gpg \
        -o /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] \
http://packages.osrfoundation.org/gazebo/ubuntu-stable $(lsb_release -cs) main" \
        > /etc/apt/sources.list.d/gazebo-stable.list
    ok "Gazebo apt repo added"
else
    skip "Gazebo apt repo"
fi

# NodeSource (Node.js 22)
if ! grep -q 'node_22' /etc/apt/sources.list.d/nodesource.list 2>/dev/null; then
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key \
        | gpg --dearmor -o /usr/share/keyrings/nodesource.gpg
    echo "deb [signed-by=/usr/share/keyrings/nodesource.gpg] \
https://deb.nodesource.com/node_22.x nodistro main" \
        > /etc/apt/sources.list.d/nodesource.list
    ok "NodeSource (Node 22) apt repo added"
else
    skip "NodeSource apt repo"
fi

apt-get update -qq

# ── Step 1: ROS 2 Jazzy + Gazebo + Nav2 + SLAM + foxglove ────────────────────
log "[1/7] ROS 2 Jazzy Desktop + dev tools"
apt_install_missing \
    python3-pip python3-venv python3-vcstool \
    python3-colcon-common-extensions python3-rosdep python3-argcomplete \
    ros-jazzy-desktop ros-jazzy-ros-base ros-jazzy-rmw-cyclonedds-cpp \
    ros-dev-tools

log "[2/7] Gazebo Harmonic + ros_gz bridge"
apt_install_missing \
    gz-harmonic \
    ros-jazzy-ros-gz ros-jazzy-ros-gz-bridge \
    ros-jazzy-ros-gz-sim ros-jazzy-ros-gz-image

log "[3/7] Nav2"
apt_install_missing \
    ros-jazzy-navigation2 ros-jazzy-nav2-bringup ros-jazzy-nav2-msgs \
    ros-jazzy-nav2-rviz-plugins ros-jazzy-nav2-simple-commander \
    ros-jazzy-nav2-mppi-controller ros-jazzy-nav2-velocity-smoother \
    ros-jazzy-nav2-collision-monitor ros-jazzy-nav2-behavior-tree \
    ros-jazzy-nav2-minimal-tb3-sim

log "[4/7] SLAM Toolbox + perception + foxglove_bridge + TurtleBot3"
apt_install_missing \
    ros-jazzy-slam-toolbox \
    ros-jazzy-apriltag-ros ros-jazzy-image-proc \
    ros-jazzy-foxglove-bridge \
    ros-jazzy-turtlebot3 ros-jazzy-turtlebot3-msgs \
    ros-jazzy-turtlebot3-simulations ros-jazzy-turtlebot3-gazebo \
    ros-jazzy-rviz2 ros-jazzy-robot-state-publisher \
    ros-jazzy-joint-state-publisher ros-jazzy-xacro ros-jazzy-tf2-tools

# rosdep init/update
if [[ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]]; then
    rosdep init || true
    ok "rosdep init"
else
    skip "rosdep init"
fi
sudo -u "$DEV_USER" -H bash -c 'rosdep update --rosdistro=jazzy' 2>/dev/null || \
    rosdep update --rosdistro=jazzy || true

# /etc/profile.d/ros2.sh — system-wide ROS env
if [[ ! -f /etc/profile.d/ros2.sh ]]; then
    cat > /etc/profile.d/ros2.sh << 'EOF'
source /opt/ros/jazzy/setup.bash
export TURTLEBOT3_MODEL=burger
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
EOF
    ok "/etc/profile.d/ros2.sh created"
else
    skip "/etc/profile.d/ros2.sh"
fi

# ── Step 2: Node.js 22 + Claude Code ─────────────────────────────────────────
log "[5/7] Node.js 22 + Claude Code"
if command -v node >/dev/null 2>&1 && node --version 2>/dev/null | grep -q '^v22\.'; then
    skip "node $(node --version)"
else
    apt_install_missing nodejs
    ok "Node.js installed: $(node --version 2>/dev/null || echo unknown)"
fi

if command -v claude >/dev/null 2>&1; then
    skip "claude code $(claude --version 2>/dev/null | head -1)"
else
    npm install -g @anthropic-ai/claude-code
    ok "Claude Code installed: $(claude --version 2>/dev/null | head -1)"
fi

# ── Step 3: cloudflared ──────────────────────────────────────────────────────
log "[6/7] cloudflared"
if command -v cloudflared >/dev/null 2>&1; then
    skip "cloudflared $(cloudflared --version 2>&1 | head -1)"
else
    ARCH=$(dpkg --print-architecture)
    DEB=/tmp/cloudflared.deb
    curl -fsSL -o "$DEB" \
        "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-${ARCH}.deb"
    dpkg -i "$DEB"
    rm -f "$DEB"
    ok "cloudflared installed: $(cloudflared --version 2>&1 | head -1)"
fi

# ── Step 4: dev user + sudo NOPASSWD ─────────────────────────────────────────
log "[7/7] dev user, sudo NOPASSWD, bashrc"

if id "$DEV_USER" >/dev/null 2>&1; then
    skip "user $DEV_USER exists"
else
    useradd -m -s /bin/bash "$DEV_USER"
    ok "user $DEV_USER created"
fi

# Set / refresh password (idempotent: setting again is fine)
echo "${DEV_USER}:${DEV_PASS}" | chpasswd
ok "password set for $DEV_USER"

# Add to common groups if available
for g in sudo video audio dialout plugdev; do
    if getent group "$g" >/dev/null 2>&1; then
        usermod -aG "$g" "$DEV_USER" 2>/dev/null || true
    fi
done

# sudoers NOPASSWD
SUDOERS_FILE=/etc/sudoers.d/dev
if [[ ! -f "$SUDOERS_FILE" ]] || ! grep -q "^${DEV_USER} ALL=(ALL) NOPASSWD:ALL" "$SUDOERS_FILE"; then
    echo "${DEV_USER} ALL=(ALL) NOPASSWD:ALL" > "$SUDOERS_FILE"
    chmod 0440 "$SUDOERS_FILE"
    visudo -cf "$SUDOERS_FILE" >/dev/null
    ok "sudoers NOPASSWD for $DEV_USER"
else
    skip "sudoers NOPASSWD for $DEV_USER"
fi

# /home/dev/.bashrc — idempotent block via markers
BASHRC=/home/$DEV_USER/.bashrc
[[ -f "$BASHRC" ]] || { touch "$BASHRC"; chown "$DEV_USER:$DEV_USER" "$BASHRC"; }

BEGIN_MARK="# >>> setup_master.sh >>>"
END_MARK="# <<< setup_master.sh <<<"
if grep -q "$BEGIN_MARK" "$BASHRC"; then
    # Remove old block
    sed -i "/$BEGIN_MARK/,/$END_MARK/d" "$BASHRC"
fi
cat >> "$BASHRC" << 'EOF'
# >>> setup_master.sh >>>
# Auto-source ROS 2 Jazzy
if [ -f /opt/ros/jazzy/setup.bash ]; then
    source /opt/ros/jazzy/setup.bash
fi
export TURTLEBOT3_MODEL=burger
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export RCUTILS_COLORIZED_OUTPUT=1

# Auto-source workspaces if built
for ws in /workspace/amr_pallet /workspace/nav_test /workspace/tb3_nav_demo; do
    [ -f "$ws/install/setup.bash" ] && source "$ws/install/setup.bash"
done

# Claude Code alias — skip permission prompts
alias claude='claude --dangerously-skip-permissions'

# Convenience aliases
alias cb='colcon build --symlink-install'
alias cbt='colcon build --symlink-install --packages-select'
# <<< setup_master.sh <<<
EOF
chown "$DEV_USER:$DEV_USER" "$BASHRC"
ok "$BASHRC configured (alias claude, source ROS 2, workspaces)"

# Ensure /workspace is owned/writable by dev
chown -R "$DEV_USER:$DEV_USER" /workspace 2>/dev/null || true

# ── Step 5: colcon build of /workspace/* ─────────────────────────────────────
log "Building workspaces with colcon"
for ws in "${WORKSPACES[@]}"; do
    WS_DIR=/workspace/$ws
    if [[ ! -d "$WS_DIR/src" ]]; then
        warn "$WS_DIR has no src/ — skipping"
        continue
    fi
    # Skip if there are no packages at all (no package.xml under src/)
    if ! find "$WS_DIR/src" -name package.xml -print -quit | grep -q .; then
        warn "$WS_DIR/src has no package.xml — skipping"
        continue
    fi
    echo "  → building $WS_DIR"
    sudo -u "$DEV_USER" -H bash -lc "
        set -e
        source /opt/ros/jazzy/setup.bash
        cd '$WS_DIR'
        colcon build --symlink-install \
            --event-handlers console_cohesion+ console_package_list+ \
            --cmake-args -DCMAKE_BUILD_TYPE=Release
    " && ok "$ws built" || warn "$ws build had errors (see log)"
done

# ── Step 6: Final verification ───────────────────────────────────────────────
log "Verification"

verify() {
    local label="$1"; shift
    if "$@" >/dev/null 2>&1; then
        ok "$label"
        return 0
    else
        warn "$label — FAILED"
        return 1
    fi
}

VERIFY_FAIL=0
# ROS 2
verify "ROS 2 Jazzy (/opt/ros/jazzy/setup.bash exists)" \
    test -f /opt/ros/jazzy/setup.bash || VERIFY_FAIL=$((VERIFY_FAIL+1))
verify "ros2 CLI runs" \
    bash -c 'source /opt/ros/jazzy/setup.bash && ros2 pkg list | head -1' || VERIFY_FAIL=$((VERIFY_FAIL+1))
# Gazebo
verify "Gazebo Harmonic (gz binary)" command -v gz || VERIFY_FAIL=$((VERIFY_FAIL+1))
# Nav2
verify "Nav2 bringup pkg" pkg_installed ros-jazzy-nav2-bringup || VERIFY_FAIL=$((VERIFY_FAIL+1))
# SLAM Toolbox
verify "SLAM Toolbox pkg" pkg_installed ros-jazzy-slam-toolbox || VERIFY_FAIL=$((VERIFY_FAIL+1))
verify "AprilTag ROS pkg" pkg_installed ros-jazzy-apriltag-ros || VERIFY_FAIL=$((VERIFY_FAIL+1))
# foxglove_bridge
verify "foxglove_bridge pkg" pkg_installed ros-jazzy-foxglove-bridge || VERIFY_FAIL=$((VERIFY_FAIL+1))
# cloudflared
verify "cloudflared binary" command -v cloudflared || VERIFY_FAIL=$((VERIFY_FAIL+1))
# Node 22
verify "Node.js 22" bash -c 'node --version | grep -q "^v22\."' || VERIFY_FAIL=$((VERIFY_FAIL+1))
# Claude Code
verify "Claude Code CLI" command -v claude || VERIFY_FAIL=$((VERIFY_FAIL+1))
# dev user + sudo
verify "user dev exists" id "$DEV_USER" || VERIFY_FAIL=$((VERIFY_FAIL+1))
verify "dev has sudo NOPASSWD" \
    bash -c "grep -q '^${DEV_USER} ALL=(ALL) NOPASSWD:ALL' '$SUDOERS_FILE'" || VERIFY_FAIL=$((VERIFY_FAIL+1))
verify "dev bashrc has claude alias" \
    bash -c "grep -q 'alias claude=.*--dangerously-skip-permissions' '$BASHRC'" || VERIFY_FAIL=$((VERIFY_FAIL+1))
verify "dev bashrc sources ROS 2" \
    bash -c "grep -q '/opt/ros/jazzy/setup.bash' '$BASHRC'" || VERIFY_FAIL=$((VERIFY_FAIL+1))
# Workspace builds
for ws in "${WORKSPACES[@]}"; do
    verify "workspace $ws built (install/setup.bash)" \
        test -f "/workspace/$ws/install/setup.bash" || VERIFY_FAIL=$((VERIFY_FAIL+1))
done

echo ""
echo "============================================================"
if [[ $VERIFY_FAIL -eq 0 ]]; then
    echo "  ✓ setup_master.sh COMPLETE — all checks passed"
else
    echo "  ! setup_master.sh finished with $VERIFY_FAIL failed check(s)"
    echo "  See $LOG for details."
fi
echo "  $(date)"
echo "============================================================"
exit $VERIFY_FAIL
