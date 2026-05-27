#!/usr/bin/env python3
import sys
import math
import rclpy
from rclpy.qos import qos_profile_sensor_data
from rclpy.node import Node
from geometry_msgs.msg import Vector3, PoseStamped
from sensor_msgs.msg import Imu
import time

sys.path.append('/usr/local/lib/python3.8/site-packages')
sys.path.append('/usr/local/lib/python3/dist-packages')
sys.path.append('/home/cyberdog_utils')

try:
    from move.driver.dog import Dog
    from move.core.types import GAIT_TROT_10V5
except ImportError as e:
    print(f"❌ 挂载底盘部件失败: {e}")
    sys.exit(1)

# 🌟 引入你的四大天王任务模块
from race_core.tasks import Task1_StonePath
from race_core.task2 import Task2_MockWildPearl
from race_core.task3 import Task3_CurveCharge
from race_core.task4 import Task4_TunnelTreasure

def quat_to_yaw(q):
    siny = 2.0 * (q.w * q.z + q.x * q.y)
    cosy = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny, cosy)

class GlobalBrain(Node):
    def __init__(self):
        super().__init__('global_brain')
        
        self.create_subscription(Vector3, '/perception/yellow_line', self.line_cb, 10)
# 统一使用 sensor_data QoS 以匹配 Gazebo 底层传感器
        self.create_subscription(PoseStamped, '/pose', self.pose_cb, qos_profile_sensor_data)
        self.create_subscription(Imu, '/imu', self.imu_cb, qos_profile_sensor_data)
        
        self.perception_data = {
            'line_error': 0.0, 
            'hard_turn': 0.0, 
            'line_z': 0.0,        
            'current_yaw': None,
            'cx': None,
            'cy': None
        }
        
        self.get_logger().info("正在连接底盘...")
        self.dog = Dog(gait=GAIT_TROT_10V5, step_height=0.08)
        
        # 🌟 注册所有比赛任务
        self.task_list = {
            1: Task1_StonePath(self.dog, self.get_logger()),
            2: Task2_MockWildPearl(self.dog, self.get_logger()),
            3: Task3_CurveCharge(self.dog, self.get_logger()),
            4: Task4_TunnelTreasure(self.dog, self.get_logger())
        }
        self.current_task_id = 1
        
        self.sys_state = "INIT_STAND"
        self.stand_start_time = 0.0
        self.timer = self.create_timer(0.1, self.fsm_loop)
        self.get_logger().info("🧠 全局四任务主控大脑就绪！")

    def line_cb(self, msg):
        self.perception_data['line_error'] = msg.x
        self.perception_data['hard_turn'] = msg.y    
        self.perception_data['line_z'] = msg.z  

    def pose_cb(self, msg):
        self.perception_data['current_yaw'] = quat_to_yaw(msg.pose.orientation)
        self.perception_data['cx'] = msg.pose.position.x
        self.perception_data['cy'] = msg.pose.position.y

    def imu_cb(self, msg):
        pass 

    def fsm_loop(self):
        if self.sys_state == "INIT_STAND":
            self.dog.stand()
            self.get_logger().info("🐕 起立...")
            self.stand_start_time = time.time()
            self.sys_state = "WAIT_STAND"
            
        elif self.sys_state == "WAIT_STAND":
            if time.time() - self.stand_start_time > 4.0:
                self.get_logger().info("✅ 狗已站稳！启动赛段任务流转。")
                self.sys_state = "RUNNING_TASKS"
                
        elif self.sys_state == "RUNNING_TASKS":
            current_task = self.task_list.get(self.current_task_id)
            
            if current_task is None:
                self.get_logger().info("🎉 所有 4 个可用赛段已经通关！自动泊车。")
                self.dog.stop()
                self.timer.cancel()
                return
                
            is_task_done = current_task.execute(self.perception_data)
            
            if is_task_done:
                self.get_logger().info(f"🏆 赛段 {self.current_task_id} 结束，切入赛段 {self.current_task_id + 1}...")
                self.current_task_id += 1

def main():
    rclpy.init()
    node = GlobalBrain()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.dog.stop()
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()