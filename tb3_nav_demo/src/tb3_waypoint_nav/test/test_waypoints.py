"""Unit tests for waypoint geometry — no ROS runtime required."""
import math
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tb3_waypoint_nav.waypoint_navigator import WAYPOINTS, make_pose


def test_waypoint_count():
    assert len(WAYPOINTS) == 5, f"Expected 5 waypoints, got {len(WAYPOINTS)}"


def test_last_waypoint_is_origin():
    last = WAYPOINTS[-1]
    assert abs(last["x"]) < 1e-6 and abs(last["y"]) < 1e-6, \
        "Last waypoint should return to origin (0, 0)"


def test_pose_orientation_normalised():
    """Quaternion from yaw must be unit length."""
    for wp in WAYPOINTS:
        p = make_pose(wp["x"], wp["y"], wp["yaw"])
        q = p.pose.orientation
        norm = math.sqrt(q.x**2 + q.y**2 + q.z**2 + q.w**2)
        assert abs(norm - 1.0) < 1e-6, \
            f"Quaternion not normalised for {wp['name']}: norm={norm}"


def test_pose_position_matches_waypoint():
    for wp in WAYPOINTS:
        p = make_pose(wp["x"], wp["y"], wp["yaw"])
        assert abs(p.pose.position.x - wp["x"]) < 1e-9
        assert abs(p.pose.position.y - wp["y"]) < 1e-9


def test_pose_frame_is_map():
    for wp in WAYPOINTS:
        p = make_pose(wp["x"], wp["y"], wp["yaw"])
        assert p.header.frame_id == "map", \
            f"Expected frame 'map', got '{p.header.frame_id}'"


def test_yaw_roundtrip():
    """Encode yaw to quaternion and back, within 1e-6 rad."""
    for wp in WAYPOINTS:
        yaw_in = wp["yaw"]
        p = make_pose(0.0, 0.0, yaw_in)
        q = p.pose.orientation
        siny = 2.0 * (q.w * q.z + q.x * q.y)
        cosy = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
        yaw_out = math.atan2(siny, cosy)
        assert abs(yaw_out - yaw_in) < 1e-6, \
            f"Yaw roundtrip failed for {wp['name']}: {yaw_in:.4f} → {yaw_out:.4f}"


if __name__ == "__main__":
    tests = [
        test_waypoint_count,
        test_last_waypoint_is_origin,
        test_pose_orientation_normalised,
        test_pose_position_matches_waypoint,
        test_pose_frame_is_map,
        test_yaw_roundtrip,
    ]
    passed = failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {t.__name__}: {e}")
            failed += 1
    print(f"\n{passed}/{passed+failed} tests passed")
    sys.exit(0 if failed == 0 else 1)
