#!/usr/bin/env python3
import math
import time

class Task1_StonePath:
    def __init__(self, dog_instance, logger):
        self.dog = dog_instance
        self.logger = logger
        
        self.kp_vision = 0.6  
        self.kp_yaw = 1.5     
        
        self.lost_counter = 0
        self.max_lost_ticks = 15  
        self.last_valid_wz = 0.0
        
        self.init_yaw = None      
        # 🌟 新增：起点坐标记录，用于计算绝对行驶距离
        self.start_x = None
        self.start_y = None

    def execute(self, p_data):
        line_valid = p_data['line_valid']
        line_error = p_data['line_error']
        hard_turn  = p_data['hard_turn']
        current_yaw = p_data['current_yaw']
        cx = p_data['cx']  
        cy = p_data['cy']  

        # 1. 记录初始位姿
        if self.init_yaw is None and current_yaw is not None:
            self.init_yaw = current_yaw
            self.logger.info(f"🧭 [Task 1] 已锁定初始航向: {math.degrees(self.init_yaw):.1f}°")
            
        if self.start_x is None and cx is not None:
            self.start_x = cx
            self.start_y = cy
            self.logger.info(f"📍 [Task 1] 已锁定起跑点物理坐标: ({cx:.2f}, {cy:.2f})")

        # 🌟【第一性原理：绝对几何距离判定】
        if self.start_x is not None and cx is not None:
            # 计算当前点到起跑点的绝对直线距离 (勾股定理)
            distance_traveled = math.hypot(cx - self.start_x, cy - self.start_y)
            
            # 当累积走过 4.5 米，且当前视野内已经没有急弯（说明已经完全转过来，踏入第二赛段）：
            if distance_traveled > 4.5 and hard_turn == 0.0:
                self.logger.info(f"🎉 [Task 1] 累积行驶距离 {distance_traveled:.2f}m > 4.5m，圆满通过弯道，任务结束！")
                return True # 切入任务二

        # 2. 正常直角急弯拦截模式
        if hard_turn != 0.0:
            self.lost_counter = 0  
            vx = 0.12  
            wz = -self.kp_vision * hard_turn * 1.5  
            wz = max(min(wz, 0.6), -0.6)  
            
            self.dog.move(vx=vx, wz=wz)
            self.last_valid_wz = wz
            
            turn_str = "右转" if hard_turn > 0.0 else "left"
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

        # 4. 视觉丢失处理
        else:
            self.lost_counter += 1
            if self.lost_counter < self.max_lost_ticks:
                if abs(self.last_valid_wz) > 0.3:
                    self.dog.move(vx=0.05, wz=self.last_valid_wz)
                else:
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
                self.logger.error("🚨 彻底脱轨！原地旋转重新捕获黄线...")
                search_wz = 0.4 if self.last_valid_wz >= 0 else -0.4
                self.dog.move(vx=0.0, wz=search_wz)
                
        return False