#!/usr/bin/env python3
import sys
import math
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Vector3, PoseStamped
import time

# 动态挂载
sys.path.append('/usr/local/lib/python3.8/site-packages')
sys.path.append('/usr/local/lib/python3/dist-packages')
sys.path.append('/home/cyberdog_utils')

try:
    from move.driver.dog import Dog
    from move.core.types import GAIT_TROT_10V5
except ImportError as e:
    print(f"❌ 挂载队友部件失败: {e}")
    sys.exit(1)

# 导入刚才剥离出去的任务模块
from .tasks import Task1_StonePath

def quat_to_yaw(q):
    siny = 2.0 * (q.w * q.z + q.x * q.y)
    cosy = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny, cosy)

class GlobalBrain(Node):
    def __init__(self):
        super().__init__('global_brain')
        
        # 订阅视觉与底盘定位
        self.sub_line = self.create_subscription(Vector3, '/perception/yellow_line', self.line_cb, 10)
        self.sub_pose = self.create_subscription(PoseStamped, '/pose', self.pose_cb, 10)
        
        # 全局状态总线 (新增 cx, cy 实时坐标)
        self.perception_data = {
            'line_error': 0.0, 
            'hard_turn': 0.0, 
            'line_valid': False, 
            'current_yaw': None,
            'cx': 0.0,
            'cy': 0.0
        }
        
        # 初始化底盘组件 (步态 Trot, 步高 8cm 过石板)
        self.get_logger().info("正在连接底盘...")
        self.dog = Dog(gait=GAIT_TROT_10V5, step_height=0.08)
        
        # 注册并挂载任务
        self.task_list = {
            1: Task1_StonePath(self.dog, self.get_logger()),
            2: None # 🌟 待填空：把队友B写的“荒野寻珠”状态机类挂载在这里！
        }
        
        self.current_task_id = 1
        self.sys_state = "INIT_STAND"
        self.stand_start_time = 0.0
        
        self.timer = self.create_timer(0.1, self.fsm_loop)
        self.get_logger().info("🧠 全局多任务主控大脑启动完毕！")

    def line_cb(self, msg):
        self.perception_data['line_error'] = msg.x
        self.perception_data['hard_turn'] = msg.y    
        self.perception_data['line_valid'] = (msg.z > 0.5)

    def pose_cb(self, msg):
        self.perception_data['current_yaw'] = quat_to_yaw(msg.pose.orientation)
        self.perception_data['cx'] = msg.pose.position.x
        self.perception_data['cy'] = msg.pose.position.y

    def fsm_loop(self):
        # -----------------------------------------------------
        # 系统唤醒状态机 (仅在刚开机时运行一次)
        # -----------------------------------------------------
        if self.sys_state == "INIT_STAND":
            self.dog.stand()
            self.get_logger().info("🐕 正在发力站立，等待 4 秒站稳...")
            self.stand_start_time = time.time()
            self.sys_state = "WAIT_STAND"
            
        elif self.sys_state == "WAIT_STAND":
            if time.time() - self.stand_start_time > 4.0:
                self.get_logger().info("✅ 狗已站稳！启动赛段任务状态机。")
                self.sys_state = "RUNNING_TASKS"
                
        # -----------------------------------------------------
        # 赛段任务流转状态机
        # -----------------------------------------------------
        elif self.sys_state == "RUNNING_TASKS":
            current_task = self.task_list.get(self.current_task_id)
            
            if current_task is None:
                self.get_logger().info("🏁 恭喜！全场比赛任务已自主执行完毕！安全停车。")
                self.dog.stop()
                self.timer.cancel()
                return
                
            # 执行当前赛段任务
            is_task_done = current_task.execute(self.perception_data)
            
            if is_task_done:
                self.get_logger().info(f"🏆 赛段 {self.current_task_id} 通关！准备流转到下一赛段...")
                self.current_task_id += 1 # 自动切换到下一个任务！

def main():
    rclpy.init()
    node = GlobalBrain()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("安全停车...")
        node.dog.stop()
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()