---
tags: [metro-thickness, role, fundamentals]
chapters: [1, 2]
created: 2026-10-06
---

# 01 · Role and the Manufacturing-to-Metrology Loop（角色與製程—量測迴路）

← [[00 - Metro Thickness Hub]] · next → [[02 Process Modules]]

## 1. What the job actually is（工作本質）

A Thickness Metro Applications Engineer（膜厚量測應用工程師）owns the **trustworthiness of a number**. The number (film thickness, n, k, CD, height…) is a *CTQ — Critical To Quality*（關鍵品質特性）that Process, Equipment, PI (Process Integration 製程整合) and Yield all act on. If that number is wrong, every downstream decision inherits the error, including SPC holds, APC (Advanced Process Control 先進製程控制) feedback, chamber qualification, and lot disposition.

Seven properties the measurement must have:

| Property | Chinese | Practical test |
|---|---|---|
| Physically meaningful | 物理意義正確 | Model stack matches the real film; result agrees with a reference method (XSEM/TEM, XRR) |
| Accurate | 準確 | Bias vs. reference / standard is small and known |
| Repeatable | 重複性 | Static & dynamic repeat on one tool (σ_repeat) |
| Stable over time | 長期穩定 | Control/monitor wafer trend flat; no unexplained drift |
| Comparable between tools | 機台匹配 | Tool-to-tool offset/slope within matching spec |
| Suitable for control | 適合製程控制 | P/T (precision-to-tolerance) and %GRR acceptable; fast enough for sampling plan |
| Sensitive | 靈敏度 | Detects the smallest process shift that matters (≈ ¼–⅓ of the tolerance or less) |

**Key reframe:** you are *not* a tool operator. Operators run recipes; the Applications Engineer decides **whether the recipe's output can be believed**, and **what the output says about the process**.

### The five layers of "thickness"

Each arrow below can fail, and each failure has a typical signature:

```text
Process ──► Physical film ──► Raw signal ──► Model/recipe ──► Extracted number ──► Decision
  (chamber)   (real d, n, k,     (spectrum,     (stack, n/k,      (thickness, GOF)   (SPC, APC,
               roughness,         Ψ/Δ, X-ray     constraints)                          disposition)
               interface)         counts)
```

| Failing box | Typical symptom |
|---|---|
| Process | Spatial signature changes (center/edge/tilt); chamber-specific; correlates with sensor data |
| Physical film | n/k change (density, composition, H content); thickness and index co-move |
| Raw signal | Intensity low, noisy spectrum, focus/pattern-recognition failure, all layers on one tool shift |
| Model | Goodness-of-fit (GOF) drops, residual has structure, parameters hit bounds |
| Statistics/decision | Wrong site map, wrong limits, wrong grouping; "excursion" is a reporting artifact |

## 2. The full loop（完整迴路）

The booklet's loop, annotated with **who owns each step** and **what the Metro engineer contributes**:

| Step | Owner | Metro engineer contribution |
|---|---|---|
| Process recipe (ALD/CVD/PVD/…) | Process / Equipment | Know which knobs move thickness and in which spatial pattern |
| Film | — (physics) | Know the real stack, including native oxide, interfacial layers, roughness |
| Metrology tool → raw signal | Metro equipment | Health checks: lamp, detector, focus, stage, calibration |
| Metro recipe → physical model → fit | **Metro applications** | Build/validate model, select fit parameters, set GOF/reject thresholds |
| Wafer map / statistics | Metro + Process | Site map, summary statistics definitions, outlier rules |
| SPC / Cpk / trend | Process + Metro | Chart design, limits, run rules; separate measurement vs. process variation |
| Excursion detection → RCA | Shared | First question: **"Is it real?"** (measurement vs. process) |
| Corrective action → verify next lot | Process/Equipment | Confirm recovery with the *same* trusted measurement |

### Closed-loop control (APC / R2R)

Many thickness CTQs feed **run-to-run (R2R) control**（批次間控制）:

$$
t_{dep,next} = \frac{T_{target}}{\widehat{DR}}, \qquad \widehat{DR}_k = \lambda\frac{T_k}{t_k} + (1-\lambda)\widehat{DR}_{k-1}
$$

(EWMA estimate of deposition rate; λ ≈ 0.2–0.5.) The consequence: **a Metro bias becomes a process bias**. If the Metro tool reads +0.5 nm high, the controller shortens deposition and the *real* film comes out 0.5 nm thin — while SPC on the Metro data looks perfect. Matching and drift control are therefore not paperwork; they directly set the physical film.

## Core questions — expanded

1. **What is physically being measured?** E.g., ellipsometry measures polarization change (Ψ, Δ), not thickness. Thickness is an *inference*.
2. **How is the signal converted?** Through a forward model (Fresnel/transfer matrix, RCWA, X-ray Parratt) + regression.
3. **Which assumptions are inside the model?** Fixed n/k, sharp interfaces, no roughness, known substrate, isotropy, perfect periodicity (OCD).
4. **How repeatable/reproducible?** GR&R, P/T, long-term monitor. See [[12 MSA and Gauge R&R]].
5. **Is the change from the process?** Reference wafer + second tool + spatial/time signature. See [[17 Root Cause Framework]].
6. **What upstream parameter explains it?** Process physics (Arrhenius vs. mass-transport, ALD window…). See [[02 Process Modules]].
7. **Does it matter?** Relate Δthickness to device CTQ: e.g., gate-oxide capacitance $C_{ox}=\varepsilon_{ox}/t_{ox}$ — a 2 % thickness error is a 2 % C_ox error.

## One-line summary

> The Metro engineer converts a **spectrum** into a **decision** and must be able to defend every step in between.
