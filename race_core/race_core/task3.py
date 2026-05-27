#!/usr/bin/env python3
import math
import time

class Task3_CurveCharge:
    def __init__(self, dog_instance, logger):
        self.dog = dog_instance
        self.logger = logger
        self.state = "INIT"
        
        self.kp_vision = 1.3  # 曲线要求灵敏，转向增益拉高
        self.smoothed_error = 0.0
        
        # 🌟 根据任务规划，设定第三赛段的终点绝对坐标
        self.target_x = 3.0
        self.target_y = 7.0
        self.end_threshold = 0.4  # 距离目标点 0.4 米以内判定为到达
        
        self.logger.info("🏎️ 任务三：[高速纯追踪 + 绝对坐标结束判定] 已装载！")

    def execute(self, p_data):
        line_z = p_data.get('line_z', 0.0)
        line_error = p_data.get('line_error', 0.0)
        cx = p_data.get('cx')
        cy = p_data.get('cy')
        
        if cx is None or cy is None:
            return False

        line_valid = (line_z == 1.0)

        if self.state == "INIT":
            try:
                from move.core.types import GAIT_TROT_FAST
                self.dog.set_gait(GAIT_TROT_FAST)
            except Exception:
                self.dog.set_gait(9)
                
            self.dog.set_step_height(0.04) 
            self.logger.info("⚡ [Task 3] 切入贴地极速步态，开始冲刺！")
            self.state = "RUNNING"

        elif self.state == "RUNNING":
            # 🌟【第一性原理：绝对欧氏距离判定出口】
            # 实时计算当前狗的坐标与目标终点 (3, 7) 之间的直线距离
            dist_to_target = math.hypot(cx - self.target_x, cy - self.target_y)
            
            if dist_to_target < self.end_threshold:
                self.logger.info(f"🏆 [Task 3] 抵达坐标点 ({cx:.2f}, {cy:.2f})，距离目标 (3,7) 仅差 {dist_to_target:.2f}m！第三赛段圆满通关！")
                return True

            # 正常高速巡线
            if line_valid:
                vx = 0.45 
                self.smoothed_error = 0.3 * line_error + 0.7 * getattr(self, 'smoothed_error', 0.0)
                wz = -self.kp_vision * self.smoothed_error
                wz = max(min(wz, 0.7), -0.7) 
                self.dog.move(vx=vx, vy=0.0, wz=wz)
            else:
                self.dog.move(vx=0.15, vy=0.0, wz=0.0)
                self.logger.warn(f"⚠️ [Task 3] 视野丢失，减速试探中... 距终点还剩 {dist_to_target:.2f}m", throttle_duration_sec=1.0)

        return False