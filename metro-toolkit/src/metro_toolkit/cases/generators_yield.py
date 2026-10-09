"""Case generators for yield analysis, split experiments, weekly KPIs and defects review cannot classify.

Same contract as generators.py: (rng, level) -> {v, evidence, guide, answer}. Every situation has more than one
outcome (the data decides the right answer), so reading the charts matters. All synthetic: generic fab practice,
no real lots, products, tools or recipes.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..guide import insights as gi
from .generators import LAYERS, SPLIT_NAMES, _fmt, _lot

PITCH = 9.0  # die pitch (mm): about 760 dies on a 300 mm wafer
AREA = round(PITCH * PITCH / 100, 2)  # die area (cm²)
R_DIE = 147.0  # edge exclusion: a die must sit fully inside this radius


def _bi(zh: str, en: str) -> dict:
    return {"zh": zh, "en": en}


def _dies() -> pd.DataFrame:
    c = np.arange(-150 + PITCH / 2, 150, PITCH)
    gx, gy = np.meshgrid(c, c)
    keep = np.hypot(np.abs(gx) + PITCH / 2, np.abs(gy) + PITCH / 2) <= R_DIE
    return pd.DataFrame({"x": gx[keep], "y": gy[keep]})


def _clock(theta: float) -> int:
    """Angle (radians, 0 = +x, counter-clockwise) -> o'clock position with the notch at 6."""
    return int(round((3 - np.degrees(theta) / 30) % 12)) or 12


# --------------------------------------------------------------------------- A + G: inline defects vs probe fails
STEP_PAIRS = [
    ("post-dep surface", "post-etch-back", _bi("沉積後表面檢查", "post-deposition surface inspection"),
     _bi("etch-back 後檢查", "post-etch-back inspection")),
    ("post-CMP surface", "post-cap-etch", _bi("CMP 後表面檢查", "post-CMP surface inspection"),
     _bi("cap 蝕刻後檢查", "post-cap-etch inspection")),
]
FAIL_BINS = [("Bin S (short)", _bi("相鄰線短路", "shorts between neighbouring lines")),
             ("Bin O (open)", _bi("線路斷路", "open lines"))]


def _defects_on(rng, dies: pd.DataFrame, idx: np.ndarray, step: str) -> pd.DataFrame:
    j = rng.uniform(-0.4, 0.4, (len(idx), 2)) * PITCH
    return pd.DataFrame({"x": dies.x.to_numpy()[idx] + j[:, 0], "y": dies.y.to_numpy()[idx] + j[:, 1], "die": idx, "step": step})


def _capture_table(dies: pd.DataFrame, defects: pd.DataFrame, steps: list[str]) -> pd.DataFrame:
    fail = dies["fail"].to_numpy()
    chance = fail.mean()
    rows = []
    for s in steps:
        d = defects[defects.step == s]
        on_fail = fail[d["die"].to_numpy()]
        hit_dies = set(d.loc[on_fail, "die"])
        raw = on_fail.mean() if len(d) else 0.0
        rows.append({"step": s, "defects": len(d), "on fail dies": int(on_fail.sum()),
                     "capture": 100 * len(hit_dies) / max(fail.sum(), 1),
                     "kill_ratio": 100 * max(raw - chance, 0) / (1 - chance), "chance": 100 * chance})
    return pd.DataFrame(rows)


def ye_inline_probe_corr(rng, level):
    """Probe fails cluster in one zone. Two inline inspections cover the module: the current monitor and a second
    step. Either the monitor is blind to the killers (low capture rate; the other step sees them) or it works and the
    job is to quantify the yield the source is costing. Y = exp(-D * A * KR) gives the expected gain."""
    s1, s2, s1_txt, s2_txt = STEP_PAIRS[int(rng.integers(len(STEP_PAIRS)))]
    bin_name, bin_txt = FAIL_BINS[int(rng.integers(len(FAIL_BINS)))]
    lot = _lot(rng)
    wafer = f"{lot}.{int(rng.integers(1, 26)):02d}"
    blind = bool(rng.random() < 0.55)
    low, high = {"basic": (0.10, 0.88), "intermediate": (0.16, 0.84), "advanced": (0.22, 0.80)}[level]
    cap = (low, high) if blind else (high, 0.45)
    dies = _dies()
    n = len(dies)
    r = np.hypot(dies.x, dies.y).to_numpy()
    theta0 = rng.uniform(0, 2 * np.pi)
    edge = bool(rng.random() < 0.6)
    for _ in range(40):  # redraw until capture rates sit clearly on the intended side of the 30 / 60 % lines
        if edge:
            ang = np.angle(np.exp(1j * (np.arctan2(dies.y, dies.x).to_numpy() - theta0)))
            w = np.where((r > 0.72 * R_DIE) & (np.abs(ang) < 0.9), 12.0, 1.0)
        else:
            w = np.where(r < 0.45 * R_DIE, 10.0, 1.0)
        n_kill = int(n * rng.uniform(0.06, 0.08))
        kill = rng.choice(n, n_kill, replace=False, p=w / w.sum())
        rest = np.setdiff1d(np.arange(n), kill)
        other = rng.choice(rest, int(0.012 * n), replace=False)  # fails from other causes: no inline defect explains them
        dies["fail"] = False
        dies.loc[np.r_[kill, other], "fail"] = True
        parts = []
        for step, c, n_nk in ((s1, cap[0], int(rng.uniform(2.0, 2.6) * n_kill)), (s2, cap[1], int(rng.uniform(0.6, 0.9) * n_kill))):
            seen = kill[rng.random(n_kill) < c]
            parts.append(_defects_on(rng, dies, np.r_[seen, rng.choice(n, n_nk)], step))
        defects = pd.concat(parts, ignore_index=True)
        table = _capture_table(dies, defects, [s1, s2])
        c1, c2 = table["capture"]
        if (blind and c1 < 27 and c2 >= 63) or (not blind and c1 >= 63 and 30 <= c2 < 60):
            break
    f_map = gi.probe_overlay(dies, bin_name, R_DIE)
    f_ck = gi.capture_kill(table, s1, AREA, n)
    t = table.set_index("step")
    v = {"lot": lot, "wafer": wafer, "bin": bin_name, "bin_txt": bin_txt, "s1": s1, "s2": s2, "s1_txt": s1_txt, "s2_txt": s2_txt,
         "n_fail": f_map.v["n_fail"], "fail_pct": f_map.v["fail_pct"], "zone": f_map.v["fail_zone"],
         "cap1": round(float(t.loc[s1, "capture"])), "cap2": round(float(t.loc[s2, "capture"])),
         "kr1": round(float(t.loc[s1, "kill_ratio"])), "kr2": round(float(t.loc[s2, "kill_ratio"])),
         "chance": f_ck.v["chance"], "best_step": f_ck.v["best_step"], "d_best": f_ck.v["d_best"], "area": AREA,
         "kr_best": f_ck.v["kr_best"], "gain": f_ck.v["gain"], "n_dies": n,
         "verdict": (_bi(f"目前的監控站 {s1} 幾乎看不到這些失效（capture {round(float(t.loc[s1, 'capture']))}%），{s2} 才抓得到"
                         f"（{round(float(t.loc[s2, 'capture']))}%）：監控站放錯位置",
                         f"the current monitor {s1} barely sees these fails (capture {round(float(t.loc[s1, 'capture']))}%), while {s2} "
                         f"catches them ({round(float(t.loc[s2, 'capture']))}%): the monitor sits at the wrong step") if blind else
                     _bi(f"目前的監控站 {s1} 抓得到這些失效（capture {round(float(t.loc[s1, 'capture']))}%、kill ratio "
                         f"{round(float(t.loc[s1, 'kill_ratio']))}%）：是真的 killer 缺陷來源",
                         f"the current monitor {s1} does catch these fails (capture {round(float(t.loc[s1, 'capture']))}%, kill ratio "
                         f"{round(float(t.loc[s1, 'kill_ratio']))}%): a real killer-defect source")),
         "ask": (_bi(f"把這個 module 的缺陷監控移到（或加上）{s2}，設定抽樣、SPC 與 review；{s1} 的 count 不能用來放行這種失效",
                     f"move (or add) this module's defect monitor to {s2} with sampling, SPC and review; {s1}'s counts cannot clear "
                     "lots for this fail mode") if blind else
                 _bi(f"把疊圖、kill ratio 和預期良率回收交給 PE／EE，優先修缺陷來源；{s1} 維持監控",
                     f"send the overlay, the kill ratio and the expected yield gain to PE / EE to fix the defect source first; "
                     f"{s1} stays the monitor"))}
    answer = ({"cause": "C_INSP_BLIND", "action": "A_MOVE_MONITOR", "decision": "D_SWITCH_MONITOR",
               "notify": ["PIE_YE", "RDA", "PE"]} if blind else
              {"cause": "C_KILLER_SOURCE", "action": "A_SOURCE_FIX", "decision": "D_FIX_SOURCE", "notify": ["PIE_YE", "PE", "EE"]})
    gain_tab = pd.DataFrame([{"item": "D = defects / (dies × A)", "value": f"{f_ck.v['d_best']} /cm²  ({f_ck.v['best_step']})"},
                             {"item": "A = die area", "value": f"{AREA} cm²"},
                             {"item": "KR = kill ratio (chance-adjusted)", "value": f"{f_ck.v['kr_best']}"},
                             {"item": "loss = 1 − exp(−D·A·KR)", "value": f"{f_ck.v['gain']} pp"}])
    return {"v": v, "answer": answer,
            "evidence": [{"kind": "probe_overlay", "dies": dies, "defects": defects, "steps": [s1, s2], "bin": bin_name,
                          "title": f"{wafer} · {bin_name} vs inline"},
                         {"kind": "capture_kill", "table": table, "monitor": s1},
                         {"kind": "table", "table": gain_tab, "title": "預期良率回收 · expected yield gain  Y = exp(−D·A·KR)"}],
            "guide": [("probe_overlay", f_map), ("capture_kill", f_ck)]}


# --------------------------------------------------------------------------- B: is the split valid at all?
def split_confounded(rng, level):
    """A three-group split (POR / B-low / B-high). Either a litho FEM on the same wafers confounds it, or the B-high
    group never ran (the run log shows the B-low recipe), or it is clean. PE's claim is read off the planned groups."""
    split = SPLIT_NAMES[int(rng.integers(len(SPLIT_NAMES)))]
    lot = _lot(rng)
    kind = str(rng.choice(["confounded", "misset", "valid"], p=[0.45, 0.25, 0.30]))
    noise = {"basic": 0.7, "intermediate": 0.9, "advanced": 1.1}[level]
    for _ in range(60):
        slots = np.arange(1, 25)
        planned = np.array(["POR"] * 8 + ["B-low"] * 8 + ["B-high"] * 8)[rng.permutation(24)]
        actual = planned.copy()
        fem = np.array(["nominal"] * 24, dtype=object)
        e_low, e_high = (rng.uniform(-0.2, 0.4),) * 2 if kind == "confounded" else (rng.uniform(1.6, 2.4), rng.uniform(3.0, 3.8))
        if kind == "confounded":
            n_b = {"basic": 6, "intermediate": 6, "advanced": 5}[level]
            b_idx = rng.choice(np.where(planned != "POR")[0], n_b, replace=False)
            p_idx = rng.choice(np.where(planned == "POR")[0], 6 - n_b, replace=False)
            fem[np.r_[b_idx, p_idx].astype(int)] = "off"
        elif rng.random() < 0.5:  # a balanced FEM: 2 off-nominal wafers in every group
            for g in ("POR", "B-low", "B-high"):
                fem[rng.choice(np.where(planned == g)[0], 2, replace=False)] = "off"
        if kind == "misset":
            actual[planned == "B-high"] = "B-low"
        eff = np.where(actual == "B-low", e_low, np.where(actual == "B-high", e_high, 0.0))
        fem_loss = {"basic": 9.0, "intermediate": 8.0, "advanced": 10.0}[level] * rng.uniform(0.9, 1.1)
        y = 88.0 + eff - np.where(fem == "off", fem_loss, 0.0) + rng.normal(0, noise, 24)
        t = pd.DataFrame({"wafer_id": [f"{lot}.{s:02d}" for s in slots], "slot": slots, "planned": planned, "actual": actual,
                          "fem": fem, "yield": np.round(y, 1)})
        f = gi.split_check(t)
        ok = {"confounded": f.v["delta_all"] <= -1.5 and abs(f.v["delta_nom"]) < 0.8 and f.status == "act",
              "misset": abs(f.v["d_setting"]) < 0.8 and f.v["delta_all"] > 1.0,
              "valid": f.v["delta_nom"] >= 1.5 and f.v["d_setting"] >= 0.8}[kind]
        if ok and (kind != "valid" or f.status == "good"):
            break
    claim = {"confounded": _bi(f"B 組比 POR 低 {abs(f.v['delta_all'])} pp，B 條件比較差，建議放棄",
                               f"B is {abs(f.v['delta_all'])} pp below POR, so condition B is worse and should be dropped"),
             "misset": _bi(f"B-high 比 B-low 只差 {f.v['d_setting']:+} pp，加高沒有用，直接選 B-low 轉換",
                           f"B-high is only {f.v['d_setting']:+} pp vs B-low, so the higher setting does nothing: convert with B-low"),
             "valid": _bi(f"B 組比 POR 高 {f.v['delta_all']} pp，B-high 最好，建議轉換",
                          f"B is {f.v['delta_all']} pp above POR and B-high is best, so convert")}[kind]
    runlog = (_bi(f"計畫 B-high 的 {f.v['n_misrun']} 片，run log 都是 B-low 的 recipe", f"all {f.v['n_misrun']} wafers planned as B-high "
                  "ran the B-low recipe per the run log") if kind == "misset" else
              _bi("每片的 recipe 都和計畫一致", "every wafer ran the recipe it was planned for"))
    fem_txt = (_bi(f"同一批還跑了 litho FEM：偏離標準條件的 {f.v['n_fem_off']} 片中 B 組 {f.v['fem_b']} 片、POR 組 {f.v['fem_por']} 片",
                   f"the same lot also carried a litho FEM: of the {f.v['n_fem_off']} off-nominal wafers, {f.v['fem_b']} are in B and "
                   f"{f.v['fem_por']} in POR") if f.v["n_fem_off"] else
               _bi("這批沒有其他實驗", "no other experiment ran on this lot"))
    verdict = {"confounded": _bi("B 組的差異來自 FEM 偏離條件的晶圓，不是 B 條件：這個 split 結果不能用（無法下結論），要用乾淨的晶圓重跑",
                                 "the B difference comes from the off-nominal FEM wafers, not from condition B: the split is "
                                 "inconclusive and must be rerun on clean wafers"),
               "misset": _bi("B-high 實際上沒有跑：「加高沒用」的結論不成立，設定的問題無法下結論，要補跑 B-high",
                             "B-high never actually ran, so \"the higher setting does nothing\" does not hold: the setting question "
                             "is inconclusive and B-high must be rerun"),
               "valid": _bi("分組照計畫執行、沒有其他實驗干擾，只看標準條件晶圓也成立：split 結果有效，可以進入轉換評估",
                            "the groups ran as planned, nothing else interferes, and the result holds on nominal wafers alone: "
                            "the split is valid and can go to the conversion review")}[kind]
    v = {"split": split, "lot": lot, "claim": claim, "runlog": runlog, "fem_txt": fem_txt, "verdict": verdict,
         **{k: f.v[k] for k in ("delta_all", "delta_nom", "d_setting", "n_misrun", "n_fem_off", "fem_b", "fem_por")}}
    answer = {"confounded": {"cause": "C_CONFOUNDED", "action": "A_RERUN_SPLIT", "decision": "D_INCONCLUSIVE"},
              "misset": {"cause": "C_SPLIT_MISSET", "action": "A_RERUN_SPLIT", "decision": "D_INCONCLUSIVE"},
              "valid": {"cause": "C_SPLIT_VALID", "action": "A_REPORT_SPLIT", "decision": "D_SPLIT_VALID"}}[kind]
    g = t.groupby("planned", sort=False)
    summ = pd.DataFrame({"planned group": ["POR", "B-low", "B-high"]})
    summ["wafers"] = summ["planned group"].map(g.size())
    summ["ran as planned"] = summ["planned group"].map(t[t.planned == t.actual].groupby("planned").size()).fillna(0).astype(int)
    summ["FEM off-nominal"] = summ["planned group"].map(t[t.fem == "off"].groupby("planned").size()).fillna(0).astype(int)
    summ["mean yield (%)"] = summ["planned group"].map(g["yield"].mean())
    summ["nominal FEM only (%)"] = summ["planned group"].map(t[t.fem == "nominal"].groupby("planned")["yield"].mean())
    return {"v": v, "answer": answer,
            "evidence": [{"kind": "split_check", "table": t, "title": f"{lot} · split {split['en']}"},
                         {"kind": "table", "table": summ, "title": "依計畫分組 · by planned group (run log and FEM check)"}],
            "guide": [("split_check", f)]}


# --------------------------------------------------------------------------- C: zone-based split result
def split_zone_decision(rng, level):
    """Head-to-head POR vs B: B gains in the centre and loses at the edge. Either the die-weighted net is a clear gain
    (adopt and follow the edge up) or the edge loss cancels it (keep POR, fix the edge and re-split)."""
    split = SPLIT_NAMES[int(rng.integers(len(SPLIT_NAMES)))]
    lot_p, lot_b = _lot(rng), _lot(rng)
    gain = bool(rng.random() < 0.55)
    share = {"centre": 25.0, "mid": 39.0, "edge": 36.0}  # area of r < 0.5 R, 0.5-0.8 R, > 0.8 R
    base = {"centre": 93.0, "mid": 91.0, "edge": 83.0}
    k = {"basic": 1.0, "intermediate": 0.8, "advanced": 0.65}[level]
    n = 12
    for _ in range(60):
        dz = ({"centre": rng.uniform(3.2, 4.2) * k, "mid": rng.uniform(1.6, 2.2) * k, "edge": -rng.uniform(1.2, 1.6) * k} if gain else
              {"centre": rng.uniform(3.2, 4.2) * k, "mid": rng.uniform(0.2, 0.6) * k, "edge": -rng.uniform(3.0, 3.6) * k})
        rows = []
        for grp in ("POR", "B"):
            for i in range(n):
                wid = f"{lot_p if grp == 'POR' else lot_b}.{i + 1:02d}"
                for z in share:
                    rows.append({"wafer_id": wid, "group": grp, "zone": z,
                                 "yield": base[z] + (dz[z] if grp == "B" else 0.0) + rng.normal(0, 1.1)})
        w = pd.DataFrame(rows)
        tot = (w.assign(wy=w["yield"] * w["zone"].map(share) / 100).groupby(["group", "wafer_id"])["wy"].sum())
        net = float(tot["B"].mean() - tot["POR"].mean())
        net_se = float(np.sqrt(tot["B"].var(ddof=1) / n + tot["POR"].var(ddof=1) / n))
        m = w.groupby(["zone", "group"])["yield"].agg(["mean", "var"]).unstack("group")
        zt = pd.DataFrame({"zone": list(share), "share": [share[z] for z in share], "por": [m.loc[z, ("mean", "POR")] for z in share],
                           "b": [m.loc[z, ("mean", "B")] for z in share]})
        zt["delta"] = zt["b"] - zt["por"]
        zt["se"] = [np.sqrt((m.loc[z, ("var", "B")] + m.loc[z, ("var", "POR")]) / n) for z in share]
        zt["weighted"] = zt["delta"] * zt["share"] / 100
        edge_sig = zt.set_index("zone").loc["edge", "delta"] < -2 * zt.set_index("zone").loc["edge", "se"]
        if edge_sig and ((gain and net > 2.5 * net_se) or (not gain and abs(net) < 1.5 * net_se)):
            break
    f = gi.zone_split(zt, net, net_se)
    dies_gain = round(net / 100 * len(_dies()), 1)
    verdict = (_bi(f"加權淨效果 {net:+.2f} ± {net_se:.2f} pp，明顯為正：建議轉換到 B（每片約多 {dies_gain} 顆良品），同時追蹤邊緣的損失",
                   f"the die-weighted net is {net:+.2f} ± {net_se:.2f} pp, clearly positive: convert to B (about {dies_gain} more good dies "
                   "per wafer) and follow up the edge loss") if gain else
               _bi(f"中心的增益被邊緣的損失抵消，加權淨效果 {net:+.2f} ± {net_se:.2f} pp，看不出整體好處：維持 POR，請 PE 先解決 B 的邊緣問題再重做 split",
                   f"the centre gain is cancelled by the edge loss; the die-weighted net is {net:+.2f} ± {net_se:.2f} pp, no overall "
                   "gain: keep POR and have PE fix B's edge loss before re-splitting"))
    v = {"split": split, "lot_p": lot_p, "lot_b": lot_b, "n_por": n, "n_b": n, "dies_gain": dies_gain, "verdict": verdict,
         **{k_: f.v[k_] for k_ in ("d_c", "d_m", "d_e", "share_c", "share_m", "share_e", "net", "net_se")}}
    answer = ({"cause": "C_NET_GAIN", "action": "A_ADOPT_FOLLOWUP", "decision": "D_ADOPT_SPLIT", "notify": ["PE", "PIE_YE", "MGR_QE"]}
              if gain else {"cause": "C_ZONE_CANCEL", "action": "A_FIX_ZONE_RESPLIT", "decision": "D_KEEP_POR", "notify": ["PE", "PIE_YE"]})
    tab = zt.rename(columns={"share": "die share (%)", "por": "POR (%)", "b": "B (%)", "delta": "B − POR (pp)", "se": "± SE (pp)",
                             "weighted": "weighted (pp)"})
    return {"v": v, "answer": answer,
            "evidence": [{"kind": "zone_yield", "table": zt, "net": net, "net_se": net_se,
                          "title": f"POR {lot_p} vs B {lot_b} · {split['en']}"},
                         {"kind": "table", "table": tab, "title": "依區域 · by zone (weighted = Δ × die share)"}],
            "guide": [("zone_yield", f)]}


# --------------------------------------------------------------------------- D + F: the weekly KPI review
LEVELS_M = ["M1", "M2", "M3", "M4"]
PARTICLE_TOOLS = ["CVD01", "CVD02", "ETCH03", "CMP02"]


def kpi_dly_trend(rng, level):
    """Twelve weeks of defect-limited yield (DLY) by probe week vs goal, its random / systematic split, inline killer
    density by process week, and opens / shorts passing per metal level. The latest week is red, for one of three
    reasons: lots processed before a fix still reaching probe (lag), a few excursion wafers dragging the average
    (the baseline is on goal), or a growing systematic loss on one level."""
    kind = str(rng.choice(["lag", "outlier", "level"], p=[0.36, 0.30, 0.34]))
    weeks = [f"W{30 + i}" for i in range(12)]
    goal = float(rng.choice([91.0, 91.5, 92.0, 92.5, 93.0]))
    k = {"basic": 1.0, "intermediate": 0.85, "advanced": 0.72}[level]
    lag = 3
    fix_i = 8  # W38: the fix week in the lag story; process weeks 6-8 (W36-W38) are hit
    lvl = str(rng.choice(LEVELS_M[1:]))
    mode = str(rng.choice(["opens", "shorts"]))
    tool = str(rng.choice(PARTICLE_TOOLS))
    xlot = _lot(rng)
    for _ in range(60):
        rand = (100 - goal - 1.1) * 0.6 + rng.normal(0, 0.15, 12)
        sys_ = (100 - goal - 1.1) * 0.4 + rng.normal(0, 0.12, 12)
        dens = 0.10 + rng.normal(0, 0.006, 12)
        if kind == "lag":
            bump = rng.uniform(2.2, 2.8) * k
            dens[6:9] *= 1 + np.array([0.8, 1.5, 1.2]) * bump / 2
            rand[6 + lag:] += np.array([1.0, 1.6, 1.35]) * bump  # probe weeks W39-W41 carry the W36-W38 lots
        elif kind == "level":
            sys_[8:] += np.array([0.5, 1.0, 1.6, 2.2]) * k
        dly = 100 - rand - sys_
        dly_ex = dly.copy()
        if kind == "outlier":
            n_w, bad = 48, rng.uniform(52, 62)
            dly[-1] = (dly_ex[-1] * (n_w - 2) + 2 * bad) / n_w
        w = pd.DataFrame({"week": weeks, "dly": dly, "dly_ex": dly_ex, "random_loss": rand, "sys_loss": sys_, "density": dens})
        f = gi.dly_trend(w, goal, weeks[fix_i] if kind == "lag" else None)
        earlier_red = (w["dly"].iloc[:8] < goal).any()
        ok = f.status == "act" and not earlier_red and {
            "lag": w["dly"].iloc[9:].lt(goal).all() and dens[9:].max() < 0.12,
            "outlier": dly_ex[-1] >= goal + 0.3 and w["dly"].iloc[8:11].ge(goal).all(),
            "level": w["dly"].iloc[10:].lt(goal).all() and w["dly"].iloc[8] >= goal}[kind]
        if ok:
            break
    rows = []
    for i, wk in enumerate(weeks):
        for lv_ in LEVELS_M:
            for md in ("opens", "shorts"):
                p = 99.7 - (0.1 if md == "shorts" else 0.0) + rng.normal(0, 0.05)
                if kind == "level" and lv_ == lvl and md == mode and i >= 8:
                    p -= sys_[i] - (100 - goal - 1.1) * 0.4
                if kind == "lag" and md == "shorts" and i >= 6 + lag:
                    p -= 0.12
                rows.append({"week": wk, "level": lv_, "mode": md, "pass_pct": p})
    lv = pd.DataFrame(rows)
    f_lv = gi.level_pass(lv)
    last = weeks[-1]
    lots = []
    for j in range(6):
        pw = weeks[-1 - lag + int(rng.integers(-1, 1))]  # processed ~3 weeks before probe
        lot = xlot if (kind == "outlier" and j == 2) else _lot(rng)
        d = round(float(w["dly_ex"].iloc[-1] + rng.normal(0, 0.4)), 1)
        flag = ""
        if kind == "outlier" and j == 2:
            d, flag = round(float((d * 6 + 2 * 57) / 8), 1), "2 wafers scratched at handling (already dispositioned)"
        lots.append({"lot": lot, "process week": pw, "probe week": last, "wafers": 8, "DLY (%)": d, "flag": flag})
    lot_tab = pd.DataFrame(lots)
    dly_l, dly_x = f.v["dly_latest"], f.v["dly_ex_latest"]
    story = {
        "lag": dict(driver_key=weeks[fix_i],
                    context=_bi(f"{weeks[6]}–{weeks[fix_i]} 在 {tool} 找到微粒來源，{weeks[fix_i]} 已清腔修好。",
                                f"A particle source on {tool} was found in {weeks[6]}–{weeks[fix_i]} and fixed by a chamber clean in {weeks[fix_i]}."),
                    status_text=_bi("紅燈，但原因已知且已修", "red, with a known cause that is already fixed"),
                    driver=_bi(f"{last} 的低良率 lot 都是在修好（{weeks[fix_i]}）之前製造的；probe 比製程晚約 {lag} 週，所以 DLY 落後於修正。"
                               f"inline killer 密度在 {weeks[fix_i + 1]} 起已回到基準（{f.v['dens_latest']}/cm²）",
                               f"the low lots probed in {last} were all processed before the fix ({weeks[fix_i]}); probe runs about {lag} "
                               f"weeks behind processing, so DLY lags the fix. Inline killer density is back to baseline since "
                               f"{weeks[fix_i + 1]} ({f.v['dens_latest']}/cm²)"),
                    actions=_bi("修正維持；DLY 改用製程週對照，並用 inline 密度作為領先指標", "keep the fix; read DLY against process week and use "
                                "the inline density as the leading indicator"),
                    watch=_bi(f"第一批修正後製造的 lot 預計 {lag} 週後 probe，確認 DLY 回到目標", f"the first lots processed after the fix reach probe "
                              f"in about {lag} weeks: verify DLY is back on goal")),
        "outlier": dict(driver_key=xlot,
                        context=_bi(f"這週有一批已知異常 lot（{xlot}）。", f"There was one known excursion lot ({xlot}) this week."),
                        status_text=_bi(f"含全部晶圓為紅燈（{dly_l}%），不含 {xlot} 的 2 片異常晶圓為 {dly_x}%（達標）",
                                        f"red with all wafers ({dly_l}%), {dly_x}% without the 2 excursion wafers of {xlot} (on goal)"),
                        driver=_bi(f"{xlot} 的 2 片晶圓（handling 刮傷，已處置）把整週平均拉低；基準線在目標之上，隨機與系統性損失都正常",
                                   f"2 wafers of {xlot} (handling scratch, already dispositioned) drag the weekly average; the baseline is "
                                   "above goal and both random and systematic loss are normal"),
                        actions=_bi("同時報告含與不含的數字並寫明排除原因；刮傷事件另開 excursion 追蹤，不從資料中刪除",
                                    "report the number with and without those wafers and state why; track the scratch event as its own "
                                    "excursion and never delete it from the data"),
                        watch=_bi("確認 handling 的修正有效、下週沒有新的刮傷晶圓", "confirm the handling fix holds and no new scratched wafers appear next week")),
        "level": dict(driver_key=lvl,
                      context=_bi("這段時間沒有記錄到任何製程變更。", "No process change was recorded in this period."),
                      status_text=_bi(f"紅燈，而且是真的：{lvl} {mode} 持續變差", f"red, and real: {lvl} {mode} keeps getting worse"),
                      driver=_bi(f"系統性損失從 {f.v['sys_base']} pp 升到 {f.v['sys_latest']} pp；{lvl} 的 {mode} 通過率 {f_lv.v['worst_base']}% → "
                                 f"{f_lv.v['worst_latest']}%，隨機缺陷損失與 inline 密度都正常",
                                 f"systematic loss rose from {f.v['sys_base']} to {f.v['sys_latest']} pp; {lvl} {mode} passing went "
                                 f"{f_lv.v['worst_base']}% → {f_lv.v['worst_latest']}%, while random-defect loss and inline density are normal"),
                      actions=_bi(f"對 {lvl} module 開 excursion：commonality、該層 inline 資料、失效晶粒 FA", f"open an excursion on the {lvl} module: "
                                  "commonality, that level's inline data and FA on failing dies"),
                      watch=_bi(f"{lvl} {mode} 的週趨勢與 FA 結果", f"the weekly {lvl} {mode} trend and the FA result"))}[kind]
    v = {"latest": last, "dly_latest": dly_l, "dly_ex": dly_x, "goal": goal, "lag": lag, "fix_week": weeks[fix_i], "tool": tool,
         "xlot": xlot, "level": lvl, "mode": mode, "n_red": f.v["n_red"], **story}
    answer = {"lag": {"cause": "C_PROBE_LAG", "action": "A_TRACK_LEADING", "decision": "D_KEEP_FIX_VERIFY", "notify": ["MGR_QE", "PIE_YE"]},
              "outlier": {"cause": "C_OUTLIER_WAFERS", "action": "A_REPORT_BOTH", "decision": "D_BASELINE_OK", "notify": ["MGR_QE", "PIE_YE"]},
              "level": {"cause": "C_LEVEL_SYSTEMATIC", "action": "A_ESCALATE_LEVEL", "decision": "D_RED_ESCALATE",
                        "notify": ["MGR_QE", "PIE_YE", "PE", "RDA"]}}[kind]
    return {"v": v, "answer": answer,
            "evidence": [{"kind": "dly_trend", "w": w, "goal": goal, "fix_week": weeks[fix_i] if kind == "lag" else None},
                         {"kind": "level_pass", "lv": lv},
                         {"kind": "table", "table": lot_tab, "title": f"{last} probe 的 lot · lots probed in {last}"}],
            "guide": [("dly_trend", f), ("level_pass", f_lv)]}


# --------------------------------------------------------------------------- E: a defect review cannot classify
NEXT_LAYER = {"Metal-2 Cu CMP": "via-2 etch", "contact etch": "contact W CMP", "STI CMP": "gate poly etch",
              "word-line etch": "word-line spacer dep", "via-1 clean": "Metal-2 trench etch"}
SEM_CLASSES = [("rough surface", "粗糙表面"), ("no defect visible", "看不到缺陷"), ("shallow bubble-like", "淺層氣泡狀"), ("other", "其他")]


def insp_unclassified_defect(rng, level):
    """Optical inspection shows a cluster SEM review cannot classify (rough surface / nothing / a shallow bubble). The
    next layer's inspection decides it: the cluster comes back at the same place (a real, possibly sub-surface
    defect: cross-section it) or vanishes (a surface artefact: tune the recipe)."""
    layer = str(rng.choice(LAYERS))
    nxt = NEXT_LAYER[layer]
    lot = _lot(rng)
    wafer = f"{lot}.{int(rng.integers(1, 26)):02d}"
    real = bool(rng.random() < 0.55)
    radius = 0.5
    edge = bool(rng.random() < 0.6)
    theta = rng.uniform(0, 2 * np.pi)
    rc = rng.uniform(118, 135) if edge else rng.uniform(0, 30)
    cx, cy = rc * np.cos(theta), rc * np.sin(theta)
    loc = (_bi(f"邊緣 {_clock(theta)} 點鐘方向", f"edge at {_clock(theta)} o'clock") if edge else _bi("晶圓中心", "wafer centre"))
    p_rep = {"basic": 0.82, "intermediate": 0.68, "advanced": 0.58}[level] if real else rng.uniform(0.02, 0.07)
    for _ in range(40):
        n_c = int(rng.integers(35, 60))
        cl = pd.DataFrame({"x": cx + rng.normal(0, 6, n_c), "y": cy + rng.normal(0, 6, n_c), "cluster": True})

        def scatter(m):
            rr, aa = 145 * np.sqrt(rng.random(m)), rng.uniform(0, 2 * np.pi, m)
            return pd.DataFrame({"x": rr * np.cos(aa), "y": rr * np.sin(aa)})

        d1 = pd.concat([cl, scatter(int(rng.integers(60, 90))).assign(cluster=False)], ignore_index=True)
        rep = cl[rng.random(n_c) < p_rep]
        d2 = pd.concat([pd.DataFrame({"x": rep.x + rng.normal(0, 0.12, len(rep)), "y": rep.y + rng.normal(0, 0.12, len(rep))}),
                        scatter(int(rng.integers(50, 80)))], ignore_index=True)
        f = gi.layer_repeat(d1, d2, radius, loc)
        if (real and f.v["repeat_pct"] >= 52) or (not real and f.v["repeat_pct"] < 12):
            break
    n_rev = 30
    sem = rng.multinomial(n_rev, rng.dirichlet([6, 3, 3, 1]))
    top = int(np.argmax(sem[:3]))
    rev = pd.DataFrame({"review mode": ["SEM top-down"] * 4 + ["optical review"] * 2,
                        "class": [f"{e} {z}" for e, z in SEM_CLASSES] + ["colour change 色差", "blister-like 鼓起狀"],
                        "count": list(sem) + [int(n_rev * 0.6), n_rev - int(n_rev * 0.6)]})
    sem_top = _bi(SEM_CLASSES[top][1], SEM_CLASSES[top][0])
    verdict = (_bi("同位置在下一層再出現：是真的實體缺陷（可能在表面下或被覆蓋），SEM 俯視看不出來不代表不存在",
                   "it reappears at the same place at the next layer: a real physical defect (possibly below the surface or "
                   "covered); SEM top-down not seeing it does not mean it is not there") if real else
               _bi("下一層同位置幾乎沒有再出現：是表面才有的假訊號（色差／粗糙度），屬於 nuisance",
                   "it does not come back at the next layer: a surface-only signal (colour / roughness), i.e. nuisance"))
    ask = (_bi(f"請在 cluster（{loc['zh']}）做 FIB 切面，並換 review 方式（傾斜 SEM、EDX）；下一層與 probe 繼續追蹤這幾片",
               f"please cut a FIB cross-section in the cluster ({loc['en']}) and try other review modes (tilted SEM, EDX); keep "
               "following these wafers at the next layer and at probe") if real else
           _bi("用這批的 review 結果調整檢查 recipe（threshold、nuisance filter），確認真缺陷的 capture rate 沒有下降",
               "tune the inspection recipe (threshold, nuisance filter) with this lot's review data and confirm the capture rate "
               "of real defects does not drop"))
    gain = (_bi("在 probe 前知道缺陷是什麼、會不會致命，必要時及早處置受影響晶圓", "know what the defect is and whether it kills before "
                "probe, so affected wafers can be dispositioned early") if real else
            _bi("減少假訊號、避免不必要的 review 與 hold", "fewer false signals, no needless review or hold"))
    v = {"layer": layer, "next_layer": nxt, "lot": lot, "wafer": wafer, "cluster_loc": loc, "sem_top": sem_top, "radius": radius,
         "verdict": verdict, "ask": ask, "gain_text": gain, "n_rev": n_rev,
         **{k: f.v[k] for k in ("n1", "n2", "cluster_n", "n_repeat", "repeat_pct")}}
    answer = ({"cause": "C_SUBSURFACE", "action": "A_XSECTION", "decision": "D_FLAG_TRACK", "notify": ["RDA", "PE", "PIE_YE"]} if real else
              {"cause": "C_SURFACE_ARTIFACT", "action": "A_TUNE_RECIPE", "decision": "D_RELEASE", "notify": ["RDA"]})
    return {"v": v, "answer": answer,
            "evidence": [{"kind": "layer_repeat", "d1": d1, "d2": d2, "radius": radius, "layers": [layer, nxt],
                          "title": f"{wafer} · {layer} → {nxt}"},
                         {"kind": "table", "table": rev, "title": f"cluster review（{n_rev} 顆）· review of the cluster"}],
            "guide": [("layer_repeat", f)]}


YIELD_GENERATORS = {"ye_inline_probe_corr": ye_inline_probe_corr, "split_confounded": split_confounded,
                    "split_zone_decision": split_zone_decision, "kpi_dly_trend": kpi_dly_trend,
                    "insp_unclassified_defect": insp_unclassified_defect}
