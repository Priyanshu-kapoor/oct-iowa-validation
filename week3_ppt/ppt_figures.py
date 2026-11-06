r"""
Week 3 slide figures (new outputs only; nothing existing is changed).

    python -I week3\ppt_figures.py

Reads week3\progress.csv (eyes marked done), week3\outputs\<ID>\<ID>_Surfaces_Retina-JEI-Final.xml and GT_Layers.
Thickness between boundaries i<j = b_j - b_i per A-scan; error = IOWA - GT in um (3.125 um per depth pixel). No masking,
same as week-2 scoring (w2tables.thickness_run).
Writes week3\tables\pairwise_thickness_error.csv, week3\tables\ppt_numbers.csv and PNGs in week3\figures\ppt\.
"""
import csv
import shutil
import sys
from pathlib import Path

import cv2
import numpy as np
from scipy.ndimage import gaussian_filter

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

ROOT = Path(r"C:\octa500")
sys.path.insert(0, str(ROOT / "week2" / "scripts"))
import w2common as W  # noqa: E402

W3 = ROOT / "week3"
OUT = W3 / "figures" / "ppt"
TAB = W3 / "tables"
CACHE = Path(sys.argv[1]) if len(sys.argv) > 1 else None   # optional folder for an .npz cache
UM = W.UM_DEPTH
NAMES = W.GT_BOUNDARIES
DPI = 200
INK, MUTED, GRID = "#1a1a1a", "#555555", "#e2e2e2"
DIV = LinearSegmentedColormap.from_list("div", ["#2a78d6", "#f2f2f2", "#eb6834"])   # IOWA thinner blue, thicker orange
plt.rcParams.update({"font.size": 11, "axes.facecolor": "white", "figure.facecolor": "white", "savefig.facecolor": "white",
                     "text.color": INK, "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED,
                     "axes.edgecolor": MUTED, "axes.spines.top": False, "axes.spines.right": False})


def done_eyes():
    with open(W3 / "progress.csv", newline="") as f:
        rows = list(csv.DictReader(f))
    done = [r for r in rows if r["status"] == "done"]
    return sorted({r["ID"] for r in done}, key=int), rows


def load_all(eyes):
    """{eye: (gt, iowa)} in depth pixels, (6, 304, 304) each."""
    if CACHE and (CACHE / "w3_bounds.npz").exists():
        z = np.load(CACHE / "w3_bounds.npz")
        if list(z["eyes"]) == eyes:
            gt, io = z["gt"], z["io"]                     # read each array once
            return {e: (gt[k], io[k]) for k, e in enumerate(eyes)}
    d = {}
    for k, e in enumerate(eyes, 1):
        io, info = W.iowa_boundaries(W3 / "outputs" / e / f"{e}_Surfaces_Retina-JEI-Final.xml")
        assert io.shape == (6, 304, 304) and abs(info["um_depth"] - UM) < 0.01, e
        d[e] = (W.gt_layers(e), io)
        print(f"loaded {k}/{len(eyes)} {e}", flush=True)
    if CACHE:
        CACHE.mkdir(parents=True, exist_ok=True)
        np.savez(CACHE / "w3_bounds.npz", eyes=np.array(eyes), gt=np.stack([d[e][0] for e in eyes]),
                 io=np.stack([d[e][1] for e in eyes]))
    return d


def fovea_bscan(gt):
    """Week-2 rule (screen_abnormal.py): min of Gaussian-smoothed GT total thickness, B-scans 101-205, columns 76-227."""
    sm = gaussian_filter((gt[5] - gt[0]) * UM, 3)
    return 100 + int(np.unravel_index(sm[100:205, 76:228].argmin(), (105, 152))[0]) + 1


def save(fig, name):
    fig.savefig(OUT / name, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print("saved", name)


# ------------------------------------------------------------------------------------------------ 1. pairwise
def pairwise(data, eyes):
    pairs = [(i, j) for i in range(6) for j in range(i + 1, 6)]
    rows, pooled = [], {}
    for i, j in pairs:
        per = {"rmse": [], "bias": [], "mae": []}
        s2 = s1 = sa = n = 0.0
        for e in eyes:
            gt, io = data[e]
            err = ((io[j] - io[i]) - (gt[j] - gt[i])) * UM
            per["rmse"].append(np.sqrt((err ** 2).mean()))
            per["bias"].append(err.mean())
            per["mae"].append(np.abs(err).mean())
            s2 += (err ** 2).sum(); s1 += err.sum(); sa += np.abs(err).sum(); n += err.size
        p = dict(rmse=np.sqrt(s2 / n), bias=s1 / n, mae=sa / n)
        pooled[(i, j)] = (p, per)
        row = dict(i=i + 1, j=j + 1, boundary_i=NAMES[i], boundary_j=NAMES[j], adjacent=int(j == i + 1),
                   n_eyes=len(eyes), n_ascans=int(n))
        for m in ("rmse", "bias", "mae"):
            v = np.array(per[m])
            row[f"pooled_{m}_um"] = round(p[m], 4)
            row[f"eye_mean_{m}_um"] = round(v.mean(), 4)
            row[f"eye_sd_{m}_um"] = round(v.std(ddof=1), 4)
        rows.append(row)
    with open(TAB / "pairwise_thickness_error.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print("saved tables\\pairwise_thickness_error.csv")
    for metric, cmap, label, fname in (("rmse", "Blues", "Thickness RMSE, IOWA vs GT (µm)", "pairwise_rmse_heatmap.png"),
                                       ("bias", DIV, "Mean thickness bias, IOWA − GT (µm)", "pairwise_bias_heatmap.png")):
        M = np.full((5, 5), np.nan)                       # rows = j (2..6), cols = i (1..5)
        for (i, j), (p, _) in pooled.items():
            M[j - 1, i] = p[metric]
        if metric == "bias":
            lim = np.nanmax(np.abs(M)); vmin, vmax = -lim, lim
        else:
            vmin, vmax = 0, np.nanmax(M)
        cm = (plt.get_cmap(cmap) if isinstance(cmap, str) else cmap).copy()
        cm.set_bad("white")
        fig, ax = plt.subplots(figsize=(7.2, 6))
        im = ax.imshow(np.ma.masked_invalid(M), cmap=cm, vmin=vmin, vmax=vmax)
        for r in range(5):
            for c in range(5):
                if np.isfinite(M[r, c]):
                    v = M[r, c]
                    frac = abs(v) / vmax if metric == "bias" else (v - vmin) / (vmax - vmin)
                    ax.text(c, r, f"{v:.2f}", ha="center", va="center", fontsize=12,
                            color="white" if frac > 0.6 else INK)
        ax.set_xticks(range(5)); ax.set_xticklabels([f"{k + 1} {NAMES[k]}" for k in range(5)], rotation=30, ha="right")
        ax.set_yticks(range(5)); ax.set_yticklabels([f"{k + 2} {NAMES[k + 1]}" for k in range(5)])
        ax.set_xlabel("Upper boundary i"); ax.set_ylabel("Lower boundary j")
        for s in ax.spines.values():
            s.set_visible(False)
        ax.tick_params(length=0)
        fig.colorbar(im, ax=ax, shrink=0.8).set_label(label)
        save(fig, fname)
    return pooled, rows


# ------------------------------------------------------------------------------------------------ 2. whole retina
def whole_retina(data, eyes, fovea):
    E = np.zeros((len(eyes), 304))
    per_eye = {}
    for k, e in enumerate(eyes):
        gt, io = data[e]
        err = ((io[5] - io[0]) - (gt[5] - gt[0])) * UM             # (304 B-scans, 304 A-scans)
        E[k] = np.sqrt((err ** 2).mean(axis=1))
        per_eye[e] = np.sqrt((err ** 2).mean())
    order = sorted(eyes, key=lambda e: per_eye[e])
    v = np.array([per_eye[e] for e in order])
    mean = v.mean()
    fig, ax = plt.subplots(figsize=(16, 5))
    x = np.arange(len(order))
    ax.bar(x, v, width=0.75, color="#2a6fb0", zorder=3)
    ax.axhline(mean, ls="--", color=INK, lw=1.2, zorder=4)
    ax.text(len(order) * 0.02, mean, f" mean {mean:.2f} µm", va="bottom", fontsize=10, color=INK)
    for e, off in zip(order[-3:], [(-150, 40), (-90, 85), (-45, -10)]):
        xi = order.index(e)
        ax.annotate(f"{e}: {per_eye[e]:.1f} µm", (xi, per_eye[e]), xytext=off, textcoords="offset points",
                    ha="right", va="center", fontsize=10, arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))
    ax.set_xticks(x); ax.set_xticklabels(order, rotation=90, fontsize=8)
    ax.set_xlim(-0.7, len(order) - 0.3)
    ax.set_xlabel("Eye (sorted by error)"); ax.set_ylabel("Whole-retina thickness RMSE (µm)")
    ax.grid(axis="y", color=GRID, zorder=0)
    save(fig, "whole_retina_rmse_per_eye.png")

    fig, ax = plt.subplots(figsize=(14, 12))
    rows = order                                                    # same order as the bar chart: best at top
    M = np.array([E[eyes.index(e)] for e in rows])
    vmax = np.percentile(M, 99)
    im = ax.imshow(M, cmap="Blues", vmin=0, vmax=vmax, aspect="auto", interpolation="nearest",
                   extent=(0.5, 304.5, len(rows) - 0.5, -0.5))
    ax.scatter([fovea[e] for e in rows], range(len(rows)), marker="|", s=40, color="#eb6834", lw=1.6,
               label="Foveal B-scan")
    ax.set_yticks(range(len(rows))); ax.set_yticklabels(rows, fontsize=7)
    ax.set_xlabel("B-scan number"); ax.set_ylabel("Eye (sorted by whole-retina RMSE, best at top)")
    ax.set_xticks([1, 50, 100, 150, 200, 250, 304])
    ax.legend(loc="upper right", bbox_to_anchor=(1.0, 1.04), frameon=False, fontsize=10)
    cb = fig.colorbar(im, ax=ax, shrink=0.6, extend="max")
    cb.set_label(f"Whole-retina thickness RMSE (µm), colour capped at {vmax:.1f}")
    save(fig, "whole_retina_rmse_eye_by_bscan.png")
    return per_eye, E, vmax


# ------------------------------------------------------------------------------------------------ 3. per layer
def per_layer(pooled):
    labels = [f"{NAMES[i]}→{NAMES[i + 1]}" for i in range(5)]
    for metric, ylabel, fname, col in (("rmse", "Thickness RMSE, IOWA vs GT (µm)", "layer_rmse_bars.png", "#2a6fb0"),
                                       ("bias", "Mean thickness bias, IOWA − GT (µm)", "layer_bias_bars.png", "#c06a2b")):
        m = np.array([np.mean(pooled[(i, i + 1)][1][metric]) for i in range(5)])
        s = np.array([np.std(pooled[(i, i + 1)][1][metric], ddof=1) for i in range(5)])
        fig, ax = plt.subplots(figsize=(9, 5))
        x = np.arange(5)
        ax.bar(x, m, width=0.55, color=col, zorder=3)
        low = np.minimum(s, m) if metric == "rmse" else s          # an RMSE cannot go below 0: clip the lower whisker
        ax.errorbar(x, m, yerr=[low, s], fmt="none", ecolor=INK, elinewidth=1.2, capsize=5, zorder=4)
        for xi, mi, si in zip(x, m, s):
            y = mi + si if mi >= 0 else mi - si
            ax.text(xi + 0.08, y, f"{mi:.2f}", ha="left", va="bottom" if mi >= 0 else "top", fontsize=10)
        if metric == "bias":
            ax.axhline(0, color=MUTED, lw=0.8)
        ax.set_xticks(x); ax.set_xticklabels(labels, rotation=15, ha="right")
        ax.set_ylabel(ylabel)
        ax.grid(axis="y", color=GRID, zorder=0)
        save(fig, fname)


# ------------------------------------------------------------------------------------------------ 5. photos
def overlay(data, eye, bscan, fname):
    """Week-2 style (t4_diseased.overlay_figure): grey B-scan, GT solid, IOWA dashed, one colour per boundary."""
    gt, io = data[eye][0][:, bscan - 1, :], data[eye][1][:, bscan - 1, :]
    img = cv2.imread(str(W.OCT_DIR / eye / f"{bscan}.bmp"), cv2.IMREAD_GRAYSCALE)
    lo = int(max(0, min(gt[0].min(), io[0].min()) - 40))
    hi = int(min(639, max(gt[5].max(), io[5].max()) + 70))
    fig, ax = plt.subplots(figsize=(8, 5.2))
    ax.imshow(img[lo:hi], cmap="gray", aspect="auto", extent=(0, 304 * W.UM_SIDE / 1000, hi, lo),
              interpolation="bilinear")
    xs = np.arange(304) * W.UM_SIDE / 1000
    for g, nm in enumerate(NAMES):
        c = np.array(W.BOUNDARY_RGB[g]) / 255
        ax.plot(xs, gt[g], "-", color=c, lw=1.1, label=nm)
        ax.plot(xs, io[g], "--", color=c, lw=1.1)
    ax.plot([], [], "-", color="k", lw=1.1, label="GT (solid)")
    ax.plot([], [], "--", color="k", lw=1.1, label="IOWA (dashed)")
    ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1), frameon=False, fontsize=9)
    ax.set_xlabel("Position across the B-scan (mm)"); ax.set_ylabel("Depth (pixels; 1 px = 3.125 µm)")
    save(fig, fname)


def thickness_map(data, eye, fname):
    """Total retina thickness map (week-2 t3_maps.heatmap layout): GT | IOWA | IOWA - GT; grey = boundaries crossing."""
    gt, io = data[eye]
    tg = np.where(W.quality_mask(gt), (gt[5] - gt[0]) * UM, np.nan)
    ti = np.where(W.quality_mask(io), (io[5] - io[0]) * UM, np.nan)
    d = ti - tg
    lo, hi = np.nanpercentile(np.concatenate([tg.ravel(), ti.ravel()]), [1, 99])
    dl = max(np.nanpercentile(np.abs(d), 99), 1.0)
    ext = (0, 3, 3, 0)
    fig, ax = plt.subplots(1, 3, figsize=(15, 4.6), constrained_layout=True)
    for k, (arr, lab, cm, vl) in enumerate([(tg, "GT thickness (µm)", "Blues", (lo, hi)),
                                            (ti, "IOWA thickness (µm)", "Blues", (lo, hi)),
                                            (d, "IOWA − GT (µm)", DIV, (-dl, dl))]):
        c = (plt.get_cmap(cm) if isinstance(cm, str) else cm).copy()
        c.set_bad("#bdbdb8")
        im = ax[k].imshow(np.ma.masked_invalid(arr), cmap=c, vmin=vl[0], vmax=vl[1], extent=ext, interpolation="nearest")
        ax[k].set_xlabel("Across B-scan (mm)")
        if k == 0:
            ax[k].set_ylabel("B-scan position (mm)")
        fig.colorbar(im, ax=ax[k], shrink=0.85).set_label(lab)
    save(fig, fname)
    return int((~np.isfinite(ti)).sum()), int((~np.isfinite(tg)).sum())


def screenshots():
    from PIL import Image
    src1 = W3 / "_test" / "debug" / "10301_attempt1_142959_file_dialog.png"
    im = Image.open(src1)
    im.crop((0, 0, 1920, 1020)).save(OUT / "screenshot_file_dialog.png")        # drop the Windows taskbar (rows 1020+)
    src2 = W3 / "debug" / "10301_dialog1.png"                                    # already OCTExplorer's own window
    im = Image.open(src2)
    im.resize((im.width * 2, im.height * 2), Image.LANCZOS).save(OUT / "screenshot_click_ok_popup.png")
    print("saved screenshots from", src1.name, "and", src2.name)
    return src1, src2


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    eyes, prog = done_eyes()
    print(f"{len(eyes)} eyes marked done")
    data = load_all(eyes)
    fovea = {e: fovea_bscan(data[e][0]) for e in eyes}
    pooled, prow = pairwise(data, eyes)
    per_eye, E, vmax = whole_retina(data, eyes, fovea)
    per_layer(pooled)
    order = sorted(eyes, key=lambda e: per_eye[e])
    best, worst = order[0], order[-1]
    worst_b = int(E[eyes.index(worst)].argmax()) + 1
    overlay(data, best, fovea[best], f"overlay_good_{best}_bscan{fovea[best]}.png")      # both at the foveal B-scan
    overlay(data, worst, fovea[worst], f"overlay_worst_{worst}_bscan{fovea[worst]}.png")
    n_bad_i, n_bad_g = thickness_map(data, best, f"thickness_map_total_{best}.png")
    screenshots()

    done = [r for r in prog if r["status"] == "done"]
    sec = np.array([float(r["seconds"]) for r in done])
    ram = np.array([float(r["peak_ram_gb"]) for r in done if r["peak_ram_gb"]])
    v = np.array([per_eye[e] for e in eyes])
    bme = {e: np.sqrt((((data[e][1][3] - data[e][0][3]) * UM) ** 2).mean()) for e in eyes}
    bshift = {e: (data[e][1][3] - data[e][0][3]).mean() for e in eyes}
    num = [("eyes_done", len(eyes)), ("eyes_in_list", 78), ("bscans_scored", len(eyes) * 304),
           ("ascans_scored", len(eyes) * 304 * 304),
           ("seconds_per_eye_mean", sec.mean()), ("seconds_per_eye_median", np.median(sec)),
           ("seconds_per_eye_min", sec.min()), ("seconds_per_eye_max", sec.max()),
           ("total_run_hours_sum_of_eyes", sec.sum() / 3600),
           ("first_start", min(r["start"] for r in prog)), ("last_end", max(r["end"] for r in done)),
           ("peak_ram_gb_max", ram.max()), ("peak_ram_gb_mean", ram.mean()),
           ("attempts_not_done", len(prog) - len(done)),
           ("whole_retina_rmse_eye_mean", v.mean()), ("whole_retina_rmse_eye_sd", v.std(ddof=1)),
           ("whole_retina_rmse_eye_median", np.median(v)),
           ("whole_retina_rmse_pooled", pooled[(0, 5)][0]["rmse"]),
           ("best_eyes", ";".join(f"{e}={per_eye[e]:.2f}" for e in order[:3])),
           ("worst_eyes", ";".join(f"{e}={per_eye[e]:.2f}" for e in order[-3:][::-1])),
           ("worst_eye_worst_bscan", f"{worst} B-scan {worst_b} = {E[eyes.index(worst)].max():.2f}"),
           ("worst_eye_fovea_bscan", f"{worst} B-scan {fovea[worst]} = {E[eyes.index(worst)][fovea[worst] - 1]:.2f}"),
           ("best_eye_fovea_bscan", f"{best} B-scan {fovea[best]} = {E[eyes.index(best)][fovea[best] - 1]:.2f}"),
           ("heatmap_colour_cap_um", vmax),
           ("eyes_bmeis_boundary_rmse_over_20um", int(sum(b > 20 for b in bme.values()))),
           ("eyes_bmeis_iowa_above_gt_by_over_10px_on_average", int(sum(d < -10 for d in bshift.values()))),
           ("eyes_bmeis_iowa_below_gt_by_over_10px_on_average", int(sum(d > 10 for d in bshift.values()))),
           ("bmeis_boundary_rmse_eye_median", float(np.median(list(bme.values())))),
           ("ob_rpe_boundary_rmse_worst_eye", float(np.sqrt((((data[worst][1][5] - data[worst][0][5]) * UM) ** 2).mean()))),
           ] + [(f"layer_thickness_rmse_eye_median | {NAMES[i]}->{NAMES[i + 1]}",
                 float(np.median(pooled[(i, i + 1)][1]["rmse"]))) for i in range(5)] + [
           ("map_masked_columns_iowa_gt", f"{n_bad_i};{n_bad_g}"),
           ("fovea_bscan_range", f"{min(fovea.values())}-{max(fovea.values())}")]
    with open(TAB / "ppt_numbers.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["quantity", "value"])
        for k, val in num:
            w.writerow([k, f"{val:.4f}" if isinstance(val, float) else val])
    for k, val in num:
        print(f"{k}: {val}")
    # per-eye whole-retina RMSE, for the record
    with open(TAB / "whole_retina_rmse_per_eye.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["eye", "whole_retina_thickness_rmse_um", "fovea_bscan", "worst_bscan", "worst_bscan_rmse_um"])
        for e in order:
            r = E[eyes.index(e)]
            w.writerow([e, f"{per_eye[e]:.4f}", fovea[e], int(r.argmax()) + 1, f"{r.max():.4f}"])


if __name__ == "__main__":
    main()
