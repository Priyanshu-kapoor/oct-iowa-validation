# Week 3 facts for the slides

Sources: `week3\progress.csv`, `week3\tables\pairwise_thickness_error.csv`, `week3\tables\ppt_numbers.csv`,
`week3\tables\whole_retina_rmse_per_eye.csv`, `week3\tables\summary.csv`. Script: `week3\ppt_figures.py`.

## What was run

- Eyes: all 78 NORMAL eyes in `eye_list.csv` are marked done in `progress.csv`, and all 78 are scored. This is every eye on the list.
- B-scans scored: 78 × 304 = 23,712. A-scans (columns) scored: 7,208,448.
- Each eye is one full 304-B-scan volume, segmented in OCTExplorer 5.0.0b with Configuration-Default.json and no manual editing.
- Time per eye: 305 s on average (median 300 s, range 265–395 s), about 5 minutes.
- Total segmentation time: 6.6 hours (sum over the 78 eyes). The run started 5 Nov 2026 at 01:27 and the last eye finished at 09:08,
  so 7 h 41 min passed in total, including one pause of about an hour after a manual stop.
- Peak RAM of OCTExplorer: 10.56 GB at most, 9.68 GB on average (the machine has 16 GB).
- Two attempts did not finish the first time: 10357 stalled once (nothing changed on screen for 90 s) and 10399 was stopped by hand
  (Ctrl+C). Both finished when they were run again.

## How to read the numbers

Boundaries: 1 ILM, 2 IPL-INL, 3 OPL-HFL, 4 BMEIS, 5 IB_RPE, 6 OB_RPE. For a pair i<j the thickness is b_j − b_i at each A-scan,
and the error is IOWA minus ground truth (GT), in µm (1 depth pixel = 3.125 µm). "Pooled" means one number over all eyes,
B-scans and A-scans together. "Per eye" means one value for each eye, then the mean ± SD of those 78 values. A positive bias means
IOWA measures the layer thicker than GT. No columns were left out (same rule as the week-2 scoring).

## The 15 pairwise cells (µm)

| i → j | pooled RMSE | pooled bias | pooled MAE | RMSE per eye, mean ± SD | bias per eye, mean ± SD |
|---|---|---|---|---|---|
| ILM → IPL-INL | 18.70 | −4.47 | 8.85 | 13.39 ± 13.13 | −4.47 ± 10.90 |
| ILM → OPL-HFL | 28.62 | −8.63 | 16.13 | 21.39 ± 19.14 | −8.63 ± 19.49 |
| ILM → BMEIS | 46.85 | −21.01 | 23.78 | 30.80 ± 35.53 | −21.01 ± 32.26 |
| ILM → IB_RPE | 9.05 | −3.79 | 6.21 | 7.85 ± 4.53 | −3.79 ± 5.36 |
| ILM → OB_RPE (whole retina) | 3.34 | 0.67 | 2.14 | 3.11 ± 1.24 | 0.67 ± 0.98 |
| IPL-INL → OPL-HFL | 19.56 | −4.17 | 10.94 | 15.47 ± 12.04 | −4.17 ± 10.64 |
| IPL-INL → BMEIS | 37.20 | −16.55 | 19.61 | 26.30 ± 26.48 | −16.55 ± 23.61 |
| IPL-INL → IB_RPE | 16.77 | 0.67 | 9.64 | 13.31 ± 10.26 | 0.67 ± 7.90 |
| IPL-INL → OB_RPE | 19.15 | 5.14 | 8.98 | 13.66 ± 13.51 | 5.14 ± 11.17 |
| OPL-HFL → BMEIS | 23.02 | −12.38 | 13.92 | 18.09 ± 14.32 | −12.38 ± 14.07 |
| OPL-HFL → IB_RPE | 24.17 | 4.84 | 14.88 | 19.32 ± 14.61 | 4.84 ± 15.63 |
| OPL-HFL → OB_RPE | 28.95 | 9.31 | 16.17 | 21.59 ± 19.41 | 9.31 ± 19.71 |
| BMEIS → IB_RPE | 40.84 | 17.22 | 21.24 | 27.52 ± 30.36 | 17.22 ± 27.97 |
| BMEIS → OB_RPE | 47.26 | 21.69 | 23.85 | 31.08 ± 35.84 | 21.69 ± 32.48 |
| IB_RPE → OB_RPE | 9.16 | 4.47 | 6.05 | 7.75 ± 4.91 | 4.47 ± 5.44 |

The five adjacent-pair cells and the whole-retina cell match `summary.csv`, which was made earlier by `score_all.py` with the
week-2 code. The two scripts agree.

Median across eyes of the per-eye thickness RMSE, for the 5 layers (less pulled by the bad eyes than the mean):
ILM→IPL-INL 6.93, IPL-INL→OPL-HFL 8.30, OPL-HFL→BMEIS 10.78, BMEIS→IB_RPE 6.98, IB_RPE→OB_RPE 6.40 µm.

## Whole retina (ILM → OB_RPE)

- Per eye: 3.11 ± 1.24 µm (mean ± SD over 78 eyes), median 2.89 µm. Pooled over everything: 3.34 µm.
- Best eyes: 10375 (2.45 µm), 10368 (2.55), 10316 (2.55).
- Worst eyes: 10371 (13.49 µm), 10334 (4.07), 10347 (3.74). 10371 is the only clear outlier. Its OB_RPE boundary alone has
  14.6 µm RMSE, and the error is high across most of the volume, not in one spot.
- Foveal B-scan (week-2 rule: thinnest smoothed GT retina near the centre) falls between B-scans 136 and 169 in all eyes.
- Overlays: best eye 10375 at its foveal B-scan 151 (whole-retina RMSE 3.52 µm on that B-scan); worst eye 10371 at its foveal
  B-scan 155 (12.88 µm). 10371's single worst B-scan is B-scan 1 at the volume edge (25.11 µm); it was not used for the overlay
  because an edge scan is not typical of the eye.
- Thickness map: eye 10375, total retina, GT | IOWA | IOWA − GT. No columns had to be masked (0 in IOWA, 0 in GT).

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

- The inner layers have large errors in part of the eyes, and this drives the big means and SDs above. In 32 of the 78 eyes the
  BMEIS boundary is off by more than 20 µm RMSE (the median eye is 6.2 µm). In 23 eyes IOWA puts BMEIS more than 10 pixels (31 µm)
  above GT on average, and never below. Looking at eye 10394, the GT line sits on the bright band and IOWA's line sits higher,
  inside the outer nuclear layer, so in these eyes the error looks like IOWA's. In 10394, IOWA's IPL-INL and OPL-HFL are also higher than GT.
  ILM and OB_RPE are not affected, which is why the whole-retina error stays small.
- Week 2 already had this for some eyes: of the 20 eyes in both weeks, 6 had BMEIS errors near 50 µm on their week-2 B-scan.
  The volume size changed the result for a few eyes: 10320, 10377 and 10396 were fine as 21-B-scan volumes in week 2 but have
  50+ µm BMEIS errors as full volumes in week 3, while 10314 went the other way.
- The GT was started from IOWA output and then corrected by hand, so close agreement partly reflects that shared starting point.
- 10333 and 10388 are the same scan stored twice (byte-identical images and GT). 10333 is included and 10388 is left out, so
  there are 78 normal eyes, not 79.
- Only NORMAL eyes are in week 3; DR, AMD and CNV eyes are not part of these numbers.
- The file-dialog screenshot comes from the 2-eye test run on 4 Nov (`_test\debug\`). The real run saved only the pop-ups, not
  the file dialog. The pop-up screenshot is from the real run (eye 10301) and is shown at 2× size.
- In the eye × B-scan heat map the colour scale stops at 9.7 µm (99th percentile), so 10371 and a few edge B-scans appear at the
  darkest colour even where their error is larger.
