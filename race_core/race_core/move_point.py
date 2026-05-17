#!/usr/bin/env python3
"""定点移动：直接用 robot_control_cmd_lcmt 走底层运控接口。
支持：步高、步态、朝向、速度限制。"""
import sys
# 【第一性原理解决方案】：告诉 Python 去哪找系统里安装好的库
# 即使 ROS 2 屏蔽了路径，我们也要强行把它加进搜索清单
sys.path.append('/usr/local/lib/python3.8/site-packages')
sys.path.append('/usr/local/lib/python3/dist-packages')
import math
import time
import importlib.util
import lcm
import rclpy
from rclpy.node import Node
from rclpy.executors import SingleThreadedExecutor
from geometry_msgs.msg import PoseStamped

# —— 加载 robot_control_cmd_lcmt ——
_spec = importlib.util.spec_from_file_location(
    "robot_control_cmd_lcmt",
    "/home/cyberdog_sim/src/cyberdog_locomotion/common/lcm_type/lcm/robot_control_cmd_lcmt.py")
_gcm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_gcm)
robot_control_cmd_lcmt = _gcm.robot_control_cmd_lcmt

# —— LCM 频道 & 地址 (运控接口) ——
LCM_CMD_URL = "udpm://239.255.76.67:7671?ttl=255"
LCM_CMD_CHANNEL = "robot_control_cmd"

# —— 模式常量 (control_flags_release.hpp) ——
MODE_OFF = 0
MODE_QPSTAND = 3
MODE_PURE_DAMPER = 7
MODE_LOCOMOTION = 11
MODE_RECOVERY_STAND = 12

# —— 步态常量 ——
GAIT_STAND = 1
GAIT_WALK = 6
GAIT_TROT_10V5 = 9
GAIT_TROT_10V4 = 5
GAIT_TROT_FAST = 10


class MovePoint(Node):
    """走到目标点。到达后自动站立。支持步高、步态、朝向。"""

    GAIT_WALK = GAIT_WALK
    GAIT_TROT_10V5 = GAIT_TROT_10V5
    GAIT_TROT_10V4 = GAIT_TROT_10V4
    GAIT_TROT_FAST = GAIT_TROT_FAST

    def __init__(self, tx, ty, yaw_deg=None, gain=0.3, thr=0.15, max_speed=0.5,
                 yaw_gain=1.0, yaw_thr_deg=6.0,
                 gait=None, step_height=None,
                 node_name=None, on_done=None):
        name = node_name or f"move_point_{id(self):x}"
        super().__init__(name)
        self.tx, self.ty = tx, ty
        self.yaw_target = math.radians(yaw_deg) if yaw_deg is not None else None
        self.gain = gain
        self.thr = thr
        self.max_speed = max_speed
        self.yaw_gain = yaw_gain
        self.yaw_thr = math.radians(yaw_thr_deg)
        self.gait = gait or GAIT_TROT_10V5
        self._step_h = step_height
        self.cx = self.cy = None
        self.done = False
        self._on_done = on_done
        self._yaw_ok = (yaw_deg is None)

        # LCM 发送端 (运控接口端口)
        self._lc = lcm.LCM(LCM_CMD_URL)
        self._cmd = robot_control_cmd_lcmt()
        self._cmd_life = 0

        # 步高
        if step_height is not None:
            self._cmd.step_height[0] = step_height
            self._cmd.step_height[1] = step_height

        # 步态
        self._cmd.gait_id = self.gait

        # 1) 进入 RecoveryStand（use_rc 默认为 1，LCM 直接生效）
        self._send_cmd(MODE_RECOVERY_STAND)
        self._stand_start = time.time()
        self._stood_up = False
        self._cmd_life += 1

        # 持续发送 (25ms 心跳)
        self._timer = self.create_timer(0.025, self._tick)
        self._sub = self.create_subscription(
            PoseStamped, "/pose", self._on_pose, 10)
        self.get_logger().info(
            f"目标: ({tx:.2f}, {ty:.2f})"
            f"{'  yaw:'+str(yaw_deg)+'°' if yaw_deg is not None else ''}"
            f"  增益:{gain}  阈值:{thr}  max_speed:{max_speed}"
            f"  gait:{self.gait}"
            f"{'  step_h:'+str(step_height) if step_height else ''}")

    # ---- LCM 底层发送 ----
    def _send_cmd(self, mode):
        self._cmd.mode = mode
        self._cmd.life_count = self._cmd_life % 128
        self._lc.publish(LCM_CMD_CHANNEL, self._cmd.encode())

    # ---- 定时回调 ----
    def _tick(self):
        if self.done:
            self._timer.cancel()
            return
        self._send_cmd(self._cmd.mode)

    # ---- 四元数 → yaw ----
    @staticmethod
    def _quat_to_yaw(q):
        siny = 2.0 * (q.w * q.z + q.x * q.y)
        cosy = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
        return math.atan2(siny, cosy)

    # ---- 姿态回调 ----
    def _on_pose(self, msg: PoseStamped):
        if self.done:
            return
        self.cx = msg.pose.position.x
        self.cy = msg.pose.position.y

        # 阶段 1: 等 RecoveryStand 完成
        if not self._stood_up:
            z = msg.pose.position.z
            elapsed = time.time() - self._stand_start
            if z > 0.15 or elapsed > 5.0:
                self._stood_up = True
                self._cmd_life += 1
                self._send_cmd(MODE_LOCOMOTION)
                self.get_logger().info("RecoveryStand 完成, 进入 Locomotion")
            return

        # 阶段 2: 移向目标
        dx, dy = self.tx - self.cx, self.ty - self.cy
        dist = math.hypot(dx, dy)
        yaw_err = 0.0
        if self.yaw_target is not None:
            cyaw = self._quat_to_yaw(msg.pose.orientation)
            yaw_err = math.atan2(
                math.sin(self.yaw_target - cyaw),
                math.cos(self.yaw_target - cyaw))
            self._yaw_ok = abs(yaw_err) < self.yaw_thr

        if dist < self.thr and self._yaw_ok:
            self.get_logger().info("到达！")
            self.stop()
            self.done = True
            if self._on_done:
                self._on_done()
            return

        # 世界系速度 → 本体系速度
        cyaw = self._quat_to_yaw(msg.pose.orientation)
        cos_y, sin_y = math.cos(cyaw), math.sin(cyaw)
        vx_w = max(-self.max_speed, min(dx * self.gain, self.max_speed))
        vy_w = max(-self.max_speed, min(dy * self.gain, self.max_speed))
        vx_b = vx_w * cos_y + vy_w * sin_y
        vy_b = -vx_w * sin_y + vy_w * cos_y
        vyaw = max(-1.0, min(yaw_err * self.yaw_gain, 1.0))

        self._cmd.vel_des[0] = vx_b
        self._cmd.vel_des[1] = vy_b
        self._cmd.vel_des[2] = vyaw
        self._cmd_life += 1
        self._send_cmd(MODE_LOCOMOTION)

        extra = ""
        if self.yaw_target is not None:
            extra = f" yaw_err:{math.degrees(yaw_err):.0f}°"
        self.get_logger().info(
            f"pos:({self.cx:.2f},{self.cy:.2f}) dist:{dist:.2f}"
            f" vx:{vx_b:.2f} vy:{vy_b:.2f}{extra}")

    def stop(self):
        """停车 + QP 站立。"""
        self._cmd.vel_des = [0.0, 0.0, 0.0]
        self._cmd_life += 1
        self._send_cmd(MODE_QPSTAND)
        self.get_logger().info("已停车站立")

    def wait(self, timeout=None):
        """阻塞直到到达。Ctrl+C 安全停车。"""
        executor = SingleThreadedExecutor()
        executor.add_node(self)
        t0 = time.time()
        try:
            while not self.done:
                executor.spin_once(timeout_sec=0.05)
                if timeout and time.time() - t0 > timeout:
                    self.get_logger().warn("超时！")
                    return False
            return True
        except KeyboardInterrupt:
            self.stop()
            raise
        finally:
            self._timer.cancel()
            executor.remove_node(self)


# —— 别名 + 相对移动 ——
move_to = MovePoint

def move(dx, dy, **kwargs):
    """相对位置移动。读取当前位置 + (dx,dy) 为目标。"""
    if not rclpy.ok():
        raise RuntimeError("rclpy 未初始化")
    node = rclpy.create_node("move_get_pose")
    pose = None
    def _cb(msg):
        nonlocal pose
        pose = msg.pose
    sub = node.create_subscription(PoseStamped, "/pose", _cb, 10)
    ex = SingleThreadedExecutor()
    ex.add_node(node)
    t0 = time.time()
    while pose is None and rclpy.ok():
        ex.spin_once(timeout_sec=0.05)
        if time.time() - t0 > 3.0:
            ex.remove_node(node); node.destroy_node()
            raise TimeoutError("/pose 无数据")
    ex.remove_node(node); node.destroy_node()
    return MovePoint(pose.position.x + dx, pose.position.y + dy, **kwargs)


# —— CLI ——
def main():
    rclpy.init()
    usage = ("用法:\n"
             "  python3 move_point.py <tx> <ty> [yaw_deg] [gain] [thr] [max_speed] [gait] [step_height]\n"
             "  python3 move_point.py --rel <dx> <dy>  ...\n"
             "  yaw_deg: 0=东 90=北\n"
             "  gait: 9=trot 5=trot10v4 10=trotFast 6=walk\n"
             "  step_height: 0.04=低 0.06=默认 0.08=高")
    if len(sys.argv) < 2:
        print(usage); sys.exit(1)
    if sys.argv[1] == "--rel":
        if len(sys.argv) < 4:
            print("--rel <dx> <dy> [...]"); sys.exit(1)
        dx, dy = float(sys.argv[2]), float(sys.argv[3])
        kw = {}
        keys = ["yaw_deg","gain","thr","max_speed","gait","step_height"]
        for i, k in enumerate(keys):
            if len(sys.argv) > 4 + i and sys.argv[4 + i]:
                kw[k] = float(sys.argv[4 + i]) if k != "gait" else int(sys.argv[4 + i])
        mp = move(dx, dy, **kw)
    else:
        tx, ty = float(sys.argv[1]), float(sys.argv[2])
        yaw = float(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3] else None
        gain = float(sys.argv[4]) if len(sys.argv) > 4 and sys.argv[4] else 0.3
        thr = float(sys.argv[5]) if len(sys.argv) > 5 and sys.argv[5] else 0.15
        ms = float(sys.argv[6]) if len(sys.argv) > 6 and sys.argv[6] else 0.5
        gait = int(sys.argv[7]) if len(sys.argv) > 7 and sys.argv[7] else None
        sh = float(sys.argv[8]) if len(sys.argv) > 8 and sys.argv[8] else None
        mp = MovePoint(tx, ty, yaw_deg=yaw, gain=gain, thr=thr, max_speed=ms,
                       gait=gait, step_height=sh)
    mp.wait()
    rclpy.shutdown()


if __name__ == "__main__":
    main()