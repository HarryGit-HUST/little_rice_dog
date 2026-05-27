#!/usr/bin/env python3
import math
import time
import threading

class Task2_MockWildPearl:
    def __init__(self, dog_instance, logger):
        self.dog = dog_instance
        self.logger = logger
        self.state = "INIT"
        self.task_done = False
        self.logger.info("🎭 任务二 (Mock)：[调用队友 go_to 组合导航] 已装载！")

    def execute(self, p_data):
        cx = p_data.get('cx')
        cy = p_data.get('cy')
        current_yaw = p_data.get('current_yaw')
        
        if cx is None or cy is None or current_yaw is None:
            return False

        if self.state == "INIT":
            self.dog.set_step_height(0.06)
            self.dog.set_gait(9)
            
            # 完全保留你的目标点计算参数！
            tx1 = cx 
            ty1 = cy + 3.8 
            tx2 = tx1 - 3.5 
            ty2 = ty1 
            
            lock_yaw_deg = math.degrees(current_yaw)

            def _run_navigation():
                self.logger.info(f"⏩ [Task 2] 阶段 A: 前进到 ({tx1:.2f}, {ty1:.2f})")
                self.dog.go_to(tx=tx1, ty=ty1, yaw_deg=lock_yaw_deg, max_speed=0.35, thr=0.15)
                
                self.logger.info(f"⬅️ [Task 2] 阶段 B: 螃蟹步左平移到 ({tx2:.2f}, {ty2:.2f})")
                self.dog.go_to(tx=tx2, ty=ty2, yaw_deg=lock_yaw_deg, max_speed=0.3, thr=0.15)
                
                self.logger.info("🎉 [Task 2] 成功绕过雷区，抵达第三赛段入口！")
                self.task_done = True

            threading.Thread(target=_run_navigation, daemon=True).start()
            self.state = "WAITING_NAVIGATION"

        elif self.state == "WAITING_NAVIGATION":
            if self.task_done:
                return True

        return False