#!/usr/bin/env python3
import sys
# 【第一性原理解决方案】：告诉 Python 去哪找系统里安装好的库
# 即使 ROS 2 屏蔽了路径，我们也要强行把它加进搜索清单
sys.path.append('/usr/local/lib/python3.8/site-packages')
sys.path.append('/usr/local/lib/python3/dist-packages')
import rclpy
from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor
from std_msgs.msg import Float32

# 【原封不动地黑盒导入队友的类】
from .move_point import MovePoint 

class BrainNode(Node):
    def __init__(self, driver_node):
        super().__init__('main_brain')
        
        # 保存队友的驱动节点实例
        self.dog_driver = driver_node
        
        # 订阅视觉模块的黄线偏差
        self.sub_line = self.create_subscription(Float32, '/perception/line_error', self.line_callback, 10)
        self.line_error = 0.0
        
        # 大脑监控时钟 (10Hz)
        self.timer = self.create_timer(0.1, self.fsm_loop)
        self.get_logger().info("🧠 主控大脑启动！已挂载队友的黑盒驱动。")

    def line_callback(self, msg):
        self.line_error = msg.data

    def fsm_loop(self):
        # 目前队友的代码是一个“定点导航”黑盒
        # 只要实例化了，它就会自动起立，并朝着初始化的坐标前进
        
        # 【架构师的无奈】：我们虽然收到了视觉偏差 self.line_error
        # 但队友的黑盒目前没有提供给我们“修改航向角/角速度”的动态接口！
        # 所以目前大脑只能监控，无法干预狗的巡线转向。
        
        if self.dog_driver.done:
            self.get_logger().info("🏁 队友的黑盒报告：到达指定坐标点！准备切换下一赛段...")
            # TODO: self.state = "TASK_2"
        else:
            self.get_logger().info(f"监控中: 视觉偏差={self.line_error:.1f}, 狗正由队友代码驱动前往坐标点...")


def main(args=None):
    rclpy.init(args=args)
    
    # 1. 实例化队友的黑盒驱动
    # 任务一：我们让它往前直走 5 米 (tx=5.0, ty=0.0)，步态设为 Trot，步高 0.08 跨石板
    teammate_driver = MovePoint(tx=5.0, ty=0.0, max_speed=0.35, gait=9, step_height=0.08)
    
    # 2. 实例化你的主脑，把队友的驱动传进去
    brain = BrainNode(teammate_driver)
    
    # 3. 核心：必须使用多线程执行器，让你们俩的节点同时工作！
    executor = MultiThreadedExecutor()
    executor.add_node(teammate_driver)
    executor.add_node(brain)
    
    try:
        # 启动！
        executor.spin()
    except KeyboardInterrupt:
        brain.get_logger().info("安全停车...")
        teammate_driver.stop()
    
    brain.destroy_node()
    teammate_driver.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()