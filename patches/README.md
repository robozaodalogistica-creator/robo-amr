# Patches

Out-of-tree patches against external repos used in this workspace.
Apply with `patch -p0 < patches/<name>.patch` from a clean checkout, or use
`git apply --directory=...` for git-tracked targets.

## `rbot-depth-camera-10hz.patch`

Lowers the `depth_camera` SDF `<update_rate>` from 30 Hz to 10 Hz in
`rbot/src/robot/rlai_description/urdf/gazebo/gazebo_sensors.urdf.xacro`.

**Why:** under Gazebo Harmonic with Ogre2 software rendering, the 30 Hz depth
stream (640x480 R_FLOAT32) was a major contributor to server-side GPU/CPU load.
B4 optimization in the GPU-acceleration workstream; combine with B1 (revert
`--headless-rendering` in `rlai_gazebo/launch/gazebo.launch.py`) when running
on Xorg + NVIDIA so the server uses GLX directly instead of EGL surfaceless.

Apply against the `rlxai/rbot` source tree (this workspace's `/workspace/rbot/`):

```
cd /workspace/rbot
patch -p0 < /workspace/patches/rbot-depth-camera-10hz.patch
```
