# -*- coding: utf-8 -*-
import zipfile, os
from pathlib import Path

out = Path(r"D:\python\dmx\cdtest\docs\听书测试物料\mp3\Higgs_XR3_对比听测_0824")
dest = out / "Higgs_XR3_对比听测_0824_交付包.zip"
files = sorted([p for p in out.iterdir() if p.is_file() and p.name != dest.name])
with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
    for p in files:
        z.write(p, p.name)
print("created:", dest)
print("files:", len(files))
print("size MB: %.2f" % (dest.stat().st_size / 1048576))
