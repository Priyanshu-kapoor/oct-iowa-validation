r"""
Make the IOWA input volumes for the 30-image protocol (uses step3_make_mhd.py, unchanged):
  mhd\<eye>_<a>-<b>.mhd/.raw           21 B-scans centred on the chosen B-scan, 30 eyes (Default configuration runs)
  mhd\10301_140-160.mhd/.raw           pilot: 21 B-scans centred on 150, to time a run and to compare 21 vs the 61-scan result
  mhd_cyst\<eye>\<eye>_<a>-<b>.mhd/.raw   copies for the 4 Cyst-configuration runs, one folder per eye so output names do not clash
Then checks every header against its .raw size. Re-running rewrites the same files.

    python -I week2\scripts\make_volumes.py
"""
import csv
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import w2common as W

STEP3 = W.ROOT / "step3_make_mhd.py"
CYST = W.ROOT / "mhd_cyst"
sel = list(csv.DictReader(open(W.TABLES / "image_selection.csv")))
jobs = [("10301", 140, 160)] + [(r["eye"], int(r["a"]), int(r["b"])) for r in sel]

for eye, a, b in jobs:
    subprocess.run([sys.executable, "-I", str(STEP3), eye, "--range", str(a), str(b)], check=True, capture_output=True,
                   cwd=W.ROOT)
for r in sel:
    if int(r["cyst_run"]):
        d = CYST / r["eye"]
        d.mkdir(parents=True, exist_ok=True)
        for ext in (".mhd", ".raw"):
            shutil.copy2(W.MHD / f"{r['volume']}{ext}", d / f"{r['volume']}{ext}")

bad = 0
for m in sorted(list(W.MHD.glob("*_*-*.mhd")) + list(CYST.glob("*/*.mhd"))):
    t = m.read_text()
    dims = [int(x) for x in re.search(r"DimSize = (.*)", t).group(1).split()]
    raw = m.with_suffix(".raw")
    ok = raw.exists() and raw.stat().st_size == dims[0] * dims[1] * dims[2]
    if "_old" in str(m) or not any(m.stem.startswith(e) for e, _, _ in jobs):
        continue
    bad += not ok
    if dims[2] == 21 and not ok:
        print("PROBLEM", m)
n21 = sum(1 for e, a, b in jobs if (W.MHD / f"{e}_{a}-{b}.mhd").exists())
print(f"{n21} volumes of 21 B-scans in mhd\\ (30 eyes + pilot), {sum(1 for _ in CYST.glob('*/*.mhd'))} Cyst copies; header/raw problems: {bad}")
