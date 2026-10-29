r"""
Writes week2\RUN_CHECKLIST.md: the 35 IOWA runs in batches of 10 (run 1 = pilot, 2-31 = Default, 32-35 = Cyst) with the exact
file to open, the B-scan that will be scored, and tick boxes. Tick state is read from the result files on disk
(a run is done when its Final XML exists). Cyst runs (32-35) are an optional side experiment. Time estimates are NOT written here.

    python -I week2\scripts\make_checklist.py
"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import w2common as W

sel = sorted(csv.DictReader(open(W.TABLES / "image_selection.csv")), key=lambda r: int(r["default_run_no"]))
runs = [(1, "pilot (eye 10301, normal; times a run, checks 21 vs 61 scans)", r"mhd\10301_140-160.mhd", 150, "Default")]
for r in sel:
    runs.append((int(r["default_run_no"]), f"{r['eye']} {r['group']}", rf"mhd\{r['volume']}.mhd", int(r["bscan"]), "Default"))
for r in sorted((r for r in sel if r["cyst_run_no"]), key=lambda r: int(r["cyst_run_no"])):
    runs.append((int(r["cyst_run_no"]), f"{r['eye']} {r['group']} (Cyst side experiment)",
                 rf"mhd_cyst\{r['eye']}\{r['volume']}.mhd", int(r["bscan"]), "Cyst"))
runs.sort()
def _done(r):
    f = Path(r[2])
    return (W.ROOT / f.with_name(f.stem + "_Surfaces_Retina-JEI-Final.xml")).exists()


dflt = [r for r in runs if r[4] == "Default"]
missing = [r[1].split()[0] for r in dflt if not _done(r)]
out = ["# IOWA run checklist (35 runs, batches of 10)", "",
       f"Status (read from the result files): {sum(_done(r) for r in dflt)} of {len(dflt)} Default runs done (run 1 = pilot 10301, runs 2-31 = the 30 eyes)."
       + (f" Still missing: {', '.join(missing)}." if missing else " All Default runs are done."),
       f"Cyst runs 32-35 (side experiment): optional, {'not done' if not any(_done(r) for r in runs if r[4] == 'Cyst') else 'some done'}.", "",
       "Per run, in OCTExplorer 5.0.0b: drag the .mhd (NOT the .raw) onto the window (or File > Open image); check the status bar voxel",
       "size is 0.00987 x 0.00313 x 0.00987 mm; in the pre-segmentation dialog pick the configuration named in the last column;",
       "click Next (pre-segmentation), then Next (final segmentation); do NOT edit or nudge anything; wait until the result is saved",
       "(the watcher prints 'eye X done'). Cyst runs: pick `Configuration-Cyst.json`; everything else `Configuration-Default.json`.",
       "Start once, in a PowerShell window:  `cd C:\\octa500` then `python -I week2\\scripts\\watch_and_score.py` (leave it open).",
       "Progress and time estimate at any moment:  `python -I week2\\scripts\\watch_and_score.py --status`.", ""]
for batch in range(1, 5):
    mine = [r for r in runs if (r[0] - 1) // 10 + 1 == batch]
    out += [f"## Batch {batch} (runs {mine[0][0]}-{mine[-1][0]})", "", "| done | run | what | file to open (under C:\\octa500) | scored B-scan | configuration |", "|---|---|---|---|---|---|"]
    for n, what, f, b, cfg in mine:
        xml = W.ROOT / Path(f).with_name(Path(f).stem + "_Surfaces_Retina-JEI-Final.xml")
        state = "[x] done" if xml.exists() else ("[ ] optional, not done" if cfg == "Cyst" else "[ ] NOT DONE")
        out.append(f"| {state} | {n} | {what} | `{f}` | {b} | {cfg} |")
    out.append("")
(W.W2 / "RUN_CHECKLIST.md").write_text("\n".join(out), encoding="utf-8")
print(f"wrote {W.W2 / 'RUN_CHECKLIST.md'} ({len(runs)} runs)")
