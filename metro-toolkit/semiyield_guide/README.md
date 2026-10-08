# SemiYield hover guide

Adds explanations to SemiYield's dashboard without changing SemiYield:

* **Inputs and metric cards** get a `?` icon. Hover it to see what the parameter means and where it sits in the process.
* **Chart points** show what the point represents (values with units, and why it matters). Reference lines
  (UCL / CL / LCL, background doping, junction depth xj) explain themselves when you hover them.
* **Under every chart**:
  * a status line read from the chart itself, with the reason (for example "1 of the last 5 points breaks a WE rule
    → follow the OCAP");
  * a **📖 怎麼讀這張圖 · How to read this chart** panel covering the legend, what the chart shows, good vs bad
    patterns, the next step, what to record, and ready-to-send messages for RDA, PE, EE, PIE/YE and Manager/QE.

  The panel text comes from metro-toolkit's `src/metro_toolkit/guide/charts_semiyield.yaml`.
* **Legend entries** are added for lines SemiYield draws without one: CL, UCL/LCL, WE violations, background
  doping, junction depth.
* **Language:** the sidebar switch **說明語言 Guide language** selects 繁中 + English, 繁中 or English for tooltips,
  hover text and panels. The English text is in `explanations.yaml` (`help_en`, `hover_en`, `en` / `note_en`).
  Switching keeps SemiYield's page and inputs: the launcher gives each SemiYield control a stable key.

**Covered:** all six pages (Simulation, Data Generator, SPC Dashboard, Yield Prediction, Process Optimizer,
SPICE Export): every input, metric card and button, the section headers that need context (SHAP, process
window, BSIM parameters), and every chart. Process-parameter names (`gate_oxide_thickness`, `poly_cd`, ...) are
explained wherever they appear: Yield Prediction inputs, SHAP bars, the trend chart, under the SPC selector.

> ⚠ The **Process Optimizer** page optimises a demonstration formula whose optimum is always the centre of the
> bounds you enter. Its tooltips say so; use it to learn the Bayesian-optimisation workflow, not for conclusions.

## Fixes applied at runtime (SemiYield's files stay unchanged)

**1. Yield Prediction: negative R².** With SemiYield's default data the page showed R² = −1.47. Cause: the
ensemble learns its stacking weights with an unconstrained Ridge regression on a small validation slice
(last 15% of training rows). Yield is ≈ 0.999 for 99% of wafers, so that slice held only 2 low-yield wafers,
and Ridge learned weights such as −0.11 / +1.76: every predicted yield drop was amplified ≈ 1.65×.
`yield_fix.py` makes the weights non-negative and sum to 1 (they can no longer amplify), then refits the
tree models on all training rows after the weights are chosen. The test set (newest 20% of wafers) is never
used for training. Result on 8 random seeds: mean R² 0.18 → 0.80, none negative (default seed −1.47 → 0.79).
A caption under the page title says the fix is active.

**2. SPC: counters in the parameter list.** `lot_sequence` and `wafer_sequence` were the first options, so the
page opened on a counter and flagged every point. They are now removed from the list (also typical counter
columns in uploaded CSVs: names ending in `_sequence`, `_id`, `_index`), and the page opens on
`gate_oxide_thickness`. A caption lists what was removed.

## Use your own imported data in SemiYield

1. Import a file on metro-toolkit's **Data import** page and click 儲存並使用.
2. In SemiYield (started with this launcher) open the sidebar panel **metro-toolkit 匯入資料**, choose the
   dataset and click **載入這份資料**. SPC Dashboard and Yield Prediction now use it; **改回合成資料** switches back.
   * Spec limits carried by the file (LSL / USL columns) are used first. Without them, the data-based
     baseline rule is used. SemiYield's synthetic yield window is never applied to your data.
   * Yield Prediction needs a column named `yield` and at least one of SemiYield's parameter names
     (`gate_oxide_thickness`, `poly_cd`, …). Rename columns on the import page; otherwise the Train button
     is disabled with an explanation.
   * The launcher reads `metro-toolkit/data/imported` (or `METRO_IMPORT_PATH`).

## Reliable USL / LSL on the SPC page

SemiYield's own defaults are the 0.5 / 99.5 percentiles of the plotted data. Specs taken from the data always
fit around the data, so Cp comes out ≈ 0.9 whether the process is good or bad. The launcher replaces them with
a suggested value (`spec_limits.py`, hybrid method). The method is shown under the boxes; hover `?` for the numbers.
You can still type your own spec.

| Parameter type | Rule | Example (default generated data) |
|---|---|---|
| Has a yield window in SemiYield's yield model (gate_oxide_thickness, poly_cd, contact_resistance) | nominal target ± 3σ, where its parametric yield starts to fall | gate oxide 7.6 / 9.4 nm → Cpk 0.87 |
| Other process parameters | baseline (first 20% of rows = earliest lots) median ± 4·σ_short-term (moving range / 1.128) → Cp = 1.33 at baseline | implant dose 9.16e12 / 1.08e13 → Cpk 1.32 |
| Smaller is better (deposition_unif, defect_density, wafer_map_std) | USL as above, LSL = 0 | deposition_unif 0 / 3.29 % |
| Bigger is better (yield, wafer_map_mean) | LSL as above, USL = 1 | yield 0.9987 / 1 |

For one-sided parameters only Cpk (the relevant side) is meaningful; Cp is not. Uploaded CSVs use the data rule
for every parameter and assume rows are in time order.

## Run it (Windows, using SemiYield's environment)

```powershell
# 1. get the newest files from the branch
cd $HOME\projects\crrer
git pull

# 2. one-time: the launcher needs pyyaml inside SemiYield's environment
cd $HOME\projects\semiyield
.venv\Scripts\python.exe -m pip install pyyaml

# 3. start SemiYield with the hover guide (port 8502, private to your PC)
.venv\Scripts\python.exe -m streamlit run ..\crrer\metro-toolkit\semiyield_guide\launch_semiyield.py --server.address localhost --server.port 8502
```

Open http://localhost:8502. To use plain SemiYield again, run its own `dashboard\app.py` as before.

If SemiYield is not next to the `crrer` folder, set `SEMIYIELD_DIR`:

```powershell
$env:SEMIYIELD_DIR = "D:\tools\semiyield"
```

## What to try

* **Simulation → Oxidation:** hover the `?` by *Atmosphere*; move the mouse along the curve.
* **Simulation → Implantation:** hover the dashed red line (background) and the dotted orange line (xj).
* **Data Generator:** set Drift rate / Aging factor, click *Generate Dataset*.
* **SPC Dashboard:** it opens on gate_oxide_thickness with suggested USL/LSL; hover points
  (red = rule violation), the UCL/CL/LCL lines, and the `?` by Cpk / Ppk.
* **Yield Prediction:** train the model, then hover the SHAP bars and the `?` by R² / RMSE / MAE.
* **Process Optimizer:** run it and hover the convergence points; read the `?` by *Parameter Bounds*.
* **SPICE Export:** hover `?` by *Computed SPICE Parameters* for VTH0, U0, K1, CDSC, RDSW.
* Sidebar → *Metro 說明覆蓋率*: lists inputs that still have no explanation.

## Editing or adding explanations

Edit `explanations.yaml` (format described at the top of the file) and restart. A tooltip that doesn't match
(e.g. SemiYield renamed a label in an update) is simply missing; it never breaks the app.

## Tests

```powershell
python -m pytest tests\test_semiyield_guide.py
```

The YAML checks always run. The launcher test runs when SemiYield is found (set `SEMIYIELD_DIR`).
