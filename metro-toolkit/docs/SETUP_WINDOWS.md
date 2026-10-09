# Windows setup guide

How to run **metro-toolkit** (mine, recommended first) and **SemiYield** (optional) on a Windows PC.

> **What was tested:** the metro-toolkit steps were verified on Linux in a clean virtual environment
> (editable install, 47 tests, demo report). Windows-specific commands (PowerShell activation,
> execution policy) are standard Python practice but were **not** run on a Windows machine.
> SemiYield's lightweight tests (SPC, data generation, simulation: 63 tests) were run; its PyTorch /
> XGBoost / BoTorch parts were not installed here. WaferLens and sem-toolkit are covered at the end.

> **Company PCs:** check your IT policy before installing Python packages or cloning repos on a work
> machine. Never put real wafer data, recipes, or tool/chamber names into any GitHub repo.

---

## 0. Prerequisites (once)

| Need | How |
|---|---|
| **Python 3.11** (3.10-3.12 are fine) | https://www.python.org/downloads/ . Tick **"Add python.exe to PATH"** in the installer. Or use Anaconda/Miniconda. |
| **Git** | https://git-scm.com/download/win (defaults are fine) |

Check in PowerShell:

```powershell
python --version
git --version
```

## 1. metro-toolkit (about 5 minutes, ~500 MB)

```powershell
# 1. Get the code (branch name is the one this work was pushed to)
git clone -b ccr-62433344-6p1yf7 https://github.com/blses1283513-hub/crrer.git
cd crrer\metro-toolkit

# 2. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1
```

If PowerShell says *"running scripts is disabled on this system"*:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
.venv\Scripts\Activate.ps1
```

(Command Prompt users: `.venv\Scripts\activate.bat`.)

```powershell
# 3. Install. The -e (editable) flag is REQUIRED: config files are found relative to the source tree.
pip install -e ".[dashboard,dev]"

# 4. Check everything works (47 tests, ~25 s)
python -m pytest

# 5. Generate the demo report -> reports\demo\report.md (+ 7 PNG charts), ~15 s
python -m metro_toolkit.demo

# 6. Open the interactive dashboard (browser opens at http://localhost:8501)
streamlit run src\metro_toolkit\dashboard\app.py
```

**Conda alternative** (instead of `python -m venv`):

```powershell
conda create -n metro python=3.11 -y
conda activate metro
pip install -e ".[dashboard,dev]"
```

### Open the dashboard without a terminal (after the one-time setup above)

**Double-click `Metro Toolkit.bat`** in the `metro-toolkit` folder. It finds the project from its own location,
uses the `.venv` you created, starts the dashboard on a free port (8501, or the next free one) and opens your
browser. Close the black window to stop it. The dashboard listens on this PC only (`localhost`), not on the
office network.

Desktop shortcut: right-click `Metro Toolkit.bat` → **Send to → Desktop (create shortcut)**. Rename or re-icon the
shortcut as you like; do not move the `.bat` itself out of the `metro-toolkit` folder (move the shortcut instead).

If the window says it cannot find `.venv\Scripts\python.exe`, the one-time setup (steps 1-3) is not done in
this folder. If it closes at once with an error, run it from PowerShell once to read the message:
`.\"Metro Toolkit.bat"`.

Alternative, from any folder in an activated environment (no `cd`): `metro-toolkit` (it is installed by
`pip install -e`; re-run that once after a `git pull` to get the command). Options: `--port 8600`, `--no-browser`.

### Using your own data

Easiest: dashboard → **Data import** page (CSV / Excel / SECOM, automatic column matching, unit
conversion to nm, check report, reusable mapping profiles). After `git pull`, rerun
`pip install -e ".[dashboard,dev]"` once so Excel support (`openpyxl`) is installed.

Manual alternative:

Keep real data **outside** the repo and point to it with environment variables:

```powershell
$env:METRO_DATA_PATH   = "D:\metro_data"       # your measurement CSVs
$env:METRO_CONFIG_PATH = "D:\metro_config"     # a copy of config\ with your recipes/limits
```

Your CSV needs at least: `timestamp, lot_id, wafer_id, parameter, value, x, y`
(full schema in the README). Check a file before analysis:

```python
from metro_toolkit.schema import load_measurements, validate
df = load_measurements(r"D:\metro_data\my_export.csv")
print(validate(df) or "OK")
```

In the dashboard, use the sidebar **Upload** box on the *Wafer map* and *SPC* pages.

### Updating later

```powershell
cd crrer\metro-toolkit
git pull
pip install -e ".[dashboard,dev]"
```

### Troubleshooting

| Symptom | Fix |
|---|---|
| `python` not found | Reinstall Python with "Add to PATH", or use `py -3.11` instead of `python` |
| `streamlit` not found | The venv is not active. Re-run `.venv\Scripts\Activate.ps1` |
| `ModuleNotFoundError: metro_toolkit` | Run step 3 from inside `metro-toolkit\` and keep the `-e` flag |
| `FileNotFoundError ... films.yaml` | You installed without `-e`. Run `pip uninstall metro-toolkit`, then `pip install -e ".[dashboard,dev]"` |
| Dashboard port busy | `streamlit run ... --server.port 8600` |
| Matplotlib font warnings | Harmless |

---

## 2. SemiYield (optional: Bayesian DOE, yield models, SPC; about 15-30 minutes, 3-5 GB)

It installs PyTorch, BoTorch, XGBoost and SHAP, so it is heavy. Use a **separate** environment.

```powershell
cd ..\..            # back to the folder where you want projects
git clone https://github.com/OutBlade/semiyield.git
cd semiyield

python -m venv .venv
.venv\Scripts\Activate.ps1

# Optional but recommended on a laptop without an NVIDIA GPU: smaller CPU-only PyTorch
pip install torch --index-url https://download.pytorch.org/whl/cpu

pip install -e ".[dev]"
python -m pytest tests\test_spc.py tests\test_datagen.py tests\test_simulation.py   # quick sanity check
streamlit run dashboard\app.py                                                       # http://localhost:8501
```

**Do not use SemiYield's `start.bat`.** It contains the author's personal paths
(`C:\Users\Sebastian\...`) and opens a public Cloudflare tunnel to your PC. Use the `streamlit` command above.

Use it as a library:

```python
from semiyield.datagen import FabDataGenerator
from semiyield.spc import ControlChart
from semiyield.doe import ProcessWindowOptimizer
```

To see hover explanations for SemiYield's parameters and charts, use the launcher in
`metro-toolkit\semiyield_guide` (see its README).

SemiYield is MIT-licensed. If you copy code from it into your own project, keep its copyright and license
notice (see `NOTICE.md` in metro-toolkit for how this was done).

---

## 3. The other two upstream projects

**WaferLens** (MIT): needs Docker Desktop, [uv](https://docs.astral.sh/uv/), Python 3.12, `make`
(use WSL or Git Bash on Windows) and a PostgreSQL/TimescaleDB container.
Steps from its README: `cp .env.example .env`, `make install`, `make up`, `make seed PROFILE=dev`.
Its SPC and root-cause packages are still empty, so it is mainly a data-model reference today.
The commands in older guides (`python -m simulate.wafer`, `streamlit run dashboard/app.py`) are from v1 and no longer apply.

**sem-toolkit** (no license): you may run it locally for personal learning, but not copy or redistribute its code.
- Module 2 (thin film) needs no data, but its physics has errors; use metro-toolkit for thin-film work.
- Module 1 needs `data\secom.data` and `data\secom_labels.data` from the UCI SECOM dataset (create the `data\` folder).
- Module 3 needs `data\LSWMD.pkl` (WM-811K, a large Kaggle download that needs a Kaggle account).
- Install: `pip install -r requirements.txt` (includes PyTorch).
