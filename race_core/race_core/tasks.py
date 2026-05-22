#!/usr/bin/env python3
import math
import time

class Task1_StonePath:
    def __init__(self, dog_instance, logger):
        self.dog = dog_instance
        self.logger = logger
        
        self.kp_vision = 0.6  
        self.kp_yaw = 1.5     
        
        # 丢失容忍度
        self.lost_counter = 0
        self.max_lost_ticks = 15  
        self.last_valid_wz = 0.0
        self.init_yaw = None      

        # 🌟【第一性原理升级】：时间门控转弯锁 (拒绝传感器死锁，保证前进式转弯)
        self.is_turning = False
        self.turn_start_time = 0.0
        self.turn_direction = 0.0
        # 核心参数：强行锁死转弯的时间（秒）。2.2秒在0.6rad/s下刚好转过约75度
        self.turn_duration = 2.2  

    def execute(self, p_data):
        line_z = p_data['line_z']
        line_error = p_data['line_error']
        hard_turn  = p_data['hard_turn']
        current_yaw = p_data['current_yaw']
        
        line_valid = (line_z == 1.0)

        # 记录起跑方向 (仅作日志参考，绝不参与控制死锁)
        if self.init_yaw is None and current_yaw is not None:
            self.init_yaw = current_yaw
            self.logger.info(f"🧭 记录初始航向角: {math.degrees(self.init_yaw):.1f}°")

        # 1. 终极地标出口 (看到蓝球通关)
        if line_z == 2.0:
            self.logger.info("🎉 视野中捕获浅蓝色小球！第一赛段圆满通关！")
            return True 

        # ====================================================
        # 🌟 2. 时间门控转弯锁 (Time-Gated Turn Lock)
        # ====================================================
        
        # 视觉一旦报出急弯信号，立即启动时间锁
        if hard_turn != 0.0 and not self.is_turning:
            self.is_turning = True
            self.turn_start_time = time.time()
            self.turn_direction = hard_turn
            self.logger.warn("🚨 面前发现横向路障！启动时间锁定转向程序...")

        if self.is_turning:
            elapsed_time = time.time() - self.turn_start_time
            
            # 时间一到，无条件强制解锁，让近场巡线进行二次对准
            if elapsed_time > self.turn_duration:
                self.is_turning = False
                self.logger.info("✅ 转向时间到，强行解除转向锁，恢复视觉巡线！")
            else:
                # 🌟【前进式过弯】：vx=0.18 保证小狗在向前行进中画出圆弧，而不是原地打转
                vx = 0.18
                wz = -0.6 if self.turn_direction > 0.0 else 0.6 
                self.dog.move(vx=vx, wz=wz)
                self.logger.info(f"🔄 强制过弯中... 已持续 {elapsed_time:.2f} 秒 | vx={vx}, wz={wz}")
                return False

        # ====================================================
        # 3. 正常巡线 (近场 EMA 滤波)
        # ====================================================
        if line_valid:
            self.lost_counter = 0
            vx = 0.25 
            self.smoothed_error = 0.4 * line_error + 0.6 * getattr(self, 'smoothed_error', 0.0)
            wz = -self.kp_vision * self.smoothed_error
            wz = max(min(wz, 0.4), -0.4)
            self.last_valid_wz = wz
            self.dog.move(vx=vx, wz=wz)

        # ====================================================
        # 4. 颠簸丢失防错
        # ====================================================
        else:
            self.lost_counter += 1
            if self.lost_counter < self.max_lost_ticks:
                if abs(self.last_valid_wz) > 0.3:
                    # 如果是在过弯时突然瞎了，保持刚才的角速度继续转
                    self.dog.move(vx=0.08, wz=self.last_valid_wz)
                else:
                    # 石板路上震瞎了，靠初始航向锁死直行
                    vx = 0.25
                    wz = 0.0
                    if self.init_yaw is not None and current_yaw is not None:
                        yaw_error = math.atan2(math.sin(self.init_yaw - current_yaw), 
                                               math.cos(self.init_yaw - current_yaw))
                        wz = max(min(self.kp_yaw * yaw_error, 0.4), -0.4)
                    self.dog.move(vx=vx, wz=wz)
            else:
                self.logger.error("🚨 彻底脱轨！原地旋转重新捕获黄线...")
                search_wz = 0.3 if self.last_valid_wz >= 0 else -0.3
                self.dog.move(vx=0.0, wz=search_wz)
                
        return False