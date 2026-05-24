"""Launch AprilTag detection for pallet docking."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    pkg = FindPackageShare("rlai_apriltag")
    default_tag_config = PathJoinSubstitution(
        [pkg, "config", "pallet_tags_36h11.yaml"]
    )

    declared_args = [
        DeclareLaunchArgument(
            "use_sim_time",
            default_value="true",
            description="Use simulation (Gazebo) clock",
        ),
        DeclareLaunchArgument(
            "image_topic",
            default_value="/depth_camera/image_raw",
            description="RGB image topic used for AprilTag detection",
        ),
        DeclareLaunchArgument(
            "camera_info_topic",
            default_value="/depth_camera/camera_info",
            description="CameraInfo topic matching image_topic",
        ),
        DeclareLaunchArgument(
            "image_rect_topic",
            default_value="/depth_camera/image_rect",
            description="Rectified image topic consumed by apriltag_ros",
        ),
        DeclareLaunchArgument(
            "tag_config",
            default_value=default_tag_config,
            description="AprilTag detector YAML configuration",
        ),
    ]

    rectify_rgb = Node(
        package="image_proc",
        executable="rectify_node",
        name="depth_rgb_rectify",
        output="screen",
        parameters=[{"use_sim_time": LaunchConfiguration("use_sim_time")}],
        remappings=[
            ("image", LaunchConfiguration("image_topic")),
            ("camera_info", LaunchConfiguration("camera_info_topic")),
            ("image_rect", LaunchConfiguration("image_rect_topic")),
        ],
    )

    apriltag_detector = Node(
        package="apriltag_ros",
        executable="apriltag_node",
        name="pallet_apriltag",
        namespace="apriltag",
        output="screen",
        parameters=[
            LaunchConfiguration("tag_config"),
            {"use_sim_time": LaunchConfiguration("use_sim_time")},
        ],
        remappings=[
            ("/apriltag/image_rect", LaunchConfiguration("image_rect_topic")),
            ("/camera/camera_info", LaunchConfiguration("camera_info_topic")),
        ],
    )

    return LaunchDescription(declared_args + [rectify_rgb, apriltag_detector])
