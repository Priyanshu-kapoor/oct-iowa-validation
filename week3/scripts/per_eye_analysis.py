r"""
Week 3 pairwise thickness error, PER EYE (no averaging across eyes). Summary numbers are medians [IQR] across eyes and
counts of eyes, never means. Adds new files only (and pairwise_per_eye.csv gains an mae column).

    python -I week3\per_eye_analysis.py [cache_folder]

Writes
  week3\figures\per_eye\<ID>_pairwise.png        RMSE + bias triangle of one eye, colour scales shared by all eyes
  week3\tables\pairwise_per_eye.csv               eye, pair, i, j, rmse_um, bias_um, mae_um
  week3\tables\pairwise_median_iqr.csv            per pair: median [IQR] of RMSE / bias / MAE across eyes, eyes > 10 / 20 um
  week3\tables\representative_eyes.csv            the 3 eyes chosen by rule, with their numbers
  week3\tables\per_eye_summary_numbers.csv        whole-retina median [IQR], colour caps, rule values
  week3\figures\ppt\pair_by_eye_rmse.png / pair_by_eye_bias.png   rows = 15 pairs, columns = eyes; BMEIS rows marked
  week3\figures\ppt\median_triangle.png           median [IQR] across eyes (RMSE and bias)
  week3\figures\ppt\whole_retina_rmse_per_eye_median.png          one bar per eye, dashed MEDIAN line
  week3\figures\ppt\rep_<kind>_<ID>.png and rep_<kind>_<ID>_overlay.png   kind = typical, bmeis, worst
"""
import csv
import shutil
import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

sys.path.insert(0, str(Path(__file__).parent))
import ppt_figures as P  # noqa: E402  (same data loading, overlay style, plain white style)

UM, OUT, TAB, INK, MUTED, DIV = P.UM, P.OUT, P.TAB, P.INK, P.MUTED, P.DIV
PER = P.W3 / "figures" / "per_eye"
SHORT = ["ILM", "IPL/INL", "OPL/HFL", "BMEIS", "IB_RPE", "OB_RPE"]
PAIRS = [(i, j) for i in range(6) for j in range(i + 1, 6)]
LABEL = {p: f"{SHORT[p[0]]}-{SHORT[p[1]]}" for p in PAIRS}
WHOLE = PAIRS.index((0, 5))
BMEIS_ADJ = [PAIRS.index((2, 3)), PAIRS.index((3, 4))]          # OPL/HFL-BMEIS and BMEIS-IB_RPE (the two layers touching BMEIS)
UNIT = {"rmse": "Thickness RMSE, IOWA vs GT (µm)", "bias": "Thickness bias, IOWA − GT (µm)"}


def cells_per_eye(data, eyes):
    C = {m: np.zeros((len(eyes), 15)) for m in ("rmse", "bias", "mae")}
    for k, e in enumerate(eyes):
        gt, io = data[e]
        for c, (i, j) in enumerate(PAIRS):
            err = ((io[j] - io[i]) - (gt[j] - gt[i])) * UM            # all 304 B-scans x 304 A-scans of this eye
            C["rmse"][k, c] = np.sqrt((err ** 2).mean())
            C["bias"][k, c] = err.mean()
            C["mae"][k, c] = np.abs(err).mean()
    return C


def triangle(vals):
    M = np.full((5, 5), np.nan)                       # rows = lower boundary j (2..6), cols = upper boundary i (1..5)
    for c, (i, j) in enumerate(PAIRS):
        M[j - 1, i] = vals[c]
    return M


def cm(name):
    c = (plt.get_cmap(name) if isinstance(name, str) else name).copy()
    c.set_bad("white")
    return c


def draw_triangle(ax, vals, cmap, vmin, vmax, signed, text=None, fs=11):
    M = triangle(vals)
    im = ax.imshow(M, cmap=cm(cmap), vmin=vmin, vmax=vmax)
    T = triangle(np.arange(15)) if text is not None else None
    for r in range(5):
        for c in range(5):
            if np.isfinite(M[r, c]):
                v = M[r, c]
                frac = min(abs(v) / vmax, 1) if signed else min((v - vmin) / (vmax - vmin), 1)
                s = text[int(T[r, c])] if text is not None else f"{v:.1f}"
                ax.text(c, r, s, ha="center", va="center", fontsize=fs, color="white" if frac > 0.6 else INK)
    ax.set_xticks(range(5)); ax.set_xticklabels([f"{k + 1} {SHORT[k]}" for k in range(5)], rotation=30, ha="right")
    ax.set_yticks(range(5)); ax.set_yticklabels([f"{k + 2} {SHORT[k + 1]}" for k in range(5)])
    ax.set_xlabel("Upper boundary i")
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(length=0)
    return im


def eye_triangle(C, k, eye, caps, path):
    fig, axes = plt.subplots(1, 2, figsize=(14, 6), gridspec_kw=dict(wspace=0.45))
    for ax, m in zip(axes, ("rmse", "bias")):
        signed = m == "bias"
        im = draw_triangle(ax, C[m][k], "Blues" if not signed else DIV, -caps[m] if signed else 0, caps[m], signed)
        fig.colorbar(im, ax=ax, shrink=0.8, extend="both" if signed else "max").set_label(UNIT[m])
    axes[0].set_ylabel("Lower boundary j")
    fig.text(0.01, 0.98, f"Eye {eye}  (all 304 B-scans)", fontsize=13, va="top", color=INK)
    fig.savefig(path, dpi=P.DPI, bbox_inches="tight")
    plt.close(fig)


def pair_by_eye(C, order, eyes, metric, cap):
    A = C[metric][order].T
    signed = metric == "bias"
    fig, ax = plt.subplots(figsize=(18, 6.4))
    im = ax.imshow(A, cmap=cm(DIV if signed else "Blues"), vmin=-cap if signed else 0, vmax=cap, aspect="auto",
                   interpolation="nearest")
    ax.set_yticks(range(15))
    ax.set_yticklabels([("▶ " if 3 in p else "") + LABEL[p] for p in PAIRS], fontsize=10)
    for c, p in enumerate(PAIRS):
        if 3 in p:                                                     # a pair that has BMEIS as one of its two boundaries
            ax.add_patch(Rectangle((-0.5, c - 0.5), A.shape[1], 1, fill=False, ec=INK, lw=1.4))
            ax.get_yticklabels()[c].set_fontweight("bold")
    ax.set_xticks(range(len(order))); ax.set_xticklabels([eyes[k] for k in order], rotation=90, fontsize=7.5)
    ax.set_xlabel("Eye (sorted by whole-retina thickness RMSE, best on the left).  ▶ boxed rows = pairs with BMEIS as one boundary")
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(length=0)
    cb = plt.colorbar(im, ax=ax, shrink=0.9, pad=0.01, extend="both" if signed else "max")
    cb.set_label(f"{UNIT[metric]}\ncolour stops at {'±' if signed else ''}{cap:.0f}")
    P.save(fig, f"pair_by_eye_{metric}.png")


def q(v):
    return np.percentile(v, [50, 25, 75])


def median_triangle(C):
    fig, axes = plt.subplots(1, 2, figsize=(16, 6.6), gridspec_kw=dict(wspace=0.45))
    for ax, m in zip(axes, ("rmse", "bias")):
        stats = np.array([q(C[m][:, c]) for c in range(15)])          # (15, 3) median, Q1, Q3
        signed = m == "bias"
        cap = np.abs(stats[:, 0]).max() if signed else stats[:, 0].max()
        txt = [f"{s[0]:.1f}\n[{s[1]:.1f}, {s[2]:.1f}]" for s in stats]
        im = draw_triangle(ax, stats[:, 0], DIV if signed else "Blues", -cap if signed else 0, cap, signed, text=txt, fs=9.5)
        fig.colorbar(im, ax=ax, shrink=0.8).set_label("Median RMSE across eyes (µm)" if m == "rmse"
                                                      else "Median bias across eyes, IOWA − GT (µm)")
    axes[0].set_ylabel("Lower boundary j")
    fig.text(0.01, 0.01, "Each cell: median across eyes, [25th, 75th percentile] below. Each eye contributes one value "
             "(its own 304 B-scans).", fontsize=9, color=MUTED)
    P.save(fig, "median_triangle.png")


def whole_retina_bars(C, order, eyes):
    v = C["rmse"][order, WHOLE]
    med = np.median(C["rmse"][:, WHOLE])
    fig, ax = plt.subplots(figsize=(16, 5))
    x = np.arange(len(order))
    ax.bar(x, v, width=0.75, color="#2a6fb0", zorder=3)
    ax.axhline(med, ls="--", color=INK, lw=1.2, zorder=4)
    ax.text(len(order) * 0.02, med, f" median {med:.2f} µm", va="bottom", fontsize=10)
    for n, off in zip(range(3), [(-150, 40), (-90, 85), (-45, -10)][::-1]):
        k = order[-1 - n]
        ax.annotate(f"{eyes[k]}: {C['rmse'][k, WHOLE]:.1f} µm", (len(order) - 1 - n, C["rmse"][k, WHOLE]), xytext=off,
                    textcoords="offset points", ha="right", va="center", fontsize=10,
                    arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))
    ax.set_xticks(x); ax.set_xticklabels([eyes[k] for k in order], rotation=90, fontsize=8)
    ax.set_xlim(-0.7, len(order) - 0.3)
    ax.set_xlabel("Eye (sorted by error)"); ax.set_ylabel("Whole-retina thickness RMSE (µm)")
    ax.grid(axis="y", color=P.GRID, zorder=0)
    P.save(fig, "whole_retina_rmse_per_eye_median.png")


def closest_to_median(idx, values):
    """Index (from idx) whose value is closest to the median of values[idx]; a tie goes to the lower value."""
    v = values[idx]
    med = np.median(v)
    best = sorted(zip(np.abs(v - med), v, idx))[0]
    return int(best[2]), float(med)


def main():
    PER.mkdir(parents=True, exist_ok=True)
    eyes, _ = P.done_eyes()
    print(f"{len(eyes)} eyes marked done")
    data = P.load_all(eyes)
    C = cells_per_eye(data, eyes)
    order = list(np.argsort(C["rmse"][:, WHOLE], kind="stable"))
    caps = dict(rmse=float(np.percentile(C["rmse"], 99)), bias=float(np.percentile(np.abs(C["bias"]), 99)))

    with open(TAB / "pairwise_per_eye.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["eye", "pair", "i", "j", "rmse_um", "bias_um", "mae_um"])
        for k in order:
            for c, (i, j) in enumerate(PAIRS):
                w.writerow([eyes[k], LABEL[(i, j)], i + 1, j + 1] + [f"{C[m][k, c]:.4f}" for m in ("rmse", "bias", "mae")])
    print("saved tables\\pairwise_per_eye.csv")

    with open(TAB / "pairwise_median_iqr.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["pair", "i", "j", "adjacent_layer", "n_eyes"] +
                   [f"{m}_{s}_um" for m in ("rmse", "bias", "mae") for s in ("median", "q1", "q3")] +
                   ["n_eyes_rmse_over_10um", "n_eyes_rmse_over_20um"])
        for c, (i, j) in enumerate(PAIRS):
            row = [LABEL[(i, j)], i + 1, j + 1, int(j == i + 1), len(eyes)]
            for m in ("rmse", "bias", "mae"):
                row += [f"{x:.4f}" for x in q(C[m][:, c])]
            row += [int((C["rmse"][:, c] > 10).sum()), int((C["rmse"][:, c] > 20).sum())]
            w.writerow(row)
    print("saved tables\\pairwise_median_iqr.csv")

    for k, e in enumerate(eyes):
        eye_triangle(C, k, e, caps, PER / f"{e}_pairwise.png")
    print(f"saved {len(eyes)} per-eye triangles in figures\\per_eye\\")

    for m in ("rmse", "bias"):
        pair_by_eye(C, order, eyes, m, caps[m])
    median_triangle(C)
    whole_retina_bars(C, order, eyes)

    # ---- representative eyes, chosen by rule
    allidx = np.arange(len(eyes))
    typ, med_whole = closest_to_median(allidx, C["rmse"][:, WHOLE])
    bmeis_val = C["rmse"][:, BMEIS_ADJ].max(axis=1)                 # worse of the two layers touching BMEIS
    fail = allidx[bmeis_val > 20]
    bme, med_bme = closest_to_median(fail, bmeis_val)
    worst = int(np.argmax(C["rmse"][:, WHOLE]))
    reps = [("typical", typ), ("bmeis", bme), ("worst", worst)]
    rows = []
    for kind, k in reps:
        e = eyes[k]
        fb = P.fovea_bscan(data[e][0])
        shutil.copy2(PER / f"{e}_pairwise.png", OUT / f"rep_{kind}_{e}.png")
        P.overlay(data, e, fb, f"rep_{kind}_{e}_overlay.png")
        gt, io = data[e]
        fe = ((io[5, fb - 1] - io[0, fb - 1]) - (gt[5, fb - 1] - gt[0, fb - 1])) * UM
        r = dict(kind=kind, eye=e, fovea_bscan=fb, rank_whole_retina=order.index(k) + 1,
                 whole_retina_rmse_um=round(C["rmse"][k, WHOLE], 4),
                 bmeis_adjacent_max_rmse_um=round(bmeis_val[k], 4),
                 fovea_bscan_whole_retina_rmse_um=round(float(np.sqrt((fe ** 2).mean())), 4))
        for c in range(15):
            r[f"rmse | {LABEL[PAIRS[c]]}"] = round(C["rmse"][k, c], 4)
        for c in range(15):
            r[f"bias | {LABEL[PAIRS[c]]}"] = round(C["bias"][k, c], 4)
        rows.append(r)
    with open(TAB / "representative_eyes.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    print("saved tables\\representative_eyes.csv")

    wq = q(C["rmse"][:, WHOLE])
    nums = [("n_eyes", len(eyes)),
            ("whole_retina_rmse_median", wq[0]), ("whole_retina_rmse_q1", wq[1]), ("whole_retina_rmse_q3", wq[2]),
            ("whole_retina_rmse_min", C["rmse"][:, WHOLE].min()), ("whole_retina_rmse_max", C["rmse"][:, WHOLE].max()),
            ("n_eyes_whole_retina_over_10um", int((C["rmse"][:, WHOLE] > 10).sum())),
            ("n_eyes_bmeis_adjacent_over_20um", len(fail)), ("bmeis_failure_group_median_um", med_bme),
            ("whole_retina_median_used_for_typical", med_whole),
            ("colour_cap_rmse_um", caps["rmse"]), ("colour_cap_bias_um", caps["bias"])]
    with open(TAB / "per_eye_summary_numbers.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["quantity", "value"])
        for a, b in nums:
            w.writerow([a, f"{b:.4f}" if isinstance(b, float) else b])
    for a, b in nums:
        print(f"{a}: {b}")
    for r in rows:
        print({k: r[k] for k in list(r)[:7]})


if __name__ == "__main__":
    main()
