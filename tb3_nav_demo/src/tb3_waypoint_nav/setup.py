import os
from glob import glob
from setuptools import setup

package_name = 'tb3_waypoint_nav'

setup(
    name=package_name,
    version='1.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
        (os.path.join('share', package_name, 'maps'), glob('maps/*')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='dev',
    maintainer_email='dev@example.com',
    description='TurtleBot3 5-waypoint navigation demo',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'waypoint_navigator = tb3_waypoint_nav.waypoint_navigator:main',
            'waypoint_monitor   = tb3_waypoint_nav.waypoint_monitor:main',
            'robot_sim          = tb3_waypoint_nav.robot_sim:main',
        ],
    },
)
