# /workspace — ROS 2 Jazzy dev environment

This directory holds the ROS 2 Jazzy + Gazebo Harmonic + Nav2 development
environment and three demo workspaces.

## Quick start

Provision (or re-provision) **everything** with a single command:

```bash
sudo /workspace/setup_master.sh
```

The script is **idempotent** — re-running it only installs or fixes what is
missing. It is safe to run it on a fresh container or to repair a partial
install. All output is also appended to `/workspace/setup_master.log`.

After it finishes, open a new shell as `dev` to pick up the configured
environment:

```bash
su - dev          # password: dev123
# ROS 2 is now sourced, claude is aliased with --dangerously-skip-permissions,
# and the three workspaces are sourced if they were built.
```

## What `setup_master.sh` does

| Step | What it installs / configures                                              |
|------|----------------------------------------------------------------------------|
| 0    | APT base tools, `en_US.UTF-8` locale, ROS 2 / Gazebo / NodeSource repos    |
| 1    | ROS 2 Jazzy Desktop + dev tools                                            |
| 2    | Gazebo Harmonic + `ros_gz` bridge                                          |
| 3    | Nav2 (bringup, MPPI, simple commander, behavior tree, …)                   |
| 4    | SLAM Toolbox, `foxglove_bridge`, TurtleBot3 sim                            |
| 5    | Node.js 22 + Claude Code (`@anthropic-ai/claude-code`, global)             |
| 6    | `cloudflared` (latest .deb from GitHub)                                    |
| 7    | User `dev` (password `dev123`), sudo NOPASSWD, `~/.bashrc` configured      |
| —    | `colcon build --symlink-install` for `amr_pallet`, `nav_test`, `tb3_nav_demo` |
| —    | Verification of every component above                                      |

### `dev` user `~/.bashrc` additions

The script writes a marker-delimited block to `/home/dev/.bashrc`:

- Sources `/opt/ros/jazzy/setup.bash`
- Sources each `/workspace/<ws>/install/setup.bash` if present
- Sets `TURTLEBOT3_MODEL=burger`, `RMW_IMPLEMENTATION=rmw_cyclonedds_cpp`
- `alias claude='claude --dangerously-skip-permissions'`
- `alias cb='colcon build --symlink-install'`
- `alias cbt='colcon build --symlink-install --packages-select'`

Re-running the script replaces the block in place — it does not stack.

## Workspaces

| Path                          | Purpose                                              |
|-------------------------------|------------------------------------------------------|
| `/workspace/amr_pallet`       | AMR pallet handling demo                             |
| `/workspace/nav_test`         | Nav2 integration tests                               |
| `/workspace/tb3_nav_demo`     | TurtleBot3 5-waypoint autonomous navigation demo     |

Each is built with `colcon build --symlink-install`. After build, sourcing
`/home/dev/.bashrc` (the default for the `dev` user) makes their packages
available via `ros2 run` / `ros2 launch`.

## Verifying manually

```bash
source /opt/ros/jazzy/setup.bash
ros2 pkg list | grep -E 'nav2_bringup|slam_toolbox|foxglove_bridge'
gz sim --version
node --version            # v22.x
claude --version
cloudflared --version
id dev && sudo -l -U dev
```

## Logs and exit codes

- Full log: `/workspace/setup_master.log` (appended on every run)
- Exit code `0` = all verification checks passed
- Non-zero = number of verification failures (inspect the log)

## Re-running selectively

The script has no flags — it always runs the full sequence. Because each step
checks state before acting, a second run on a healthy system finishes in
seconds and only re-runs `colcon build` (which is incremental anyway).
