#!/usr/bin/env python3
"""Task 5: 独木桥 — 挂载队友 sub_main_control/jump_and_go_seq 跳走序列。"""
import sys
import threading

sys.path.append('/home/cyberdog_utils')
from sub_main_control.jump_and_go_seq import run as run_jump_and_go


class Task5_PlankBridge:
    def __init__(self, dog_instance, logger):
        self.dog = dog_instance
        self.logger = logger
        self.state = "INIT"
        self._done = False
        self._fail = False
        self.logger.info("🌉 任务五：[独木桥] 跳走序列装载完成！")

    def execute(self, p_data):
        if self.state == "INIT":
            self.logger.info("🚀 启动任务五：独木桥跳走序列...")
            threading.Thread(target=self._run, daemon=True).start()
            self.state = "RUNNING"

        elif self.state == "RUNNING":
            if self._done:
                self.logger.info("🎉 任务五：独木桥完成！")
                return True
            if self._fail:
                self.logger.error("❌ 任务五失败，继续下一任务")
                return True
        return False

    def _run(self):
        try:
            # 自包含初始化：task4 可能蹲着/趴着，先站起来
            import time
            self.logger.info("🐕 [Task 5] 站起并稳定...")
            self.dog.stand()
            time.sleep(1.5)
            # 后续由 jump_and_go_seq 自己导航至各目标点
            run_jump_and_go(self.dog)
            self._done = True
        except Exception:
            self.logger.exception("jump_and_go 崩溃")
            self._fail = True
