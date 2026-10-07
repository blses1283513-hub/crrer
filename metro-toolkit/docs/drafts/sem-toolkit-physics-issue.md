# DRAFT: GitHub issue for Narain115/sem-toolkit (NOT posted)

Review, edit, and post it yourself: https://github.com/Narain115/sem-toolkit/issues/new
Every number below was reproduced by running the repo's own functions (`modules/module2_optical.py`,
commit `936417e`) on 2026-10-07. Line numbers refer to that commit.

Tip: post the license issue and this one separately; they are independent requests.

---

**Title:**

Module 2 (optical metrology): ambient medium, ellipsometry model, and Si constants

**Body:**

Hi Narain, I've been learning from Module 2 and found a few physics issues that change the results.
Sharing them in case they're useful; happy to help test a fix.

**1. The ambient medium `'air'` gets n = 1.5 instead of 1.0** (lines 65–66)

`'air'` isn't one of the cases in `get_optical_constants`, so it falls through to the default
`n = 1.5`. Every stack in the module (lines 149–158, 259) therefore sits under a glass-like medium.

Reproduced: bare Si at 633 nm gives R = 0.160 with the current code, versus 0.309 with the same Si model
and n = 1 ambient (literature value for real Si is about 0.35). Suggested fix: add
`elif material == 'air': n = np.ones_like(w); k = np.zeros_like(w)`.

**2. `simulate_ellipsometry` does not compute Ψ and Δ** (lines 259–269)

- `tmm_reflectance` has no polarization argument (it implements s-polarization only), so `R_s_65` and
  `R_p_65` are both s-polarized reflectances, at 65° and 75° respectively. Ψ is then
  `arctan(sqrt(R_s(75°)/R_s(65°)))`, which is not the ellipsometric Ψ.
- Δ is computed only from wavelength (`exp(2πi·λ/500)`), so it does not depend on the film at all.
  Reproduced: Δ for 100 nm and 200 nm SiO2 is identical (`[36, 126, 216, 306, 36]` deg at 300–800 nm).
  So in the fit, Δ contributes nothing and only the pseudo-Ψ constrains thickness.

Ellipsometry needs the complex Fresnel coefficients of the whole stack for both polarizations at the
same angle: ρ = r_p / r_s = tan(Ψ)·e^{iΔ}. A p-polarization branch in the transfer matrix (using
η = N / cos θ instead of N·cos θ) plus returning the complex r instead of |r|² is enough.
Many tools fit N/C/S (cos 2Ψ, sin 2Ψ cos Δ, sin 2Ψ sin Δ) instead of raw Δ to avoid the 0/360° wrap.

**3. Si optical constants are not the Palik/literature values** (lines 44–48)

The Si model is a Gaussian around n = 3.5. At 633 nm it gives n = 3.50, k = 0.001 (literature:
3.87, 0.016); at 400 nm it gives 5.15, 0.10 (literature: 5.61, 0.30). Since the README cites Palik,
a small tabulated n,k file with interpolation would match it. M. A. Green, *Sol. Energ. Mat. Sol. Cells*
92, 1305 (2008) is available in the public domain (CC0) via refractiveindex.info.

**4. Smaller points**

- **Local-only fit** (line 285): Nelder-Mead from 120 nm can converge to a neighbouring interference
  minimum for thicker films. A coarse thickness grid before the local refinement avoids this.
- **Uniformity definition** (lines 209–214): σ is taken over an 80×80 grid with no edge exclusion.
  Industry maps usually use a defined sampling plan (e.g. 49 points with 3 mm edge exclusion), and
  quoting which definition is used (1σ %, range %, or (max−min)/(2·mean)) helps comparison.
- **Script runs on import**: all computation is at module level, so `import module2_optical` writes files
  to `outputs/`. Wrapping it in functions plus `if __name__ == "__main__":` would make it reusable.

Thanks for putting this project together!
