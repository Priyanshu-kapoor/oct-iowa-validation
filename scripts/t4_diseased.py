r"""
Task 4: how does IOWA do on the diseased images, and does the Cyst configuration help when cysts are present?
Reads the scores saved by watch_and_score.py / score_runs.py (30-image protocol: one B-scan per eye).

 A. Diseased eyes, Default configuration (main comparison):
    tables\t4_diseased_per_eye.csv     per eye: RMSE per boundary, Dice per layer, worst first
    tables\t4_failure_stats.csv        per eye and boundary: RMSE, largest error and where (column), share of columns off by
                                       more than 10 um, mean signed error (IOWA - GT), columns where boundaries cross
    tables\t4_notes.txt                one factual sentence per image for the 3 worst (numbers only; the plain-language
                                       explanation of WHY (cysts, shadows, ...) must be written by looking at the overlay)
    figures\t4_worst3_overlay.png      the 3 worst images: OCT B-scan with GT (solid) and IOWA (dashed) boundaries, and the
                                       RMSE of each boundary as bars
 B. Side experiment: the same eyes run with Configuration-Cyst.json (folder mhd_cyst\<eye>\):
    tables\t4_cyst_vs_default.csv      per eye, per boundary / layer: Default, Cyst, Cyst - Default
    tables\t4_cyst_vs_default_mean.csv mean and SD over the eyes
    figures\t4_cyst_vs_default_{rmse,dice,thickness}.png   bar graphs, Default vs Cyst, per boundary / layer

CAUTION (state it in the report): the ground truth was started from IOWA's default-style settings and then hand-corrected, so a
Cyst run can score slightly worse against it and still be closer to the real anatomy. A lower score is not proof that Cyst is worse.

 C. The same 3-worst overlay for the normal-looking eyes: figures\t4_worst3_overlay_normal.png, tables\t4_normal_per_eye.csv.

    python -I week2\scripts\t4_diseased.py
"""
import csv
import sys
from pathlib import Path

import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import w2common as W

INK, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#e3e2de", "#fcfcfb"
C_DEFAULT, C_CYST = "#1baf7a", "#6250d6"                  # categorical slots 3 and 7 (validated pair)
plt.rcParams.update({"font.size": 9.5, "axes.facecolor": SURFACE, "figure.facecolor": SURFACE, "text.color": INK,
                     "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED, "axes.edgecolor": MUTED})
CAUTION = ("Caution: the ground truth was started from IOWA's default-style settings and then hand-corrected. A higher error for "
           "Cyst against this GT does not prove that Cyst is worse.")


def table(name, group="diseased"):
    with open(W.TABLES / name, newline="") as f:
        return [r for r in csv.DictReader(f) if r["variant"] == "original" and r["image_mode"] == "1" and r["group"] == group]


def write_csv(path, rows):
    with open(path, "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        wr.writeheader()
        wr.writerows([{k: (f"{v:.4f}" if isinstance(v, float) else v) for k, v in r.items()} for r in rows])


def runs_by_key(group="diseased"):
    out = {}
    for x in W.find_results():
        if x["config"] in ("default", "cyst"):
            r = W.load_run(x["path"])
            if r["image_mode"] and r["group"] == group:
                out[(r["eye"], r["config"])] = r
    return out


def overlay_figure(worst, runs, title, fname):
    """The worst images: OCT B-scan with GT (solid) and IOWA (dashed) boundaries on top, RMSE per boundary as bars below."""
    fig = plt.figure(figsize=(5.2 * len(worst), 7.6), constrained_layout=True)
    gs = fig.add_gridspec(2, len(worst), height_ratios=[1.35, 1])
    for k, r in enumerate(worst):
        run = runs.get((r["eye"], "default"))
        if run is None:
            continue
        bscan = int(r["a"])
        img = cv2.imread(str(W.OCT_DIR / r["eye"] / f"{bscan}.bmp"), cv2.IMREAD_GRAYSCALE)
        lo = int(max(0, run["gt"][0, 0].min() - 40))
        hi = int(min(639, max(run["gt"][5, 0].max(), run["iowa"][5, 0].max()) + 70))
        ax = fig.add_subplot(gs[0, k])
        ax.imshow(img[lo:hi], cmap="gray", aspect="auto", extent=(0, 304 * W.UM_SIDE / 1000, hi, lo), interpolation="bilinear")
        xs = np.arange(304) * W.UM_SIDE / 1000
        for g, nm in enumerate(W.GT_BOUNDARIES):
            col = np.array(W.BOUNDARY_RGB[g]) / 255
            ax.plot(xs, run["gt"][g, 0], "-", color=col, lw=1.1)
            ax.plot(xs, run["iowa"][g, 0], "--", color=col, lw=1.1)
        ax.set_title(f"{r['eye']}, B-scan {bscan}: RMSE {float(r['rmse_ALL']):.1f} um", loc="left")
        ax.set_xlabel("Column position (mm)")
        ax.set_ylabel("Depth (pixels; 1 px = 3.125 um)" if k == 0 else "")
        bx = fig.add_subplot(gs[1, k])
        vals = [float(r[f"rmse_{nm}"]) for nm in W.GT_BOUNDARIES]
        bx.bar(range(6), vals, color=[np.array(c) / 255 for c in W.BOUNDARY_RGB], edgecolor=SURFACE, linewidth=1.2, zorder=2)
        bx.set_xticks(range(6))
        bx.set_xticklabels(W.GT_BOUNDARIES, fontsize=8, rotation=30)
        bx.set_ylabel("RMSE vs GT (um)" if k == 0 else "")
        bx.grid(axis="y", color=GRID, zorder=0)
        for s in ("top", "right"):
            bx.spines[s].set_visible(False)
    fig.suptitle(title, fontsize=11, x=0.01, ha="left")
    fig.savefig(W.FIGS / fname, dpi=140)
    plt.close(fig)
    print(f"saved figures\\{fname}")


def part_a(scores, runs):
    dflt = sorted([r for r in scores if r["config"] == "default"], key=lambda r: -float(r["rmse_ALL"]))
    if not dflt:
        print("[A] no diseased Default results yet")
        return
    keep = ["eye", "a"] + [c for c in dflt[0] if c.startswith("rmse_") or c.startswith("dice_")]
    write_csv(W.TABLES / "t4_diseased_per_eye.csv", [dict({k: r[k] for k in keep}, bscan=r["a"]) for r in dflt])
    stats, notes = [], []
    for r in dflt:
        run = runs.get((r["eye"], "default"))
        if run is None:
            continue
        err = (run["iowa"][:, 0, :] - run["gt"][:, 0, :]) * run["um"]
        cross = int((~W.quality_mask(run["iowa"])).sum())
        for g, nm in enumerate(W.GT_BOUNDARIES):
            e = err[g]
            stats.append(dict(eye=r["eye"], bscan=r["a"], boundary=nm, rmse_um=np.sqrt((e ** 2).mean()),
                              max_abs_error_um=np.abs(e).max(), column_of_max=int(np.abs(e).argmax()) + 1,
                              share_cols_over_10um=float((np.abs(e) > 10).mean()), mean_signed_error_um=e.mean(),
                              crossing_columns=cross))
    if stats:
        write_csv(W.TABLES / "t4_failure_stats.csv", stats)
    worst = dflt[:3]
    for r in worst:
        s = [x for x in stats if x["eye"] == r["eye"]]
        if not s:
            continue
        top = max(s, key=lambda x: x["rmse_um"])
        notes.append(f"Eye {r['eye']} (B-scan {r['a']}): overall RMSE {float(r['rmse_ALL']):.2f} um. Largest error on {top['boundary']} "
                     f"(RMSE {top['rmse_um']:.2f} um); its worst column is {top['column_of_max']} "
                     f"({(top['column_of_max'] - 1) * W.UM_SIDE / 1000:.2f} mm from the left edge) with {top['max_abs_error_um']:.1f} um; "
                     f"{100 * top['share_cols_over_10um']:.0f}% of its columns are off by more than 10 um; "
                     f"boundaries cross in {top['crossing_columns']} column(s).")
    (W.TABLES / "t4_notes.txt").write_text("\n".join(notes) + "\n")
    print("\n".join(notes))
    overlay_figure(worst, runs, "Three worst diseased images (Default configuration): solid = ground truth, dashed = IOWA",
                   "t4_worst3_overlay.png")


def part_b(scores, thick):
    eyes = sorted({r["eye"] for r in scores if r["config"] == "cyst"})
    eyes = [e for e in eyes if any(r["eye"] == e and r["config"] == "default" for r in scores)]
    if not eyes:
        print("[B] no Cyst results yet")
        return
    sc = {(r["eye"], r["config"]): r for r in scores}
    th = {(r["eye"], r["config"], r["layer"]): r for r in thick if r["source"] == "IOWA"}
    items = [("rmse", f"rmse_{nm}", nm) for nm in W.GT_BOUNDARIES + ["ALL"]] + \
            [("dice", f"dice_{nm}", nm) for nm in W.LAYER_NAMES + ["whole_retina"]]
    long, per = [], {}
    for e in eyes:
        for metric, col, nm in items:
            d, c = float(sc[(e, "default")][col]), float(sc[(e, "cyst")][col])
            long.append(dict(eye=e, metric=metric, item=nm, default=d, cyst=c, cyst_minus_default=c - d))
            per.setdefault((metric, nm), []).append((d, c))
        for nm in W.LAYER_NAMES + [W.TOTAL]:
            if (e, "default", nm) in th and (e, "cyst", nm) in th:
                d, c = float(th[(e, "default", nm)]["rmse_um"]), float(th[(e, "cyst", nm)]["rmse_um"])
                long.append(dict(eye=e, metric="thickness_rmse", item=nm, default=d, cyst=c, cyst_minus_default=c - d))
                per.setdefault(("thickness_rmse", nm), []).append((d, c))
    write_csv(W.TABLES / "t4_cyst_vs_default.csv", long)
    mean_rows = []
    for (metric, nm), v in per.items():
        a = np.array(v)
        mean_rows.append(dict(metric=metric, item=nm, n_eyes=len(v), default_mean=a[:, 0].mean(), default_sd=a[:, 0].std(ddof=1) if len(v) > 1 else float("nan"),
                              cyst_mean=a[:, 1].mean(), cyst_sd=a[:, 1].std(ddof=1) if len(v) > 1 else float("nan"),
                              mean_cyst_minus_default=(a[:, 1] - a[:, 0]).mean()))
    write_csv(W.TABLES / "t4_cyst_vs_default_mean.csv", mean_rows)
    for metric, fname, ylab, ttl in (("rmse", "t4_cyst_vs_default_rmse.png", "RMSE vs GT (um)", "Boundary error"),
                                     ("dice", "t4_cyst_vs_default_dice.png", "Dice overlap with GT", "Layer overlap"),
                                     ("thickness_rmse", "t4_cyst_vs_default_thickness.png", "Thickness RMSE vs GT (um)", "Layer thickness error")):
        names = [k[1] for k in per if k[0] == metric]
        if not names:
            continue
        fig, ax = plt.subplots(figsize=(max(7.5, 1.3 * len(names) + 2), 4.9), constrained_layout=True)
        w = 0.38
        for j, (lab, colr) in enumerate((("Default configuration", C_DEFAULT), ("Cyst configuration", C_CYST))):
            vals = np.array([per[(metric, nm)] for nm in names])[:, :, j]            # (items, eyes)
            m = vals.mean(axis=1)
            sd = vals.std(axis=1, ddof=1) if vals.shape[1] > 1 else np.zeros_like(m)
            x = np.arange(len(names)) + (j - 0.5) * w
            ax.bar(x, m, width=w * 0.9, color=colr, edgecolor=SURFACE, linewidth=1.5, label=f"{lab} (n = {vals.shape[1]} eyes)", zorder=2)
            ax.errorbar(x, m, yerr=np.vstack([np.minimum(sd, m) if vals.min() >= 0 else sd, sd]), fmt="none", ecolor=INK, elinewidth=1.1, capsize=3, zorder=4)
            for u in range(vals.shape[1]):
                ax.plot(x, vals[:, u], "o", ms=3, mfc=INK, mec=SURFACE, mew=0.5, zorder=5)
        ax.set_xticks(np.arange(len(names)))
        ax.set_xticklabels([n.replace("->", "\n->\n").replace(" (", "\n(") for n in names], fontsize=8.5)
        ax.set_ylabel(ylab)
        if metric == "dice":
            ax.set_ylim(0, 1.05)
        ax.set_title(f"{ttl}: Default vs Cyst configuration, diseased eyes\nmean +/- SD across eyes; dots = individual eyes", loc="left", fontsize=10)
        ax.grid(axis="y", color=GRID, zorder=0)
        ax.set_axisbelow(True)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        ax.legend(frameon=False, loc="lower left" if metric == "dice" else "upper left")
        fig.text(0.01, -0.02, CAUTION, fontsize=8, color=MUTED, ha="left", va="top", wrap=True)
        fig.savefig(W.FIGS / fname, dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"saved figures\\{fname}")
    print(f"Cyst vs Default on {len(eyes)} eyes: {', '.join(eyes)}\n{CAUTION}")


if __name__ == "__main__":
    W.FIGS.mkdir(parents=True, exist_ok=True)
    scores = table("scores_per_eye.csv")
    thick = table("thickness_per_eye.csv")
    runs = runs_by_key()
    part_a(scores, runs)
    part_b(scores, thick)
    # C. the same overlay for the normal-looking eyes (they also show large errors at the foveal pit)
    nscores = sorted(table("scores_per_eye.csv", "normal"), key=lambda r: -float(r["rmse_ALL"]))
    if nscores:
        overlay_figure(nscores[:3], runs_by_key("normal"),
                       "Three worst normal-looking images (Default configuration): solid = ground truth, dashed = IOWA",
                       "t4_worst3_overlay_normal.png")
        keep = ["eye", "a"] + [c for c in nscores[0] if c.startswith(("rmse_", "dice_"))]
        write_csv(W.TABLES / "t4_normal_per_eye.csv", [{k: r[k] for k in keep} for r in nscores])
