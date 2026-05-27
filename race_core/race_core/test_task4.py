#!/usr/bin/env python3
"""独立测试任务四：深隧寻珍
前提：Gazebo 仿真 + cyberdog_control 已在运行

用法：
  # 1) 先传送到起点
  gz model -m robot -x 2.1 -y 7.3 -z 0.5 -Y 1.5708
  # 2) 运行测试
  python3 test_task4.py
"""
import sys
import time
import rclpy

sys.path.append('/home/cyberdog_utils')
from move.driver.dog import Dog
from move.core.types import GAIT_TROT_10V5
from task4 import Task4_TunnelTreasure


def main():
    rclpy.init()
    node = rclpy.create_node("test_task4")

    print("正在连接底盘...")
    dog = Dog(gait=GAIT_TROT_10V5, step_height=0.08)

    print("🐕 站立...")
    dog.stand()
    time.sleep(3.0)
    print("✅ 就绪，启动任务四！")

    task = Task4_TunnelTreasure(dog, node.get_logger())

    # 模拟简单 perception_data（task4 只用 cx, cy）
    p_data = {"cx": None, "cy": None}

    # 姿势回调，填 p_data
    from geometry_msgs.msg import PoseStamped
    from rclpy.qos import qos_profile_sensor_data

    def on_pose(msg):
        p_data["cx"] = msg.pose.position.x
        p_data["cy"] = msg.pose.position.y

    node.create_subscription(PoseStamped, "/pose", on_pose, qos_profile_sensor_data)

    # 等待首次 pose 到达
    t0 = time.time()
    while p_data["cx"] is None and rclpy.ok():
        rclpy.spin_once(node, timeout_sec=0.05)
        if time.time() - t0 > 10:
            print("❌ /pose 超时，请检查 pose_broadcaster")
            break

    print(f"📍 初始位置: ({p_data['cx']:.2f}, {p_data['cy']:.2f})")

    # 执行任务
    while rclpy.ok() and not task.is_done:
        rclpy.spin_once(node, timeout_sec=0.05)
        done = task.execute(p_data)
        if done:
            break
        time.sleep(0.05)

    print("✅ 任务四测试完成！")
    dog.stop()
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
