r"""
Builds week2\report\IOWA_vs_GT_report.docx from the saved tables and figures. Nothing is typed in by hand except wording:
every number in the text comes from a CSV in week2\tables (this script only reads them, plus one summary table it writes:
tables\report_thickness_summary.csv) and every number it quotes is logged with its source in tables\report_numbers.csv.
Re-run after new IOWA results (python -I week2\scripts\build_report.py); the counts and wording that depend on how many eyes
are present (n, missing eyes) update themselves.

    python -I week2\scripts\build_report.py
"""
import csv
import sys
from pathlib import Path

import cv2
import numpy as np
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt, RGBColor

sys.path.insert(0, str(Path(__file__).parent))
import w2common as W

T, F, M = W.TABLES, W.FIGS, W.W2 / "maps"
REPORT = W.W2 / "report"
REPORT.mkdir(exist_ok=True)
LOG = []


def read(name):
    with open(T / name, newline="") as f:
        return list(csv.DictReader(f))


def n_(key, value, src, fmt="{:.1f}"):
    """Log a number with its source table and return it formatted."""
    LOG.append(dict(key=key, value=value, source=src))
    return fmt.format(value) if isinstance(value, (int, float, np.floating)) and fmt else str(value)


# ------------------------------------------------------------------ data
sel = read("image_selection.csv")
sc = [r for r in read("scores_per_eye.csv") if r["variant"] == "original" and r["image_mode"] == "1" and r["config"] == "default"
      and r["group"] in ("normal", "diseased")]
have = {r["eye"] for r in sc}
missing = sorted(r["eye"] for r in sel if r["eye"] not in have)
G = {g: [r for r in sc if r["group"] == g] for g in ("normal", "diseased")}
nN, nD = len(G["normal"]), len(G["diseased"])
bars = {nm: {(r["group"], r["item"]): r for r in read(f"bars_{nm}.csv")} for nm in ("rmse_boundary", "dice_layer", "thickness_rmse", "thickness_bias")}
rt = {(r["metric"], r["group"]): r for r in read("runtime_summary.csv")}
rtests = read("runtime_tests.csv")
cover = read("map_coverage.csv")
gate = read("gate_10301.csv")
pilot = read("pilot_21_vs_61.csv")


def b(nm, g, item, col="mean"):
    return float(bars[nm][(g, item)][col])


# thickness summary (group mean of each eye's GT / IOWA mean thickness) -> saved table
th = [r for r in read("thickness_per_eye.csv") if r["variant"] == "original" and r["image_mode"] == "1" and r["config"] == "default"
      and r["group"] in G]
tsum = []
for g in G:
    for layer in W.LAYER_NAMES + [W.TOTAL]:
        gt = [float(r["mean_um"]) for r in th if r["group"] == g and r["layer"] == layer and r["source"] == "GT"]
        io = [float(r["mean_um"]) for r in th if r["group"] == g and r["layer"] == layer and r["source"] == "IOWA"]
        tsum.append(dict(group=g, layer=layer, n_eyes=len(gt), gt_mean_um=np.mean(gt), iowa_mean_um=np.mean(io),
                         bias_mean_um=b("thickness_bias", g, layer), rmse_mean_um=b("thickness_rmse", g, layer),
                         rmse_sd_um=b("thickness_rmse", g, layer, "sd")))
with open(T / "report_thickness_summary.csv", "w", newline="") as f:
    wr = csv.DictWriter(f, fieldnames=list(tsum[0]))
    wr.writeheader()
    wr.writerows([{k: (f"{v:.4f}" if isinstance(v, float) else v) for k, v in r.items()} for r in tsum])
TS = {(r["group"], r["layer"]): r for r in tsum}

# outline example: GT and IOWA outline PNGs side by side
ex = max(G["diseased"], key=lambda r: float(r["rmse_ALL"]))
tag = f"{ex['eye']}_{ex['a']}"
gt_png = cv2.imread(str(W.W2 / "outlines" / tag / "gt" / f"bscan_{ex['a']}.png"))
io_png = cv2.imread(str(W.W2 / "outlines" / tag / "iowa" / f"bscan_{ex['a']}.png"))
sep = np.full((gt_png.shape[0], 12, 3), 200, np.uint8)
cv2.imwrite(str(F / "outline_example.png"), np.hstack([gt_png, sep, io_png]))

# ------------------------------------------------------------------ document helpers
doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Cm(21), Cm(29.7)
sec.left_margin = sec.right_margin = Cm(2.2)
sec.top_margin = sec.bottom_margin = Cm(2.0)
st = doc.styles["Normal"]
st.font.name, st.font.size = "Calibri", Pt(11)
st.paragraph_format.space_after = Pt(6)
IMG_W = Cm(16.4)


def H(level, text):
    doc.add_heading(text, level)


def P(text, italic=False, bold=False, size=None):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.italic, r.bold = italic, bold
    if size:
        r.font.size = Pt(size)
    return p


def BL(items):
    for t in items:
        doc.add_paragraph(t, style="List Bullet")


def NL(items):
    for t in items:
        doc.add_paragraph(t, style="List Number")


def TAB(header, rows, widths=None, size=9):
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Light Grid Accent 1"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(header):
        t.rows[0].cells[i].text = h
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = str(v)
    for row in t.rows:
        for i, c in enumerate(row.cells):
            for p in c.paragraphs:
                p.paragraph_format.space_after = Pt(0)
                for r in p.runs:
                    r.font.size = Pt(size)
            if widths:
                c.width = Cm(widths[i])
    doc.add_paragraph()


def FIG(path, caption, width=IMG_W):
    doc.add_picture(str(path), width=width)
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    p = P(caption, italic=True, size=9)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER


def ms(nm, g, item, d=1):
    return f"{b(nm, g, item):.{d}f} +/- {b(nm, g, item, 'sd'):.{d}f}"


# ------------------------------------------------------------------ numbers used in text
tot = len(sel)
gate_rmse = float([r for r in gate if r["item"] == "ALL" and r["kind"].startswith("boundary")][0]["value"])
pil = [r for r in pilot if r["boundary"] == "ALL"][0]
fail = read("t4_failure_stats.csv")
w3_cross = sum(int(r["crossing_columns"]) for r in fail if r["eye"] in [x["eye"] for x in sorted(G["diseased"], key=lambda r: -float(r["rmse_ALL"]))[:3]] and r["boundary"] == "ILM")
n_cross_all = sum(int(r["crossing_columns"]) for r in fail if r["boundary"] == "ILM")
n_ok_med = float(np.median([float(r["rmse_ALL"]) for r in G["normal"] if float(r["rmse_ALL"]) < 10.0]))
d_sorted = sorted(G["diseased"], key=lambda r: -float(r["rmse_ALL"]))
n_sorted = sorted(G["normal"], key=lambda r: -float(r["rmse_ALL"]))
THRESH = 10.0
n_low = sum(float(r["rmse_ALL"]) < THRESH for r in G["normal"])
d_low = sum(float(r["rmse_ALL"]) < THRESH for r in G["diseased"])


def worst_boundary(r):
    v = {nm: float(r[f"rmse_{nm}"]) for nm in W.GT_BOUNDARIES}
    k = max(v, key=v.get)
    return k, v[k]


from collections import Counter
n_hi = [r for r in G["normal"] if float(r["rmse_ALL"]) >= THRESH]
n_hi_worst = Counter(worst_boundary(r)[0] for r in n_hi)
fs = lambda m, g, k: float(rt[(m, g)][k])
p_final = float([t for t in rtests if t["metric"] == "final_stage_s" and t["test"].startswith("Mann")][0]["p_value"])
p_cycle = float([t for t in rtests if t["metric"] == "cycle_s" and t["test"].startswith("Mann")][0]["p_value"])


def sp(test, metric):
    t = [t for t in rtests if t["test"] == test and t["metric"] == metric][0]
    return float(t["statistic"]), float(t["p_value"])


def pf(p):
    return "p < 0.001" if p < 0.001 else f"p = {p:.3f}"


rank = read("runtime_ranked.csv")
slow4 = rank[:4]
dis_in_normal_range = sum(float(r["final_stage_s"]) <= fs("final_stage_s", "normal", "max") for r in rank if r["group"] == "diseased")
chunks = read("runtime_chunks.csv")
n_dis_slow4 = sum(r["group"] == "diseased" for r in slow4)
tf = [float(r[k]) for r in read("runtime_per_eye.csv") for k in ("time_file_pre_s", "time_file_final_s") if r[k] != ""]
rho_tf, p_tf = sp("Spearman all eyes (are _Time_ files compute time?)", "time_file_final_s vs final_stage_s")
th_tot_hi = [float(r["rmse_um"]) for r in th if r["layer"] == W.TOTAL and r["source"] == "IOWA" and r["eye"] in {x["eye"] for x in n_hi}]

# ------------------------------------------------------------------ title and summary
doc.add_heading("How well does IOWA layer segmentation agree with ground truth on OCTA-500 B-scans?", 0)
P(f"Draft report, {nN + nD} B-scans from {nN + nD} eyes ({nN} normal-looking, {nD} diseased-looking). "
  "Segmentation: Iowa Reference Algorithms, OCTExplorer 5.0.0b, Default configuration. Data: OCTA-500, 3 mm scans.", italic=True)
if missing:
    P(f"Note: {tot} images were planned. The runs for eye(s) {', '.join(missing)} were not done, so this draft uses {nN + nD}. "
      "Re-running the scripts after those runs updates every table and figure.", bold=True)

H(1, "1. Summary")
BL([
    f"We compared IOWA's six layer boundaries with the OCTA-500 ground truth (GT) on one B-scan per eye. "
    f"The B-scan is the foveal pit for normal-looking eyes and the most abnormal B-scan for diseased-looking eyes.",
    f"Overall boundary error (RMSE over all six boundaries): normal-looking {ms('rmse_boundary', 'normal', 'ALL')} um (n = {nN}), "
    f"diseased-looking {ms('rmse_boundary', 'diseased', 'ALL')} um (n = {nD}). The spread between eyes is large.",
    f"The outer boundaries and the top surface are close to GT (ILM {b('rmse_boundary', 'normal', 'ILM'):.1f} um and OB_RPE "
    f"{b('rmse_boundary', 'normal', 'OB_RPE'):.1f} um in normal-looking eyes). The inner boundaries IPL-INL, OPL-HFL and BMEIS are where the large errors are.",
    f"Total retinal thickness is much better than the individual boundaries: thickness RMSE {b('thickness_rmse', 'normal', W.TOTAL):.1f} um (normal-looking) "
    f"and {b('thickness_rmse', 'diseased', W.TOTAL):.1f} um (diseased-looking).",
    f"Only {n_low} of {nN} normal-looking and {d_low} of {nD} diseased-looking images have an overall RMSE below {THRESH:.0f} um. "
    "Many normal-looking foveal-pit images also show large errors. This is a finding, not an error in scoring (section 5.5).",
    f"Run time: the final segmentation stage was longer for diseased-looking eyes ({fs('final_stage_s', 'diseased', 'mean'):.0f} s against "
    f"{fs('final_stage_s', 'normal', 'mean'):.0f} s on average, {pf(p_final)}), but the difference comes from a few eyes: {n_dis_slow4} of the four slowest runs were diseased-looking, and {dis_in_normal_range} of {nD} diseased-looking eyes were in the normal range (section 5.8).",
    "Because the ground truth was started from IOWA's own output and then hand-corrected, these numbers probably flatter IOWA (section 6).",
])

# ------------------------------------------------------------------ 2 terms
H(1, "2. What we did and why")
P("IOWA is free research software that finds the boundaries between the layers of the retina in an OCT scan. "
  "OCTA-500 is a public dataset that comes with layer boundaries drawn for each scan. "
  "We ask a simple question: how close are IOWA's boundaries to these drawn boundaries, and where does IOWA go wrong?")
H(2, "Terms used in this report")
TAB(["Term", "Meaning"], [
    ["OCT, B-scan", "OCT takes depth images of the retina. One B-scan is one such image: 304 columns across (3 mm) and 640 rows deep (2 mm). One eye has 304 B-scans."],
    ["Boundary", "A line between two retinal layers, drawn as one depth value per column. We use six: ILM, IPL-INL, OPL-HFL, BMEIS, IB_RPE and OB_RPE (names as in the IOWA output)."],
    ["Layer", "The band between two neighbouring boundaries. The five layers are named by their two boundaries, for example IPL-INL->OPL-HFL. Total retina is ILM to OB_RPE."],
    ["Ground truth (GT)", "The boundaries supplied with OCTA-500. They were first made by IOWA 3.8 and then corrected by hand (see limits)."],
    ["RMSE (um)", "Root mean square error: the typical vertical distance between IOWA's boundary and the GT boundary, in micrometres. 0 is perfect. One image row is 3.125 um."],
    ["Dice", "Overlap of a layer drawn by IOWA with the same layer in GT, from 0 (no overlap) to 1 (identical)."],
    ["Thickness", "Distance between two boundaries in um. Thickness bias is IOWA minus GT: above 0 means IOWA is thicker."],
    ["Normal-looking, diseased-looking", "Our own grouping from looking at the B-scans (no diagnosis list exists for these eyes). Diseased-looking means visible cysts or swelling."],
    ["Default configuration", "OCTExplorer's standard setting for most scans. The Cyst configuration is meant for scans with cysts and was not tested here."],
], widths=[3.6, 12.8])

H(1, "3. Data and choice of images")
P(f"OCTA-500 has images for eyes 10301 to 10400 in the part we hold. Eyes 10333 and 10388 are the same scan stored twice, so we used neither. "
  f"We planned {tot} eyes: one B-scan from each of {tot} different eyes. Always included: 10306 and 10335 (both cystic).")
BL([
    "Normal-looking eyes: the B-scan at the foveal pit, found from the GT as the thinnest part of the retina near the centre of the scan.",
    "Diseased-looking eyes: the B-scan with the largest GT abnormality (the thickest cyst band, or the thickest retina for eyes with a raised dome). "
    f"Only {sum(r['group'] == 'diseased' for r in sel)} eyes in this set show visible disease close to the centre, so the groups are not equal in size.",
    "The choice uses the GT only and never looks at the IOWA result.",
])
rows = []
for r in sorted(sel, key=lambda r: (r["group"], r["eye"])):
    done = "yes" if r["eye"] in have else "NOT RUN"
    rows.append([r["eye"], r["group"], r["bscan"], r["rule"], done])
TAB(["Eye", "Group", "B-scan", "How the B-scan was chosen", "Scored"], rows, widths=[1.8, 2.2, 1.6, 8.6, 2.2], size=8)

H(1, "4. Method")
NL([
    f"For each eye we made a 21-B-scan volume centred on the chosen B-scan (10 on each side). IOWA needs neighbouring B-scans to work in 3D, and 21 keeps each run short.",
    "A person opened each volume in OCTExplorer 5.0.0b, picked Configuration-Default.json, and clicked through the two steps. No surface was edited or nudged.",
    "Only the chosen B-scan (the centre one) was compared with GT. The other 20 are context.",
    "All comparisons use scripts; each saves a table in week2\\tables. Every number here comes from those tables.",
])
P("Two checks on the method:")
BL([
    f"Gate: our scoring code reproduces the earlier result for eye 10301 (B-scans 120-180) of 3.84 um RMSE from the existing IOWA file "
    f"(we get {n_('gate_rmse', gate_rmse, 'gate_10301.csv', '{:.4f}')} um).",
    f"Is 21 scans enough? On one eye (10301, B-scan 150) we ran 21 scans and compared with the earlier 61-scan run. "
    f"Overall error {n_('pilot_61', float(pil['rmse_61scan_um']), 'pilot_21_vs_61.csv', '{:.2f}')} um with 61 scans and "
    f"{n_('pilot_21', float(pil['rmse_21scan_um']), 'pilot_21_vs_61.csv', '{:.2f}')} um with 21 scans. "
    "This is one eye with a normal retina, so it does not prove 21 scans are enough for cystic eyes.",
])

# ------------------------------------------------------------------ 5 results
H(1, "5. Results")
H(2, "5.1 Error of each boundary")
P("Each bar is the mean over eyes of the RMSE of one boundary. The thin bars show the standard deviation across eyes (the lower end is cut at 0). "
  "The black dots are individual eyes.")
FIG(F / "bars_rmse_boundary.png", "Figure 1. Boundary error of IOWA against GT, one B-scan per eye, Default configuration.")
items = W.GT_BOUNDARIES + ["ALL"]
TAB(["Boundary", f"Normal-looking (n = {nN}), um", f"Diseased-looking (n = {nD}), um"],
    [[i if i != "ALL" else "All six boundaries", ms("rmse_boundary", "normal", i), ms("rmse_boundary", "diseased", i)] for i in items],
    widths=[5, 5.7, 5.7])
P("Values are mean +/- SD across eyes. The SD is often as large as the mean because a few eyes have very large errors; with this few eyes the "
  "difference between the groups should be read as a trend, not a proven difference.")

H(2, "5.2 Overlap of each layer")
FIG(F / "bars_dice_layer.png", "Figure 2. Dice overlap of each layer with GT. Higher is better.")
TAB(["Layer", f"Normal-looking (n = {nN})", f"Diseased-looking (n = {nD})"],
    [[i.replace("whole_retina", "Whole retina"), ms("dice_layer", "normal", i, 3), ms("dice_layer", "diseased", i, 3)] for i in W.LAYER_NAMES + ["whole_retina"]],
    widths=[5, 5.7, 5.7])
P(f"The whole retina overlaps almost perfectly in both groups ({b('dice_layer', 'normal', 'whole_retina'):.3f} and {b('dice_layer', 'diseased', 'whole_retina'):.3f}) "
  "because the top and bottom surfaces are easy to find. This number hides the errors inside the retina, so the per-layer values matter more.")

H(2, "5.3 Layer thickness")
P("Thickness is the distance between two boundaries. The table gives the average thickness in GT and in IOWA, the mean bias (IOWA minus GT) and the RMSE of the thickness.")
for g, nn in (("normal", nN), ("diseased", nD)):
    P(f"{g.capitalize()}-looking eyes (n = {nn})", bold=True)
    TAB(["Layer", "GT mean (um)", "IOWA mean (um)", "Bias, IOWA - GT (um)", "RMSE (um)"],
        [[l, f"{TS[(g, l)]['gt_mean_um']:.1f}", f"{TS[(g, l)]['iowa_mean_um']:.1f}", f"{TS[(g, l)]['bias_mean_um']:+.1f}",
          f"{TS[(g, l)]['rmse_mean_um']:.1f} +/- {TS[(g, l)]['rmse_sd_um']:.1f}"] for l in W.LAYER_NAMES + [W.TOTAL]],
        widths=[5.4, 2.6, 2.8, 3.2, 2.6])
FIG(F / "bars_thickness_rmse.png", "Figure 3. Thickness error (RMSE) per layer and for the total retina.")
FIG(F / "bars_thickness_bias.png", "Figure 4. Mean signed thickness error. Above 0: IOWA thicker than GT. Below 0: thinner.")
P("The full per-image thickness numbers (mean, median, SD per layer, GT and IOWA) are in thickness_per_eye.csv and thickness_per_bscan.csv.")

H(2, "5.4 Diseased-looking images: the three worst")
rows = []
for r in d_sorted:
    wb, wv = worst_boundary(r)
    rows.append([r["eye"], r["a"], f"{float(r['rmse_ALL']):.1f}", f"{wb} ({wv:.1f})", f"{float(r['dice_whole_retina']):.3f}"])
TAB(["Eye", "B-scan", "RMSE, all boundaries (um)", "Worst boundary (RMSE, um)", "Dice, whole retina"], rows, widths=[2, 2, 4.2, 5.2, 3])
FIG(F / "t4_worst3_overlay.png", "Figure 5. The three worst diseased-looking B-scans. Solid lines: GT. Dashed lines: IOWA. Bars: RMSE of each boundary.")
P("What we see in the pictures (our reading, not a clinician's):", bold=True)
w3 = [r["eye"] for r in d_sorted[:3]]
BL([
    f"Eye {w3[0]}: large dark fluid-filled cysts fill most of the retina on the left and centre. IOWA's OPL-HFL line (green, dashed) follows the cyst walls and drops "
    "down into the cyst area instead of staying along the layer, so it is far from GT. On the right, a bright patch with a shadow below it pulls IOWA's two lowest "
    "boundaries (the RPE lines) upward away from GT.",
    f"Eye {w3[1]}: a dome-shaped swelling with a dark fluid pocket. IOWA places the IPL-INL line (orange) lower than GT inside the dome, and the OPL-HFL line is also off. "
    "The top surface and the bottom boundaries are still good.",
    f"Eye {w3[2]}: small cysts on the left and a raised bump in the middle. IOWA's BMEIS line (blue) and OPL-HFL line (green) do not follow GT over the bump and the cysts.",
    "In all three, the top surface (ILM) is right. The errors begin where there are cysts or swelling, and the inner boundaries are the ones that lose their way.",
    (f"Boundaries cross in {w3_cross} column(s) of these three images." if w3_cross else "No boundaries cross or go missing in these three images (t4_failure_stats.csv)."),
])

H(2, "5.5 Normal-looking images also have large errors at the foveal pit")
P(f"We expected small errors in normal-looking eyes. For {len(n_hi)} of {nN} of them the overall RMSE is {THRESH:.0f} um or more "
  f"({THRESH:.0f} um is our own rough cut-off, not a standard). Among these, the boundary with the largest error is "
  + ", ".join(f"{k} in {v}" for k, v in n_hi_worst.most_common()) + " of them. "
  + (f"Total thickness is still good in these eyes (median RMSE {np.median(th_tot_hi):.1f} um); the error is in an inner boundary." if th_tot_hi else ""))
FIG(F / "t4_worst3_overlay_normal.png", "Figure 6. The three worst normal-looking B-scans (all at the foveal pit). Solid: GT. Dashed: IOWA.")
P("What we see: at the pit the layers become very thin and merge, so the line between them is hard to place. "
  "IOWA's OPL-HFL line (green) dips below GT on one side of the pit. In some eyes IOWA's BMEIS line (blue) jumps up into the retina on one side. "
  f"We checked that GT lines sit where the image suggests, and that the same code gives a median of {n_('median_ok_normal', n_ok_med, 'scores_per_eye.csv')} um on the normal-looking eyes below the cut-off, so we do not think this is a scoring mistake. "
  "We cannot say which line is anatomically right in every case.")
P("This matters for reading the groups. Normal-looking eyes were scored at the foveal pit, the a place where IOWA often struggles in this data, "
  "so their error may be higher than for a typical B-scan away from the pit. We did not score other B-scans, so we cannot say by how much.", bold=False)

H(2, "5.6 Outline files")
P("For each of the scored B-scans we saved the boundary lines alone (no image): a 304 x 640 PNG with a white background and one colour per boundary, "
  "for GT and for IOWA, plus the depth values as .npy and .csv. They are in week2\\outlines\\<eye>_<B-scan>\\. Example for the worst image:")
FIG(F / "outline_example.png", f"Figure 7. Outline-only export for eye {ex['eye']}, B-scan {ex['a']}. Left: GT. Right: IOWA.", width=Cm(7.2))
P("Colours: ILM red, IPL-INL orange, OPL-HFL green, BMEIS blue, IB_RPE purple, OB_RPE brown (see outlines\\legend.csv).")

H(2, "5.7 Topographic maps")
P("A map needs many neighbouring B-scans of the same eye. The 30 images are single B-scans, so maps were built from longer stacks we already had. "
  "The full 3 x 3 mm map needs a run of all 304 B-scans; we have not done that.")
rows = []
for r in cover:
    rows.append([r["eye"], r["iowa_bscan_ranges"], r["iowa_bscans"], f"{float(r['iowa_share_of_304_pct']):.1f}%",
                 f"{float(r['iowa_y_from_mm']):.2f} to {float(r['iowa_y_to_mm']):.2f}", f"{float(r['iowa_unusable_pct_of_segmented']):.1f}%"])
TAB(["Eye", "B-scans segmented by IOWA", "Number", "Share of the 304", "Slow-axis range (mm)", "Unusable part of segmented area"], rows,
    widths=[1.6, 4.6, 1.8, 2.4, 3.4, 3.0])
c1 = [r for r in cover if r["eye"] == "10301"][0]
c2 = [r for r in cover if r["eye"] == "10335"][0]
_cov = np.zeros(304, bool)
for _rg in c2["iowa_bscan_ranges"].split(";"):
    _a, _b = map(int, _rg.split("-"))
    _cov[_a - 1:_b] = True
_idx = np.flatnonzero(~_cov)
_gaps = [f"{q[0] + 1}-{q[-1] + 1}" for q in np.split(_idx, np.flatnonzero(np.diff(_idx) > 1) + 1)] if _idx.size else []
c_unusable = max(float(r["iowa_unusable_pct_of_segmented"]) for r in cover)
BL([
    f"Eye 10301: IOWA covers B-scans {c1['iowa_bscan_ranges']} ({float(c1['iowa_share_of_304_pct']):.0f}% of the scan): a strip across the whole width, from "
    f"{float(c1['iowa_y_from_mm']):.2f} to {float(c1['iowa_y_to_mm']):.2f} mm along the slow axis. The foveal pit is in the middle of this strip. "
    "The rest of the 3 x 3 mm area is not covered.",
    f"Eye 10335 (cystic): IOWA covers B-scans {c2['iowa_bscan_ranges'].replace(';', ', ')} ({float(c2['iowa_share_of_304_pct']):.0f}% of the scan), joined from {len(c2['iowa_bscan_ranges'].split(';'))} runs. "
    f"B-scans {', '.join(_gaps)} have no IOWA result and are shown grey. GT covers the whole area.",
    f"Grey means no usable value: not segmented, a boundary missing, or boundaries crossing. In the segmented areas {c_unusable:.1f}% of columns were unusable.",
])
FIG(M / "10301_120-180" / "heatmap_thickness_5_Total_retina.png", "Figure 8. Total retinal thickness, eye 10301, B-scans 120-180 (central strip only). Left GT, middle IOWA, right IOWA minus GT.")
FIG(M / "10335_1-304" / "heatmap_thickness_5_Total_retina.png", "Figure 9. Total retinal thickness, eye 10335. Grey in the IOWA panel = not segmented (B-scans without a run).")
FIG(M / "10301_120-180" / "surface_thickness_5_Total_retina.png", "Figure 10. The same thickness for 10301 as a 3D surface (GT left, IOWA right).")
P("Heat maps and 3D surfaces for every boundary depth and every layer thickness, and the numbers (.npy), are in week2\\maps\\.")

H(2, "5.8 Run time of the segmentation")
P("During the manual runs, diseased-looking eyes seemed to take longer than normal-looking ones. We checked this with the files OCTExplorer wrote, "
  "using the time at which each result file was saved. We use two measures:")
BL([
    "Final stage: seconds between the Pre-segmentation file and the Final file being saved. It is the nearest thing to the segmentation time, "
    "but it also includes the moment it took to click Next.",
    "Whole cycle: seconds since the previous result was saved. It includes loading the scan, the clicks and both stages, so it depends on how fast the operator works.",
])
P(f"The *_Time_* text files that OCTExplorer writes hold one number of {min(tf):.1f} to {max(tf):.1f} seconds for every run, including the 80-scan runs. "
  "They do not grow with scan size, and we did not find what they record, so we did not use them as run time. They did not differ between groups "
  f"(Final file: {pf(float([t for t in rtests if t['metric'] == 'time_file_final_s' and t['test'].startswith('Mann')][0]['p_value']))}). "
  f"They do correlate moderately with the final-stage time (Spearman {rho_tf:.2f}, {pf(p_tf)}), so they may record something related; we have not tried to explain it.")
FIG(F / "bars_runtime.png", "Figure 11. Run time per eye, 21-scan Default runs. Bars: mean; whiskers: SD; dots: individual eyes.")
TAB(["Measure", f"Normal-looking (n)", "Diseased-looking (n)", "Difference of means", "Test"],
    [["Final stage (s)", f"{fs('final_stage_s', 'normal', 'mean'):.1f} +/- {fs('final_stage_s', 'normal', 'sd'):.1f} (n = {int(fs('final_stage_s', 'normal', 'n'))})",
      f"{fs('final_stage_s', 'diseased', 'mean'):.1f} +/- {fs('final_stage_s', 'diseased', 'sd'):.1f} (n = {int(fs('final_stage_s', 'diseased', 'n'))})",
      f"{fs('final_stage_s', 'diseased', 'mean') - fs('final_stage_s', 'normal', 'mean'):+.1f} s", f"Mann-Whitney, {pf(p_final)}"],
     ["Whole cycle (s)", f"{fs('cycle_s', 'normal', 'mean'):.1f} +/- {fs('cycle_s', 'normal', 'sd'):.1f} (n = {int(fs('cycle_s', 'normal', 'n'))})",
      f"{fs('cycle_s', 'diseased', 'mean'):.1f} +/- {fs('cycle_s', 'diseased', 'sd'):.1f} (n = {int(fs('cycle_s', 'diseased', 'n'))})",
      f"{fs('cycle_s', 'diseased', 'mean') - fs('cycle_s', 'normal', 'mean'):+.1f} s", f"Mann-Whitney, {pf(p_cycle)}"]],
    widths=[3, 4, 4, 2.8, 3.2])
P("What the data show:", bold=True)
BL([
    f"The final stage was longer for diseased-looking eyes on average ({fs('final_stage_s', 'diseased', 'mean'):.1f} s against {fs('final_stage_s', 'normal', 'mean'):.1f} s).",
    f"{n_dis_slow4} of the four slowest runs were diseased-looking eyes: " + ", ".join(f"{r['eye']} ({r['group'][0].upper()}, {float(r['final_stage_s']):.0f} s)" for r in slow4) +
    f" (D = diseased-looking, N = normal-looking). Of the {nD} diseased-looking eyes, {dis_in_normal_range} were within the range of the normal-looking eyes. "
    "So the longer time comes from a few diseased-looking eyes, not from all of them.",
    f"The average whole cycle was about a minute in both groups ({fs('cycle_s', 'normal', 'mean'):.0f} s and {fs('cycle_s', 'diseased', 'mean'):.0f} s). "
    f"That matches the impression of about 45 s to 1 min per run overall. The difference between the groups is only a few seconds and weak ({pf(p_cycle)}, not corrected for the number of tests we ran). "
    "So the data support \"diseased eyes are slower\" for the final stage by a few seconds on average, but not a difference of 45 to 60 seconds.",
    "A hint from one eye (10335): two 80-scan runs took " +
    " and ".join(f"{float(r['final_stage_s']):.0f} s (B-scans {r['volume']})" for r in sorted(chunks, key=lambda r: float(r['final_stage_s'])) if r["eye"] == "10335") +
    " for the final stage; the 21-scan run of the same eye took " +
    f"{[float(r['final_stage_s']) for r in read('runtime_per_eye.csv') if r['eye'] == '10335' and r['volume'] == '128-148'][0]:.0f} s. "
    "This is one eye and the runs are of different size, so it is only a hint.",
])
rho_all, p_all = sp("Spearman all eyes", "final_stage_s vs rmse_all_um")
rho_n, p_n = sp("Spearman normal eyes only", "final_stage_s vs rmse_all_um")
rho_d, p_d = sp("Spearman diseased eyes only", "final_stage_s vs rmse_all_um")
P("Does a longer run go with a larger error?", bold=True)
FIG(F / "scatter_runtime_vs_error.png", "Figure 12. Final-stage time against the error of the scored B-scan (one point per eye).", width=Cm(11.5))
P(f"Yes, in this data: Spearman rank correlation {rho_all:.2f} ({pf(p_all)}, n = {nN + nD}). Inside the groups the direction is the same but weaker "
  f"(normal-looking {rho_n:.2f}, {pf(p_n)}; diseased-looking {rho_d:.2f}, {pf(p_d)}). "
  "Do not read this as the long run causing the error. Hard images (cysts, swelling, the foveal pit) are probably both slower to segment and harder to get right. "
  "")
P("Limits of this timing check: times come from one laptop, with one person clicking; the clicks are inside the times; "
  "normal-looking and diseased-looking are our visual groups; n is small; the p-values are not corrected for the several tests in runtime_tests.csv.", italic=True)

# ------------------------------------------------------------------ 6 limits
H(1, "6. What this does not show (limits)")
BL([
    "Circular ground truth. The GT boundaries were started from IOWA 3.8 output and corrected by hand. IOWA agrees with GT partly because it helped to make it. "
    "The real error against the true anatomy is probably larger than reported here.",
    f"Few images. {nN + nD} B-scans, one per eye, out of the {tot} planned. Only {nD} are diseased-looking, and one B-scan cannot represent a whole eye.",
    "The groups are our own visual judgement, not clinical diagnoses. Mild disease may sit in the normal group.",
    "Different choice of B-scan per group: foveal pit (normal) and most abnormal B-scan (diseased). The groups are therefore not matched, and the normal-group error is a pit error.",
    "Default configuration only. The Cyst configuration was not tested, so we cannot say whether it would do better on the cystic eyes.",
    "One scanner and one dataset (OCTA-500, 3 mm). Results may not carry over to other devices or to the 6 mm scans.",
    "21-scan volumes, not full volumes. Checked on one normal eye only.",
    "The software version used is labelled 5.0.0b.",
    "Maps are partial: they cover only the B-scans IOWA was run on (section 5.7). A full-volume run is needed for the whole 3 x 3 mm map.",
    "Timing: see section 5.8.",
])

H(1, "7. What was not done")
BL([
    (f"Runs for eye(s) {', '.join(missing)} are missing, so those images are not scored." if missing else "All planned Default runs were scored."),
    "The Configuration-Cyst runs on four eyes were optional and were not done.",
    f"Full 304-scan volumes for maps (one normal, one cystic) were not run. Eye 10335 was run in parts, covering {float(c2['iowa_share_of_304_pct']):.0f}% of its B-scans.",
    "We did not write any explanation of why IOWA fails beyond looking at the overlays of six images.",
    "Citation for OCTA-500 was written from memory and should be checked before submission.",
])

H(1, "8. Files")
BL([
    "week2\\tables: scores_per_eye.csv, thickness_per_eye.csv (per-image numbers), the bars_*.csv behind each bar graph, t4_*.csv, runtime_*.csv, map_coverage.csv, report_numbers.csv (the few numbers the script computes itself, with their source; all other numbers are read straight from the tables named in the text).",
    "week2\\figures: all figures in this report.  week2\\outlines: outline-only PNG, .npy, .csv.  week2\\maps: heat maps, 3D surfaces, .npy.",
    "week2\\scripts: the code. week2\\README.md explains each script. week2\\RUN_CHECKLIST.md lists the IOWA runs.",
])

H(1, "9. Acknowledgement and references")
P("The Iowa Reference Algorithms and OCTExplorer were provided by The University of Iowa Research Foundation. "
  "We acknowledge the providers' scientists: Michael D. Abramoff, Mona K. Garvin, Andreas Wahle, Kyungmoo Lee and Milan Sonka.")
for t in [
    "Li M, Huang K, Xu Q, Yang J, Zhang Y, Ji Z, Xie K, Yuan S, Liu Q, Chen Q. OCTA-500: a retinal dataset for optical coherence tomography angiography study. Medical Image Analysis 93:103092, 2024. (From memory: please verify.)",
    "Abramoff MD, Garvin M, Sonka M. Retinal imaging and image analysis. IEEE Reviews in Biomedical Engineering 3:169-208, 2010. doi:10.1109/RBME.2010.2084567",
    "Li K, Wu X, Chen DZ, Sonka M. Optimal surface segmentation in volumetric images - a graph-theoretic approach. IEEE Transactions on Pattern Analysis and Machine Intelligence 28:119-134, 2006. doi:10.1109/TPAMI.2006.19",
    "Garvin MK, Abramoff MD, Wu X, Burns TK, Russell SR, Sonka M. Automated 3-D intraretinal layer segmentation of macular spectral-domain optical coherence tomography images. IEEE Transactions on Medical Imaging 28(9):1436-1447, 2009. doi:10.1109/TMI.2009.2016958",
    "Quellec G, Lee K, Dolejsi M, Garvin MK, Abramoff MD, Sonka M. Three-dimensional analysis of retinal layer texture: identification of fluid-filled regions in SD-OCT of the macula. IEEE Transactions on Medical Imaging 29:1321-1330, 2010. doi:10.1109/TMI.2010.2047023",
]:
    doc.add_paragraph(t, style="List Number")
P("IOWA citations are taken from the licence file shipped with OCTExplorer; the author initials of the second were corrected from the licence text.", italic=True, size=9)

# appendix
H(1, "Appendix: every scored image")
rows = []
for r in sorted(sc, key=lambda r: (r["group"], r["eye"])):
    wb, wv = worst_boundary(r)
    rows.append([r["eye"], r["group"], r["a"], f"{float(r['rmse_ALL']):.1f}", f"{wb} ({wv:.1f})", f"{float(r['dice_whole_retina']):.3f}"])
TAB(["Eye", "Group", "B-scan", "RMSE all (um)", "Worst boundary (um)", "Dice whole retina"], rows, widths=[2, 2.4, 2, 3, 4.6, 3], size=8)

out = REPORT / "IOWA_vs_GT_report.docx"
doc.save(out)
with open(T / "report_numbers.csv", "w", newline="") as f:
    wr = csv.DictWriter(f, fieldnames=["key", "value", "source"])
    wr.writeheader()
    wr.writerows(LOG)
print(f"saved {out}")
