#!/usr/bin/env python3
"""Task 2: 荒野寻珠 — 挂载队友 race/stage2，在 4x4 球阵中识别并击打橙球。"""
import sys
import threading

sys.path.append('/home/cyberdog_utils')
from race.stage2 import run_stage2


class Task2_MockWildPearl:
    def __init__(self, dog_instance, logger):
        self.dog = dog_instance
        self.logger = logger
        self.state = "INIT"
        self._done = False
        self._fail = False
        self.logger.info("🔮 任务二：[荒野寻珠] stage2 FSM 挂载完成！")

    def execute(self, p_data):
        if self.state == "INIT":
            self.logger.info("🚀 启动 stage2 荒野寻珠...")
            threading.Thread(target=self._run, daemon=True).start()
            self.state = "RUNNING"

        elif self.state == "RUNNING":
            if self._done:
                self.logger.info("🎉 任务二：荒野寻珠完成！")
                return True
            if self._fail:
                self.logger.error("❌ 任务二失败，继续下一任务")
                return True
        return False

    def _run(self):
        try:
            result = run_stage2(
                dog=self.dog,
                enter_field=False,
                shutdown=False,
            )
            if result.success:
                self.logger.info(f"stage2: 命中 {result.hit_count} 个橙球, {result.belief_summary}")
                self._done = True
            else:
                self.logger.error(f"stage2 异常: {result.final_state}")
                self._fail = True
        except Exception:
            self.logger.exception("stage2 崩溃")
            self._fail = True
