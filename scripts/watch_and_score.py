r"""
Task 6: watch mhd\ (Default runs) and mhd_cyst\ (Cyst runs), sub-folders included but not folders starting with _old, for new or
re-written *_Surfaces_Retina-JEI-Final.xml. When the file is complete it scores the run (one B-scan per eye in the 30-image
protocol), saves the tables (scores + thickness + run timing) and prints "eye X done" with the progress (k of 30 / 4 / pilot).
Safe to re-run: tables are updated in place, keyed by eye/B-scan/config; the seen-file state is saved in tables\watch_state.json,
so a restart only processes new or changed files.

    python -I week2\scripts\watch_and_score.py              # keep watching (Ctrl+C to stop), check every 10 s
    python -I week2\scripts\watch_and_score.py --once       # process what is there now, then exit
    python -I week2\scripts\watch_and_score.py --status     # show which of the 35 runs are done, per batch, and a time estimate
    python -I week2\scripts\watch_and_score.py --rescore    # ignore the saved state, redo everything found
    options: --interval N   --pattern "*_Surfaces_Iowa.xml"  (e.g. results of the IOWA 3.8.0 batch)   --all-variants

Timing (tables\run_timing.csv): for each result, when Pre and Final were written, Pre -> Final seconds, and the gap since the
previous result (this includes your own clicking and waiting, which is what the schedule needs). The _Time_ files hold only
the human interaction time that OCTExplorer measured (seconds), not computing time.
"""
import csv
import json
import statistics
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import w2common as W
import w2tables as T

STATE = W.TABLES / "watch_state.json"
TIMING = W.TABLES / "run_timing.csv"
argv = sys.argv[1:]


def opt(name, default=None):
    return argv[argv.index(name) + 1] if name in argv else default


def stable(path, wait=3.0):
    """True when size is unchanged over `wait` seconds and the XML parses to the end (IOWA writes it in one go, but be safe)."""
    s1 = path.stat().st_size
    time.sleep(wait)
    if path.stat().st_size != s1 or s1 == 0:
        return False
    try:
        ET.parse(path)
    except ET.ParseError:
        return False
    return True


def plan():
    """The 35 planned runs: [(run_no, label, eye, a, b, config)]. Run 1 = pilot, 2-31 = Default, 32-35 = Cyst."""
    out = [(1, "pilot", W.PILOT[0], W.PILOT[1], W.PILOT[2], "default")]
    sel = sorted(W.selection().values(), key=lambda r: int(r["default_run_no"]))
    for r in sel:
        out.append((int(r["default_run_no"]), f"{r['eye']} {r['group']}", r["eye"], int(r["a"]), int(r["b"]), "default"))
    for r in sorted((r for r in sel if r["cyst_run_no"]), key=lambda r: int(r["cyst_run_no"])):
        out.append((int(r["cyst_run_no"]), f"{r['eye']} {r['group']} CYST", r["eye"], int(r["a"]), int(r["b"]), "cyst"))
    return out


def timing_rows():
    if not TIMING.exists():
        return []
    with open(TIMING, newline="") as f:
        return list(csv.DictReader(f))


def record_timing(r, path):
    pre = path.with_name(path.name.replace("-Final.xml", "-Pre.xml"))
    tf = path.stat().st_mtime
    tp = pre.stat().st_mtime if pre.exists() else None
    human = []
    for kind in ("Pre", "Final"):
        t = path.with_name(path.name.replace("_Surfaces_", "_Time_").replace("Final.xml", f"{kind}.txt").replace("Pre.xml", f"{kind}.txt"))
        try:
            human.append(float(t.read_text().split()[0]))
        except Exception:
            human.append("")
    others = [float(x["final_epoch"]) for x in timing_rows() if (x["eye"], x["config"], x["vol_a"], x["vol_b"]) != (r["eye"], r["config"], str(r["vol_a"]), str(r["vol_b"]))
              and float(x["final_epoch"]) < tf]
    gap = tf - max(others) if others else ""
    W.upsert_csv(TIMING, [dict(eye=r["eye"], config=r["config"], vol_a=r["vol_a"], vol_b=r["vol_b"],
                               pre_written=datetime.fromtimestamp(tp).strftime("%Y-%m-%d %H:%M:%S") if tp else "",
                               final_written=datetime.fromtimestamp(tf).strftime("%Y-%m-%d %H:%M:%S"), final_epoch=f"{tf:.0f}",
                               pre_to_final_s=(tf - tp) if tp else "", gap_since_previous_s=gap,
                               human_time_pre_s=human[0], human_time_final_s=human[1])],
                 ["eye", "config", "vol_a", "vol_b"])


def status():
    done = {(x["eye"], x["config"], int(x["vol_a"]), int(x["vol_b"])) for x in timing_rows()}
    pl = plan()
    if len(pl) == 1:
        print("image_selection.csv missing: run make_selection.py first")
    for batch in range(1, 5):
        mine = [p for p in pl if (p[0] - 1) // 10 + 1 == batch]
        if not mine:
            continue
        n = sum((p[2], p[5], p[3], p[4]) in done for p in mine)
        print(f"batch {batch}: {n}/{len(mine)} done   " + " ".join(
            ("[x]" if (p[2], p[5], p[3], p[4]) in done else "[ ]") + f"{p[0]}:{p[2]}{'c' if p[5] == 'cyst' else ''}" for p in sorted(mine)))
    gaps = [float(x["gap_since_previous_s"]) for x in timing_rows() if x["gap_since_previous_s"] not in ("",)]
    gaps = [g for g in gaps if g <= 1800]            # ignore breaks longer than 30 min
    left = sum(1 for p in pl if (p[2], p[5], p[3], p[4]) not in done)
    if gaps:
        med = statistics.median(gaps)
        print(f"typical time per run so far (median of {len(gaps)} gaps between results): {med / 60:.1f} min; "
              f"{left} runs left, about {left * med / 3600:.1f} h of work at that pace")
    else:
        print("no timing yet (needs two finished runs; with one run only Pre -> Final is known)")


def process(path):
    r = W.load_run(path)
    sb, se = T.score_run(r)
    W.upsert_csv(W.TABLES / "scores_per_bscan.csv", sb, T.SCORE_KEY)
    W.upsert_csv(W.TABLES / "scores_per_eye.csv", [se], T.EYE_KEY)
    tb, te = T.thickness_run(r)
    W.upsert_csv(W.TABLES / "thickness_per_bscan.csv", tb, T.SCORE_KEY + ["layer"])
    W.upsert_csv(W.TABLES / "thickness_per_eye.csv", te, T.EYE_KEY + ["layer", "source"])
    record_timing(r, path)
    what = f"B-scan {r['a']}" if r["image_mode"] else f"B-scans {r['a']}-{r['b']}"
    print(f"eye {r['eye']} done  ({what}, {r['group']}, {r['config']} config): RMSE {se['rmse_ALL']:.2f} um, "
          f"Dice whole retina {se['dice_whole_retina']:.4f}, flagged columns {se['flagged_cols']}   "
          f"[{datetime.now():%H:%M:%S}]", flush=True)
    if r["nudge"]:
        print(f"   WARNING eye {r['eye']}: a NudgeLines file sits beside this result, so manual edits may be included. "
              f"Move old results to _old and re-run without nudging.", flush=True)
    done = {(x["eye"], x["config"], int(x["vol_a"]), int(x["vol_b"])) for x in timing_rows()}
    pl = plan()
    for kind, sel in (("Default", [p for p in pl if p[5] == "default" and p[1] != "pilot"]), ("Cyst", [p for p in pl if p[5] == "cyst"])):
        if sel:
            print(f"   progress {kind}: {sum((p[2], p[5], p[3], p[4]) in done for p in sel)}/{len(sel)}", flush=True)


def scan(state):
    pat = opt("--pattern")
    for x in W.find_results(pattern=pat, variants=None if "--all-variants" in argv else ("original",)):
        p = x["path"]
        sig = [p.stat().st_mtime, p.stat().st_size]
        if state.get(str(p)) == sig:
            continue
        if not stable(p):
            print(f"   {p.name}: still being written, will retry", flush=True)
            continue
        try:
            process(p)
            state[str(p)] = [p.stat().st_mtime, p.stat().st_size]
            STATE.write_text(json.dumps(state, indent=1))
        except Exception as e:                       # bad file: report, keep watching
            print(f"   {p.name}: could not score ({type(e).__name__}: {e})", flush=True)


if __name__ == "__main__":
    if "--status" in argv:
        status()
        sys.exit(0)
    state = {} if "--rescore" in argv or not STATE.exists() else json.loads(STATE.read_text())
    interval = float(opt("--interval", 10))
    print(f"watching {W.MHD} and {W.MHD_CYST} (every {interval:.0f} s, Ctrl+C to stop)" if "--once" not in argv else "one pass", flush=True)
    try:
        while True:
            scan(state)
            if "--once" in argv:
                break
            time.sleep(interval)
    except KeyboardInterrupt:
        print("stopped")
