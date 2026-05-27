#!/usr/bin/env python3
import time
import threading
import sys

# 挂载队友工具箱路径以引入语音播报
sys.path.append('/home/cyberdog_utils')
try:
    from tts.speak import speak_blocked
except ImportError:
    print("⚠️ 警告：无法挂载 tts 模块，使用 Mock 播报代替。")
    def speak_blocked(text):
        print(f"[MOCK TTS] 🔊: {text}")
        time.sleep(2.0)

class Task4_TunnelTreasure:
    def __init__(self, dog_instance, logger):
        self.dog = dog_instance
        self.logger = logger
        self.state = "INIT"
        self.is_done = False
        self.logger.info("🎒 任务四：[深隧寻珍] 伪装感知 + 绝对坐标导航战术装载！")

    def _crouch_reverse(self):
        """蹲姿倒退：转身 180° → 蹲走前进(物理世界后退) → 停住。"""
        yaw = self.dog.read_yaw()
        if yaw is None:
            self.logger.warn("⚠️ 读不到 yaw，跳过蹲姿倒退")
            return
        self.logger.info(f"↩️ 蹲姿倒退: 转身 {yaw:.0f}° → {yaw+180:.0f}° ...")
        self.dog.turn_to(yaw + 180.0, wz=1.0)
        self.dog.crouch_walk()
        self.dog.stand()
        self.dog.turn_to(yaw, wz=1.0)
        self.dog.stand()

    def execute(self, p_data):
        cx = p_data.get('cx')
        cy = p_data.get('cy')

        if cx is None or cy is None:
            return False

        if self.state == "INIT":
            self.logger.info("🚀 启动任务四后台导航线程...")
            threading.Thread(target=self._run_mission, daemon=True).start()
            self.state = "RUNNING"

        elif self.state == "RUNNING":
            if self.is_done:
                self.logger.info("🎉 任务四全部子任务执行完毕！")
                return True
        return False

    def _run_mission(self):
        """顺序执行的阻塞式剧本线"""
        
        def go(tx, ty, yaw_deg=None):
            self.logger.info(f"➡️ 导航至 ({tx:.2f}, {ty:.2f})"
                            + (f" 面朝 {yaw_deg:.0f}°" if yaw_deg is not None else ""))
            self.dog.go_to(tx=tx, ty=ty, yaw_deg=yaw_deg, max_speed=0.4, thr=0.15)
            time.sleep(0.5)

        # --------------------------------------------------
        # 子任务一：足球与限高杆
        # --------------------------------------------------
        self.logger.info("=== 📍 开始子任务一 ===")
        go(2.1, 7.3)
        go(2.1, 7.6)
        
        
        go(2.05, 9.45)
        speak_blocked("识别到限高杆")
        speak_blocked("识别到足球")
        self.logger.info("🐕 启用蹲姿前进 (9.8 -> 10.8)...")
        self.dog.crouch_walk()
        
        self.logger.info("⚽ 踢球成功！转身蹲姿后退...")
        self._crouch_reverse()

        time.sleep(0.2)
        go(2.1, 7.3)

        # --------------------------------------------------
        # 子任务二：障碍物与橙色小球
        # --------------------------------------------------
        self.logger.info("=== 📍 开始子任务二 ===")
        go(1.1, 7.3)
        speak_blocked("识别到无法跨越障碍")
        
        go(1.5, 8.5)
        go(1.1, 10.5)
        speak_blocked("识别到橙色小球")
        
        go(1.0, 11.3)
        self.logger.info("🎾 撞击球成功！原路返回...")
        
        go(1.1, 10.5)
        go(1.5, 8.5)
        go(1.1, 7.3)

        # --------------------------------------------------
        # 子任务三：限高杆与大桶可乐
        # --------------------------------------------------
        self.logger.info("=== 📍 开始子任务三 ===")
        go(0.0, 7.3)
        
        
        go(0.0, 8.9)
        speak_blocked("识别到限高杆")
        speak_blocked("识别到可乐瓶")
        self.logger.info("🐕 启用蹲姿前进 (8.9 -> 10.5)...")
        self.dog.crouch_walk()
        
        self.dog.stand() # 起身
        time.sleep(1.0)
        go(0.0, 11.3)
        self.logger.info("🥤 撞倒可乐！后退返回...")
        
        go(0.0, 10.5, yaw_deg=-90.0)  # 强制面朝 y 负方向(南)，蹲走才能朝 7.3 前进
        self.logger.info("🐕 蹲姿前进 (10.5 -> 8.9, 面朝 -90°)...")
        self.dog.crouch_walk()
        time.sleep(1.0)

        go(0.0, 7.3)

        # --------------------------------------------------
        # 任务四收尾：前往任务五交接点 (对齐 x=3.1, 面朝 -90°)
        # --------------------------------------------------
        self.logger.info("=== 🏁 任务四收尾 ===")
        go(3.1, 7.3, yaw_deg=90.0)

        self.is_done = True