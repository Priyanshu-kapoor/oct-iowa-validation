# week2 - what is here (final scope, 2026-10-28)

Run everything from C:\octa500 with `python -I week2\scripts\<script>`. Scope: 30 B-scans from 30 different eyes, each scored
from a 21-scan IOWA volume centred on it; Default configuration for all; Cyst configuration on 4 diseased eyes; full volumes only
for the topographic maps. Manual steps: `week2\RUN_CHECKLIST.md`.

| script | what it does |
|---|---|
| gate_check.py | rule 4: reproduces 3.84 um for 10301 (B-scans 120-180) from the existing XML. Result 3.8439 um, PASSED |
| screen_abnormal.py | GT-only abnormality screen of all 98 eyes -> tables\abnormal_screening.csv (helps find diseased candidates) |
| make_selection.py | the 30 eyes, chosen B-scan, volume range, run order -> tables\image_selection.csv |
| make_volumes.py | writes the 21-scan .mhd files (step3_make_mhd.py), the pilot, and the Cyst copies in mhd_cyst\<eye>\ |
| make_checklist.py | writes RUN_CHECKLIST.md (35 runs, batches of 10) |
| watch_and_score.py | watches mhd\ and mhd_cyst\, scores each new result (chosen B-scan only), saves tables and run_timing.csv, prints "eye X done"; `--status` = progress and time estimate |
| score_runs.py, t1_thickness.py | same scoring / thickness tables without watching |
| t2_outlines.py | outline-only PNG (GT and IOWA, 304x640, white), .npy, .csv per image -> outlines\ |
| t3_maps.py | en-face maps + 3D surfaces from VOLUMES (not single images); `--stitch` joins overlapping chunks -> maps\ |
| t4_diseased.py | diseased images: per-layer error, 3 worst overlays, failure stats; Cyst vs Default per layer |
| t5_bars.py | bar graphs normal vs diseased with error bars (SD across eyes, every eye as a dot) -> figures\ |
| t6_runtime.py | run time per eye (Pre->Final file times, whole cycle), normal vs diseased bars, time vs error correlation -> tables\runtime_*.csv, figures\bars_runtime.png, figures\scatter_runtime_vs_error.png |
| build_report.py | writes report\IOWA_vs_GT_report.docx from the saved tables and figures (re-run after new results) |
| build_report_part1.py | writes report\IOWA_vs_GT_report_Part1.docx (Part 1: boundary error, layer overlap, thickness, worst images) |
| edge_effect.py, compare_pilot.py | evidence for "is 21 scans enough?" (before / after the pilot run) |

Shared code: w2common.py, w2tables.py. Tables are updated in place keyed by eye / B-scan / config, so every script is safe to re-run.
`_superseded\` holds the 8-eye x 61-scan screening script. `figures\_test\` = test figures from eye 10301 only.

## Choices made (change them if you disagree)
- No diagnosis spreadsheet exists. Groups are my visual judgement (central B-scan plus GT-based screening), not clinical labels.
  Only 9 eyes show visible pathology within +/-60 B-scans of the centre (10302, 10306, 10310, 10317, 10325, 10335, 10367, 10373,
  10380), so the set is 21 normal + 9 diseased, not 15 + 15.
- Chosen B-scan uses GT only: foveal pit (normal) or largest GT abnormality (diseased). 10317 (B-scan 212) sits at the +/-60 limit.
- "Not segmented" = boundaries missing or out of order at a column; the XML <undefined_region> list is counted (format unknown).
- Error bars: SD across eyes; dots = individual eyes. `--err ci95` for a 95% CI.
- STATUS 2026-10-28: real IOWA results exist for the pilot and 28 of the 30 eyes (19 normal + 9 diseased). NOT RUN: 10340
  (mhd\10340_145-165.mhd) and 10343 (mhd\10343_152-172.mhd). Run them, then `watch_and_score.py --once`, t1, t2, t4, t5, t6 and
  build_report.py again. 10399 is one of the 30 eyes (run 31), not a spare. Cyst runs 32-35: optional, not done.
- Maps: 10301 (61 scans, B-scans 120-180) and 10335 stitched from three runs (1-80, 128-148, 153-232 = 60% of the B-scans), see
  tables\map_coverage.csv. Full 304-scan volumes were not run.
- Foveal-pit B-scans of normal eyes often have large OPL-HFL / BMEIS errors (figures\t4_worst3_overlay_normal.png).
- The *_Time_* files are not compute time (1.5-5.7 s whatever the scan size); run time = Pre->Final file times (t6_runtime.py).
