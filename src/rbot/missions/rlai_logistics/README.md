# rlai_logistics

Galp warehouse pallet mission package.

This first version sequences fixed map-frame poses:

1. Navigate to a pallet pose with Nav2.
2. Raise the simulated fork through `/fork_lift_controller/commands`.
3. Navigate to the delivery pose.
4. Lower the fork and continue.

It does not yet attach the pallet model to the robot or use AprilTags for fine
docking. Those are the next layers after the end-to-end mission skeleton is
stable.

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
