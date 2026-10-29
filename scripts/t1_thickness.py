r"""
Task 1: layer thickness (um) for the 5 layers and the total retina, IOWA vs GT.
Saves (updates in place) tables\thickness_per_bscan.csv (one row per B-scan x layer: GT mean, IOWA mean, difference,
column-wise RMSE) and tables\thickness_per_eye.csv (per eye x layer x source: mean, median, SD; for IOWA also bias and RMSE
of the thickness error). Layer k is the band between consecutive boundaries (names in w2common.LAYER_NAMES).

    python -I week2\scripts\t1_thickness.py [--all-variants] [xml ...]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import w2common as W
import w2tables as T

args = [a for a in sys.argv[1:] if not a.startswith("--")]
paths = args or [x["path"] for x in W.find_results(variants=None if "--all-variants" in sys.argv else ("original",))]
if not paths:
    sys.exit("No Final XML found")
for p in paths:
    r = W.load_run(p)
    bs, ey = T.thickness_run(r)
    W.upsert_csv(W.TABLES / "thickness_per_bscan.csv", bs, T.SCORE_KEY + ["layer"])
    W.upsert_csv(W.TABLES / "thickness_per_eye.csv", ey, T.EYE_KEY + ["layer", "source"])
    tot = [x for x in ey if x["layer"] == W.TOTAL]
    g, i = tot[0], tot[1]
    print(f"{r['eye']} {r['a']}-{r['b']} {r['variant']}: total retina GT {g['mean_um']:.1f} um (SD {g['sd_um']:.1f}), "
          f"IOWA {i['mean_um']:.1f} um, bias {i['bias_um']:.2f}, RMSE {i['rmse_um']:.2f}")
print(f"saved tables in {W.TABLES}")
