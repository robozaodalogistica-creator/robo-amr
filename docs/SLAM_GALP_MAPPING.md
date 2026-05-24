# SLAM Galp Mapping Notes

> Working note for regenerating the `galp_amr` occupancy map from Gazebo SLAM.
> The tracked production map was not replaced by the first candidate.

## Current result

On 2026-05-23, the SLAM stack was launched against `world:=galp_amr` in
headless mode and produced candidate maps under `/tmp`:

- `/tmp/robo_amr_slam/maps/galp_amr_slam_candidate.yaml`
- `/tmp/robo_amr_slam/maps/galp_amr_slam_candidate.pgm`
- `/tmp/robo_amr_slam_center/maps/galp_amr_center_spin.yaml`
- `/tmp/robo_amr_slam_center/maps/galp_amr_center_spin.pgm`

The best candidate was still not better than the tracked map in
`src/rbot/mapping/rlai_mapping/maps/galp_amr.*`, so the tracked map remains in
place.

## Repeat the run

From the repo root:

```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash

bash scripts/generate_galp_slam_candidate.sh
```

Useful overrides:

```bash
OUT_DIR=/tmp/robo_amr_slam/maps \
OUT_NAME=galp_amr_slam_candidate \
START_X=1.0 START_Y=1.0 START_YAW=0.0 \
bash scripts/generate_galp_slam_candidate.sh
```

Rendering note: on the current machine, forcing Mesa software rendering made
Gazebo crash inside the sensor render thread. The script defaults to NVIDIA
EGL (`RENDER_BACKEND=nvidia`) because that path kept Gazebo, `/scan`, `/map`,
controllers, and `slam_toolbox` alive.

## Key finding

The simulated empty pallets are lower than the 2D LiDAR scan plane:

- `base_footprint -> base_link` raises `base_link` by `0.0625 m`.
- `lidar_2d_link` is mounted at `z=0.18 m` relative to `base_link`.
- Effective LiDAR scan height is about `0.2425 m`.
- `galp_amr.sdf` pallets are `0.15 m` tall.

That means the 2D LiDAR scans above the empty pallets. A SLAM-generated map
from `/scan` should be expected to capture the warehouse shell and taller
fixtures, but not the low empty pallet decks.

## Implication

This is probably correct for docking work, because the pickup pallet should
not behave like a permanent wall in the global map. It does mean pallet
handling needs its own layer:

- AprilTag/depth-camera docking for final approach.
- Optional local costmap/perception handling for pallet bodies.
- A deliberate decision on whether global maps should include only static
warehouse structure or also known pallet/storage zones.

Until that decision is made, do not replace `galp_amr.yaml` with the generated
candidate map just because it came from SLAM.

## Next technical step

Proceed with AprilTag docking and use the generated structural map only as a
candidate/reference. Once docking can place the fork under the pallet, rerun
the mission with:

```bash
world:=galp_amr_attach
detachable_pallets_enabled:=true
enable_gazebo_attach:=true
```
