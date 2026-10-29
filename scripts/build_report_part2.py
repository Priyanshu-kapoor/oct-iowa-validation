r"""
Builds week2\report\IOWA_vs_GT_report_Part2.docx: Part 2 of the report (outline export, topographic maps and run time of the
segmentation, with the limits of the whole study, the references and the appendices). It can be read without Part 1; the accuracy of
the boundaries against the ground truth is reported in Part 1.

Every number in the text is read from a table in week2\tables (this script writes no table and changes no other report file).
The figures are the original PNG files in week2\figures and week2\maps, embedded unchanged. REPO_URL (below) is the address of the
code repository shown as a link in Appendix B.

    python -I week2\scripts\build_report_part2.py
"""
import csv
import sys
from pathlib import Path

import numpy as np
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt

sys.path.insert(0, str(Path(__file__).parent))
import w2common as W

REPO_URL = "https://github.com/Priyanshu-kapoor/oct-iowa-validation"      # address of the code repository
if "<" in REPO_URL:
    print("WARNING: REPO_URL is still a placeholder; Appendix B will show it as is. Edit REPO_URL at the top of this script.")

T, F, M = W.TABLES, W.FIGS, W.W2 / "maps"
REPORT = W.W2 / "report"
REPORT.mkdir(exist_ok=True)


def read(name):
    with open(T / name, newline="") as f:
        return list(csv.DictReader(f))


# ------------------------------------------------------------------ data (same selection and tables as the full report)
sel = read("image_selection.csv")
sc = [r for r in read("scores_per_eye.csv") if r["variant"] == "original" and r["image_mode"] == "1" and r["config"] == "default"
      and r["group"] in ("normal", "diseased")]
have = {r["eye"] for r in sc}
missing = sorted(r["eye"] for r in sel if r["eye"] not in have)
G = {g: [r for r in sc if r["group"] == g] for g in ("normal", "diseased")}
nN, nD = len(G["normal"]), len(G["diseased"])
tot = len(sel)
rt = {(r["metric"], r["group"]): r for r in read("runtime_summary.csv")}
rtests = read("runtime_tests.csv")
cover = read("map_coverage.csv")
chunks = read("runtime_chunks.csv")
rpe = read("runtime_per_eye.csv")
rank = read("runtime_ranked.csv")


def fs(m, g, k):
    return float(rt[(m, g)][k])


def pf(p):
    return "p < 0.001" if p < 0.001 else f"p = {p:.3f}"


def sp(test, metric):
    t = [t for t in rtests if t["test"] == test and t["metric"] == metric][0]
    return float(t["statistic"]), float(t["p_value"])


def mw_p(metric):
    return float([t for t in rtests if t["metric"] == metric and t["test"].startswith("Mann")][0]["p_value"])


p_final, p_cycle = mw_p("final_stage_s"), mw_p("cycle_s")
slow4 = rank[:4]
n_dis_slow4 = sum(r["group"] == "diseased" for r in slow4)
dis_in_normal_range = sum(float(r["final_stage_s"]) <= fs("final_stage_s", "normal", "max") for r in rank if r["group"] == "diseased")
tf = [float(r[k]) for r in rpe for k in ("time_file_pre_s", "time_file_final_s") if r[k] != ""]
rho_tf, p_tf = sp("Spearman all eyes (are _Time_ files compute time?)", "time_file_final_s vs final_stage_s")
rho_all, p_all = sp("Spearman all eyes", "final_stage_s vs rmse_all_um")
rho_n, p_n = sp("Spearman normal eyes only", "final_stage_s vs rmse_all_um")
rho_d, p_d = sp("Spearman diseased eyes only", "final_stage_s vs rmse_all_um")
ex = max(G["diseased"], key=lambda r: float(r["rmse_ALL"]))            # eye shown in the outline example
c1 = [r for r in cover if r["eye"] == "10301"][0]
c2 = [r for r in cover if r["eye"] == "10335"][0]
_cov = np.zeros(304, bool)
for _rg in c2["iowa_bscan_ranges"].split(";"):
    _a, _b = map(int, _rg.split("-"))
    _cov[_a - 1:_b] = True
_idx = np.flatnonzero(~_cov)
_gaps = [f"{q[0] + 1}-{q[-1] + 1}" for q in np.split(_idx, np.flatnonzero(np.diff(_idx) > 1) + 1)] if _idx.size else []
c_unusable = max(float(r["iowa_unusable_pct_of_segmented"]) for r in cover)
n_sel_dis = sum(r["group"] == "diseased" for r in sel)


def worst_boundary(r):
    v = {nm: float(r[f"rmse_{nm}"]) for nm in W.GT_BOUNDARIES}
    k = max(v, key=v.get)
    return k, v[k]


# ------------------------------------------------------------------ document helpers
doc = Document()
doc.core_properties.author = ""
doc.core_properties.title = "IOWA layer segmentation on OCTA-500: outline export, topographic maps and run time"
doc.core_properties.comments = ""
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


def P(text, italic=False, bold=False, size=None, keep=False):
    p = doc.add_paragraph()
    p.paragraph_format.keep_with_next = keep
    r = p.add_run(text)
    r.italic, r.bold = italic, bold
    if size:
        r.font.size = Pt(size)
    return p


def BL(items):
    for t in items:
        doc.add_paragraph(t, style="List Bullet")


def NUM(items):
    """Numbered list that always starts at 1 (typed numbers, so two lists in one document cannot continue each other)."""
    for i, t in enumerate(items, 1):
        p = doc.add_paragraph(f"{i}. {t}")
        p.paragraph_format.left_indent = Cm(0.9)
        p.paragraph_format.first_line_indent = Cm(-0.9)
        p.paragraph_format.space_after = Pt(4)


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
    for k, row in enumerate(t.rows):
        for i, c in enumerate(row.cells):
            for p in c.paragraphs:
                p.paragraph_format.space_after = Pt(0)
                if len(rows) <= 14 and k < len(t.rows) - 1:          # short tables stay on one page
                    p.paragraph_format.keep_with_next = True
                for r in p.runs:
                    r.font.size = Pt(size)
            if widths:
                c.width = Cm(widths[i])
    doc.add_paragraph()


def add_hyperlink(paragraph, url, text):
    """Append a clickable external hyperlink (blue, underlined) to a paragraph."""
    from docx.opc.constants import RELATIONSHIP_TYPE as RT
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    rid = paragraph.part.relate_to(url, RT.HYPERLINK, is_external=True)
    link = OxmlElement("w:hyperlink")
    link.set(qn("r:id"), rid)
    run = OxmlElement("w:r")
    rpr = OxmlElement("w:rPr")
    color = OxmlElement("w:color")
    color.set(qn("w:val"), "0563C1")
    underline = OxmlElement("w:u")
    underline.set(qn("w:val"), "single")
    rpr.append(color)
    rpr.append(underline)
    run.append(rpr)
    t = OxmlElement("w:t")
    t.text = text
    run.append(t)
    link.append(run)
    paragraph._p.append(link)


def FIG(path, caption, width=IMG_W):
    doc.add_picture(str(path), width=width)
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    p = P(caption, italic=True, size=9)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER


# ================================================================== title
doc.add_heading("IOWA layer segmentation on OCTA-500: outline export, topographic maps and run time", 0)
P("30 B-scans from 30 eyes (21 normal-looking, 9 diseased-looking). Iowa Reference Algorithms, OCTExplorer 5.0.0b, "
  "Default configuration. OCTA-500, 3 mm scans.", italic=True)
P("Priyanshu Kapoor, IIT Delhi", bold=True)

# ================================================================== 1 Introduction
H(1, "1. Introduction")
P("IOWA is free research software that finds the boundaries between the layers of the retina in an OCT scan [2-5]. "
  "OCTA-500 is a public dataset that comes with layer boundaries drawn for each scan [1].")
H(2, "1.1 Terms used in this report")
TAB(["Term", "Meaning"], [
    ["OCT, B-scan", "OCT takes depth images of the retina. One B-scan is one such image: 304 columns across (3 mm) and 640 rows deep (2 mm). One eye has 304 B-scans."],
    ["Boundary", "A line between two retinal layers, drawn as one depth value per column. We use six: ILM, IPL-INL, OPL-HFL, BMEIS, IB_RPE and OB_RPE (names as in the IOWA output)."],
    ["Layer", "The band between two neighbouring boundaries. The five layers are named by their two boundaries, for example IPL-INL->OPL-HFL. Total retina is ILM to OB_RPE."],
    ["Ground truth (GT)", "The boundaries supplied with OCTA-500. They were first made by IOWA 3.8 and then corrected by hand (see section 4.1)."],
    ["RMSE (um)", "Root mean square error: the typical vertical distance between IOWA's boundary and the GT boundary, in micrometres. 0 is perfect. One image row is 3.125 um."],
    ["Dice", "Overlap of a layer drawn by IOWA with the same layer in GT, from 0 (no overlap) to 1 (identical)."],
    ["Thickness", "Distance between two boundaries in um. Thickness bias is IOWA minus GT: above 0 means IOWA is thicker."],
    ["Normal-looking, diseased-looking", "Our own grouping from looking at the B-scans (no diagnosis list exists for these eyes). Diseased-looking means visible cysts or swelling."],
    ["Default configuration", "OCTExplorer's standard setting for most scans. The Cyst configuration is meant for scans with cysts and was not tested here."],
], widths=[3.6, 12.8])
H(2, "1.2 Aim of this report")
P("This report describes three outputs of the project: an outline-only export of the boundaries (section 3.1), topographic maps built from "
  "stacks of B-scans (section 3.2), and the time taken by the segmentation runs (section 3.3). "
  "The accuracy of the boundaries against the ground truth is reported in a companion report, "
  "\"How well does IOWA layer segmentation agree with ground truth on OCTA-500 B-scans?\".")

# ================================================================== 2 Methodology
H(1, "2. Methodology")
H(2, "2.1 Data and choice of images")
P(f"OCTA-500 has images for eyes 10301 to 10400 in the part we hold. Eyes 10333 and 10388 are the same scan stored twice, so we used neither. "
  f"We planned {tot} eyes: one B-scan from each of {tot} different eyes. Always included: 10306 and 10335 (both cystic).")
BL([
    "Normal-looking eyes: the B-scan at the foveal pit, found from the GT as the thinnest part of the retina near the centre of the scan.",
    "Diseased-looking eyes: the B-scan with the largest GT abnormality (the thickest cyst band, or the thickest retina for eyes with a raised dome). "
    f"Only {n_sel_dis} eyes in this set show visible disease close to the centre, so the groups are not equal in size.",
    "The choice uses the GT only and never looks at the IOWA result.",
])
if missing:
    P(f"Note: {tot} images were planned. The runs for eye(s) {', '.join(missing)} were not done, so this report uses {nN + nD}.", bold=True)
else:
    P(f"All {tot} planned Default runs were scored.")
P("The eye, group and chosen B-scan of every image are listed in Appendix A (section 8).")

H(2, "2.2 Segmentation procedure")
NUM([
    "For each eye we made a 21-B-scan volume centred on the chosen B-scan (10 on each side). IOWA needs neighbouring B-scans to work in 3D, and 21 keeps each run short.",
    "A person opened each volume in OCTExplorer 5.0.0b, picked Configuration-Default.json, and clicked through the two steps. No surface was edited or nudged.",
    "Only the chosen B-scan (the centre one) was compared with GT. The other 20 are context.",
    "The comparisons were made with the code listed in Appendix B (section 9). The resulting tables are in the repository folder tables/.",
])

H(2, "2.3 Outline export")
P("For each scored B-scan we save the boundary lines alone, without the image, for GT and for IOWA. Each outline image is 304 x 640 pixels with a white "
  "background and one colour per boundary. The depth values of the boundaries are saved as .npy and .csv files (section 3.1).")

H(2, "2.4 Topographic maps")
P("A topographic map shows how the depth of a boundary, or the thickness of a layer, changes across the scanned area of one eye. "
  "It needs many neighbouring B-scans of the same eye. The scored images are single B-scans, so the maps are built from longer stacks of B-scans that we already had (section 3.2). "
  "In a map the horizontal axis is the column position (mm), the vertical axis is the B-scan position (mm), and the value is the depth below the top of the image (um) "
  "of one boundary, or the thickness (um) of one layer or of the total retina. We show GT, IOWA, and IOWA minus GT. "
  "When several runs of one eye cover different B-scans, we join them into one volume (stitching); B-scans that two runs share are averaged. "
  "Grey in a map means no usable value: a B-scan that was not segmented, a boundary that is missing, or boundaries that cross.")

H(2, "2.5 Run-time measurement")
P("We measure run time from the times at which OCTExplorer saved its result files, using two measures. "
  "The final stage is the number of seconds between the Pre-segmentation file and the Final file being saved. It is the nearest thing to the segmentation time, "
  "but it also includes the moment it took to click Next. "
  "The whole cycle is the number of seconds since the previous result was saved. It includes loading the scan, the clicks and both stages, "
  "so it depends on how fast the operator works. "
  "OCTExplorer also writes a *_Time_* text file for each stage. We do not use these files as run time: each holds one number that does not grow with scan size, "
  "and we did not find what it records (section 3.3). "
  "We compare the groups with the Mann-Whitney test and relate time to error with the Spearman rank correlation.")

# ================================================================== 3 Results
H(1, "3. Results")
H(2, "3.1 Outline files")
P("For each of the scored B-scans we saved the boundary lines alone (no image): a 304 x 640 PNG with a white background and one colour per boundary, "
  "for GT and for IOWA, plus the depth values as .npy and .csv. They are in outlines/<eye>_<B-scan>/. Example for the worst image:")
FIG(F / "outline_example.png", f"Figure 1. Outline-only export for eye {ex['eye']}, B-scan {ex['a']}. Left: GT. Right: IOWA.", width=Cm(7.2))
P("Colours: ILM red, IPL-INL orange, OPL-HFL green, BMEIS blue, IB_RPE purple, OB_RPE brown (see outlines/legend.csv).")

H(2, "3.2 Topographic maps")
P("A map needs many neighbouring B-scans of the same eye. The 30 images are single B-scans, so maps were built from longer stacks we already had. "
  "The full 3 x 3 mm map needs a run of all 304 B-scans; we have not done that.")
rows = []
for r in cover:
    rows.append([r["eye"], r["iowa_bscan_ranges"], r["iowa_bscans"], f"{float(r['iowa_share_of_304_pct']):.1f}%",
                 f"{float(r['iowa_y_from_mm']):.2f} to {float(r['iowa_y_to_mm']):.2f}", f"{float(r['iowa_unusable_pct_of_segmented']):.1f}%"])
TAB(["Eye", "B-scans segmented by IOWA", "Number", "Share of the 304", "Slow-axis range (mm)", "Unusable part of segmented area"], rows,
    widths=[1.6, 4.6, 1.8, 2.4, 3.4, 3.0])
BL([
    f"Eye 10301: IOWA covers B-scans {c1['iowa_bscan_ranges']} ({float(c1['iowa_share_of_304_pct']):.0f}% of the scan): a strip across the whole width, from "
    f"{float(c1['iowa_y_from_mm']):.2f} to {float(c1['iowa_y_to_mm']):.2f} mm along the slow axis. The foveal pit is in the middle of this strip. "
    "The rest of the 3 x 3 mm area is not covered.",
    f"Eye 10335 (cystic): IOWA covers B-scans {c2['iowa_bscan_ranges'].replace(';', ', ')} ({float(c2['iowa_share_of_304_pct']):.0f}% of the scan), joined from {len(c2['iowa_bscan_ranges'].split(';'))} runs. "
    f"B-scans {', '.join(_gaps)} have no IOWA result and are shown grey. GT covers the whole area.",
    f"Grey means no usable value: not segmented, a boundary missing, or boundaries crossing. In the segmented areas {c_unusable:.1f}% of columns were unusable.",
])
FIG(M / "10301_120-180" / "heatmap_thickness_5_Total_retina.png", "Figure 2. Total retinal thickness, eye 10301, B-scans 120-180 (central strip only). Left GT, middle IOWA, right IOWA minus GT.")
FIG(M / "10335_1-304" / "heatmap_thickness_5_Total_retina.png", "Figure 3. Total retinal thickness, eye 10335. Grey in the IOWA panel = not segmented (B-scans without a run).")
FIG(M / "10301_120-180" / "surface_thickness_5_Total_retina.png", "Figure 4. The same thickness for 10301 as a 3D surface (GT left, IOWA right).")
P("Heat maps and 3D surfaces for every boundary depth and every layer thickness, and the numbers (.npy), are in maps/.")

H(2, "3.3 Run time of the segmentation")
P("During the manual runs, diseased-looking eyes seemed to take longer than normal-looking ones. We checked this with the files OCTExplorer wrote, "
  "using the time at which each result file was saved. We use two measures:")
BL([
    "Final stage: seconds between the Pre-segmentation file and the Final file being saved. It is the nearest thing to the segmentation time, "
    "but it also includes the moment it took to click Next.",
    "Whole cycle: seconds since the previous result was saved. It includes loading the scan, the clicks and both stages, so it depends on how fast the operator works.",
])
P(f"The *_Time_* text files that OCTExplorer writes hold one number of {min(tf):.1f} to {max(tf):.1f} seconds for every run, including the 80-scan runs. "
  "They do not grow with scan size, and we did not find what they record, so we did not use them as run time. They did not differ between groups "
  f"(Final file: {pf(mw_p('time_file_final_s'))}). "
  f"They do correlate moderately with the final-stage time (Spearman {rho_tf:.2f}, {pf(p_tf)}), so they may record something related; we have not tried to explain it.")
FIG(F / "bars_runtime.png", "Figure 5. Run time per eye, 21-scan Default runs. Bars: mean; whiskers: SD; dots: individual eyes.")
TAB(["Measure", "Normal-looking (n)", "Diseased-looking (n)", "Difference of means", "Test"],
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
    f"{[float(r['final_stage_s']) for r in rpe if r['eye'] == '10335' and r['volume'] == '128-148'][0]:.0f} s. "
    "This is one eye and the runs are of different size, so it is only a hint.",
])
P("Does a longer run go with a larger error?", bold=True, keep=True)
FIG(F / "scatter_runtime_vs_error.png", "Figure 6. Final-stage time against the error of the scored B-scan (one point per eye).", width=Cm(11.5))
P(f"Yes, in this data: Spearman rank correlation {rho_all:.2f} ({pf(p_all)}, n = {nN + nD}). Inside the groups the direction is the same "
  f"(normal-looking {rho_n:.2f}, {pf(p_n)}; diseased-looking {rho_d:.2f}, {pf(p_d)}). "
  "Do not read this as the long run causing the error. Hard images (cysts, swelling, the foveal pit) are probably both slower to segment and harder to get right.")
P("Limits of this timing check: times come from one laptop, with one person clicking; the clicks are inside the times; "
  "normal-looking and diseased-looking are our visual groups; n is small; the p-values are not corrected for the several tests in tables/runtime_tests.csv.", italic=True)

# ================================================================== 4 Discussion
H(1, "4. Discussion")
P("The outline export keeps only the boundary lines of GT and of IOWA for each scored B-scan, as images and as depth values (section 3.1). "
  "Because the image is left out, the two sets of boundaries can be compared as curves.")
P(f"The maps are partial. For eye 10301 IOWA covers B-scans {c1['iowa_bscan_ranges']}, {float(c1['iowa_share_of_304_pct']):.0f}% of the scan, "
  f"a strip across the whole width from {float(c1['iowa_y_from_mm']):.2f} to {float(c1['iowa_y_to_mm']):.2f} mm along the slow axis with the foveal pit in the middle. "
  f"For eye 10335 IOWA covers B-scans {c2['iowa_bscan_ranges'].replace(';', ', ')}, {float(c2['iowa_share_of_304_pct']):.0f}% of the scan, joined from "
  f"{len(c2['iowa_bscan_ranges'].split(';'))} runs; B-scans {', '.join(_gaps)} have no IOWA result and are shown grey, while GT covers the whole area. "
  f"In the segmented areas {c_unusable:.1f}% of columns were unusable. The full 3 x 3 mm map needs a run of all 304 B-scans, which we have not done (section 3.2).")
P(f"The final stage of the segmentation was longer for diseased-looking eyes on average ({fs('final_stage_s', 'diseased', 'mean'):.1f} s against "
  f"{fs('final_stage_s', 'normal', 'mean'):.1f} s, {pf(p_final)}). This comes from a few eyes: {n_dis_slow4} of the four slowest runs were diseased-looking, "
  f"and {dis_in_normal_range} of the {nD} diseased-looking eyes were within the range of the normal-looking eyes (section 3.3).")
P(f"Longer final stages go with larger errors: the Spearman rank correlation between the final-stage time and the error of the scored B-scan is {rho_all:.2f} "
  f"({pf(p_all)}, n = {nN + nD}), and the direction is the same inside both groups. "
  "This does not show that the long run causes the error. Hard images (cysts, swelling, the foveal pit) are probably both slower to segment and harder to get right.")
H(2, "4.1 Limitations")
BL([
    "Circular ground truth. The GT boundaries were started from IOWA 3.8 output and corrected by hand. IOWA agrees with GT partly because it helped to make it. "
    "The real error against the true anatomy is probably larger than reported here.",
    f"Few images. {nN + nD} B-scans, one per eye, out of the {tot} planned. Only {nD} are diseased-looking, and one B-scan cannot represent a whole eye.",
    "The groups are our own visual judgement, not clinical diagnoses. Mild disease may sit in the normal group.",
    "Different choice of B-scan per group: foveal pit (normal) and most abnormal B-scan (diseased). The groups are therefore not matched, and the normal-group error is a pit error.",
    "Default configuration only. The Cyst configuration was not tested, so we cannot say whether it would do better on the cystic eyes.",
    "One scanner and one dataset (OCTA-500, 3 mm). Results may not carry over to other devices or to the 6 mm scans.",
    "21-scan volumes, not full volumes. The comparison of 21-scan and 61-scan volumes was made on one normal eye only.",
    "The software version used is labelled 5.0.0b.",
    "Maps are partial: they cover only the B-scans IOWA was run on (section 3.2). A full-volume run is needed for the whole 3 x 3 mm map.",
    "Timing: the times come from one laptop with one person clicking, and the clicks are inside the times; n is small; the p-values are not corrected for the several tests (section 3.3).",
])

# ================================================================== 5 Conclusion
H(1, "5. Conclusion")
P(f"We saved outline-only exports of the GT and IOWA boundaries for each of the {nN + nD} scored B-scans. "
  f"The topographic maps cover only the B-scans that IOWA was run on: {float(c1['iowa_share_of_304_pct']):.0f}% of the scan for eye 10301 and "
  f"{float(c2['iowa_share_of_304_pct']):.0f}% for eye 10335. "
  f"The final stage of the segmentation was longer for diseased-looking eyes on average ({fs('final_stage_s', 'diseased', 'mean'):.1f} s against {fs('final_stage_s', 'normal', 'mean'):.1f} s), "
  "but this comes from a few eyes. "
  f"Longer final stages go with larger errors (Spearman {rho_all:.2f}), which does not show that the long run causes the error. "
  "These results come from one laptop, one scanner and a small, visually defined grouping.")

# ================================================================== 6 Future work
H(1, "6. Future work")
BL([
    "Run IOWA with the Cyst configuration on the cystic eyes and compare it with the Default configuration. These runs were optional and were not done. "
    "A lower score against GT would not by itself show that the Cyst configuration is worse, because the GT began with IOWA's own output.",
    f"Run IOWA on full 304-scan volumes, one normal-looking and one cystic eye, to obtain complete maps. Eye 10335 was run in parts that cover {float(c2['iowa_share_of_304_pct']):.0f}% of its B-scans.",
    "Explain why IOWA fails. So far we have only looked at overlays of six images, which are described in the companion report.",
])

# ================================================================== 7 References
H(1, "7. References")
P("The Iowa Reference Algorithms and OCTExplorer were provided by The University of Iowa Research Foundation. "
  "We acknowledge the providers' scientists: Michael D. Abramoff, Mona K. Garvin, Andreas Wahle, Kyungmoo Lee and Milan Sonka.")
NUM([
    "Li M, Huang K, Xu Q, Yang J, Zhang Y, Ji Z, Xie K, Yuan S, Liu Q, Chen Q. OCTA-500: A retinal dataset for optical coherence tomography angiography study. arXiv:2012.07261 (v3), 2022.",
    "Abramoff MD, Garvin M, Sonka M. Retinal imaging and image analysis. IEEE Reviews in Biomedical Engineering 3:169-208, 2010. doi:10.1109/RBME.2010.2084567",
    "Li K, Wu X, Chen DZ, Sonka M. Optimal surface segmentation in volumetric images - a graph-theoretic approach. IEEE Transactions on Pattern Analysis and Machine Intelligence 28:119-134, 2006. doi:10.1109/TPAMI.2006.19",
    "Garvin MK, Abramoff MD, Wu X, Burns TK, Russell SR, Sonka M. Automated 3-D intraretinal layer segmentation of macular spectral-domain optical coherence tomography images. IEEE Transactions on Medical Imaging 28(9):1436-1447, 2009. doi:10.1109/TMI.2009.2016958",
    "Quellec G, Lee K, Dolejsi M, Garvin MK, Abramoff MD, Sonka M. Three-dimensional analysis of retinal layer texture: identification of fluid-filled regions in SD-OCT of the macula. IEEE Transactions on Medical Imaging 29:1321-1330, 2010. doi:10.1109/TMI.2010.2047023",
])

# ================================================================== 8 Appendix A
H(1, "8. Appendix A: every scored image")
rows = []
for r in sorted(sc, key=lambda r: (r["group"], r["eye"])):
    wb, wv = worst_boundary(r)
    rows.append([r["eye"], r["group"], r["a"], f"{float(r['rmse_ALL']):.1f}", f"{wb} ({wv:.1f})", f"{float(r['dice_whole_retina']):.3f}"])
TAB(["Eye", "Group", "B-scan", "RMSE all (um)", "Worst boundary (um)", "Dice whole retina"], rows, widths=[2, 2.4, 2, 3, 4.6, 3], size=8)

# ================================================================== 9 Appendix B
H(1, "9. Appendix B: code and files")
_p = P("The code is in the repository ")
add_hyperlink(_p, REPO_URL, REPO_URL)
_p.add_run(". The folders named in this report are folders of that repository:")
BL([
    "tables/: scores_per_eye.csv and thickness_per_eye.csv (per-image numbers), the bars_*.csv behind each bar graph, t4_*.csv, runtime_*.csv and map_coverage.csv.",
    "figures/: all figures in the reports.",
    "outlines/: outline-only PNG, .npy and .csv files.",
    "maps/: heat maps, 3D surfaces and .npy files.",
    "scripts/: the code listed in the table below. README.md explains each script, and RUN_CHECKLIST.md lists the IOWA runs.",
])
readme = (W.W2 / "README.md").read_text(encoding="utf-8").splitlines()
code_rows, started = [], False
for ln in readme:
    if ln.startswith("| Script |"):
        started = True
        continue
    if started and ln.startswith("|---"):
        continue
    if started and ln.startswith("|"):
        cells = [c.strip().replace("`", "").replace("\\", "/") for c in ln.strip().strip("|").split("|")]
        code_rows.append(cells[:3])
    elif started:
        break
if not code_rows:
    sys.exit("script table not found in README.md")
TAB(["Script", "What it does", "Main output"], code_rows, widths=[3.4, 8.2, 4.8], size=8)

out = REPORT / "IOWA_vs_GT_report_Part2.docx"
doc.save(out)
print(f"saved {out}")
