r"""
Task 6: do diseased eyes take longer to segment in OCTExplorer, and does a longer run go together with larger errors?
Reads only saved tables (run_timing.csv written by watch_and_score.py, scores_per_eye.csv) and the *_Time_* files in mhd\.

What is measured (all from file time stamps and the *_Time_* files; nothing is timed by hand):
  final_stage_s   seconds between the Pre XML and the Final XML being written = final segmentation plus the moment it took the
                  user to click Next. This is the best available stand-in for "segmentation time".
  cycle_s         seconds since the previous result of the session was written = loading, clicking, Pre, Final. It contains the
                  user's own pace, so it is the coarse number ("about a minute per run"). The first run of the session has none.
  time_file_pre_s, time_file_final_s   the single number inside each *_Time_Retina-JEI-{Pre,Final}.txt. They stay at 2-5 s whatever
                  the scan size (an 80-scan chunk reads 2.6 s while its final stage took 98 s), so they are NOT used as the run
                  time. What they record is not stated in the files; they are only compared here (runtime_tests.csv).
Only the 21-scan Default runs of the chosen eyes are compared (normal vs diseased group). The pilot (10301) and the 10335 chunk runs
are listed separately. Normal / diseased is my visual judgement (see image_selection.csv), not a clinical label.

Writes: tables\runtime_per_eye.csv, runtime_summary.csv, runtime_tests.csv, runtime_ranked.csv, runtime_chunks.csv,
        figures\bars_runtime.png, figures\scatter_runtime_vs_error.png

    python -I week2\scripts\t6_runtime.py
"""
import csv
import sys
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

sys.path.insert(0, str(Path(__file__).parent))
import w2common as W

COLORS = {"normal": "#2a78d6", "diseased": "#eb6834"}
MARK = {"normal": "o", "diseased": "^"}
INK, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#e3e2de", "#fcfcfb"
plt.rcParams.update({"font.size": 10, "axes.facecolor": SURFACE, "figure.facecolor": SURFACE, "text.color": INK,
                     "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED, "axes.edgecolor": MUTED})


def read(name):
    with open(W.TABLES / name, newline="") as f:
        return list(csv.DictReader(f))


def write(name, rows):
    with open(W.TABLES / name, "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0]))
        wr.writeheader()
        wr.writerows([{k: (f"{v:.4f}" if isinstance(v, float) else v) for k, v in r.items()} for r in rows])
    print(f"saved tables\\{name} ({len(rows)} rows)")


def num(x):
    return float(x) if x not in ("", None) else np.nan


# ------------------------------------------------------------------ build the per-run table
timing = read("run_timing.csv")
scores = {(r["eye"], r["vol_a"], r["vol_b"]): r for r in read("scores_per_eye.csv")
          if r["variant"] == "original" and r["config"] == "default"}
last_day = max(r["final_written"][:10] for r in timing)
session = sorted([r for r in timing if r["config"] == "default" and r["final_written"][:10] == last_day],
                 key=lambda r: float(r["final_epoch"]))
cycle = {}
for prev, cur in zip(session, session[1:]):
    cycle[id(cur)] = float(cur["final_epoch"]) - float(prev["final_epoch"])

per_run = []
for k, t in enumerate(session):
    s = scores.get((t["eye"], t["vol_a"], t["vol_b"]))
    group = s["group"] if s else "other"
    dice = [num(s[f"dice_{n}"]) for n in W.LAYER_NAMES] if s else [np.nan]
    per_run.append(dict(order_in_session=k + 1, eye=t["eye"], volume=f"{t['vol_a']}-{t['vol_b']}",
                        n_bscans=int(t["vol_b"]) - int(t["vol_a"]) + 1, group=group,
                        image_mode=int(s["image_mode"]) if s else 0,
                        final_written=t["final_written"], final_stage_s=num(t["pre_to_final_s"]),
                        cycle_s=cycle.get(id(t), np.nan),
                        time_file_pre_s=num(t["human_time_pre_s"]), time_file_final_s=num(t["human_time_final_s"]),
                        rmse_all_um=num(s["rmse_ALL"]) if s else np.nan, mean_layer_dice=float(np.mean(dice)) if s else np.nan))
for r in per_run:
    r["cycle_s"] = r["cycle_s"] if np.isfinite(r["cycle_s"]) else ""
write("runtime_per_eye.csv", per_run)

cmp_rows = [r for r in per_run if r["group"] in COLORS and r["image_mode"] == 1]
G = {g: [r for r in cmp_rows if r["group"] == g] for g in COLORS}
if not all(G.values()):
    sys.exit("need both groups")


def vals(g, key):
    v = np.array([num(r[key]) for r in G[g]], float)
    return v[np.isfinite(v)]


# ------------------------------------------------------------------ summary + tests
METRICS = [("final_stage_s", "Final stage (Pre -> Final), s"), ("cycle_s", "Whole cycle per run, s"),
           ("time_file_pre_s", "*_Time_ file, Pre, s"), ("time_file_final_s", "*_Time_ file, Final, s")]
summary, tests = [], []
for key, label in METRICS:
    for g in COLORS:
        v = vals(g, key)
        summary.append(dict(metric=key, group=g, n=len(v), mean=v.mean(), sd=v.std(ddof=1), median=np.median(v),
                            q25=np.percentile(v, 25), q75=np.percentile(v, 75), min=v.min(), max=v.max()))
    a, b = vals("normal", key), vals("diseased", key)
    u = stats.mannwhitneyu(b, a, alternative="two-sided")
    tests.append(dict(test="Mann-Whitney diseased vs normal", metric=key, n_normal=len(a), n_diseased=len(b),
                      diff_of_means_s=b.mean() - a.mean(), diff_of_medians_s=np.median(b) - np.median(a),
                      statistic=float(u.statistic), p_value=float(u.pvalue)))
write("runtime_summary.csv", summary)

# does a longer run go with a larger error?  (Spearman rank correlation)
def spearman(rows, x, y, label):
    xs = np.array([num(r[x]) for r in rows]); ys = np.array([num(r[y]) for r in rows])
    ok = np.isfinite(xs) & np.isfinite(ys)
    rho, p = stats.spearmanr(xs[ok], ys[ok])
    tests.append(dict(test=f"Spearman {label}", metric=f"{x} vs {y}", n_normal=int(sum(r['group'] == 'normal' for r, o in zip(rows, ok) if o)),
                      n_diseased=int(sum(r['group'] == 'diseased' for r, o in zip(rows, ok) if o)),
                      diff_of_means_s="", diff_of_medians_s="", statistic=float(rho), p_value=float(p)))


for y in ("rmse_all_um", "mean_layer_dice"):
    spearman(cmp_rows, "final_stage_s", y, "all eyes")
    spearman(G["normal"], "final_stage_s", y, "normal eyes only")
    spearman(G["diseased"], "final_stage_s", y, "diseased eyes only")
spearman(cmp_rows, "cycle_s", "rmse_all_um", "all eyes")
spearman(cmp_rows, "time_file_final_s", "final_stage_s", "all eyes (are _Time_ files compute time?)")
spearman(cmp_rows, "order_in_session", "final_stage_s", "all eyes (does the user get faster over the session?)")
write("runtime_tests.csv", tests)

ranked = sorted(cmp_rows, key=lambda r: -r["final_stage_s"])
write("runtime_ranked.csv", [dict(rank=i + 1, eye=r["eye"], group=r["group"], final_stage_s=r["final_stage_s"],
                                  cycle_s=r["cycle_s"], rmse_all_um=r["rmse_all_um"]) for i, r in enumerate(ranked)])

other = [r for r in per_run if r["image_mode"] == 0 or r["group"] not in COLORS]
write("runtime_chunks.csv", [dict(eye=r["eye"], volume=r["volume"], n_bscans=r["n_bscans"], role=("pilot" if r["group"] == "pilot" else
                             "61-scan test" if r["n_bscans"] == 61 else "chunk of a full volume" if r["n_bscans"] > 21 else "other"),
                             final_stage_s=r["final_stage_s"], cycle_s=r["cycle_s"], time_file_final_s=r["time_file_final_s"])
                             for r in per_run if r["group"] == "pilot" or r["n_bscans"] > 21])

# ------------------------------------------------------------------ figures
W.FIGS.mkdir(parents=True, exist_ok=True)
fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.6), constrained_layout=True)
for ax, (key, label) in zip(axes, METRICS[:2]):
    for k, g in enumerate(COLORS):
        v = vals(g, key)
        sd = v.std(ddof=1)
        ax.bar(k, v.mean(), width=0.62, color=COLORS[g], edgecolor=SURFACE, linewidth=1.5, zorder=2,
               label=f"{g} (n = {len(v)} eyes)")
        ax.errorbar(k, v.mean(), yerr=[[min(sd, v.mean())], [sd]], fmt="none", ecolor=INK, elinewidth=1.2, capsize=5, zorder=4)
        jit = (np.arange(len(v)) - (len(v) - 1) / 2) * 0.28 / max(len(v), 1) * 2
        ax.plot(k + jit, v, "o", ms=3.6, mfc=INK, mec=SURFACE, mew=0.5, zorder=5)
    ax.set_xticks([0, 1]); ax.set_xticklabels(list(COLORS))
    ax.set_ylabel("seconds")
    ax.set_title(label, fontsize=10, loc="left")
    ax.grid(axis="y", color=GRID, linewidth=0.8, zorder=0); ax.set_axisbelow(True)
    for s_ in ("top", "right"):
        ax.spines[s_].set_visible(False)
    p = [t for t in tests if t["metric"] == key and t["test"].startswith("Mann")][0]["p_value"]
    ax.set_ylim(0, ax.get_ylim()[1] * 1.12)
    ax.text(0.98, 1.0, f"Mann-Whitney {'p < 0.001' if p < 0.001 else f'p = {p:.3f}'}", transform=ax.transAxes, ha="right", va="bottom",
            fontsize=9, color=MUTED)
axes[0].legend(frameon=False, loc="upper left")
fig.suptitle("Time per OCTExplorer run, 21-scan Default runs: mean +/- SD across eyes, dots = individual eyes", fontsize=10, x=0.01, ha="left")
fig.savefig(W.FIGS / "bars_runtime.png", dpi=150)
plt.close(fig)

fig, ax = plt.subplots(figsize=(6.6, 4.8), constrained_layout=True)
for g in COLORS:
    ax.scatter([r["final_stage_s"] for r in G[g]], [r["rmse_all_um"] for r in G[g]], s=38, marker=MARK[g], color=COLORS[g],
               edgecolor=SURFACE, linewidth=0.6, label=f"{g} (n = {len(G[g])})", zorder=3)
ax.set_xlabel("Final stage of the run, Pre -> Final (s)")
ax.set_ylabel("RMSE of the scored B-scan vs GT, all boundaries (um)")
rho = [t for t in tests if t["test"] == "Spearman all eyes" and t["metric"] == "final_stage_s vs rmse_all_um"][0]
ax.set_title(f"Longer run vs larger error (Spearman rho = {rho['statistic']:.2f}, {'p < 0.001' if rho['p_value'] < 0.001 else f"p = {rho['p_value']:.3f}"}, n = {rho['n_normal'] + rho['n_diseased']})",
             fontsize=10, loc="left")
ax.grid(color=GRID, linewidth=0.8, zorder=0); ax.set_axisbelow(True)
for s_ in ("top", "right"):
    ax.spines[s_].set_visible(False)
ax.legend(frameon=False)
fig.savefig(W.FIGS / "scatter_runtime_vs_error.png", dpi=150)
plt.close(fig)
print("saved figures\\bars_runtime.png, figures\\scatter_runtime_vs_error.png")

for r in summary:
    if r["metric"] in ("final_stage_s", "cycle_s"):
        print(f"{r['metric']:14s} {r['group']:9s} n={r['n']:2d} mean {r['mean']:6.1f} sd {r['sd']:5.1f} median {r['median']:6.1f} range {r['min']:.1f}-{r['max']:.1f}")
for t in tests:
    print(f"{t['test']:60s} {t['metric']:34s} stat {t['statistic']:8.3f} p {t['p_value']:.4f}")
print("slowest final stages:", ", ".join(f"{r['eye']}({r['group'][0]}) {r['final_stage_s']:.0f}s" for r in ranked[:6]))
