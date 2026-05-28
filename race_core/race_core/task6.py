#!/usr/bin/env python3
"""Task 6: 踢球 — 挂载队友 sub_main_control/ball_chaser 追球踢球。"""
import sys
import threading

sys.path.append('/home/cyberdog_utils')
from sub_main_control.ball_chaser import BallChaser


class Task6_KickBall:
    def __init__(self, dog_instance, logger):
        self.dog = dog_instance
        self.logger = logger
        self.state = "INIT"
        self._done = False
        self._fail = False
        self.logger.info("⚽ 任务六：[踢球] 追球踢球战术装载完成！")

    def execute(self, p_data):
        if self.state == "INIT":
            self.logger.info("🚀 启动任务六：追球踢球...")
            threading.Thread(target=self._run, daemon=True).start()
            self.state = "RUNNING"

        elif self.state == "RUNNING":
            if self._done:
                self.logger.info("🎉 任务六：踢球完成！")
                return True
            if self._fail:
                self.logger.error("❌ 任务六失败，继续")
                return True
        return False

    def _run(self):
        try:
            chaser = BallChaser(self.dog, ball_name="football3")
            ok = chaser.chase(
                target_x=3.2, target_y=12.65,
                done_x=3.0,
                zone_xmin=0.8, zone_xmax=2.5,
                zone_ymin=10.0, zone_ymax=14.3,
                temp_target_x=1.7, temp_target_y=13.5,
                kick_dist=0.1,
                max_loops=100, loop_timeout=300,
                kick_x_acc=30.0, kick_z_acc=0.0,
                kick_pitch=0.5, kick_crouch_z=0.06,
                kick_heading=170,
            )
            if ok:
                self._done = True
            else:
                self._fail = True
        except Exception:
            self.logger.exception("ball_chaser 崩溃")
            self._fail = True
