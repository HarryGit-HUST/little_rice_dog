#!/usr/bin/env python3
import math
import time
import threading

class Task1_StonePath:
    def __init__(self, dog_instance, logger):
        self.dog = dog_instance
        self.logger = logger
        
        # 完整的状态流水线：
        # INIT -> TURN_180 (掉头) -> BACKWARD_WALK_WAIT (定点倒走) -> TURN_90 (反向过弯) -> DONE
        self.state = "INIT"
        
        # 绝对定位参考点
        self.start_x = None
        self.start_y = None
        self.target_x = None
        self.target_y = None
        
        self.init_yaw = None      
        self.turn_start_yaw = None
        
        # 多线程同步锁
        self.goto_done = False
        
        self.logger.info("🦾 任务一：[原地掉头 + 定点倒走 + 反向过弯] 战术已装载！")

    def execute(self, p_data):
        cx = p_data.get('cx')
        cy = p_data.get('cy')
        current_yaw = p_data.get('current_yaw')
        
        # 保护机制：如果底层节点还没发数据，原地等待
        if cx is None or cy is None or current_yaw is None:
            self.logger.warn("⏳ 等待底盘 /pose 和 /imu 数据注入...", throttle_duration_sec=2.0)
            return False

        # ====================================================
        # 状态 0: 初始化与步态设置
        # ====================================================
        if self.state == "INIT":
            # 调用队友的黑盒配置：设置步高 0.08m，步态 Trot
            self.dog.set_step_height(0.08)
            self.dog.set_gait(9)
            
            # 记录准备起步时的初始绝对航向
            self.init_yaw = current_yaw
            self.turn_start_yaw = current_yaw
            
            self.logger.info(f"📍 锁定起跑航向: {math.degrees(self.init_yaw):.1f}°，准备原地 180 度掉头！")
            self.state = "TURN_180"

        # ====================================================
        # 状态 1: 原地 180 度掉头 (屁股朝向赛道前方)
        # ====================================================
        elif self.state == "TURN_180":
            yaw_diff = abs(current_yaw - self.turn_start_yaw)
            if yaw_diff > math.pi: 
                yaw_diff = 2 * math.pi - yaw_diff
                
            if yaw_diff > 3.0:
                self.logger.info(f"✅ 成功掉头 {math.degrees(yaw_diff):.1f} 度！")
                self.dog.stop()
                
                # 🌟【第一性原理目标计算】
                # 现在狗屁股对着正前方，我们利用初始起跑方向 (init_yaw)，
                # 算出正前方 4.3 米处的世界绝对坐标！
                self.start_x = cx
                self.start_y = cy
                self.target_x = self.start_x + 3.1 * math.cos(self.init_yaw)
                self.target_y = self.start_y + 3.1 * math.sin(self.init_yaw)
                self.logger.info(f"🎯 结算目标坐标: ({self.target_x:.2f}, {self.target_y:.2f})")
                
                # 🌟【多线程启动队友黑盒】
                def _run_goto():
                    self.logger.info("🔙 调用队友 go_to 接口，开始倒退盲走...")
                    # 传入我们算好的世界坐标，限速 0.3 确保过石板不翻车
                    # 由于狗当前处于反向，队友底层的 world->body 投影计算会自动得出负数的 vx，实现倒走！
                    self.dog.go_to(tx=self.target_x, ty=self.target_y, max_speed=0.5, thr=0.15)
                    self.goto_done = True # 完成后置位

                # 丢入后台守护线程执行，绝对不阻塞大脑 10Hz 的时钟！
                threading.Thread(target=_run_goto, daemon=True).start()
                self.state = "BACKWARD_WALK_WAIT" 
            else:
                self.dog.move(vx=0.0, vy=0.0, wz=0.6)
                self.logger.info(f"🔄 180度掉头中... {math.degrees(yaw_diff):.1f}° / 180°", throttle_duration_sec=0.5)

        # ====================================================
        # 状态 2: 等待定点倒走完成
        # ====================================================
        elif self.state == "BACKWARD_WALK_WAIT":
            if self.goto_done:
                self.logger.info("🏁 队友的 go_to 报告到达目标点！到达弯道触发点！")
                # 记录准备过弯时的绝对角度
                self.turn_start_yaw = current_yaw
                self.state = "TURN_90"
            else:
                self.logger.info(f"🔙 go_to 后台倒退中... 目标({self.target_x:.2f}, {self.target_y:.2f})", throttle_duration_sec=1.0)

        # ====================================================
        # 状态 3: 原地 90 度过弯 (已修正转反 Bug)
        # ====================================================
        elif self.state == "TURN_90":
            yaw_diff = abs(current_yaw - self.turn_start_yaw)
            if yaw_diff > math.pi: 
                yaw_diff = 2 * math.pi - yaw_diff
                
            # 目标: 90度 (1.57弧度)。设 1.45 作为提前量
            if yaw_diff > 1.45:
                self.logger.info(f"✅ 成功转过弯道 {math.degrees(yaw_diff):.1f} 度！")
                self.dog.stop()
                self.state = "DONE"
            else:
                # 🌟【修复转弯符号】：改为 -0.6 (即身体右转)
                # 因为屁股朝前，向左拐弯对身体来说必须是向右扭！
                self.dog.move(vx=0.0, vy=0.0, wz=-0.6) 
                self.logger.info(f"🔄 倒挡反向过弯中... 进度: {math.degrees(yaw_diff):.1f}° / 90°", throttle_duration_sec=0.5)

        # ====================================================
        # 状态 4: 结束返回
        # ====================================================
        elif self.state == "DONE":
            self.logger.info("🎉 赛段一 (倒车定点+IMU过弯) 圆满通关！")
            return True # 通知主脑切入下一个赛段

        return False