# rlai_logistics

Galp warehouse pallet mission package.

This first version sequences fixed map-frame poses:

1. Navigate to a pallet pose with Nav2.
2. Raise the simulated fork through `/fork_lift_controller/commands`.
3. Navigate to the delivery pose.
4. Lower the fork and continue.

By default the mission uses Nav2-safe staging poses and does not physically
carry pallets. Launch with `enable_gazebo_attach:=true` to publish Gazebo
`DetachableJoint` attach/detach commands on `/pallet_N/attach` and
`/pallet_N/detach`, after starting the opt-in attach world with
`detachable_pallets_enabled:=true`. Keep this disabled until docking poses
place the fork under the pallet; AprilTags own that fine alignment layer.

## Smoke Test

```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash

MAP=$(ros2 pkg prefix rlai_mapping)/share/rlai_mapping/maps/galp_amr.yaml

ros2 launch rlai_bringup simulation.launch.py \
  world:=galp_amr \
  headless:=true \
  use_amcl:=true \
  map_yaml_file:=$MAP \
  camera_processing_enabled:=false

ros2 launch rlai_navigation navigation.launch.py
ros2 launch rlai_logistics logistics_mission.launch.py
```

## Optional Gazebo Attach/Detach

```bash
ros2 launch rlai_bringup simulation.launch.py \
  world:=galp_amr_attach \
  headless:=true \
  use_amcl:=true \
  map_yaml_file:=$MAP \
  detachable_pallets_enabled:=true \
  camera_processing_enabled:=false

ros2 launch rlai_logistics logistics_mission.launch.py \
  enable_gazebo_attach:=true
```

The Gazebo side is configured in `galp_amr_attach.sdf`, `robot.urdf.xacro`, and
`ros_gz_bridge.yaml`. Direct smoke test:

```bash
ros2 topic pub --times 3 --rate 2 /pallet_1/attach std_msgs/msg/Empty "{}"
gz topic -e -t /pallet_1/attach_state
ros2 topic pub --times 3 --rate 2 /pallet_1/detach std_msgs/msg/Empty "{}"
```
