# metro-toolkit

A thin-film-first metrology analysis toolkit for practising the daily work of a
memory-fab **Metrology Applications Engineer**: building thickness recipes,
proving gauge capability, and turning site data into SPC and root cause.

> 個人練習用 Metro AE 工具箱：以薄膜厚度量測為核心（TMM / SE 擬合 → 晶圓均勻性 →
> MSA → SPC）。全部使用合成資料，不含任何 Micron 內部資訊、recipe 或機台資料。
> This is a personal learning framework, **not** a Micron tool. It contains no
> company data, recipes, or proprietary information.

![wafer map](docs/example-report/04_wafer_map.png)

## What a Metro AE does → where it lives here

| Task on the job | Module | Key functions |
|---|---|---|
| Model a film stack, pick n/k models | `metrology/thinfilm/materials.py`, `config/films.yaml` | `Cauchy`, `Sellmeier`, `TaucLorentz`, `Tabulated` (load your own n,k CSV) |
| Simulate reflectometry / ellipsometry | `metrology/thinfilm/tmm.py` | `reflectance`, `ellipsometry` (Ψ, Δ), `ncs` |
| Thickness recipe: fit, goodness of fit, uncertainty | `metrology/thinfilm/fitting.py` | `fit` (global scan → least squares), `FitResult.correlation` |
| Recipe development studies | `metrology/thinfilm/studies.py` | `thickness_sensitivity`, `thickness_n_correlation`, `underlayer_error_transfer` |
| Spectra → wafer thickness map | `metrology/thinfilm/pipeline.py` | `simulate_site_spectra`, `fit_sites` |
| Sampling plans, uniformity, spatial signature | `wafer/` | `sampling_plan` (1/5/9/13/25/49 pt, edge exclusion), `uniformity_metrics`, `zernike_decompose`, `interpolate_map` |
| Gauge capability (MSA) | `msa/` | `gauge_rr` (ANOVA, %GRR, P/T, ndc), `static_repeatability`, `dynamic_repeatability`, `long_term_stability` |
| Tool-to-tool / chamber matching | `msa/matching.py` | `tool_matching` (TOST equivalence + Deming slope), `fleet_matching` |
| SPC and capability | `analysis/spc.py` | `control_chart` (I-MR, Xbar-R/S, EWMA, CUSUM), `western_electric`, `process_capability`, `spc_by_group` |
| Practice data with known answers | `datagen/thickness.py` | `simulate_thickness` (chamber offsets, PM-cycle drift, signatures, injected excursions + truth table), MSA study generators |

## Quick start

```bash
cd metro-toolkit
pip install -r requirements.txt          # or: pip install -e ".[dashboard,dev]"

python -m pytest                         # 47 tests: physics limits, statistics, end-to-end
PYTHONPATH=src python -m metro_toolkit.demo            # report -> reports/demo/report.md
streamlit run src/metro_toolkit/dashboard/app.py       # interactive dashboard
```

On Windows / Anaconda:

```powershell
conda create -n metro python=3.11 -y; conda activate metro
pip install -e ".[dashboard,dev]"
python -m metro_toolkit.demo
streamlit run src/metro_toolkit/dashboard/app.py
```

A pre-generated report is in [`docs/example-report/report.md`](docs/example-report/report.md).

Full step-by-step Windows instructions (including SemiYield and the other upstream tools):
[`docs/SETUP_WINDOWS.md`](docs/SETUP_WINDOWS.md). Note: install with `pip install -e` (editable); config files are located relative to the source tree.

### Dashboard pages

1. **Film stack & fit**: pick a stack from `films.yaml`, set the true thicknesses and noise, and watch the
   fit, χ², ±1σ and parameter correlation. Change a *fixed* underlayer to see a biased result that χ² does not flag.
2. **Wafer map**: contour map (absolute or deviation), uniformity metrics, Zernike signature, radial profile.
   Upload your own CSV in the standard schema.
3. **SPC**: per chamber / tool / metrology tool; wafer mean, within-wafer 1σ %, or range; I-MR, EWMA or CUSUM.
4. **MSA**: GR&R with adjustable variance sources (or upload part/operator/value), tool matching (Bland-Altman).
5. **Recipe studies**: reflectometry-vs-SE sensitivity, thickness/n correlation.

## Five lessons the demo makes concrete

1. **Scan globally before refining.** Interference makes χ²(thickness) multi-modal. On a 450–750 nm
   reflectometer a local fit started at 530 nm stops at 538.7 nm (χ² ≈ 1600); the global scan finds 742.0 nm.
2. **Pick the technique by thickness.** For a 1–3 nm oxide, normal-incidence reflectometry gives ~0.15–0.19 nm
   precision; multi-angle SE gives ~0.001 nm (same noise level assumptions).
3. **Fix n on thin films.** Floating n and t together on a 2 nm film gives |corr| > 0.99 and a σ(n) ~400x
   larger than on a 200 nm film.
4. **χ² cannot see a wrong fixed layer.** HfO2 on a fixed 1.0 nm IL: ~0.74 nm of HfO2 bias per nm of IL error,
   while χ² stays below 1 (no alarm) and the reported σ stays ~0.001 nm. Reported σ covers noise, not model error.
5. **Chart uniformity, not just the mean.** A −2 nm bowl excursion is invisible on the wafer-mean chart and
   obvious on the within-wafer 1σ % chart.

## Vocabulary study files (Eudic 歐路詞典)

191 metrology / fab / statistics terms with Traditional Chinese translations, explanations and example
sentences, one file per tool plus a combined file, in both Eudic import formats:
[`docs/eudic/`](docs/eudic/README.md). Edit `docs/eudic/glossary.yaml` and run `python -m metro_toolkit.eudic` to rebuild.

## Import your own data

Dashboard → **Data import** (first page). Works with CSV / TXT (any delimiter, UTF-8 or Big5/CP950),
Excel, and UCI SECOM (`secom.data` + `secom_labels.data`).

1. Upload the export. Two table shapes are detected: **long** (one row per measurement, ideally with site
   X/Y → wafer maps) and **wide** (one row per wafer, one column per parameter → SPC, capability, yield).
2. Columns are matched to the standard fields automatically (e.g. `Lot ID`, `LOT`, `批號` → lot_id;
   `EQP` → tool_id; `X (mm)` → x; `Spec Low` → lsl). Confirm or change each one.
3. Rename parameters, set units; Å and µm are converted to nm (spec limits too). Counter columns are excluded.
4. A check report lists errors (fix before saving), warnings and what was cleaned up.
5. **儲存並使用** saves the dataset and, optionally, the column mapping as a profile for the next export.
   The sidebar *Data source* then switches every page to it. SemiYield's launcher can load it too.

Saved data stays on this PC in `data/imported/` (git-ignored) or `METRO_IMPORT_PATH`. Code:
`src/metro_toolkit/ingest/` (readers, mapping, convert, checks, store).

## Fab simulator with an answer key

Dashboard → **Fab simulator**, or `python -m metro_toolkit.datagen.fab --scenario mixed`. Settings and
scenarios: `config/fab_sim.yaml`; code: `datagen/fab.py`, `datagen/answer_key.py`.

* **Realistic behaviour:** a DRAM-style route (pad oxide, gate oxide, ALD high-k, TiN, word-line litho/etch CD,
  ILD CMP) on tools and chambers with offsets, drift between PMs and per-chamber spatial signatures. Metrology
  sees 5 of 25 wafers at 9/13 sites through two metrology tools. E-test (Vt, Rs) and yield exist for every wafer.
* **Yield die by die:** ~620 dies of 1 cm²; a die fails if its local value leaves a step's device window or it
  catches a clustered killer defect (negative binomial; random / scratch / cluster / edge-ring patterns).
  Baseline yield ≈ 90% (sd ≈ 7%), with losses from defects, etched CD, high-k, gate oxide and ILD.
* **Scenarios:** baseline, chamber_shift, slow_drift, metrology_offset (measurement only), particle_event,
  edge_bowl, recipe_change (propagates litho → etch CD), mixed.
* **Answer key:** every event with its wafers and its **true yield impact**: each wafer is also simulated without
  events using identical random draws, so the difference is exact. Plus true yield loss by cause and die maps.
* **Score my detection:** run SPC with your chart/rule choices and compare with the key: events detected, how
  many measured wafers late, false-alarm rate, and events that sampling never saw.
* Saved like an imported dataset, so the Wafer map / SPC pages and the SemiYield launcher can use it
  (tick *SemiYield names* to make Yield Prediction work).

Lessons it makes measurable (default seed, mixed scenario): all 5 events are caught with I-MR + WE 1/2, but the
slow drift only after ~46 measured wafers (try EWMA); the edge-bowl change is caught by the within-wafer σ %
chart, not the mean chart; the metrology offset is flagged although its yield impact is exactly 0 (gauge, not
process); a simple correlation ranking puts TiN thickness above gate oxide although TiN causes no yield loss.
Even the true defect density explains only ~10–35% of wafer-yield variance, because much loss is random at
die level, so expect modest R² from any yield model.

## SemiYield hover guide

Hover explanations (Traditional Chinese + English term) for SemiYield's inputs, chart points, and SPC lines,
added by a launcher so SemiYield stays unmodified: [`semiyield_guide/`](semiyield_guide/README.md).

## Standard data schema

One row per measured site (see `schema.py`; `validate()` checks a file before analysis):

```
timestamp, product, technology, lot_id, wafer_id, slot, process_step, tool_id, chamber_id,
recipe_id, metro_tool_id, parameter, value, unit, site, x, y, target, lsl, usl
```

Required: `timestamp, lot_id, wafer_id, parameter, value, x, y`. Map your export to these names in one loader
and every module (maps, SPC, MSA, matching) works unchanged.

## Configuration and data safety

* `config/films.yaml`: materials and stack recipes. **Coefficients marked "typical" are placeholders**; replace
  them with the n/k files your tool recipes actually use.
* `config/sampling.yaml`: sampling plans and edge exclusion. `config/limits.yaml`: spec, SPC, and MSA settings.
* Environment variables keep real data out of the repo: `METRO_CONFIG_PATH`, `METRO_DATA_PATH`, `METRO_REPORT_PATH`.
* `.gitignore` blocks everything under `data/` except the synthetic sample, and all of `reports/`.
* Never commit company wafer data, recipes, tool or chamber names, or process details.

## Layout

```
metro-toolkit/
├── config/                 films.yaml · sampling.yaml · limits.yaml
├── data/sample/            synthetic site-level thickness data + excursion truth table
├── docs/example-report/    pre-generated demo report
├── src/metro_toolkit/
│   ├── metrology/thinfilm/ materials · tmm · fitting · pipeline · studies · data/si_green2008.csv
│   ├── metrology/cd/       (planned) CD-SEM edge detection, CD, LER/LWR, overlay
│   ├── metrology/rage/     (planned) vertical stack / profile metrology
│   ├── wafer/              sampling · uniformity (metrics, Zernike, maps)
│   ├── msa/                grr · repeatability · matching
│   ├── analysis/spc.py     control charts, WE rules, capability, per-chamber SPC
│   ├── datagen/            synthetic fab + MSA study data
│   ├── dashboard/app.py    Streamlit app
│   ├── demo.py             one-command report
│   ├── schema.py · config.py · viz.py
└── tests/                  47 tests
```

## How the three upstream projects were used

Reviewed on 2026-10-07 (details and licenses in [NOTICE.md](NOTICE.md)):

* **sem-toolkit**: closest in topic (TMM, ellipsometry, uniformity), but it has **no license** and its optics
  module has physics errors (ambient medium defaults to n = 1.5; Ψ built from two s-polarised reflectances; Δ
  independent of thickness; Si n,k not from literature; local-only fit). Nothing copied; the thin-film engine
  here is an independent implementation, verified against analytic limits and an independent
  characteristic-matrix solver.
* **SemiYield** (MIT): solid SPC; adapted into `analysis/spc.py` with short-term sigma for EWMA/CUSUM and exact
  EWMA limits.
* **WaferLens** (MIT): good lot → wafer → site data model. Its v2 is mid-rebuild (needs Docker + PostgreSQL /
  TimescaleDB; its SPC and root-cause packages are still empty), so only its schema ideas are used here.
  The v1 commands in older guides (`python -m simulate.wafer`, `streamlit run dashboard/app.py`) no longer apply.

## Roadmap

* **v0.2**: DOE module (factorial / response surface, wire in SemiYield's Bayesian optimiser), real-data loaders
  (CSV / Excel exports), Hotelling T² for multi-parameter stacks, SPC on Zernike coefficients.
* **v0.3**: CD module (`metrology/cd`), overlay, CD-SEM MSA.
* **v0.4**: vertical stack / profile metrology (`metrology/rage`), layer-to-layer correlation.
