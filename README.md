# Validation of IOWA layer segmentation against the OCTA-500 ground truth

This project compares the retinal layer boundaries found by the Iowa Reference Algorithms (OCTExplorer 5.0.0b) with the layer
boundaries supplied as ground truth with the OCTA-500 dataset. The comparison uses 30 B-scans from 30 different eyes of the 3 mm
OCT scans, of which 21 look normal and 9 look diseased. The aim is to measure how closely IOWA follows the ground truth for each
boundary, each layer and the total retinal thickness, and to show where it fails, in particular in eyes with cysts or swelling.
All 30 images have been segmented and scored; the scripts, tables, figures and reports are in this folder.

## Study design

- **Eyes.** The 30 eyes are taken from eyes 10301-10400 of OCTA-500 (eyes 10333 and 10388 are the same scan stored twice and are not
  used). No diagnosis table exists for these eyes, so the grouping is a visual judgement: 21 eyes are normal-looking and 9 show
  visible cysts, fluid or swelling close to the centre of the scan. The grouping is stored in `tables/image_selection.csv`.
- **One B-scan per eye.** The B-scan is chosen from the ground truth only, never from the IOWA result. For normal-looking eyes it is the
  foveal pit (the thinnest part of the retina near the centre). For diseased-looking eyes it is the B-scan with the largest
  abnormality (the thickest cyst band, or the thickest retina for eyes with a raised dome).
- **Volumes.** IOWA segments in 3D, so each eye is segmented as a 21-B-scan volume centred on the chosen B-scan. Only the centre
  B-scan is scored. The volumes are written as MetaImage files (`.mhd` and `.raw`) with the correct voxel size
  (0.009868 x 0.003125 x 0.009868 mm).
- **Segmentation.** Each volume is segmented by hand in the OCTExplorer 5.0.0b graphical interface with `Configuration-Default.json`.
  No surface is edited. OCTExplorer is operated through its graphical interface, so this step is manual.
- **Scores.** Per boundary (ILM, IPL-INL, OPL-HFL, BMEIS, IB_RPE, OB_RPE): root mean square error (RMSE) in micrometres. Per layer
  (the five bands between neighbouring boundaries) and for the whole retina: Dice overlap. Per layer and for the total retina:
  thickness error (mean bias and RMSE of IOWA minus ground truth). Results are reported per eye and as mean and standard deviation
  across the normal-looking and diseased-looking groups.
- **Method checks.** The scoring code reproduces an earlier IOWA-versus-ground-truth result for eye 10301 (B-scans 120-180). A pilot
  run on eye 10301 compares a 21-scan with a 61-scan volume on the same B-scan.

## Repository layout

| Folder or file | Content |
|---|---|
| `scripts/` | Python scripts for selection, volume creation, scoring, tables, figures and reports (see below) |
| `scripts/_superseded/` | Screening script and table of an earlier study plan (8 eyes with 61 B-scans each), kept for reference |
| `tables/` | All numerical results as CSV files, one table per script output |
| `figures/` | Figures used in the reports (bar graphs, overlays, run-time plots) |
| `figures/_test/` | Test versions of the bar graphs made from eye 10301 alone |
| `outlines/` | Outline-only exports of the boundaries (ground truth and IOWA) per scored B-scan: PNG, `.npy`, `.csv` |
| `maps/` | Topographic (en-face) thickness and depth maps and 3D surfaces, with `.npy` data |
| `report/` | Word reports generated from the tables and figures |
| `manual_batch_pages/` | Page images of the batch-processing chapter of the IOWA 3.8.0 user manual, consulted when checking for a batch mode |
| `RUN_CHECKLIST.md` | The list of IOWA runs with the file to open, the scored B-scan and the configuration for each |

## Requirements and data

- Windows with PowerShell, Python 3.13. The scripts import `numpy`, `scipy`, `matplotlib`, `opencv-python` (`cv2`) and `python-docx`
  (`docx`); the rest is the Python standard library. The results were produced with numpy 2.3.1, scipy 1.16.0, matplotlib 3.10.6,
  opencv-python 5.0.0.93 and python-docx 1.2.0.

  ```
  python -m pip install numpy scipy matplotlib opencv-python python-docx
  ```

- Neither the OCTA-500 data nor the IOWA software is included. The OCTA-500 images and labels are obtained from the dataset
  providers, and OCTExplorer from The University of Iowa Research Foundation, each under its own terms.
- The scripts expect the following layout under one project root. The root is set by the constant `ROOT` in `scripts/w2common.py`
  (default `C:\octa500`); change it if the project is located elsewhere. Commands below are run from the project root.

  ```
  <ROOT>/OCTA_3mm/OCT/<eye>/<n>.bmp     B-scans of OCTA-500, 304 per eye, numbered from 1 (eyes 10301-10400)
  <ROOT>/Label/GT_Layers/<eye>.mat      ground truth, variable Layer, shape (6, 304, 304)
  <ROOT>/step3_make_mhd.py              writes the .mhd/.raw volumes (called by make_volumes.py)
  <ROOT>/mhd/                           volumes for OCTExplorer and, beside them, the IOWA result files
  <ROOT>/mhd_cyst/<eye>/                volumes and results of the optional Cyst-configuration runs
  <ROOT>/week2/                         this folder (scripts/, tables/, figures/, ...)
  ```

## Reproducing the results

1. **Selection and volumes.**

   ```
   python -I week2/scripts/screen_abnormal.py
   python -I week2/scripts/make_selection.py
   python -I week2/scripts/make_volumes.py
   python -I week2/scripts/make_checklist.py
   ```

   `screen_abnormal.py` is a ground-truth-only screen that supports the visual grouping. `make_selection.py` writes
   `tables/image_selection.csv`, `make_volumes.py` writes the 21-scan volumes into `mhd/` (and copies for the Cyst runs into
   `mhd_cyst/`), and `make_checklist.py` writes `RUN_CHECKLIST.md`.

2. **Segmentation in OCTExplorer (manual).** Open each `.mhd` listed in `RUN_CHECKLIST.md` in OCTExplorer 5.0.0b, check that the
   voxel size in the status bar is 0.00987 x 0.00313 x 0.00987 mm, select the configuration given in the checklist, and run the
   pre-segmentation and final segmentation without editing any surface. OCTExplorer writes the result files beside the volume.
   While the runs are in progress, the watcher scores each new result and records the time at which it was saved:

   ```
   python -I week2/scripts/watch_and_score.py            # keep running during the manual runs
   python -I week2/scripts/watch_and_score.py --status   # progress per batch of runs
   python -I week2/scripts/watch_and_score.py --once     # score the results present, then exit
   ```

3. **Reference runs for the method checks.** The two checks use a 61-scan volume of eye 10301, segmented and scored in the same way:

   ```
   python step3_make_mhd.py 10301 --range 120 180
   python -I week2/scripts/gate_check.py
   python -I week2/scripts/compare_pilot.py
   python -I week2/scripts/edge_effect.py
   ```

4. **Tables and figures.**

   ```
   python -I week2/scripts/t1_thickness.py
   python -I week2/scripts/t2_outlines.py
   python -I week2/scripts/t4_diseased.py
   python -I week2/scripts/t5_bars.py
   python -I week2/scripts/t6_runtime.py
   ```

5. **Maps.** Maps need many neighbouring B-scans of one eye. For a volume, or for several overlapping runs of one eye joined with
   `--stitch`:

   ```
   python -I week2/scripts/t3_maps.py mhd/10301_120-180_Surfaces_Retina-JEI-Final.xml
   python -I week2/scripts/t3_maps.py --stitch <result.xml> <result.xml> ...
   ```

6. **Reports.**

   ```
   python -I week2/scripts/build_report.py
   python -I week2/scripts/build_report_part1.py
   ```

All scripts update their tables in place, keyed by eye, B-scan and configuration, so they can be run again safely.

## Scripts

All scripts are in `scripts/` and are run as `python -I week2/scripts/<script>`.

| Script | Purpose | Main output |
|---|---|---|
| `w2common.py` | Shared helpers: path constants, loading ground truth and IOWA surfaces, layer names, eye groups, run discovery | (imported by the other scripts) |
| `w2tables.py` | Scores and layer thickness for one IOWA result against the ground truth | (imported by the scoring scripts) |
| `screen_abnormal.py` | Ground-truth-only screen of all usable eyes for cyst-band thickness, retinal thickness, RPE elevation and foveal pit position | `tables/abnormal_screening.csv` |
| `make_selection.py` | Fixes the 30 eyes, their group, the chosen B-scan, the volume range and the run order | `tables/image_selection.csv` |
| `make_volumes.py` | Writes the 21-scan volumes, the pilot volume and the Cyst-configuration copies, and checks each header against its `.raw` size | `mhd/*.mhd`, `mhd/*.raw`, `mhd_cyst/<eye>/` |
| `make_checklist.py` | Lists the IOWA runs in batches with the file to open and the scored B-scan; tick state is read from the result files | `RUN_CHECKLIST.md` |
| `watch_and_score.py` | Watches `mhd/` and `mhd_cyst/` for new IOWA results, scores them, and records save times; `--status`, `--once`, `--rescore` | `tables/scores_per_*.csv`, `tables/thickness_per_*.csv`, `tables/run_timing.csv` |
| `score_runs.py` | Boundary RMSE and layer Dice per B-scan and per eye, without watching | `tables/scores_per_bscan.csv`, `tables/scores_per_eye.csv` |
| `t1_thickness.py` | Layer and total retinal thickness, IOWA against ground truth, with bias and RMSE | `tables/thickness_per_bscan.csv`, `tables/thickness_per_eye.csv` |
| `t2_outlines.py` | Outline-only boundary images (304 x 640, white background) and depth values for ground truth and IOWA | `outlines/<eye>_<B-scan>/` |
| `t3_maps.py` | En-face depth and thickness maps and 3D surfaces from volumes; `--stitch` joins overlapping runs of one eye | `maps/<eye>_<range>/`, `tables/map_coverage.csv` |
| `t4_diseased.py` | Per-layer error and failure statistics for diseased-looking images, overlays of the three worst images in each group, Cyst against Default comparison when Cyst runs exist | `tables/t4_*.csv`, `figures/t4_*.png` |
| `t5_bars.py` | Bar graphs of boundary RMSE, layer Dice and thickness error, normal-looking against diseased-looking, with error bars | `figures/bars_*.png`, `tables/bars_*.csv` |
| `t6_runtime.py` | Run time per eye from saved-file times, normal-looking against diseased-looking, and its relation to the error | `tables/runtime_*.csv`, `figures/bars_runtime.png`, `figures/scatter_runtime_vs_error.png` |
| `gate_check.py` | Reproduces the earlier overall RMSE of eye 10301 (B-scans 120-180) from the existing IOWA result | `tables/gate_10301.csv` |
| `compare_pilot.py` | Compares the 21-scan and the 61-scan IOWA result on the same B-scan of eye 10301 | `tables/pilot_21_vs_61.csv` |
| `edge_effect.py` | Error of B-scans by distance from the end of the 61-scan volume of eye 10301 | `tables/edge_effect_10301.csv` |
| `build_report.py` | Builds the full Word report from the saved tables and figures | `report/IOWA_vs_GT_report.docx` |
| `build_report_part1.py` | Builds Part 1 of the report (boundary error, layer overlap, thickness, worst images) | `report/IOWA_vs_GT_report_Part1.docx` |
| `build_report_part2.py` | Builds Part 2 of the report (outline export, topographic maps, run time) | `report/IOWA_vs_GT_report_Part2.docx` |

## Results

The reports in `report/` give the results: the error of each boundary, the overlap and thickness of each layer, the three worst
diseased-looking and normal-looking images, the outline files, the maps and the run time. In short, in normal-looking eyes the top
surface and the lowest boundary agree closely with the ground truth, the inner boundaries carry the larger errors, errors are
larger in diseased-looking eyes, and normal-looking eyes also show large errors at the foveal pit. All numbers are in `tables/` and in the
reports.

## Notes and limitations

- The grouping into normal-looking and diseased-looking eyes is a visual judgement, not a clinical diagnosis. The two groups are also
  scored on different kinds of B-scan (foveal pit and most abnormal B-scan).
- The ground truth was initialised with IOWA 3.8 output and then corrected by hand. Agreement between IOWA and the ground truth is
  therefore likely to be more favourable than agreement with the true anatomy.
- "Not segmented" means a column in which a boundary is missing or the boundaries are not in non-decreasing depth order. The
  undefined-region entries of the IOWA result files are counted separately.
- Run time is taken from the times at which the result files were saved (the interval between the pre-segmentation and the final
  result file). The `*_Time_*` files written by OCTExplorer hold one value of a few seconds per run regardless of scan size and do
  not reflect computation time. The times were measured on a single computer and include the time to confirm each step.
- Not done: the optional runs with `Configuration-Cyst.json` (four eyes, listed in `RUN_CHECKLIST.md`) and full 304-scan volumes.
- The maps cover only the B-scans that were segmented: a 61-scan volume of eye 10301, and three runs of eye 10335 that together
  cover part of the scan. The full 3 x 3 mm map needs a run of all 304 B-scans.
- One scanner and one dataset (OCTA-500, 3 mm scans); one B-scan per eye.

## Acknowledgement and references

The Iowa Reference Algorithms and OCTExplorer were provided by The University of Iowa Research Foundation. We acknowledge the
providers' scientists: Michael D. Abramoff, Mona K. Garvin, Andreas Wahle, Kyungmoo Lee and Milan Sonka.

Li M, Huang K, Xu Q, Yang J, Zhang Y, Ji Z, Xie K, Yuan S, Liu Q, Chen Q. OCTA-500: A retinal dataset for optical coherence
tomography angiography study. arXiv:2012.07261 (v3), 2022.

## Author

Priyanshu Kapoor, IIT Delhi
