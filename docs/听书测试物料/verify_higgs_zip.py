# -*- coding: utf-8 -*-
import zipfile
from pathlib import Path
dest = Path(r"D:\python\dmx\cdtest\docs\听书测试物料\mp3\Higgs_XR3_对比听测_0824\Higgs_XR3_对比听测_0824_交付包.zip")
with zipfile.ZipFile(dest) as z:
    names = z.namelist()
    mp3 = [n for n in names if n.endswith(".mp3")]
    srt = [n for n in names if n.endswith(".srt")]
    js  = [n for n in names if n.endswith(".json")]
    md  = [n for n in names if n.endswith(".md")]
    print("总条目:", len(names))
    print("mp3:", len(mp3), "| srt:", len(srt), "| json:", len(js), "| md:", md)
    # 校验测试文件完整性
    bad = z.testzip()
    print("zip 完整性:", "OK (无损坏)" if bad is None else ("损坏: "+bad))
