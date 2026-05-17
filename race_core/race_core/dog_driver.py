#!/usr/bin/env python3
import math
import time
import importlib.util
import lcm
from geometry_msgs.msg import PoseStamped
from cyberdog_msg.msg import YamlParam

# —— 加载队友找出的底层通信接口 ——
_spec = importlib.util.spec_from_file_location(
    "robot_control_cmd_lcmt",
    "/home/cyberdog_sim/src/cyberdog_locomotion/common/lcm_type/lcm/robot_control_cmd_lcmt.py")
_gcm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_gcm)
robot_control_cmd_lcmt = _gcm.robot_control_cmd_lcmt

class CyberdogDriver:
    """
    终极黑盒底层驱动 (吸收了队友的姿态解算和步态控制)
    """
    def __init__(self, node):
        self.node = node
        self._lc = lcm.LCM("udpm://239.255.76.67:7671?ttl=255")
        self._cmd = robot_control_cmd_lcmt()
        self._cmd_life = 0
        
        self.pub_yaml = self.node.create_publisher(YamlParam, "yaml_parameter", 10)
        self.sub_pose = self.node.create_subscription(PoseStamped, "/pose", self._on_pose, 10)
        
        # 状态变量
        self.cx = self.cy = self.cyaw = 0.0
        self.is_locomotion_ready = False
        
        # 定时器：保留队友极其关键的 40Hz 心跳发送！
        self.timer = self.node.create_timer(0.025, self._tick)

    def _tick(self):
        self._cmd.life_count = self._cmd_life % 128
        self._lc.publish("robot_control_cmd", self._cmd.encode())
        self._cmd_life += 1

    @staticmethod
    def _quat_to_yaw(q):
        siny = 2.0 * (q.w * q.z + q.x * q.y)
        cosy = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
        return math.atan2(siny, cosy)

    def _on_pose(self, msg: PoseStamped):
        self.cx = msg.pose.position.x
        self.cy = msg.pose.position.y
        self.cyaw = self._quat_to_yaw(msg.pose.orientation)
        if msg.pose.position.z > 0.15:
            self.is_locomotion_ready = True

    # ---------------- 核心对外 API ----------------

    def init_stand(self):
        """剥夺遥控，起立"""
        m = YamlParam()
        m.name = "use_rc"; m.kind = 2; m.s64_value = 0; m.is_user = 0
        self.pub_yaml.publish(m)
        self._cmd.mode = 12 # MODE_RECOVERY_STAND
        
    def start_locomotion(self, gait=9, step_height=0.08):
        """切入运动模式，保留队友的步态与步高设置"""
        self._cmd.mode = 11
        self._cmd.gait_id = gait
        self._cmd.step_height[0] = step_height
        self._cmd.step_height[1] = step_height
        self.node.get_logger().info(f"✅ 运动模式启动 | 步态:{gait} | 步高:{step_height}m")

    def move_velocity(self, vx_body, vy_body, vyaw):
        """模式 A：纯视觉闭环控制 (用于赛段一巡线，不依赖里程计)"""
        self._cmd.mode = 11
        self._cmd.vel_des[0] = vx_body
        self._cmd.vel_des[1] = vy_body
        self._cmd.vel_des[2] = vyaw

    def move_to_target(self, tx, ty, max_speed=0.5, gain=0.3):
        """模式 B：保留队友精华的世界坐标系导航 (用于赛段二、六定点找球)"""
        dx, dy = tx - self.cx, ty - self.cy
        dist = math.hypot(dx, dy)
        
        if dist < 0.15:
            self.move_velocity(0.0, 0.0, 0.0)
            return True # 到达目标
            
        # 队友的世界系速度 -> 本体系速度投影算法 (完美)
        cos_y, sin_y = math.cos(self.cyaw), math.sin(self.cyaw)
        vx_w = max(-max_speed, min(dx * gain, max_speed))
        vy_w = max(-max_speed, min(dy * gain, max_speed))
        
        vx_b = vx_w * cos_y + vy_w * sin_y
        vy_b = -vx_w * sin_y + vy_w * cos_y
        
        self.move_velocity(vx_b, vy_b, 0.0)
        return False

    def stop(self):
        self._cmd.mode = 3 # QPSTAND
        self._cmd.vel_des = [0.0, 0.0, 0.0]