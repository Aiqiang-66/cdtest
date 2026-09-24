# -*- coding: utf-8 -*-
"""5 并发 + 整章长度文案（约 1500 词）打满 10 分钟，核查长文案下的丢失。

复用 stress_5concurrent_30min_loss.py 的逻辑，只改窗口大小与时长。
"""
import importlib.util
from pathlib import Path

BASE = Path(r"D:\python\dmx\cdtest\docs\听书测试物料\stress_5concurrent_30min_loss.py")
OUT = Path(r"D:\python\dmx\cdtest\docs\听书测试物料\mp3\Higgs_5并发长文案10分钟_丢失核查_0910")

spec = importlib.util.spec_from_file_location("stress5c", BASE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

m.RUN_SECONDS = 600
m.WORKERS = 5
m.WINDOW_WORDS = 1500
m.STEP_WORDS = 300
m.OUT = OUT
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "meta").mkdir(exist_ok=True)
(OUT / "src").mkdir(exist_ok=True)

if __name__ == "__main__":
    m.main()
