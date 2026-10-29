# IOWA run checklist (35 runs, batches of 10)

Status (read from the result files): 29 of 31 Default runs done (run 1 = pilot 10301, runs 2-31 = the 30 eyes). Still missing: 10340, 10343.
Cyst runs 32-35 (side experiment): optional, not done.

Per run, in OCTExplorer 5.0.0b: drag the .mhd (NOT the .raw) onto the window (or File > Open image); check the status bar voxel
size is 0.00987 x 0.00313 x 0.00987 mm; in the pre-segmentation dialog pick the configuration named in the last column;
click Next (pre-segmentation), then Next (final segmentation); do NOT edit or nudge anything; wait until the result is saved
(the watcher prints 'eye X done'). Cyst runs: pick `Configuration-Cyst.json`; everything else `Configuration-Default.json`.
Start once, in a PowerShell window:  `cd C:\octa500` then `python -I week2\scripts\watch_and_score.py` (leave it open).
Progress and time estimate at any moment:  `python -I week2\scripts\watch_and_score.py --status`.

## Batch 1 (runs 1-10)

| done | run | what | file to open (under C:\octa500) | scored B-scan | configuration |
|---|---|---|---|---|---|
| [x] done | 1 | pilot (eye 10301, normal; times a run, checks 21 vs 61 scans) | `mhd\10301_140-160.mhd` | 150 | Default |
| [x] done | 2 | 10306 diseased | `mhd\10306_114-134.mhd` | 124 | Default |
| [x] done | 3 | 10304 normal | `mhd\10304_146-166.mhd` | 156 | Default |
| [x] done | 4 | 10307 normal | `mhd\10307_147-167.mhd` | 157 | Default |
| [x] done | 5 | 10335 diseased | `mhd\10335_128-148.mhd` | 138 | Default |
| [x] done | 6 | 10314 normal | `mhd\10314_134-154.mhd` | 144 | Default |
| [x] done | 7 | 10315 normal | `mhd\10315_142-162.mhd` | 152 | Default |
| [x] done | 8 | 10302 diseased | `mhd\10302_150-170.mhd` | 160 | Default |
| [x] done | 9 | 10320 normal | `mhd\10320_144-164.mhd` | 154 | Default |
| [x] done | 10 | 10323 normal | `mhd\10323_153-173.mhd` | 163 | Default |

## Batch 2 (runs 11-20)

| done | run | what | file to open (under C:\octa500) | scored B-scan | configuration |
|---|---|---|---|---|---|
| [x] done | 11 | 10310 diseased | `mhd\10310_139-159.mhd` | 149 | Default |
| [x] done | 12 | 10330 normal | `mhd\10330_147-167.mhd` | 157 | Default |
| [x] done | 13 | 10334 normal | `mhd\10334_143-163.mhd` | 153 | Default |
| [x] done | 14 | 10317 diseased | `mhd\10317_202-222.mhd` | 212 | Default |
| [ ] NOT DONE | 15 | 10340 normal | `mhd\10340_145-165.mhd` | 155 | Default |
| [ ] NOT DONE | 16 | 10343 normal | `mhd\10343_152-172.mhd` | 162 | Default |
| [x] done | 17 | 10325 diseased | `mhd\10325_123-143.mhd` | 133 | Default |
| [x] done | 18 | 10356 normal | `mhd\10356_142-162.mhd` | 152 | Default |
| [x] done | 19 | 10357 normal | `mhd\10357_148-168.mhd` | 158 | Default |
| [x] done | 20 | 10367 diseased | `mhd\10367_137-157.mhd` | 147 | Default |

## Batch 3 (runs 21-30)

| done | run | what | file to open (under C:\octa500) | scored B-scan | configuration |
|---|---|---|---|---|---|
| [x] done | 21 | 10363 normal | `mhd\10363_144-164.mhd` | 154 | Default |
| [x] done | 22 | 10366 normal | `mhd\10366_150-170.mhd` | 160 | Default |
| [x] done | 23 | 10373 diseased | `mhd\10373_184-204.mhd` | 194 | Default |
| [x] done | 24 | 10372 normal | `mhd\10372_133-153.mhd` | 143 | Default |
| [x] done | 25 | 10377 normal | `mhd\10377_142-162.mhd` | 152 | Default |
| [x] done | 26 | 10380 diseased | `mhd\10380_109-129.mhd` | 119 | Default |
| [x] done | 27 | 10383 normal | `mhd\10383_145-165.mhd` | 155 | Default |
| [x] done | 28 | 10395 normal | `mhd\10395_144-164.mhd` | 154 | Default |
| [x] done | 29 | 10396 normal | `mhd\10396_143-163.mhd` | 153 | Default |
| [x] done | 30 | 10398 normal | `mhd\10398_138-158.mhd` | 148 | Default |

## Batch 4 (runs 31-35)

| done | run | what | file to open (under C:\octa500) | scored B-scan | configuration |
|---|---|---|---|---|---|
| [x] done | 31 | 10399 normal | `mhd\10399_146-166.mhd` | 156 | Default |
| [ ] optional, not done | 32 | 10306 diseased (Cyst side experiment) | `mhd_cyst\10306\10306_114-134.mhd` | 124 | Cyst |
| [ ] optional, not done | 33 | 10335 diseased (Cyst side experiment) | `mhd_cyst\10335\10335_128-148.mhd` | 138 | Cyst |
| [ ] optional, not done | 34 | 10325 diseased (Cyst side experiment) | `mhd_cyst\10325\10325_123-143.mhd` | 133 | Cyst |
| [ ] optional, not done | 35 | 10380 diseased (Cyst side experiment) | `mhd_cyst\10380\10380_109-129.mhd` | 119 | Cyst |
