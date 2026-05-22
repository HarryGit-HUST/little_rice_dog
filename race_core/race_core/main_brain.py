#!/usr/bin/env python3
import sys
import math
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Vector3
from sensor_msgs.msg import Imu
import time

# 动态挂载
sys.path.append('/usr/local/lib/python3.8/site-packages')
sys.path.append('/usr/local/lib/python3/dist-packages')
sys.path.append('/home/cyberdog_utils')

try:
    from move.driver.dog import Dog
    from move.core.types import GAIT_TROT_10V5
except ImportError as e:
    print(f"❌ 挂载队友部件失败: {e}，请检查 /home/cyberdog_utils 目录是否存在！")
    sys.exit(1)

# 从同级目录的 tasks.py 导入任务类
from .tasks import Task1_StonePath

def quat_to_yaw(q):
    siny = 2.0 * (q.w * q.z + q.x * q.y)
    cosy = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny, cosy)

class GlobalBrain(Node):
    def __init__(self):
        super().__init__('global_brain')
        
        self.create_subscription(Vector3, '/perception/yellow_line', self.line_cb, 10)
        self.create_subscription(Imu, '/imu', self.imu_cb, 10)
        
        # 统一的数据总线格式
        self.perception_data = {
            'line_error': 0.0, 
            'hard_turn': 0.0, 
            'line_z': 0.0,        
            'current_yaw': None
        }
        
        self.get_logger().info("正在连接底盘...")
        self.dog = Dog(gait=GAIT_TROT_10V5, step_height=0.08)
        
        # 实例化从 tasks.py 导入的任务
        self.task1 = Task1_StonePath(self.dog, self.get_logger())
        
        self.sys_state = "INIT_STAND"
        self.stand_start_time = 0.0
        self.timer = self.create_timer(0.1, self.fsm_loop)
        self.get_logger().info("🧠 全局多任务主控大脑就绪！")

    def line_cb(self, msg):
        self.perception_data['line_error'] = msg.x
        self.perception_data['hard_turn'] = msg.y    
        self.perception_data['line_z'] = msg.z  

    def imu_cb(self, msg):
        self.perception_data['current_yaw'] = quat_to_yaw(msg.orientation)

    def fsm_loop(self):
        if self.sys_state == "INIT_STAND":
            self.dog.stand()
            self.get_logger().info("🐕 起立...")
            self.stand_start_time = time.time()
            self.sys_state = "WAIT_STAND"
            
        elif self.sys_state == "WAIT_STAND":
            if time.time() - self.stand_start_time > 4.0:
                self.get_logger().info("✅ 狗已站稳！启动赛段任务。")
                self.sys_state = "RUNNING_TASKS"
                
        elif self.sys_state == "RUNNING_TASKS":
            if self.task1.execute(self.perception_data):
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