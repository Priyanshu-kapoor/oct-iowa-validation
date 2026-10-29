r"""
Task 5: BAR graphs of IOWA-vs-GT error, normal vs diseased group, with error bars. Reads only the saved tables
(scores_per_eye.csv, thickness_per_eye.csv), so every plotted number can be traced. 30-image protocol: one B-scan per eye, so
one bar value = the mean over EYES of each eye's own result on its chosen B-scan. Writes four figures to week2\figures\ and the
plotted numbers to week2\tables\bars_<name>.csv:
  bars_rmse_boundary.png     RMSE (um) per boundary + all boundaries
  bars_dice_layer.png        Dice per layer band + whole retina
  bars_thickness_rmse.png    RMSE (um) of layer thickness (IOWA - GT) per layer + total retina
  bars_thickness_bias.png    mean signed thickness error (um): above 0 = IOWA thicker than GT
Bar = mean over eyes; error bar = SD (default) or 95% CI (t-distribution); dots = the individual eyes.
Only Default-configuration runs of the original images are used unless --config cyst is given.

    python -I week2\scripts\t5_bars.py                       # normal + diseased, Default config, image mode
    python -I week2\scripts\t5_bars.py --scope volume --groups other --tag _test10301   # test on the 61-scan 10301 volume
    options: --groups g1 g2 ...  --err sd|ci95  --config default|cyst  --scope image|volume  --tag name (added to file names)
"""
import csv
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

sys.path.insert(0, str(Path(__file__).parent))
import w2common as W

argv = sys.argv[1:]


def opt(name, default, n=1):
    if name not in argv:
        return default
    i = argv.index(name)
    return argv[i + 1] if n == 1 else [a for a in argv[i + 1:] if not a.startswith("--")]


GROUPS = opt("--groups", ["normal", "diseased"], n=0)
ERR = opt("--err", "sd")
CONFIG = opt("--config", "default")
SCOPE = opt("--scope", "image")
TAG = opt("--tag", "")
ULAB = "eye"

COLORS = {"normal": "#2a78d6", "diseased": "#eb6834", "other": "#1baf7a"}     # categorical slots 1, 2, 3 (validated)
INK, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#e3e2de", "#fcfcfb"
plt.rcParams.update({"font.size": 10, "axes.facecolor": SURFACE, "figure.facecolor": SURFACE, "text.color": INK,
                     "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED, "axes.edgecolor": MUTED})


def read(name):
    want = "1" if SCOPE == "image" else "0"
    with open(W.TABLES / name, newline="") as f:
        return [r for r in csv.DictReader(f) if r["variant"] == "original" and r["config"] == CONFIG
                and r["image_mode"] == want and r["group"] in GROUPS]


def collect(rows, items, getter):
    """-> {group: array (n_eyes, n_items)}. getter(row, item) -> float or None. One value per eye (the table has one row per
    eye and config; in volume mode each row is already an all-B-scan result of that eye)."""
    out = {}
    for g in GROUPS:
        units = {}
        for r in rows:
            if r["group"] != g:
                continue
            for j, it in enumerate(items):
                v = getter(r, it)
                if v not in (None, ""):
                    units.setdefault(r["eye"], [np.nan] * len(items))[j] = float(v)
        if units:
            out[g] = np.array(list(units.values()))
    return out


def summarise(vals):
    n = np.isfinite(vals).sum(axis=0)
    mean = np.nanmean(vals, axis=0)
    sd = np.where(n > 1, np.nanstd(vals, axis=0, ddof=1), np.nan)
    ci = np.where(n > 1, stats.t.ppf(0.975, np.maximum(n - 1, 1)) * sd / np.sqrt(np.maximum(n, 1)), np.nan)
    return mean, sd, ci


def bar_figure(name, items, data, ylabel, title, ylim=None, zero_line=False):
    if not data:
        print(f"[skip] {name}: no rows for groups {GROUPS}, config {CONFIG}, scope {SCOPE}")
        return
    fig, ax = plt.subplots(figsize=(max(7.5, 1.35 * len(items) + 2), 4.8), constrained_layout=True)
    ng, w = len(data), 0.8 / len(data)
    table = []
    for k, (g, vals) in enumerate(data.items()):
        mean, sd, ci = summarise(vals)
        err = sd if ERR == "sd" else ci
        x = np.arange(len(items)) + (k - (ng - 1) / 2) * w
        ax.bar(x, mean, width=w * 0.88, color=COLORS.get(g, "#888"), edgecolor=SURFACE, linewidth=1.5,
               label=f"{g} (n = {vals.shape[0]} {ULAB}{'s' if vals.shape[0] != 1 else ''})", zorder=2)
        up = np.where(np.isfinite(err), err, 0)
        lo = np.minimum(up, mean) if np.nanmin(vals) >= 0 else up      # an RMSE / Dice bar cannot go below 0
        ax.errorbar(x, mean, yerr=np.vstack([lo, up]), fmt="none", ecolor=INK, elinewidth=1.1, capsize=3, zorder=4)
        if vals.shape[0] <= 25:                                      # individual eyes as dots
            for u in range(vals.shape[0]):
                ax.plot(x + (u - (vals.shape[0] - 1) / 2) * w * 0.7 / max(vals.shape[0], 1), vals[u], "o", ms=2.8, mfc=INK,
                        mec=SURFACE, mew=0.5, zorder=5)
        for j, it in enumerate(items):
            table.append(dict(group=g, item=it, n_units=int(np.isfinite(vals[:, j]).sum()), mean=mean[j], sd=sd[j], ci95=ci[j],
                              min=np.nanmin(vals[:, j]), max=np.nanmax(vals[:, j])))
    ax.set_xticks(np.arange(len(items)))
    ax.set_xticklabels([i.replace("->", "\n->\n").replace(" (", "\n(") for i in items], fontsize=8.5)
    ax.set_ylabel(ylabel)
    ax.set_title(title.replace(" - ", "\n", 1), fontsize=10, loc="left")
    ax.grid(axis="y", color=GRID, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    if ylim:
        ax.set_ylim(*ylim)
    if zero_line:
        ax.axhline(0, color=MUTED, linewidth=0.9, zorder=3)
    ax.legend(frameon=False, loc="upper left" if name != "bars_dice_layer" else "lower left")
    fig.savefig(W.FIGS / f"{name}{TAG}.png", dpi=150)
    plt.close(fig)
    cols = ["group", "item", "n_units", "mean", "sd", "ci95", "min", "max"]
    with open(W.TABLES / f"{name}{TAG}.csv", "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=cols)
        wr.writeheader()
        wr.writerows([{k: (f"{v:.4f}" if isinstance(v, float) else v) for k, v in r.items()} for r in table])
    print(f"saved {W.FIGS / (name + TAG + '.png')}  and  tables\\{name}{TAG}.csv")


if __name__ == "__main__":
    W.FIGS.mkdir(parents=True, exist_ok=True)
    errname = "SD" if ERR == "sd" else "95% CI"
    what = "one B-scan per eye" if SCOPE == "image" else "all B-scans of each eye's volume"
    sub = f"mean +/- {errname} across eyes; dots = individual eyes; {what}; {CONFIG} configuration"
    sc = read("scores_per_eye.csv")
    bnames = W.GT_BOUNDARIES + ["ALL"]
    bar_figure("bars_rmse_boundary", bnames, collect(sc, bnames, lambda r, it: r.get(f"rmse_{it}")),
               "RMSE vs GT (um)", f"Boundary error of IOWA vs ground truth - {sub}")
    lnames = W.LAYER_NAMES + ["whole_retina"]
    bar_figure("bars_dice_layer", lnames, collect(sc, lnames, lambda r, it: r.get(f"dice_{it}")),
               "Dice overlap with GT (1 = perfect)", f"Layer overlap of IOWA with ground truth - {sub}", ylim=(0, 1.05))
    th = [r for r in read("thickness_per_eye.csv") if r["source"] == "IOWA"]
    tnames = W.LAYER_NAMES + [W.TOTAL]

    def by_layer(col):
        return collect(th, tnames, lambda r, it: r[col] if r["layer"] == it else None)
    bar_figure("bars_thickness_rmse", tnames, by_layer("rmse_um"), "Thickness RMSE vs GT (um)",
               f"Layer thickness error of IOWA - {sub}")
    bar_figure("bars_thickness_bias", tnames, by_layer("bias_um"), "Mean thickness error, IOWA - GT (um)",
               f"Layer thickness bias of IOWA (above 0 = thicker than GT) - {sub}", zero_line=True)
