# SemiYield hover guide

Adds explanations to SemiYield's dashboard without changing SemiYield:

* **Inputs and metric cards** get a `?` icon. Hover it to see what the parameter means and where it sits in the process.
* **Chart points** show what the point represents (values with units, and why it matters). Reference lines
  (UCL / CL / LCL, background doping, junction depth xj) explain themselves when you hover them.
* Text is Traditional Chinese with the English term, so it matches the Eudic study files.

**Covered in this version:** Simulation (oxidation, implantation, etching, deposition), the Data Generator inputs
(needed to feed SPC), and the SPC Dashboard (I-MR chart, Cp/Cpk/Pp/Ppk). Other pages still run normally; their
charts get a generic "x / y" hover until they get their own entries in `explanations.yaml`.

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
* **SPC Dashboard:** choose a real parameter (not `lot_sequence`, which is just a counter), then hover points
  (red = rule violation), the UCL/CL/LCL lines, and the `?` by Cpk / Ppk.
* Sidebar → *Metro 說明覆蓋率*: lists inputs that still have no explanation.

## Editing or adding explanations

Edit `explanations.yaml` (format described at the top of the file) and restart. A tooltip that doesn't match
(e.g. SemiYield renamed a label in an update) is simply missing; it never breaks the app.

## Tests

```powershell
python -m pytest tests\test_semiyield_guide.py
```

The YAML checks always run. The launcher test runs when SemiYield is found (set `SEMIYIELD_DIR`).
