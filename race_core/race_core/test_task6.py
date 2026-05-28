#!/usr/bin/env python3
"""独立测试任务六：踢球
前提：Gazebo + cyberdog_control + pose_broadcaster 已运行，football3 在场景中

用法：
  gz model -m robot -x 1.5 -y 12.0 -z 0.5 -Y 3.1416   # 传送到足球区面朝西
  source /opt/ros/galactic/setup.bash && source /home/cyberdog_sim/install/setup.bash
  python3 test_task6.py
"""
import sys, time, rclpy

sys.path.append('/home/cyberdog_utils')
from move.driver.dog import Dog
from move.core.types import GAIT_TROT_10V5
from task6 import Task6_KickBall
from geometry_msgs.msg import PoseStamped
from rclpy.qos import qos_profile_sensor_data


def main():
    rclpy.init()
    node = rclpy.create_node("test_task6")

    print("正在连接底盘...")
    dog = Dog(gait=GAIT_TROT_10V5, step_height=0.08)
    dog.stand()
    time.sleep(2.0)

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

    task = Task6_KickBall(dog, node.get_logger())
    while rclpy.ok():
        rclpy.spin_once(node, timeout_sec=0.05)
        if task.execute(p_data):
            break
        time.sleep(0.05)

    print("✅ 任务六测试完成！")
    dog.stop()
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
