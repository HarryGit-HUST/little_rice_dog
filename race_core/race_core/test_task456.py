#!/usr/bin/env python3
"""串联测试任务四→五→六
前提：Gazebo + cyberdog_control + pose_broadcaster 已运行，football3 在场景中

用法：
  gz model -m robot -x 2.1 -y 7.3 -z 0.5 -Y 1.5708   # 传送到任务四起点
  source /opt/ros/galactic/setup.bash && source /home/cyberdog_sim/install/setup.bash
  python3 test_task456.py
"""
import sys, time, rclpy

sys.path.append('/home/cyberdog_utils')
from move.driver.dog import Dog
from move.core.types import GAIT_TROT_10V5
from task4 import Task4_TunnelTreasure
from task5 import Task5_PlankBridge
from task6 import Task6_KickBall
from geometry_msgs.msg import PoseStamped
from rclpy.qos import qos_profile_sensor_data


def run_task(node, dog, task_cls, name, p_data):
    print(f"\n{'='*50}")
    print(f"  开始 {name}")
    print(f"{'='*50}")
    task = task_cls(dog, node.get_logger())
    while rclpy.ok():
        rclpy.spin_once(node, timeout_sec=0.05)
        if task.execute(p_data):
            break
        time.sleep(0.05)
    print(f"✅ {name} 完成！")


def main():
    rclpy.init()
    node = rclpy.create_node("test_task456")

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

    run_task(node, dog, Task4_TunnelTreasure, "任务四：深隧寻珍", p_data)
    run_task(node, dog, Task5_PlankBridge, "任务五：独木桥", p_data)
    run_task(node, dog, Task6_KickBall, "任务六：踢球", p_data)

    print("\n🎉 任务四→五→六 全部通关！")
    dog.stop()
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
