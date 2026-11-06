# Week 3 facts for the slides

Everything is reported **per eye**. Where one number has to describe all eyes, it is the **median [IQR]** across the 78 eyes
(IQR = 25th to 75th percentile) or a **count of eyes**. No means and no pooled values.

Sources: `week3\progress.csv`, `week3\tables\pairwise_per_eye.csv`, `week3\tables\pairwise_median_iqr.csv`,
`week3\tables\representative_eyes.csv`, `week3\tables\per_eye_summary_numbers.csv`, `week3\tables\ppt_numbers.csv`.
Script: `week3\per_eye_analysis.py` (it uses the loading and overlay code in `week3\ppt_figures.py`).

## What was run

- Eyes: all 78 NORMAL eyes in `eye_list.csv` are marked done in `progress.csv`, and all 78 are scored. This is every eye on the list.
- B-scans scored: 78 × 304 = 23,712. A-scans (columns) scored: 7,208,448.
- Each eye is one full 304-B-scan volume, segmented in OCTExplorer 5.0.0b with Configuration-Default.json and no manual editing.
- Time per eye: median 300 s (range 265–395 s), about 5 minutes.
- Total segmentation time: 6.6 hours (sum over the 78 eyes). The run started 5 Nov 2026 at 01:27 and the last eye finished at 09:08,
  so 7 h 41 min passed in total, including one pause of about an hour after a manual stop.
- Peak RAM of OCTExplorer: 10.56 GB at most (the machine has 16 GB).
- Two attempts did not finish the first time: 10357 stalled once (nothing changed on screen for 90 s) and 10399 was stopped by hand
  (Ctrl+C). Both finished when they were run again.

## How the numbers are made

Boundaries: 1 ILM, 2 IPL/INL, 3 OPL/HFL, 4 BMEIS, 5 IB_RPE, 6 OB_RPE. For a pair i<j the thickness is b_j − b_i at each A-scan,
and the error is IOWA minus ground truth (GT), in µm (1 depth pixel = 3.125 µm). For **each eye**, RMSE, bias and MAE are taken
over that eye's own 304 B-scans × 304 A-scans, so each eye gives one value per pair. A "layer" is a pair of neighbouring
boundaries (1-2, 2-3, 3-4, 4-5, 5-6); 1-6 is the whole retina. A positive bias means IOWA measures the layer thicker than GT. No
columns were left out (same rule as the week-2 scoring).

## Which figures to use

**For slides (per eye, or median [IQR] across eyes):**

| Figure | What each value is |
|---|---|
| `pair_by_eye_rmse.png`, `pair_by_eye_bias.png` | Per eye: rows = the 15 pairs, columns = the 78 eyes sorted by whole-retina RMSE. Boxed rows marked ▶ are the pairs with BMEIS as one boundary. |
| `..\per_eye\<ID>_pairwise.png` (78 files) | One eye: RMSE triangle and bias triangle. The colour scales are the same for every eye (RMSE 0–98 µm, bias ±93 µm, the 99th percentile of all eye-pair values). |
| `median_triangle.png` | Median [IQR] across the 78 eyes for each pair, RMSE and bias. |
| `whole_retina_rmse_per_eye_median.png` | One bar per eye, with a dashed **median** line. |
| `whole_retina_rmse_eye_by_bscan.png` | Per eye and per B-scan: each cell is one B-scan of one eye. |
| `small_multiples_rmse.png`, `small_multiples_bias.png` | Per eye: one small triangle per eye, shared colour scale. |
| `rep_typical_10340.png`, `rep_bmeis_10372.png`, `rep_worst_10371.png` (+ `_overlay.png`) | The three representative eyes (see below). |
| `screenshot_file_dialog.png`, `screenshot_click_ok_popup.png` | OCTExplorer screenshots taken by the automation. |
| `thickness_map_total_10375.png` | Total retina thickness map of one eye: GT, IOWA, IOWA − GT. |

**Not for slides (they pool or average across eyes):**

| Figure | Why not |
|---|---|
| `pairwise_rmse_heatmap.png`, `pairwise_bias_heatmap.png` | Pooled over all eyes; a few bad eyes pull every cell up. |
| `pooled_vs_median_rmse.png`, `pooled_vs_median_bias.png` | The left triangle is pooled. Use `median_triangle.png` instead. |
| `layer_rmse_bars.png`, `layer_bias_bars.png` | Bars are means ± SD across eyes. |
| `whole_retina_rmse_per_eye.png` | Its dashed line is the mean. Use `whole_retina_rmse_per_eye_median.png` instead. |
| `pairs_by_eye_rmse.png`, `pairs_by_eye_bias.png` | Older version of `pair_by_eye_*` without the BMEIS rows marked (same values). |
| `overlay_good_10375_bscan151.png`, `overlay_worst_10371_bscan155.png` | Older picks; the representative-eye overlays replace them. |

The tables `pairwise_thickness_error.csv`, `pairwise_median_across_eyes.csv` and the pooled/mean rows of `ppt_numbers.csv` are
also not for slides.

## The 15 pairs: median [IQR] across eyes, and counts (µm)

| pair | RMSE median [IQR] | bias median [IQR] | eyes > 10 µm | eyes > 20 µm |
|---|---|---|---|---|
| ILM-IPL/INL (layer) | 6.93 [3.77, 18.65] | 0.05 [-6.91, 0.80] | 29 | 19 |
| ILM-OPL/HFL | 10.06 [6.07, 39.73] | 2.31 [-20.31, 3.48] | 40 | 30 |
| ILM-BMEIS | 6.53 [3.16, 65.42] | -0.90 [-39.33, 1.47] | 34 | 32 |
| ILM-IB_RPE | 6.08 [4.13, 11.50] | -2.14 [-6.94, -0.42] | 23 | 1 |
| ILM-OB_RPE (whole retina) | 2.89 [2.75, 3.12] | 0.59 [0.22, 1.03] | 1 | 0 |
| IPL/INL-OPL/HFL (layer) | 8.30 [5.97, 26.91] | 1.69 [-11.21, 2.85] | 32 | 27 |
| IPL/INL-BMEIS | 8.91 [4.37, 53.00] | -1.63 [-34.04, 0.94] | 38 | 32 |
| IPL/INL-IB_RPE | 8.49 [6.10, 17.34] | -0.23 [-2.93, 1.89] | 35 | 17 |
| IPL/INL-OB_RPE | 6.68 [3.86, 18.34] | 0.56 [-0.32, 7.93] | 29 | 19 |
| OPL/HFL-BMEIS (layer) | 10.78 [6.05, 29.81] | -3.69 [-22.69, -1.90] | 43 | 29 |
| OPL/HFL-IB_RPE | 12.34 [7.92, 30.50] | -2.22 [-4.98, 11.86] | 48 | 29 |
| OPL/HFL-OB_RPE | 10.40 [5.73, 40.00] | -1.95 [-2.94, 21.72] | 41 | 30 |
| BMEIS-IB_RPE (layer) | 6.98 [4.22, 57.88] | 0.17 [-1.78, 33.55] | 33 | 30 |
| BMEIS-OB_RPE | 6.89 [2.90, 65.54] | 0.97 [-1.13, 39.93] | 35 | 32 |
| IB_RPE-OB_RPE (layer) | 6.40 [3.74, 11.19] | 2.90 [0.31, 7.75] | 23 | 1 |

Counts are out of 78 eyes. MAE per eye is in `pairwise_per_eye.csv`, and its median [IQR] is in `pairwise_median_iqr.csv`.

What this shows:
- The whole retina is measured well in almost every eye: median 2.89 µm [2.75, 3.12], range 2.45–13.49 µm, and only 1 eye
  (10371) is above 10 µm.
- The two outer layers that do not touch BMEIS or OPL/HFL (ILM-IB_RPE, IB_RPE-OB_RPE) are above 20 µm in only 1 eye each.
- Every pair with BMEIS as one boundary has a wide IQR whose upper end is 30–66 µm. For these pairs the eyes fall into two
  groups: about 30 eyes are far off and the rest are close. The median alone hides that, so give the IQR or the count with it.

## Representative eyes, chosen by rule

Rules (applied by `per_eye_analysis.py`; all values per eye over its 304 B-scans):
- **Typical**: the eye whose whole-retina (ILM-OB_RPE) RMSE is closest to the median of the 78 eyes (2.89 µm); a tie would go to
  the lower value.
- **BMEIS failure**: among the eyes where at least one of the two layers touching BMEIS (OPL/HFL-BMEIS or BMEIS-IB_RPE) has RMSE
  above 20 µm (32 eyes), take the larger of those two layer RMSEs for each eye, and pick the eye closest to the median of that
  group (61.16 µm).
- **Worst**: the eye with the highest whole-retina RMSE.
- Each overlay is at the eye's foveal B-scan (week-2 rule: thinnest smoothed GT retina near the centre).

| | Typical: 10340 | BMEIS failure: 10372 | Worst: 10371 |
|---|---|---|---|
| Rank by whole-retina RMSE (1 = best) | 39 of 78 | 64 of 78 | 78 of 78 |
| Whole-retina RMSE | 2.88 µm | 3.29 µm | 13.49 µm |
| Whole-retina bias | +0.95 µm | +1.80 µm | +7.12 µm |
| ILM-IPL/INL RMSE | 12.69 | 33.01 | 8.44 |
| IPL/INL-OPL/HFL RMSE | 25.97 | 23.57 | 7.93 |
| OPL/HFL-BMEIS RMSE (bias) | 30.12 (−22.78) | 37.56 (−26.97) | 9.69 (−0.46) |
| BMEIS-IB_RPE RMSE (bias) | 47.06 (+26.59) | 60.23 (+38.92) | 14.97 (+4.81) |
| IB_RPE-OB_RPE RMSE | 14.06 | 13.22 | 6.80 |
| Foveal B-scan, and its whole-retina RMSE | 155: 3.63 µm | 143: 5.05 µm | 155: 12.88 µm |

All 15 pairs for each of these eyes are in `representative_eyes.csv`.

Notes on these three:
- By the rule, the "typical" eye 10340 is itself a BMEIS-failure eye (47 µm on BMEIS-IB_RPE). The whole-retina error only
  uses ILM and OB_RPE, so it cannot see a misplaced BMEIS. A typical whole retina does not mean typical inner layers.
- In 10372 the overlay shows the failure directly: on the right half of the foveal B-scan, IOWA's BMEIS line jumps up into
  the outer nuclear layer, while GT stays on the bright band.
- 10371 is a different kind of failure: its inner layers are near the median, but OB_RPE is off (14.6 µm boundary RMSE), so the
  whole retina and BMEIS-IB_RPE are off with it.

## The BMEIS problem

- 32 of 78 eyes have at least one BMEIS layer above 20 µm. In 23 eyes IOWA places BMEIS more than 10 pixels (31 µm) above GT on
  average, and in no eye more than 10 pixels below. In eye 10394 the GT line sits on the bright band and IOWA's sits higher,
  inside the outer nuclear layer, so in these eyes the error looks like IOWA's. In 10394, IOWA's IPL/INL and OPL/HFL are also
  higher than GT.
- One eye has a different pattern: 10326's BMEIS is fine (ILM-BMEIS 2.76 µm) but its IPL/INL is off (ILM-IPL/INL 46.33 µm).
- Week 2 already had this for some eyes: of the 20 eyes in both weeks, 6 had BMEIS errors near 50 µm on their week-2 B-scan.
  The volume size changed the result for a few eyes: 10320, 10377 and 10396 were fine as 21-B-scan volumes in week 2 but have
  50+ µm BMEIS errors as full volumes in week 3, while 10314 went the other way.

## How the automation works

- A Python script (`week3\run_all.py`, pywinauto) clicks the real OCTExplorer 5.0.0b window, the same way a person would: File ▾ >
  Open image, types the .mhd path in the file dialog, checks that the status bar shows the voxel size 0.009868 × 0.003125 ×
  0.009868 mm, keeps Configuration-Default.json selected, presses Next and Finish, then File > Close image. It never calls the
  segmentation program directly and never edits a surface.
- It answers the wizard's pop-ups: OK on "Click OK to start editing." and Yes on "Are you done with the editing?" (after each one
  IOWA saves the Pre and then the Final result). Every pop-up is screenshotted. A pop-up whose text looks like an error ("error",
  "fail", "memory", "warning", ...) stops that eye instead of being clicked away.
- Resume: every attempt is written to `progress.csv`, and results are copied into `outputs\<ID>\` only when complete. Running the
  same command again skips finished eyes and carries on.
- Stopping: creating a file called `week3\STOP` lets the current eye finish and then exits cleanly. `--max-hours` does not start a
  new eye unless an average eye still fits in the time left.
- Safety caps: a step counts as failed if nothing on screen changes for 90 s while OCTExplorer is idle (a busy CPU means it is
  still computing). At most 3 OCTExplorer launches per eye. The run stops if 3 eyes in a row fail at the same step, because then
  the problem is not the eye. If memory is not released after Close image, OCTExplorer is closed and the next eye starts fresh.

## Caveats

- The GT was started from IOWA output and then corrected by hand, so close agreement partly reflects that shared starting point.
- 10333 and 10388 are the same scan stored twice (byte-identical images and GT). 10333 is included and 10388 is left out, so
  there are 78 normal eyes, not 79.
- Only NORMAL eyes are in week 3; DR, AMD and CNV eyes are not part of these numbers.
- The file-dialog screenshot comes from the 2-eye test run on 4 Nov (`_test\debug\`). The real run saved only the pop-ups, not
  the file dialog. The pop-up screenshot is from the real run (eye 10301) and is shown at 2× size.
- Colour scales in the per-eye figures stop at the 99th percentile of all eye-pair values (98 µm RMSE, ±93 µm bias); the largest
  single value is 107.49 µm (ILM-BMEIS). In the eye × B-scan heat map the scale stops at 9.7 µm.
