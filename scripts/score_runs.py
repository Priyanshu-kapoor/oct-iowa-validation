r"""
Score IOWA results against GT: per-boundary RMSE (um) and per-layer Dice, per B-scan and per eye.
Saves (and updates in place, no duplicates) tables\scores_per_bscan.csv and tables\scores_per_eye.csv.

    python -I week2\scripts\score_runs.py                 # every original-image Final XML under mhd\ (not *_old folders)
    python -I week2\scripts\score_runs.py --all-variants  # also the denoised variants (median, nlm, ...)
    python -I week2\scripts\score_runs.py path\to\x_Surfaces_Retina-JEI-Final.xml ...
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import w2common as W
import w2tables as T


def score_one(path):
    r = W.load_run(path)
    bs, eye = T.score_run(r)
    W.upsert_csv(W.TABLES / "scores_per_bscan.csv", bs, T.SCORE_KEY)
    W.upsert_csv(W.TABLES / "scores_per_eye.csv", [eye], T.EYE_KEY)
    return r, eye


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    paths = args or [x["path"] for x in W.find_results(variants=None if "--all-variants" in sys.argv else ("original",))]
    if not paths:
        sys.exit("No Final XML found")
    for p in paths:
        r, e = score_one(p)
        print(f"{r['eye']} {r['a']}-{r['b']} {r['variant']:<9} group={r['group']:<8} RMSE {e['rmse_ALL']:.2f} um  "
              f"Dice(retina) {e['dice_whole_retina']:.4f}  flagged cols {e['flagged_cols']}")
    print(f"saved tables in {W.TABLES}")
