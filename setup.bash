#!/bin/bash
set +u; source /opt/ros/jazzy/setup.bash; set -u
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export RCUTILS_COLORIZED_OUTPUT=1
[ -f /workspace/install/setup.bash ] && source /workspace/install/setup.bash
