#!/usr/bin/env python3
import math

class Task3_CurveCharge:
    def __init__(self, dog_instance, logger):
        self.dog = dog_instance
        self.logger = logger
        
        # 任务三竞速参数
        self.kp_vision = 1.5  # 曲线竞速，转向增益可以稍微大一些，提升弯道响应
        self.smoothed_error = 0.0
        self.filter_alpha = 0.3
        self.state = "INIT"

    def execute(self, p_data):
        """
        任务三主循环：沿着黄线中点一直走，不考虑急弯，不考虑结束
        """
        line_z = p_data['line_z']
        line_error = p_data['line_error']
        
        line_valid = (line_z == 1.0)

        if self.state == "INIT":
            # 曲线路段是平地，不需要 8cm 的夸张高度，恢复默认的 6cm 以减小颠簸
            self.dog.set_step_height(0.05)
            # 确保处于标准小跑步态
            self.dog.set_gait(9)
            self.logger.info("🚀 [Task 3] 曲线冲锋初始化完成！已切换为平地高速步态。")
            self.state = "RUNNING"

        # 正常巡线
        if line_valid:
            vx = 0.3  # 平地曲线，速度拉满到 0.4 m/s 冲击赛道！
            
            # EMA 低通滤波防止舵机震颤
            self.smoothed_error = self.filter_alpha * line_error + (1.0 - self.filter_alpha) * self.smoothed_error
            wz = -self.kp_vision * self.smoothed_error
            wz = max(min(wz, 0.5), -0.5) # 安全限幅
            
            self.dog.move(vx=vx, wz=wz)
            self.logger.info(f"⚡ [Task 3] 冲锋中 | vx={vx:.2f}, wz={wz:.2f}, 偏差={line_error:.2f}")
        else:
            # 临时丢失，慢速直行盲走
            self.dog.move(vx=0.15, wz=0.0)
            self.logger.warn("⚠️ [Task 3] 丢失目标，降速直行搜索中...")

        return False # 暂时不考虑结束，永远返回 False