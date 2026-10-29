"""
Tables computed from one run (IOWA result vs GT): scores and layer thickness. Used by score_runs.py, t1_thickness.py,
watch_and_score.py. Every number in the report must come from these saved tables (AGENTS.md rule 3).
In image mode a run is ONE B-scan (the chosen one of a 21-scan volume), so "per eye" = "per image".
"""
import numpy as np

import w2common as W

EYE_KEY = ["eye", "a", "b", "variant", "config"]
SCORE_KEY = EYE_KEY + ["bscan"]
LAYERS = W.LAYER_NAMES + [W.TOTAL]


def _meta(r):
    return dict(eye=r["eye"], group=r["group"], config=r["config"], image_mode=r["image_mode"], a=r["a"], b=r["b"],
                vol_a=r["vol_a"], vol_b=r["vol_b"], variant=r["variant"])


def score_run(r):
    """-> (per-B-scan rows, per-eye row). RMSE in um; Dice of the band between consecutive boundaries (+ whole retina)."""
    gt, io, um = r["gt"], r["iowa"], r["um"]
    n = gt.shape[1]
    ok = W.quality_mask(io)
    rows = []
    for k in range(n):
        d = dict(_meta(r), bscan=r["a"] + k)
        err = (io[:, k, :] - gt[:, k, :]) * um
        for g, nm in enumerate(W.GT_BOUNDARIES):
            d[f"rmse_{nm}"] = np.sqrt((err[g] ** 2).mean())
        d["rmse_ALL"] = np.sqrt((err ** 2).mean())
        for L, nm in enumerate(W.LAYER_NAMES):
            d[f"dice_{nm}"] = W.dice_band(gt[L, k], gt[L + 1, k], io[L, k], io[L + 1, k])
        d["dice_whole_retina"] = W.dice_band(gt[0, k], gt[-1, k], io[0, k], io[-1, k])
        d["flagged_cols"] = int((~ok[k]).sum())
        rows.append(d)
    e = dict(_meta(r), n_bscans=n)
    err = (io - gt) * um
    for g, nm in enumerate(W.GT_BOUNDARIES):
        e[f"rmse_{nm}"] = np.sqrt((err[g] ** 2).mean())
    e["rmse_ALL"] = np.sqrt((err ** 2).mean())
    for L, nm in enumerate(W.LAYER_NAMES):
        e[f"dice_{nm}"] = W.dice_band(gt[L], gt[L + 1], io[L], io[L + 1])
    e["dice_whole_retina"] = W.dice_band(gt[0], gt[-1], io[0], io[-1])
    e["flagged_cols"] = int((~ok).sum())
    e["undefined_regions_in_xml"] = r["n_undefined"]
    e["nudge_file_present"] = int(r["nudge"])
    return rows, e


def thickness_run(r):
    """-> (per-B-scan rows, per-eye rows). Thickness in um for 5 layers + total retina, GT and IOWA.
    Per B-scan: mean thickness over the 304 columns for GT and IOWA, their difference, and the column-wise thickness RMSE.
    Per eye (= per image in image mode): mean / median / SD over all columns (and B-scans), plus bias and RMSE of the
    thickness error (IOWA - GT)."""
    tg = W.thickness_um(r["gt"], r["um"])
    ti = W.thickness_um(r["iowa"], r["um"])
    n = tg.shape[1]
    bs_rows, eye_rows = [], []
    for L, nm in enumerate(LAYERS):
        for k in range(n):
            e = ti[L, k] - tg[L, k]
            bs_rows.append(dict(_meta(r), bscan=r["a"] + k, layer=nm, gt_mean_um=tg[L, k].mean(),
                                iowa_mean_um=ti[L, k].mean(), diff_um=e.mean(), rmse_um=np.sqrt((e ** 2).mean())))
        e = ti[L] - tg[L]
        for src, t in (("GT", tg[L]), ("IOWA", ti[L])):
            eye_rows.append(dict(_meta(r), layer=nm, source=src, n_values=t.size, mean_um=t.mean(),
                                 median_um=np.median(t), sd_um=t.std(),
                                 bias_um=e.mean() if src == "IOWA" else "", rmse_um=np.sqrt((e ** 2).mean()) if src == "IOWA" else ""))
    return bs_rows, eye_rows
