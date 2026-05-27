#!/usr/bin/env python3
import math
import time
import threading

class Task1_StonePath:
    def __init__(self, dog_instance, logger):
        self.dog = dog_instance
        self.logger = logger
        
        # 状态机：INIT -> TURN_180_WAIT -> BACKWARD_WALK_WAIT -> TURN_90_WAIT -> DONE
        self.state = "INIT"
        
        self.start_x = None
        self.start_y = None
        self.target_x = None
        self.target_y = None
        
        self.init_yaw = None      
        self.turn_start_yaw = None
        
        # 多线程同步锁
        self.turn_180_done = False
        self.goto_done = False
        self.turn_90_done = False
        
        self.logger.info("🦾 任务一：[原地闭环掉头 + go_to倒走 + turn_to过弯] 战术已装载！")

    def execute(self, p_data):
        cx = p_data.get('cx')
        cy = p_data.get('cy')
        current_yaw = p_data.get('current_yaw')
        
        if cx is None or cy is None or current_yaw is None:
            self.logger.warn("⏳ 等待底盘 /pose 和 /imu 数据注入...", throttle_duration_sec=2.0)
            return False

        # ====================================================
        # 状态 0: 初始化
        # ====================================================
        if self.state == "INIT":
            self.dog.set_step_height(0.08)
            self.dog.set_gait(9)
            
            self.init_yaw = current_yaw
            self.logger.info(f"📍 锁定起跑航向: {math.degrees(self.init_yaw):.1f}°，准备原地 180 度掉头！")

            # 计算 180 度掉头的绝对目标角度（存到 self，后续 go_to 也要用）
            self.backward_yaw_deg = math.degrees(self.init_yaw) + 180.0

            def _run_turn180():
                self.dog.turn_to(yaw_deg=self.backward_yaw_deg, wz=1.5)
                self.turn_180_done = True

            threading.Thread(target=_run_turn180, daemon=True).start()
            self.state = "TURN_180_WAIT"

        # ====================================================
        # 状态 1: 等待 180 度掉头完成，触发定点倒退
        # ====================================================
        elif self.state == "TURN_180_WAIT":
            if self.turn_180_done:
                self.logger.info("✅ 180 度闭环掉头成功！")
                self.dog.stop()
                
                # 🌟【绝对保留你的坐标参数】
                self.start_x = cx
                self.start_y = cy
                self.target_x = self.start_x + 3.1 
                self.target_y = self.start_y 
                self.logger.info(f"🎯 结算目标坐标: ({self.target_x:.2f}, {self.target_y:.2f})")
                
                def _run_goto():
                    self.logger.info("🔙 倒退走石板 (锁定 180° 朝向)...")
                    # go_to 默认会面朝目标，锁定 yaw_deg 到掉头后的方向，防止转回去
                    self.dog.go_to(tx=self.target_x, ty=self.target_y,
                                  yaw_deg=self.backward_yaw_deg, max_speed=0.4, thr=0.15)
                    self.goto_done = True

                threading.Thread(target=_run_goto, daemon=True).start()
                self.state = "BACKWARD_WALK_WAIT" 
            else:
                self.logger.info("🔄 turn_to 后台执行中 (180度)...", throttle_duration_sec=1.0)

        # ====================================================
        # 状态 2: 等待定点倒走完成，触发 90 度过弯
        # ====================================================
        elif self.state == "BACKWARD_WALK_WAIT":
            if self.goto_done:
                self.logger.info("🏁 队友的 go_to 报告到达目标点！准备转弯！")
                self.turn_start_yaw = current_yaw
                
                # 🌟 因为是倒着走，向左拐弯对身体来说必须是向右扭 (-90度)
                target_yaw_deg = math.degrees(self.turn_start_yaw) - 90.0
                
                def _run_turn90():
                    # 🌟【第一性原理】：直接调用队友的 turn_to 完成 90度闭环过弯
                    self.dog.turn_to(yaw_deg=target_yaw_deg, wz=1.5)
                    self.turn_90_done = True
                    
                threading.Thread(target=_run_turn90, daemon=True).start()
                self.state = "TURN_90_WAIT"
            else:
                self.logger.info(f"🔙 go_to 后台倒退中... 目标({self.target_x:.2f}, {self.target_y:.2f})", throttle_duration_sec=1.0)

        # ====================================================
        # 状态 3: 等待过弯完成
        # ====================================================
        elif self.state == "TURN_90_WAIT":
            if self.turn_90_done:
                self.logger.info("✅ 成功闭环转过直角弯道！")
                self.dog.stop()
                self.state = "DONE"
            else:
                self.logger.info("🔄 turn_to 后台执行中 (90度)...", throttle_duration_sec=1.0)

        # ====================================================
        # 状态 4: 赛段结束
        # ====================================================
        elif self.state == "DONE":
            self.logger.info("🎉 赛段一圆满通关！自动流转下一赛段。")
            return True 

        return False