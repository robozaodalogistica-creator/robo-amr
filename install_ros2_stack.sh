#!/bin/bash
set -euo pipefail
LOG=/workspace/install.log
exec > >(tee -a "$LOG") 2>&1

echo "======================================================"
echo " ROS 2 Jazzy + Gazebo Harmonic + Nav2 + SLAM Toolbox"
echo " Started: $(date)"
echo "======================================================"

export DEBIAN_FRONTEND=noninteractive

# ── 1. System base ────────────────────────────────────────
echo "[1/7] Updating system..."
apt-get update -q
apt-get upgrade -yq --no-install-recommends
apt-get install -yq --no-install-recommends \
    curl gnupg2 lsb-release software-properties-common \
    ca-certificates locales build-essential git wget \
    python3-pip python3-venv python3-colcon-common-extensions \
    python3-rosdep python3-vcstool python3-argcomplete \
    python3-flake8 python3-pytest-cov

locale-gen en_US.UTF-8
update-locale LANG=en_US.UTF-8

# ── 2. ROS 2 Jazzy repository ─────────────────────────────
echo "[2/7] Adding ROS 2 Jazzy repository..."
curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
    -o /usr/share/keyrings/ros-archive-keyring.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] \
http://packages.ros.org/ros2/ubuntu $(lsb_release -cs) main" \
    > /etc/apt/sources.list.d/ros2.list

apt-get update -q

# ── 3. ROS 2 Jazzy Desktop + dev tools ───────────────────
echo "[3/7] Installing ROS 2 Jazzy Desktop..."
apt-get install -yq --no-install-recommends \
    ros-jazzy-desktop \
    ros-jazzy-ros-base \
    ros-jazzy-rmw-cyclonedds-cpp \
    ros-dev-tools

# ── 4. Gazebo Harmonic ────────────────────────────────────
echo "[4/7] Installing Gazebo Harmonic..."
curl -sSL https://packages.osrfoundation.org/gazebo.gpg \
    -o /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] \
http://packages.osrfoundation.org/gazebo/ubuntu-stable $(lsb_release -cs) main" \
    > /etc/apt/sources.list.d/gazebo-stable.list

apt-get update -q
apt-get install -yq --no-install-recommends \
    gz-harmonic \
    ros-jazzy-ros-gz \
    ros-jazzy-ros-gz-bridge \
    ros-jazzy-ros-gz-sim \
    ros-jazzy-ros-gz-image

# ── 5. Nav2 ───────────────────────────────────────────────
echo "[5/7] Installing Nav2..."
apt-get install -yq --no-install-recommends \
    ros-jazzy-navigation2 \
    ros-jazzy-nav2-bringup \
    ros-jazzy-nav2-minimal-tb3-sim \
    ros-jazzy-nav2-minimal-tb4-sim \
    ros-jazzy-nav2-simple-commander \
    ros-jazzy-nav2-mppi-controller \
    ros-jazzy-nav2-velocity-smoother \
    ros-jazzy-nav2-constrained-smoother \
    ros-jazzy-nav2-collision-monitor \
    ros-jazzy-nav2-behavior-tree \
    ros-jazzy-nav2-msgs

# ── 6. SLAM Toolbox ───────────────────────────────────────
echo "[6/7] Installing SLAM Toolbox..."
apt-get install -yq --no-install-recommends \
    ros-jazzy-slam-toolbox \
    ros-jazzy-cartographer \
    ros-jazzy-cartographer-ros \
    ros-jazzy-rtabmap \
    ros-jazzy-rtabmap-ros

# ── 7. rosdep init + workspace skeleton ──────────────────
echo "[7/7] Setting up rosdep and /workspace..."
if [ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]; then
    rosdep init
fi
rosdep update

# Workspace skeleton
mkdir -p /workspace/src

cat > /workspace/setup.bash << 'EOF'
#!/bin/bash
source /opt/ros/jazzy/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export RCUTILS_COLORIZED_OUTPUT=1
[ -f /workspace/install/setup.bash ] && source /workspace/install/setup.bash
EOF
chmod +x /workspace/setup.bash

# Convenience alias file
cat > /workspace/aliases.bash << 'EOF'
alias cb='cd /workspace && colcon build --symlink-install'
alias cs='source /workspace/setup.bash'
alias cbt='colcon build --symlink-install --packages-select'
alias ros='ros2'
EOF

# ── Version report ────────────────────────────────────────
echo ""
echo "======================================================"
echo " INSTALLATION COMPLETE — $(date)"
echo "======================================================"
echo ""
echo "--- ROS 2 ---"
source /opt/ros/jazzy/setup.bash
ros2 --version 2>/dev/null || true
echo ""
echo "--- Gazebo ---"
gz sim --version 2>/dev/null || gz --version 2>/dev/null || true
echo ""
echo "--- Nav2 packages ---"
dpkg -l | grep ros-jazzy-nav2 | awk '{print $2, $3}' | head -20
echo ""
echo "--- SLAM Toolbox ---"
dpkg -l | grep ros-jazzy-slam-toolbox | awk '{print $2, $3}'
echo ""
echo "To get started:"
echo "  source /workspace/setup.bash"
echo "  source /workspace/aliases.bash"
echo "======================================================"
