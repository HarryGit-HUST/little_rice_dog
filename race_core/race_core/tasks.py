#!/usr/bin/env python3
import math
import time

class Task1_StonePath:
    def __init__(self, dog_instance, logger):
        self.dog = dog_instance
        self.logger = logger
        
        self.kp_vision = 0.6  # 视觉转向 PID 增益
        self.kp_yaw = 1.5     # 盲走时航向锁死增益
        
        # 视觉丢失容忍度机制
        self.lost_counter = 0
        self.max_lost_ticks = 15  # 允许丢失 1.5 秒
        self.last_valid_wz = 0.0
        
        self.init_yaw = None      # 起步时的绝对航向角

    def execute(self, p_data):
        """
        任务主循环。返回 True 代表本赛段结束，主脑会自动切入下一个赛段。
        """
        line_valid = p_data['line_valid']
        line_error = p_data['line_error']
        hard_turn  = p_data['hard_turn']
        current_yaw = p_data['current_yaw']
        cx = p_data['cx']  # 机器狗当前的绝对 X 坐标 (里程计提供)

        # 1. 记录初始航向角作为绝对指南针
        if self.init_yaw is None and current_yaw is not None:
            self.init_yaw = current_yaw
            self.logger.info(f"🧭 [Task 1] 已锁定初始航向: {math.degrees(self.init_yaw):.1f}°")

        # 🌟【第一性原理：赛段一自动结束出口判定】
        # 赛道图纸显示：石板路全长 400cm (4.0m)。通过弯道后，狗的 X 坐标必然大于 4.2 米。
        # 当狗的 X 轴里程超过 4.3 米，且视觉不再报直角弯（说明已经转过来了并离开了虚线）：
        if cx is not None and cx > 4.3 and hard_turn == 0.0:
            self.logger.info(f"🎉 [Task 1] 达成判定条件：X里程={cx:.2f}m > 4.3m，第一赛段圆满结束！")
            return True # 返回 True 告诉主脑：立刻切换到第二赛段

        # 2. 正常直角急弯拦截模式
        if hard_turn != 0.0:
            self.lost_counter = 0  
            vx = 0.12  # 减速慢行，确保高抬腿在窄道内转过去
            wz = -self.kp_vision * hard_turn * 1.5  
            wz = max(min(wz, 0.6), -0.6)  
            
            self.dog.move(vx=vx, wz=wz)
            self.last_valid_wz = wz
            
            turn_str = "右转" if hard_turn > 0.0 else "左转"
            self.logger.warn(f"🔄 [Task 1] 识别到直角弯！强制降速 {turn_str}!")
            return False

        # 3. 正常巡线
        if line_valid:
            self.lost_counter = 0
            if abs(line_error) > 0.4:
                vx = 0.15
                wz = -self.kp_vision * line_error * 1.2
            else:
                vx = 0.35
                wz = -self.kp_vision * line_error
                
            wz = max(min(wz, 0.6), -0.6)
            self.last_valid_wz = wz
            self.dog.move(vx=vx, wz=wz)

        # 4. 视觉丢失处理 (震颤与盲区防错)
        else:
            self.lost_counter += 1
            if self.lost_counter < self.max_lost_ticks:
                if abs(self.last_valid_wz) > 0.3:
                    # 弯道盲区，继续记忆转弯
                    self.dog.move(vx=0.05, wz=self.last_valid_wz)
                else:
                    # 直道丢失，IMU航向锁死直走
                    vx = 0.35
                    wz = 0.0
                    if self.init_yaw is not None and current_yaw is not None:
                        yaw_error = math.atan2(math.sin(self.init_yaw - current_yaw), 
                                               math.cos(self.init_yaw - current_yaw))
                        wz = max(min(self.kp_yaw * yaw_error, 0.4), -0.4)
                        self.logger.warn(f"🚧 颠簸丢失黄线，IMU 强行锁航向! wz={wz:.2f}")
                    else:
                        self.logger.warn("🚧 颠簸丢失黄线，依靠惯性直走...")
                    self.dog.move(vx=vx, wz=wz)
            else:
                # 彻底丢了
                self.logger.error("🚨 彻底脱轨！原地旋转重新捕获黄线...")
                search_wz = 0.4 if self.last_valid_wz >= 0 else -0.4
                self.dog.move(vx=0.0, wz=search_wz)
                
        return False