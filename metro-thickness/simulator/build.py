"""
build.py — assemble the DRAM Thickness Metro Simulator from the original
DRAM Metro Simulator (src/base.html) plus the thickness modules in src/.

    python build.py            -> dist/dram-thickness-metro-simulator.html

Each patch asserts that its anchor text occurs exactly once, so a change in
base.html fails loudly instead of silently producing a broken page.
"""
import json
import re
from pathlib import Path

HERE = Path(__file__).parent
SRC = HERE / "src"
OUT = HERE / "dist" / "dram-thickness-metro-simulator.html"
TERMS = HERE.parent / "glossary" / "terms.json"


def patch(text, old, new, label):
    n = text.count(old)
    assert n == 1, f"patch '{label}': anchor found {n} times"
    return text.replace(old, new)


html = (SRC / "base.html").read_text(encoding="utf-8")

# ---------------------------------------------------------------- page identity
html = patch(html, "<title>DRAM Metro Simulator</title>", "<title>DRAM Thickness Metro Simulator</title>", "title")
html = patch(
    html,
    "<h1>DRAM Metro Simulator：量測偏移 → 電子 → fail bit</h1>",
    "<h1>DRAM 膜厚量測模擬器：製程 → 膜 → 訊號 → 模型 → 膜厚 → fail bit</h1>",
    "h1",
)
html = patch(
    html,
    '<p class="lede">一階物理模型＋製程變異層。',
    '<p class="lede">以《Metro Thickness Tools Book》為骨架，延伸自 DRAM Metro Simulator：先在 T1–T4 走完膜厚量測的整條鏈'
    '（光譜→模型→膜厚→晶圓圖→SPC→根因），再看膜厚如何經 C_s、漏電與感測餘量變成 fail bit。'
    '虛線底線的術語可停留或點選，顯示中文、短定義與相關詞。一階物理模型＋製程變異層。',
    "lede",
)

# ---------------------------------------------------------------- sections
html = patch(
    html,
    '<main class="wrap">\n  <section id="m6"',
    '<main class="wrap">\n'
    '  <nav class="jump" aria-label="模組"><a href="#t4">T4 異常判讀</a><a href="#t1">T1 光學量測</a><a href="#t2">T2 ALD 晶圓圖</a>'
    '<a href="#t3">T3 SPC・量具・匹配</a><a href="#npi">NPI 驗證</a><a href="#m6">M6 漂移傳遞</a><a href="#m2">M2 cell</a><a href="#m4">M4 餘量</a><a href="#m5">M5 retention</a></nav>\n'
    '  <section id="t4" class="panel" aria-labelledby="h-t4"></section>\n'
    '  <section id="t1" class="panel" aria-labelledby="h-t1"></section>\n'
    '  <section id="t2" class="panel" aria-labelledby="h-t2"></section>\n'
    '  <section id="t3" class="panel" aria-labelledby="h-t3"></section>\n'
    '  <section id="npi" class="panel" aria-labelledby="h-npi"></section>\n'
    '  <section id="m6"',
    "sections",
)
html = patch(
    html,
    '<footer id="foot" class="panel"></footer>\n</main>',
    '<footer id="foot" class="panel"></footer>\n</main>\n<div class="wcard" id="wcard" role="dialog" aria-label="術語定義" hidden></div>',
    "wcard",
)

# ---------------------------------------------------------------- engine: dielectric leakage joins retention
html = patch(
    html,
    "    const tMain = p.tMain45_s * Math.pow(p.rMain, k) * qv;\n    const tTail = tail.t_s * Math.pow(p.rTail, k) * qv;",
    "    // dielectric leakage through the capacitor (thickness module): adds a parallel discharge rate\n"
    "    const tDiel = (p.Jcell_Acm2 > 0 && c.designOK) ? (c.Cs_fF * 1e-15 * c.Vallow_V) / (p.Jcell_Acm2 * c.A_nm2 * 1e-14) * Math.pow(p.rMain, k) : Infinity;\n"
    "    const tMain0 = p.tMain45_s * Math.pow(p.rMain, k) * qv;\n"
    "    const tTail0 = tail.t_s * Math.pow(p.rTail, k) * qv;\n"
    "    const tMain = 1 / (1 / tMain0 + 1 / tDiel);\n"
    "    const tTail = 1 / (1 / tTail0 + 1 / tDiel);",
    "engine tDiel",
)
html = patch(html, "      tREF_s: tREF, sigVt_mV: sigVt,", "      tREF_s: tREF, tDiel_s: tDiel, sigVt_mV: sigVt,", "engine return")

# ---------------------------------------------------------------- state: thickness settings, cases, export v2
html = patch(
    html,
    "      selected: 'capH', presetId: 'micron1b', scenarioId: null };",
    "      selected: 'tZ', presetId: 'micron1b', scenarioId: null, caseId: null,\n"
    "      thick: root.DMS.thick.clone(root.DMS.thick.THICK_DEFAULTS),\n"
    "      t1: { includeIL: true, floatTA: false, floatN: false, libFT: 0.9, noise: 1, xrfT: 10, xrfRho: 5.4 },\n"
    "      t3: { tool: 0, tools: [{ off: 0, slope: 1 }, { off: 0.02, slope: 1 }, { off: 0.02, slope: 1.0 }], event: 'none', amcRate: 0, plan: 'p49' } };",
    "freshState",
)
html = patch(
    html,
    """  function snapshot() {
    const base = E.compute(st.params, REF);
    const hasDrift = !!st.drift.key && (st.drift.meanShift !== 0 || st.drift.sigmaScale !== 1);
    const driftedParams = hasDrift ? E.applyDrift(st.params, st.drift, P.MEASURANDS, P.PARAM_DEFS) : st.params;
    const drifted = hasDrift ? E.compute(driftedParams, REF) : base;
    return { ...st, base, drifted, driftedParams, hasDrift };
  }""",
    """  function snapshot() {
    const T = root.DMS.thick;
    const hasDrift0 = !!st.drift.key && (st.drift.meanShift !== 0 || st.drift.sigmaScale !== 1);
    const design = hasDrift0 ? E.applyDrift(st.params, st.drift, P.MEASURANDS, P.PARAM_DEFS) : st.params;
    const nom = T.pipeline(st.params, T.THICK_DEFAULTS);
    const act = T.pipeline(design, st.thick);
    const base = E.compute(nom.params, REF);
    const hasDrift = hasDrift0 || !T.isNominal(st.thick);
    const drifted = hasDrift ? E.compute(act.params, REF) : base;
    return { ...st, base, drifted, driftedParams: act.params, designParams: design, hasDrift, thickInfo: act.info, thickBase: nom.info };
  }
  const merge = (a, b) => { const o = { ...a }; for (const [k, v] of Object.entries(b || {})) o[k] = v && typeof v === 'object' && !Array.isArray(v) && a[k] && typeof a[k] === 'object' ? merge(a[k], v) : v; return o; };
  function setThick(patch) { st.thick = merge(st.thick, patch); st.scenarioId = null; notify(); }
  function setT1(patch) { st.t1 = { ...st.t1, ...patch }; notify(); }
  function setT3(patch) { st.t3 = merge(st.t3, patch); notify(); }
  // quiet update used by T1 when the recipe bias is recomputed (no notify loop if unchanged)
  function setModelBias(v) { if (Math.abs(st.thick.metro.modelBias - v) < 1e-6) return; st.thick = merge(st.thick, { metro: { modelBias: v } }); notify(); }
  function applyCase(id) {
    const c = (root.DMS.cases || []).find((x) => x.id === id); if (!c) return;
    const fresh = freshState();
    st = { ...fresh, params: { ...fresh.params, ...clone(c.params || {}) },
      thick: merge(fresh.thick, clone(c.thick || {})), t1: { ...fresh.t1, ...(c.t1 || {}) }, t3: merge(fresh.t3, clone(c.t3 || {})),
      drift: c.drift ? { ...clone(c.drift) } : fresh.drift, selected: c.select || 'tZ', caseId: id };
    notify();
  }""",
    "snapshot",
)
html = patch(
    html,
    "  function exportJSON() { return JSON.stringify({ version: 1, params: st.params }, null, 2); }",
    "  function exportJSON() { return JSON.stringify({ version: 2, params: st.params, thick: st.thick, t1: st.t1, t3: st.t3 }, null, 2); }",
    "export",
)
html = patch(
    html,
    "    const fresh = freshState();\n    st = { ...fresh, params, presetId: 'mine' }; notify(); return true;",
    "    const fresh = freshState();\n"
    "    const okTree = (d, o) => isObj(o) && Object.entries(o).every(([k, v]) => k in d && (isObj(d[k]) ? okTree(d[k], v) : Array.isArray(d[k]) ? Array.isArray(v) : typeof v === typeof d[k] && (typeof v !== 'number' || Number.isFinite(v))));\n"
    "    st = { ...fresh, params, presetId: 'mine' };\n"
    "    if (okTree(fresh.thick, obj.thick)) st.thick = merge(fresh.thick, obj.thick);\n"
    "    if (okTree(fresh.t1, obj.t1)) st.t1 = { ...fresh.t1, ...obj.t1 };\n"
    "    if (okTree(fresh.t3, obj.t3)) st.t3 = merge(fresh.t3, obj.t3);\n"
    "    notify(); return true;",
    "import",
)
html = patch(
    html,
    "  const api = { init, get, snapshot, subscribe, setParam, setMeas, setDrift, select, selectMeasurand, applyPreset, applyScenario, reset,\n    exportJSON, importJSON, saveMine, loadMine };",
    "  const api = { init, get, snapshot, subscribe, setParam, setMeas, setDrift, select, selectMeasurand, applyPreset, applyScenario, reset,\n"
    "    exportJSON, importJSON, saveMine, loadMine, setThick, setT1, setT3, setModelBias, applyCase };",
    "state api",
)

# ---------------------------------------------------------------- chain bar: drift may come from thickness settings only
html = patch(
    html,
    "      if (s.hasDrift) {\n        const m = P.MEASURANDS[dr.key];",
    "      if (s.hasDrift && dr.key && P.MEASURANDS[dr.key] && (dr.meanShift || dr.sigmaScale !== 1)) {\n        const m = P.MEASURANDS[dr.key];",
    "chain drift guard",
)
html = patch(
    html,
    "        nodes.drift.v.textContent = s.scenarioId ? '情境' : '無';",
    "        nodes.drift.v.textContent = s.scenarioId ? '情境' : s.caseId ? '案例' : s.hasDrift ? '膜厚設定' : '無';",
    "chain drift label",
)

# ---------------------------------------------------------------- M6: ZrO2 measurand points at the new modules
html = patch(
    html,
    "measures: 'X 光反射率振盪（Kiessig fringes）或偏振變化；厚度由模型擬合', m2: 'hik',",
    "measures: 'X 光反射率振盪（Kiessig fringes）或偏振變化；厚度由模型擬合。量測鏈細節見 T1（光譜、模型、XRR）、T2（晶圓圖、孔內覆蓋）、T3（量具與匹配）', m2: 'hik',",
    "m6 tZ",
)

# ---------------------------------------------------------------- bootstrap: mount new modules
html = patch(
    html,
    "    D.chainBar.mount('#chain');\n    for (const [k, sel] of [['m6', '#m6'], ['m2', '#m2'], ['m4', '#m4'], ['m5', '#m5']]) {",
    "    D.chainBar.mount('#chain');\n    if (D.thickChain) D.thickChain.mount('#chain');\n"
    "    for (const [k, sel] of [['t4', '#t4'], ['t1', '#t1'], ['t2', '#t2'], ['t3', '#t3'], ['npi', '#npi'], ['m6', '#m6'], ['m2', '#m2'], ['m4', '#m4'], ['m5', '#m5']]) {",
    "mount",
)
html = patch(
    html,
    "    footer(document.getElementById('foot'));\n  }",
    "    footer(document.getElementById('foot'));\n    if (D.terms) D.terms.mount();\n  }",
    "terms mount",
)
html = patch(
    html,
    "      el('h2', {}, '來源、邊界與說明'),",
    "      el('h2', {}, '來源、邊界與說明'),\n"
    "      el('p', {}, '膜厚模組（T1–T4、NPI）：光學常數形狀依 Yusoh 2012、Yoon 2011（ZrO₂ n≈2.08–2.14、晶化後上升）🟠；ALD 孔內穿透深度 ∝ (曝氣量／GPC)^½ 依 Gonsalves et al. 2026（arXiv 2609.12460）🟠；"
    "DRAM 電容漏電規格 <1×10⁻⁷ A/cm²＠0.8 V 依 Lee 2024、Li 2024 🟠；O₃ 製程在 TiN 上形成 TiOx 介面層依 Jang 2024 🟠；晶化使表面粗糙依 Park 2025 🟠。"
    "TiN Drude 參數、漏電斜率、量具與機台偏差皆為 🔴 示意值。物理數值已以 Wolfram 與 Python（metro_tools.py）交叉驗證。'),",
    "footer sources",
)

# ---------------------------------------------------------------- CSS + new modules + term data
css = (SRC / "thick.css").read_text(encoding="utf-8")
html = patch(html, "  @media (prefers-reduced-motion: reduce){ *{animation:none !important;transition:none !important;} }\n</style>",
             "  @media (prefers-reduced-motion: reduce){ *{animation:none !important;transition:none !important;} }\n" + css + "\n</style>", "css")

modules = ["thick-engine.js", "thick-ui.js", "t1-optics.js", "t2-map.js", "t3-spc.js", "t4-triage.js", "npi.js", "terms.js"]
js = "\n".join(f"/* ---- {m} ---- */\n" + (SRC / m).read_text(encoding="utf-8") for m in modules)
# thick-engine must load before state.init runs (state reads DMS.thick); insert all modules before main.js
html = patch(html, "/* ---- main.js ---- */", js + "\n/* ---- main.js ---- */", "modules")
terms = json.loads(TERMS.read_text(encoding="utf-8"))
html = patch(html, "<script>window.DMS_ARTIFACT = true;",
             '<script type="application/json" id="termdata">' + json.dumps(terms, ensure_ascii=False).replace("</", "<\\/") + "</script>\n"
             '<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js" defer></script>\n'
             "<script>window.DMS_ARTIFACT = true;", "termdata")

# strip the publish skeleton that the saved artifact source carries (the Artifact tool adds its own)
html = re.sub(r"\A<!doctype html><html><head>.*?</head><body>\n", "", html, count=1, flags=re.S)
html = re.sub(r"\n</body></html>\s*\Z", "\n", html)

OUT.write_text(html, encoding="utf-8")
print(f"wrote {OUT.relative_to(HERE)}  {len(html) / 1024:.0f} KB")
