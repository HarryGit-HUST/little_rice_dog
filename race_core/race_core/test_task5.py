#!/usr/bin/env python3
"""独立测试任务五：独木桥
前提：Gazebo + cyberdog_control + pose_broadcaster 已运行

用法：
  gz model -m robot -x 3.1 -y 7.3 -z 0.5 -Y -1.5708  # 传送到起点面朝西
  source /opt/ros/galactic/setup.bash && source /home/cyberdog_sim/install/setup.bash
  python3 test_task5.py
"""
import sys, time, rclpy

sys.path.append('/home/cyberdog_utils')
from move.driver.dog import Dog
from move.core.types import GAIT_TROT_10V5
from task5 import Task5_PlankBridge
from geometry_msgs.msg import PoseStamped
from rclpy.qos import qos_profile_sensor_data


def main():
    rclpy.init()
    node = rclpy.create_node("test_task5")

    print("正在连接底盘...")
    dog = Dog(gait=GAIT_TROT_10V5, step_height=0.08)
    dog.stand()
    time.sleep(2.0)
    print("✅ 就绪，启动任务五！")

    task = Task5_PlankBridge(dog, node.get_logger())
    p_data = {"cx": None, "cy": None}

    def on_pose(msg):
        p_data["cx"] = msg.pose.position.x
        p_data["cy"] = msg.pose.position.y

    node.create_subscription(PoseStamped, "/pose", on_pose, qos_profile_sensor_data)

    t0 = time.time()
    while p_data["cx"] is None and rclpy.ok():
        rclpy.spin_once(node, timeout_sec=0.05)
        if time.time() - t0 > 10:
            print("❌ /pose 超时")
            break

    print(f"📍 初始位置: ({p_data['cx']:.2f}, {p_data['cy']:.2f})")

    while rclpy.ok():
        rclpy.spin_once(node, timeout_sec=0.05)
        if task.execute(p_data):
            break
        time.sleep(0.05)

    print("✅ 任务五测试完成！")
    dog.stop()
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
