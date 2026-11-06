r"""
Week 3: pairwise thickness error WITHOUT pooling across eyes (adds to ppt_figures.py; changes none of its outputs).

    python -I week3\ppt_figures_per_eye.py [cache_folder]

For each eye and each boundary pair i<j: thickness = b_j - b_i per A-scan, error = IOWA - GT (um), RMSE and bias over all
304 B-scans x 304 A-scans of that eye. Writes
    week3\tables\pairwise_per_eye.csv                 eye, pair, rmse, bias (+ i, j)
    week3\tables\pairwise_median_across_eyes.csv      median (and pooled, for comparison) of the 15 cells
    week3\figures\ppt\pairs_by_eye_rmse.png / pairs_by_eye_bias.png        rows = 15 pairs, columns = 78 eyes
    week3\figures\ppt\small_multiples_rmse.png / small_multiples_bias.png  one triangle per eye, shared colour scale
    week3\figures\ppt\pooled_vs_median_rmse.png / pooled_vs_median_bias.png
"""
import csv
import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).parent))
import ppt_figures as P  # noqa: E402  (same loading, colours, plain style)

UM, OUT, TAB, INK, DIV = P.UM, P.OUT, P.TAB, P.INK, P.DIV
SHORT = ["ILM", "IPL/INL", "OPL/HFL", "BMEIS", "IB_RPE", "OB_RPE"]
PAIRS = [(i, j) for i in range(6) for j in range(i + 1, 6)]
LABEL = {p: f"{SHORT[p[0]]}-{SHORT[p[1]]}" for p in PAIRS}


def per_eye_cells(data, eyes):
    """{metric: array (n_eyes, 15)} in the order of PAIRS."""
    R = np.zeros((len(eyes), 15))
    B = np.zeros((len(eyes), 15))
    S2 = np.zeros(15); S1 = np.zeros(15); N = 0
    for k, e in enumerate(eyes):
        gt, io = data[e]
        for c, (i, j) in enumerate(PAIRS):
            err = ((io[j] - io[i]) - (gt[j] - gt[i])) * UM
            R[k, c] = np.sqrt((err ** 2).mean())
            B[k, c] = err.mean()
            S2[c] += (err ** 2).sum(); S1[c] += err.sum()
        N += err.size
    return dict(rmse=R, bias=B), dict(rmse=np.sqrt(S2 / N), bias=S1 / N)


def triangle(vals):
    """15 values (PAIRS order) -> 5x5 matrix, rows j=2..6, cols i=1..5, NaN in the lower-left empty half."""
    M = np.full((5, 5), np.nan)
    for c, (i, j) in enumerate(PAIRS):
        M[j - 1, i] = vals[c]
    return M


def scale(metric, arr):
    if metric == "rmse":
        return "Blues", 0.0, float(np.percentile(arr, 99))
    lim = float(np.percentile(np.abs(arr), 99))
    return DIV, -lim, lim


def cmap_of(c):
    cm = (plt.get_cmap(c) if isinstance(c, str) else c).copy()
    cm.set_bad("white")
    return cm


UNIT = {"rmse": "Thickness RMSE, IOWA vs GT (µm)", "bias": "Mean thickness bias, IOWA − GT (µm)"}


def pairs_by_eye(cells, order_idx, eyes_sorted, metric):
    A = cells[metric][order_idx].T                                   # (15 pairs, eyes)
    cm, vmin, vmax = scale(metric, A)
    fig, ax = plt.subplots(figsize=(18, 6.2))
    im = ax.imshow(A, cmap=cmap_of(cm), vmin=vmin, vmax=vmax, aspect="auto", interpolation="nearest")
    ax.set_yticks(range(15)); ax.set_yticklabels([LABEL[p] for p in PAIRS], fontsize=10)
    ax.set_xticks(range(len(eyes_sorted))); ax.set_xticklabels(eyes_sorted, rotation=90, fontsize=7.5)
    ax.set_xlabel("Eye (sorted by whole-retina thickness RMSE, best on the left)")
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(length=0)
    cb = plt.colorbar(im, ax=ax, shrink=0.9, pad=0.01, extend="both" if metric == "bias" else "max")
    cb.set_label(f"{UNIT[metric]}\ncolour capped at ±{vmax:.0f}" if metric == "bias" else f"{UNIT[metric]}\ncolour capped at {vmax:.0f}")
    P.save(fig, f"pairs_by_eye_{metric}.png")
    return vmax


def small_multiples(cells, order_idx, eyes_sorted, metric, ncol=13):
    A = cells[metric]
    cm, vmin, vmax = scale(metric, A)
    cm = cmap_of(cm)
    nrow = int(np.ceil(len(eyes_sorted) / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(ncol * 1.35, nrow * 1.55))
    for a in axes.ravel():
        a.axis("off")
    for n, (k, e) in enumerate(zip(order_idx, eyes_sorted)):
        a = axes.ravel()[n]
        im = a.imshow(triangle(A[k]), cmap=cm, vmin=vmin, vmax=vmax, interpolation="nearest")
        a.set_title(e, fontsize=9, pad=2)
    fig.subplots_adjust(left=0.01, right=0.9, top=0.95, bottom=0.08, wspace=0.08, hspace=0.35)
    cax = fig.add_axes([0.92, 0.15, 0.012, 0.7])
    cb = fig.colorbar(im, cax=cax, extend="both" if metric == "bias" else "max")
    cb.set_label(UNIT[metric])
    fig.text(0.01, 0.02, "Each triangle: columns = upper boundary 1 ILM … 5 IB_RPE (left to right), rows = lower boundary "
             "2 IPL/INL … 6 OB_RPE (top to bottom). Eyes sorted by whole-retina RMSE, best first.", fontsize=9, color=P.MUTED)
    P.save(fig, f"small_multiples_{metric}.png")
    return vmax


def pooled_vs_median(cells, pooled, metric):
    med = np.median(cells[metric], axis=0)
    both = np.concatenate([med, pooled[metric]])
    if metric == "rmse":
        cm, vmin, vmax = "Blues", 0.0, float(both.max())
    else:
        lim = float(np.abs(both).max()); cm, vmin, vmax = DIV, -lim, lim
    cm = cmap_of(cm)
    fig, axes = plt.subplots(1, 2, figsize=(15, 6), gridspec_kw=dict(wspace=0.35))
    for a, vals, name in zip(axes, (pooled[metric], med), ("Pooled: all eyes, B-scans and A-scans together",
                                                           "Median across the 78 eyes (typical eye)")):
        M = triangle(vals)
        im = a.imshow(M, cmap=cm, vmin=vmin, vmax=vmax)
        for r in range(5):
            for c in range(5):
                if np.isfinite(M[r, c]):
                    v = M[r, c]
                    frac = abs(v) / vmax if metric == "bias" else v / vmax
                    a.text(c, r, f"{v:.2f}", ha="center", va="center", fontsize=11, color="white" if frac > 0.6 else INK)
        a.set_xticks(range(5)); a.set_xticklabels([f"{k + 1} {SHORT[k]}" for k in range(5)], rotation=30, ha="right")
        a.set_yticks(range(5)); a.set_yticklabels([f"{k + 2} {SHORT[k + 1]}" for k in range(5)])
        a.set_xlabel(f"Upper boundary i\n\n{name}")
        for s in a.spines.values():
            s.set_visible(False)
        a.tick_params(length=0)
    axes[0].set_ylabel("Lower boundary j")
    fig.colorbar(im, ax=axes, shrink=0.8).set_label(UNIT[metric])
    P.save(fig, f"pooled_vs_median_{metric}.png")
    return med


def main():
    eyes, _ = P.done_eyes()
    print(f"{len(eyes)} eyes marked done")
    data = P.load_all(eyes)
    cells, pooled = per_eye_cells(data, eyes)
    whole = cells["rmse"][:, PAIRS.index((0, 5))]
    order_idx = list(np.argsort(whole, kind="stable"))
    eyes_sorted = [eyes[k] for k in order_idx]

    with open(TAB / "pairwise_per_eye.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["eye", "pair", "i", "j", "rmse_um", "bias_um"])
        for k in order_idx:
            for c, (i, j) in enumerate(PAIRS):
                w.writerow([eyes[k], LABEL[(i, j)], i + 1, j + 1, f"{cells['rmse'][k, c]:.4f}", f"{cells['bias'][k, c]:.4f}"])
    print("saved tables\\pairwise_per_eye.csv")

    caps = {}
    for m in ("rmse", "bias"):
        caps[f"pairs_by_eye_{m}"] = pairs_by_eye(cells, order_idx, eyes_sorted, m)
        caps[f"small_multiples_{m}"] = small_multiples(cells, order_idx, eyes_sorted, m)
    med_r = pooled_vs_median(cells, pooled, "rmse")
    med_b = pooled_vs_median(cells, pooled, "bias")

    with open(TAB / "pairwise_median_across_eyes.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["pair", "i", "j", "median_rmse_um", "pooled_rmse_um", "median_bias_um", "pooled_bias_um",
                    "n_eyes_rmse_over_20um"])
        for c, (i, j) in enumerate(PAIRS):
            w.writerow([LABEL[(i, j)], i + 1, j + 1, f"{med_r[c]:.4f}", f"{pooled['rmse'][c]:.4f}", f"{med_b[c]:.4f}",
                        f"{pooled['bias'][c]:.4f}", int((cells["rmse"][:, c] > 20).sum())])
    print("saved tables\\pairwise_median_across_eyes.csv")
    for k, v in caps.items():
        print(f"colour cap {k}: {v:.2f}")


if __name__ == "__main__":
    main()
