#!/usr/bin/env python3
import sys
import math
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Vector3, PoseStamped
import time

# ==========================================
# 挂载队友工具库
# ==========================================
sys.path.append('/usr/local/lib/python3.8/site-packages')
sys.path.append('/usr/local/lib/python3/dist-packages')
sys.path.append('/home/cyberdog_utils')

try:
    from move.driver.dog import Dog
    from move.core.types import GAIT_TROT_10V5
except ImportError as e:
    print(f"❌ 挂载底盘部件失败: {e}")
    sys.exit(1)

# 使用绝对路径导入你的任务
from race_core.tasks import Task1_StonePath

def quat_to_yaw(q):
    """四元数转欧拉角(Yaw)工具函数"""
    siny = 2.0 * (q.w * q.z + q.x * q.y)
    cosy = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny, cosy)

class GlobalBrain(Node):
    def __init__(self):
        super().__init__('global_brain')
        
        # 订阅视觉和位姿
        self.create_subscription(Vector3, '/perception/yellow_line', self.line_cb, 10)
        # 🌟 里程计修好了，直接订阅队友的 /pose 拿坐标和角度！
        self.create_subscription(PoseStamped, '/pose', self.pose_cb, 10)
        
        # 🌟【第一性原理修复】：必须补齐 cx 和 cy 的坑位！
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
        
        self.task1 = Task1_StonePath(self.dog, self.get_logger())
        
        self.sys_state = "INIT_STAND"
        self.stand_start_time = 0.0
        self.timer = self.create_timer(0.1, self.fsm_loop)
        self.get_logger().info("🧠 全局多任务主控大脑就绪！")

    def line_cb(self, msg):
        self.perception_data['line_error'] = msg.x
        self.perception_data['hard_turn'] = msg.y    
        self.perception_data['line_z'] = msg.z  

    def pose_cb(self, msg):
        # 🌟 实时将坐标和偏航角塞进字典，供 Task1 提取！
        self.perception_data['current_yaw'] = quat_to_yaw(msg.pose.orientation)
        self.perception_data['cx'] = msg.pose.position.x
        self.perception_data['cy'] = msg.pose.position.y

    def fsm_loop(self):
        if self.sys_state == "INIT_STAND":
            self.dog.stand()
            self.get_logger().info("🐕 起立...")
            self.stand_start_time = time.time()
            self.sys_state = "WAIT_STAND"
            
        elif self.sys_state == "WAIT_STAND":
            if time.time() - self.stand_start_time > 4.0:
                self.get_logger().info("✅ 狗已站稳！启动赛段任务状态机。")
                self.sys_state = "RUNNING_TASKS"
                
        elif self.sys_state == "RUNNING_TASKS":
            is_task_done = self.task1.execute(self.perception_data)
            if is_task_done:
                self.get_logger().info("🏁 任务一圆满完成！安全停车。")
                self.dog.stop()
                self.timer.cancel()

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