# rlai_apriltag

AprilTag perception wrapper for pallet docking.

This package launches:

- `image_proc/rectify_node` for the simulated RGB-D camera image.
- `apriltag_ros/apriltag_node` configured for tag family `36h11`.

The detector is configured for one tag per pallet:

| Pallet | Tag ID | Frame |
|---|---:|---|
| `pallet_1` | 1 | `pallet_1_tag` |
| `pallet_2` | 2 | `pallet_2_tag` |
| `pallet_3` | 3 | `pallet_3_tag` |
| `pallet_4` | 4 | `pallet_4_tag` |

## Dependency

Install the ROS package before launching:

```bash
apt-get install -y ros-jazzy-apriltag-ros
```

`setup_master.sh` includes this dependency for fresh environments.

## Launch

```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash

ros2 launch rlai_bringup simulation.launch.py \
  world:=galp_amr \
  headless:=true \
  x:=-2.0 \
  y:=1.55 \
  yaw:=1.5708 \
  localization_enabled:=false \
  depth_camera_enabled:=true \
  camera_processing_enabled:=false \
  lidar_2d_enabled:=false \
  lidar_3d_enabled:=false \
  imu_enabled:=false \
  gps_enabled:=false

ros2 launch rlai_apriltag pallet_apriltag.launch.py

ros2 topic echo --once /apriltag/detections
```

## Simulation status

AprilTag textures have been generated and installed in
`rlai_gazebo/models/pallet_tags`, and both `galp_amr.sdf` and
`galp_amr_attach.sdf` render one tag board per pallet.

Runtime detection was validated on 2026-05-24 after rebooting the host and
switching the simulated tag boards to emissive texture maps. With the robot
spawned in front of `pallet_1`, `/apriltag/detections` reported tag ID `1` with
`hamming: 0` and decision margin around `235`.

The next step is to turn the detected tag pose into a fine docking command and
then enable Gazebo attach/detach in the mission flow.
