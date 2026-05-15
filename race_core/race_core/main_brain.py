#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import Float32, String
import time

class BrainFSMNode(Node):
    def __init__(self):
        super().__init__('brain_fsm_node')
        
        # 1. 订阅视觉模块的数据
        self.sub_line_error = self.create_subscription(Float32, '/perception/line_error', self.line_error_callback, 10)
        
        # 2. 发布底层运动控制指令
        self.pub_cmd_vel = self.create_publisher(Twist, '/cmd_vel', 10)
        # 假设官方有一个 motion_command 用于下发站立/趴下等高级指令 (需查阅实际接口，这里作演示)
        self.pub_motion = self.create_publisher(String, '/motion_command', 10)

        # 3. 状态机变量
        self.state = "INIT"  # 可能的状态：INIT, STANDING, STAGE_1_TRACKING, STAGE_1_DONE
        self.line_error = 0.0
        
        # 巡线 PID 参数 (只需 P 控制器就能跑第一段了)
        self.Kp = 0.005
        
        # 启动主控循环 (每秒10次)
        self.timer = self.create_timer(0.1, self.fsm_loop)
        self.get_logger().info("主控大脑 [Brain FSM] 启动！")

    def line_error_callback(self, msg):
        # 持续接收来自视觉组的误差更新
        self.line_error = msg.data

    def fsm_loop(self):
        cmd = Twist()

        if self.state == "INIT":
            self.get_logger().info("比赛开始，发送站立指令...")
            # 伪代码：发送站立指令（需根据小米官方手册替换具体指令，这里演示发给底盘一点微小速度激活）
            cmd.linear.z = 0.1 
            self.pub_cmd_vel.publish(cmd)
            time.sleep(3) # 等待狗站稳
            self.state = "STAGE_1_TRACKING"

        elif self.state == "STAGE_1_TRACKING":
            if self.line_error == 999.0:
                # 没看到线，原地找或者盲走
                cmd.linear.x = 0.1
                cmd.angular.z = 0.0
                self.get_logger().warning("丢失黄线，慢速盲走中...")
            else:
                # 核心逻辑：基于偏差计算角速度 (负反馈控制)
                cmd.linear.x = 0.3  # 固定前进线速度 0.3 m/s
                # error > 0 (线在右), 狗需要右转 (Z轴负方向)
                cmd.angular.z = -self.Kp * self.line_error
                self.get_logger().info(f"巡线中 -> Error: {self.line_error:.2f}, Angular: {cmd.angular.z:.2f}")

            self.pub_cmd_vel.publish(cmd)
            
            # TODO: 赛段结束条件检测（比如视觉看到某种标志，或者里程计走够了特定的距离）
            # if 离开虚线: self.state = "STAGE_2_FIND_BALL"

def main(args=None):
    rclpy.init(args=args)
    node = BrainFSMNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()