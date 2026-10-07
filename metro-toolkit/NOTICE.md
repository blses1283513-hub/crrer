# Third-party notices

metro-toolkit was written after reviewing three open-source projects. What was
reused, and under which terms:

| Source | License | What metro-toolkit uses |
|---|---|---|
| [SemiYield](https://github.com/OutBlade/semiyield) @ `2f31373` | MIT (per `pyproject.toml`) | `src/metro_toolkit/analysis/spc.py` is adapted from `semiyield/spc/control_charts.py` (control-chart constants, Western Electric rule logic, capability formulas). Changes are listed in the module docstring. Synthetic-data ideas (lot drift, equipment ageing) informed `datagen/`. |
| [WaferLens](https://github.com/anson10/waferLens) @ `77e6e1c` | MIT, Copyright (c) 2026 Anson Antony S | Design ideas only (no code): lot → wafer → site schema with site coordinates, sampled-wafer metrology, radial profile and chamber-bias simulation (`simulate/measurements.py`, `config/fab.yaml`). |
| [sem-toolkit](https://github.com/Narain115/sem-toolkit) @ `936417e` | **No license file** (all rights reserved by default) | **No code used.** Reviewed only. The thin-film module here is an independent implementation. |
| M. A. Green, *Sol. Energ. Mat. Sol. Cells* 92, 1305 (2008), via [refractiveindex.info](https://refractiveindex.info) | CC0 1.0 | `metrology/thinfilm/data/si_green2008.csv` (c-Si n, k at 300 K, 250–1000 nm). |
| I. H. Malitson, *JOSA* 55, 1205 (1965); K. Luke et al., *Opt. Lett.* 40, 4823 (2015); G. E. Jellison & F. A. Modine, *APL* 69, 371 (1996) | published formulas | Sellmeier coefficients for SiO2 and Si3N4; Tauc-Lorentz model and typical a-Si parameters. |

## SemiYield license text (MIT)

```
MIT License

Copyright (c) SemiYield Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
