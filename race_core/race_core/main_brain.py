#!/usr/bin/env python3
import sys
import math
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Vector3
from sensor_msgs.msg import Imu
import time
import threading # 🌟 引入多线程库，防止 input() 阻塞底盘心跳

# 动态挂载
sys.path.append('/usr/local/lib/python3.8/site-packages')
sys.path.append('/usr/local/lib/python3/dist-packages')
sys.path.append('/home/cyberdog_utils')

try:
    from move.driver.dog import Dog
    from move.core.types import GAIT_TROT_10V5
except ImportError as e:
    print(f"❌ 挂载底盘部件失败: {e}")
    sys.exit(1)

# 导入任务类
from .tasks import Task1_StonePath
from .task3 import Task3_CurveCharge # 🌟 导入新写好的任务三

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
        
        # 实例化任务
        self.task1 = Task1_StonePath(self.dog, self.get_logger())
        self.task3 = Task3_CurveCharge(self.dog, self.get_logger())
        
        # 状态机变量
        self.sys_state = "INIT_STAND"
        self.stand_start_time = 0.0
        
        # 🌟 人工干预过渡变量
        self.user_ready = False
        self.prompt_started = False
        
        # 10Hz 大脑循环
        self.timer = self.create_timer(0.1, self.fsm_loop)
        self.get_logger().info("🧠 全局多任务主控大脑就绪！")

    def line_cb(self, msg):
        self.perception_data['line_error'] = msg.x
        self.perception_data['hard_turn'] = msg.y    
        self.perception_data['line_z'] = msg.z  

    def imu_cb(self, msg):
        self.perception_data['current_yaw'] = quat_to_yaw(msg.orientation)

    def _wait_for_user_input(self):
        """【非阻塞子线程函数】等待玩家在终端按下 1"""
        print("\n" + "="*60)
        print("请在 Gazebo 界面里手动将机器狗『传送』到第三赛段（曲线）的起跑线上。")
        print("传送完毕并摆正后，请在此处输入数字 '1' 并按回车启动任务三：")
        print("="*60 + "\n")
        while True:
            try:
                user_in = input().strip()
                if user_in == '1':
                    self.user_ready = True
                    break
            except Exception:
                pass

    def fsm_loop(self):
        # 1. 起步唤醒序列
        if self.sys_state == "INIT_STAND":
            self.dog.stand()
            self.get_logger().info("🐕 起立...")
            self.stand_start_time = time.time()
            self.sys_state = "WAIT_STAND"
            
        elif self.sys_state == "WAIT_STAND":
            if time.time() - self.stand_start_time > 4.0:
                self.get_logger().info("✅ 狗已站稳！启动赛段任务状态机。")
                self.sys_state = "RUNNING_TASK_1"
                
        # 2. 赛段一：石径探路
        elif self.sys_state == "RUNNING_TASK_1":
            is_task_done = self.task1.execute(self.perception_data)
            if is_task_done:
                self.dog.stop() # 任务一结束，在原地老老实实站着
                
                # 🌟 【如何无缝对接任务二】：
                # 以后你拿到队友 B 写的 Task2 后，直接在这里写：
                # self.sys_state = "RUNNING_TASK_2"
                # 现在由于我们要人工干预，我们切入过渡状态：
                self.sys_state = "WAIT_FOR_TELEPORT"

        # 🌟 3. 人工干预过渡状态 (不阻塞底盘心跳)
        elif self.sys_state == "WAIT_FOR_TELEPORT":
            if not self.prompt_started:
                self.prompt_started = True
                # 开辟独立的后台线程去等待输入，主 ROS 2 线程继续 spin() 维持通信！
                threading.Thread(target=self._wait_for_user_input, daemon=True).start()

            if self.user_ready:
                self.get_logger().info("🚀 收到指令！启动任务三状态机。")
                self.sys_state = "RUNNING_TASK_3"

        # 4. 赛段三：曲道冲锋
        elif self.sys_state == "RUNNING_TASK_3":
            # 运行任务三，永远返回 False，所以它会一直顺着线冲下去
            self.task3.execute(self.perception_data)

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