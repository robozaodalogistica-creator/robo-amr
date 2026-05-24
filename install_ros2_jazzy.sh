#!/bin/bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
LOG=/workspace/install.log
exec > >(tee -a "$LOG") 2>&1

echo "============================================"
echo "  ROS 2 Jazzy + Gazebo Harmonic + Nav2 + SLAM"
echo "  $(date)"
echo "============================================"

# ── 1. Locale ────────────────────────────────────────────────────────────────
echo "[1/7] Configurando locale..."
apt-get update -qq
apt-get install -y -qq locales curl gnupg software-properties-common lsb-release wget
locale-gen en_US en_US.UTF-8
update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
export LANG=en_US.UTF-8

# ── 2. Repositórios ───────────────────────────────────────────────────────────
echo "[2/7] Adicionando repositórios ROS 2 e Gazebo..."
add-apt-repository -y universe

# ROS 2 Jazzy
curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
  -o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] \
http://packages.ros.org/ros2/ubuntu $(lsb_release -cs) main" \
  > /etc/apt/sources.list.d/ros2.list

# Gazebo Harmonic
curl -sSL https://packages.osrfoundation.org/gazebo.gpg \
  -o /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] \
http://packages.osrfoundation.org/gazebo/ubuntu-stable $(lsb_release -cs) main" \
  > /etc/apt/sources.list.d/gazebo-stable.list

apt-get update -qq

# ── 3. Ferramentas base + ROS 2 Jazzy Desktop ─────────────────────────────────
echo "[3/7] Instalando ROS 2 Jazzy Desktop + ferramentas..."
apt-get install -y -qq \
  python3-pip \
  python3-vcstool \
  python3-colcon-common-extensions \
  python3-rosdep \
  build-essential \
  git \
  ros-jazzy-desktop \
  ros-dev-tools

# ── 4. Gazebo Harmonic ────────────────────────────────────────────────────────
echo "[4/7] Instalando Gazebo Harmonic..."
apt-get install -y -qq \
  gz-harmonic \
  ros-jazzy-ros-gz \
  ros-jazzy-ros-gz-bridge \
  ros-jazzy-ros-gz-sim

# ── 5. Nav2 ───────────────────────────────────────────────────────────────────
echo "[5/7] Instalando Nav2..."
apt-get install -y -qq \
  ros-jazzy-navigation2 \
  ros-jazzy-nav2-bringup \
  ros-jazzy-nav2-msgs \
  ros-jazzy-nav2-rviz-plugins

# ── 6. SLAM Toolbox ───────────────────────────────────────────────────────────
echo "[6/7] Instalando SLAM Toolbox..."
apt-get install -y -qq \
  ros-jazzy-slam-toolbox \
  ros-jazzy-apriltag-ros \
  ros-jazzy-image-proc

# ── 7. TurtleBot3 + extras ────────────────────────────────────────────────────
echo "[7/7] Instalando TurtleBot3..."
apt-get install -y -qq \
  ros-jazzy-turtlebot3 \
  ros-jazzy-turtlebot3-msgs \
  ros-jazzy-turtlebot3-simulations \
  ros-jazzy-turtlebot3-gazebo \
  ros-jazzy-rviz2 \
  ros-jazzy-robot-state-publisher \
  ros-jazzy-joint-state-publisher \
  ros-jazzy-xacro \
  ros-jazzy-tf2-tools

# ── rosdep ────────────────────────────────────────────────────────────────────
echo "[+] Inicializando rosdep..."
rosdep init 2>/dev/null || true
rosdep update

# ── Profile ───────────────────────────────────────────────────────────────────
echo "[+] Configurando /etc/profile.d/ros2.sh..."
cat > /etc/profile.d/ros2.sh << 'EOF'
source /opt/ros/jazzy/setup.bash
export TURTLEBOT3_MODEL=burger
EOF

# ── Workspace tb3_nav_demo ────────────────────────────────────────────────────
echo "[+] Criando workspace tb3_nav_demo..."
source /opt/ros/jazzy/setup.bash
mkdir -p /workspace/tb3_nav_demo/src/tb3_waypoint_nav/tb3_waypoint_nav

cat > /workspace/tb3_nav_demo/src/tb3_waypoint_nav/tb3_waypoint_nav/__init__.py << 'PYEOF'
PYEOF

cat > /workspace/tb3_nav_demo/src/tb3_waypoint_nav/tb3_waypoint_nav/waypoint_navigator.py << 'PYEOF'
#!/usr/bin/env python3
"""TurtleBot3 autonomous waypoint navigator — 5 waypoints via Nav2 FollowWaypoints."""
import math
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from nav2_msgs.action import FollowWaypoints
from geometry_msgs.msg import PoseStamped

WAYPOINTS = [
    ( 1.0,  0.0,  0.0),
    ( 1.0,  1.0,  math.pi / 2),
    ( 0.0,  1.0,  math.pi),
    (-1.0,  0.0, -math.pi / 2),
    ( 0.0,  0.0,  0.0),
]

def make_pose(x, y, yaw):
    p = PoseStamped()
    p.header.frame_id = "map"
    p.pose.position.x = x
    p.pose.position.y = y
    p.pose.orientation.z = math.sin(yaw / 2)
    p.pose.orientation.w = math.cos(yaw / 2)
    return p

class WaypointNavigator(Node):
    def __init__(self):
        super().__init__("waypoint_navigator")
        self._ac = ActionClient(self, FollowWaypoints, "follow_waypoints")
        self.get_logger().info("Aguardando servidor FollowWaypoints...")
        self._ac.wait_for_server()
        self.get_logger().info("Servidor pronto. Enviando 5 waypoints...")
        goal = FollowWaypoints.Goal()
        goal.poses = [make_pose(*wp) for wp in WAYPOINTS]
        f = self._ac.send_goal_async(goal, feedback_callback=self._on_feedback)
        f.add_done_callback(self._on_goal)

    def _on_goal(self, f):
        h = f.result()
        if not h.accepted:
            self.get_logger().error("Goal rejeitado!")
            return
        self.get_logger().info("Navegando...")
        h.get_result_async().add_done_callback(self._on_result)

    def _on_feedback(self, fb):
        idx = fb.feedback.current_waypoint
        self.get_logger().info(f"Waypoint {idx + 1}/{len(WAYPOINTS)}")

    def _on_result(self, f):
        missed = f.result().result.missed_waypoints
        if missed:
            self.get_logger().warn(f"Waypoints perdidos: {missed}")
        else:
            self.get_logger().info("Todos os 5 waypoints concluídos!")
        rclpy.shutdown()

def main():
    rclpy.init()
    rclpy.spin(WaypointNavigator())

if __name__ == "__main__":
    main()
PYEOF

cat > /workspace/tb3_nav_demo/src/tb3_waypoint_nav/setup.py << 'PYEOF'
from setuptools import setup
setup(
    name="tb3_waypoint_nav",
    version="0.1.0",
    packages=["tb3_waypoint_nav"],
    install_requires=["setuptools"],
    entry_points={
        "console_scripts": [
            "waypoint_navigator = tb3_waypoint_nav.waypoint_navigator:main",
        ],
    },
)
PYEOF

cat > /workspace/tb3_nav_demo/src/tb3_waypoint_nav/package.xml << 'PYEOF'
<?xml version="1.0"?>
<package format="3">
  <name>tb3_waypoint_nav</name>
  <version>0.1.0</version>
  <description>TurtleBot3 autonomous waypoint navigation — 5 waypoints</description>
  <maintainer email="dev@example.com">dev</maintainer>
  <license>Apache-2.0</license>
  <exec_depend>rclpy</exec_depend>
  <exec_depend>nav2_msgs</exec_depend>
  <exec_depend>geometry_msgs</exec_depend>
  <buildtool_depend>ament_python</buildtool_depend>
  <export><build_type>ament_python</build_type></export>
</package>
PYEOF

cd /workspace/tb3_nav_demo
colcon build --symlink-install

cat > /workspace/tb3_nav_demo/README.md << 'EOF'
# tb3_nav_demo

TurtleBot3 navegando autonomamente em 5 waypoints usando ROS 2 Jazzy + Nav2.

## Como usar (3 terminais)

### Terminal 1 — Simulação Gazebo
```bash
source /opt/ros/jazzy/setup.bash
export TURTLEBOT3_MODEL=burger
ros2 launch turtlebot3_gazebo turtlebot3_world.launch.py
```

### Terminal 2 — Nav2 Navigation Stack
```bash
source /opt/ros/jazzy/setup.bash
export TURTLEBOT3_MODEL=burger
ros2 launch turtlebot3_navigation2 navigation2.launch.py \
  use_sim_time:=True \
  map:=/opt/ros/jazzy/share/turtlebot3_gazebo/maps/map.yaml
```

### Terminal 3 — Waypoint Navigator
```bash
source /opt/ros/jazzy/setup.bash
source /workspace/tb3_nav_demo/install/setup.bash
ros2 run tb3_waypoint_nav waypoint_navigator
```

## Waypoints (frame: map)
| # | X    | Y    | Yaw      |
|---|------|------|----------|
| 1 | 1.0  | 0.0  | 0°       |
| 2 | 1.0  | 1.0  | 90°      |
| 3 | 0.0  | 1.0  | 180°     |
| 4 | -1.0 | 0.0  | -90°     |
| 5 | 0.0  | 0.0  | 0° (home)|
EOF

echo ""
echo "============================================"
echo "  INSTALAÇÃO CONCLUÍDA — $(date)"
echo "============================================"
source /opt/ros/jazzy/setup.bash
echo "ROS 2: $(ros2 --version 2>&1)"
gz sim --version 2>/dev/null | head -2 || echo "Gazebo: instalado (gz-harmonic)"
python3 -c "import slam_toolbox; print('SLAM Toolbox: OK')" 2>/dev/null \
  || echo "SLAM Toolbox: instalado via apt"
echo ""
echo "Workspace: /workspace/tb3_nav_demo"
echo "Documentação: /workspace/tb3_nav_demo/README.md"
