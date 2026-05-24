#!/usr/bin/env python3
"""从 /model_states 中提取 robot 位姿，转发到 /pose（无需调服务）。"""
import sys
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from gazebo_msgs.msg import ModelStates


class PoseBroadcaster(Node):
    def __init__(self, entity_name="robot"):
        super().__init__("pose_broadcaster")
        self.entity = entity_name
        self.pub = self.create_publisher(PoseStamped, "/pose", 10)
        self.sub = self.create_subscription(
            ModelStates, "/gazebo/model_states", self._cb, 10)
        self.get_logger().info(f"等待 /gazebo/model_states 中 '{entity_name}' 的位姿...")

    def _cb(self, msg: ModelStates):
        try:
            i = msg.name.index(self.entity)
        except ValueError:
            return
        out = PoseStamped()
        out.header.stamp = self.get_clock().now().to_msg()
        out.header.frame_id = "world"
        out.pose = msg.pose[i]
        self.pub.publish(out)


def main():
    rclpy.init()
    name = sys.argv[1] if len(sys.argv) > 1 else "robot"
    rclpy.spin(PoseBroadcaster(name))


if __name__ == "__main__":
    main()
