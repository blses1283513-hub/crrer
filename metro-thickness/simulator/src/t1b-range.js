/* DRAM Thickness Metro — T1b thickness range: reflectometry vs ellipsometry (the "1000 Å" rule),
   FFT thickness for thick films (Michelson/FTIR math), n & k dispersion of each layer, GOF reading. */
(function (root) {
  'use strict';
  const D = root.DMS;
  function mount(sel) {
    const host = document.querySelector(sel);
    const u = D.ui, S = D.state, V = D.tui, X = D.ext, T = D.thick;
    const dSl = V.knob({ key: 'd', zh: 'SiO₂ 厚度（對數）', en: 'film thickness', unit: 'nm', min: 1, max: 10000, step: 1, log: true, tier: 'red', src: '示意：SiO₂／Si 單層膜' }, 100, (v) => S.setExt({ range: { d: v } }));
    const specBox = u.el('div'), sensBox = u.el('div'), fftBox = u.el('div'), nBox = u.el('div'), kBox = u.el('div'), verdict = u.el('div');
    host.append(
      u.el('h2', { id: 'h-t1b' }, 'T1b 厚度範圍、n／k 與方法選擇 ', u.el('span', { class: 'en' }, 'reflectometry vs ellipsometry · n, k, t')),
      u.el('p', { class: 'sub' }, '常聽到的經驗法則：>1000 Å 用反射光譜，<1000 Å 用橢偏。原因不是反射光譜「量不到」薄膜，而是干涉條紋不到一條時，n 和 t 分不開：除非把 n 固定，厚度的不確定度會爆掉。橢偏量的是相位 Δ，薄膜仍有足夠的資訊。拉動厚度看兩種方法的精度、光譜與 FFT 厚度。'),
      dSl, verdict,
      u.el('div', { class: 'grid2', style: 'margin-top:10px' },
        u.el('div', {}, u.el('h4', { class: 'grp' }, '厚度精度 σ_t（n 也擬合）vs 厚度'), sensBox),
        u.el('div', {}, u.el('h4', { class: 'grp' }, '目前厚度的反射光譜 R(λ)'), specBox)),
      u.el('div', { class: 'grid2', style: 'margin-top:10px' },
        u.el('div', {}, u.el('h4', { class: 'grp' }, '厚膜：條紋週期 FFT → 厚度（FTIR／Michelson 的數學）'), fftBox),
        u.el('div', {}, u.el('h4', { class: 'grp' }, '各層的折射率 n(λ)'), nBox, u.el('h4', { class: 'grp', style: 'margin-top:8px' }, '消光係數 k(λ)'), kBox)));

    // σ_t curves are independent of state: compute once
    const ds = []; for (let e = 0.3; e <= 4.0001; e += 0.1) ds.push(10 ** e);
    const curves = ds.map((d) => { const r = X.corrDNrefl(d), s = X.corrDN(d); return [d, r.sdD, r.sdDfixed, s.sdD]; });
    // n, k charts
    const wl = []; for (let l = 250; l <= 900; l += 10) wl.push(l);
    const mats = [['ZrO₂ (f_t 0.9)', (l) => T.MAT.ZrO2(l, 0.9), 'var(--accent)'], ['Al₂O₃', T.MAT.Al2O3, 'var(--ok)'], ['TiOx', T.MAT.TiOx, 'var(--leak)'], ['SiO₂', T.MAT.SiO2, 'var(--text-dim)'], ['Si', T.MAT.Si, 'var(--sig)'], ['TiN', T.MAT.TiN, 'var(--elec)']];
    nBox.replaceChildren(V.chart(mats.map(([lab, f, c]) => ({ pts: wl.map((l) => [l, f(l)[0]]), color: c, label: lab })), { h: 210, xLabel: '波長 nm', yLabel: 'n', yFmt: (v) => v.toFixed(1), aria: '折射率對波長' }));
    kBox.replaceChildren(V.chart(mats.map(([lab, f, c]) => ({ pts: wl.map((l) => [l, f(l)[1]]), color: c, label: lab })), { h: 190, xLabel: '波長 nm', yLabel: 'k', yFmt: (v) => v.toFixed(1), aria: '消光係數對波長' }),
      u.el('p', { class: 'note' }, 'k = 0 的膜（透明）：光可以穿透，厚度從干涉得到。k 大的膜（Si 在 UV、TiN 全波段）：光只穿透 1/α = λ/(4πk)，金屬超過數十 nm 就只看到表面，要改用 XRF 或聲學方法。n、k 與 t 在同一個擬合裡，常常互相補償（見 T1 的相關性）。'));

    let lastD = null;
    function draw(s) {
      const d = s.ext.range.d;
      if (!dSl.contains(document.activeElement)) dSl.sync(d);
      if (d === lastD) return; lastD = d;
      const r = X.corrDNrefl(d), e = X.corrDN(d), fr = X.sensitivity(d).fringes;
      const reflOK = r.sdD < 0.1;
      const best = reflOK ? '反射光譜可行（SE 也可）' : r.sdDfixed < 0.1 ? '橢偏 SE，或反射光譜但固定 n' : '橢偏 SE';
      verdict.replaceChildren(V.kvGrid([['干涉條紋數（400–900 nm）', fr.toFixed(2), fr < 1 ? 'badtxt' : 'goodtxt'], ['反射光譜 σ_t（n 也擬合）', `${r.sdD.toFixed(3)} nm`, r.sdD > 0.1 ? 'badtxt' : ''], ['反射光譜 σ_t（n 固定）', `${r.sdDfixed.toFixed(3)} nm`], ['橢偏 σ_t（n 也擬合）', `${e.sdD.toFixed(4)} nm`, 'goodtxt'], ['corr(t, n) 反射', r.corr.toFixed(3)], ['建議', best]]),
        u.el('p', { class: 'note' }, !reflOK && fr < 1 ? '條紋不到一條：反射光譜只看到光譜的一段斜坡，n 和 t 幾乎完全相關，σ_t 爆掉。用橢偏，或把 n 固定成已知值。' : !reflOK ? '厚膜且 n 也擬合：常數的 n 誤差被乘上厚度，σ_t 變大；用多層色散模型或 FFT 起始值，並以參考量測確認 n。' : fr < 1 ? '約半條到一條條紋之間：光譜形狀變化最大，反射光譜仍能分開 n 與 t。這就是「約 1000 Å」經驗法則的交界附近。' : '條紋超過一條：反射光譜可同時得到 n 與 t；它快、光斑小、便宜，是厚膜的主力。'));
      sensBox.replaceChildren(V.chart([
        { pts: curves.map((q) => [Math.log10(q[0]), q[1]]), color: 'var(--leak)', label: '反射光譜（n 擬合）' },
        { pts: curves.map((q) => [Math.log10(q[0]), q[2]]), color: 'var(--leak)', dash: '5 4', label: '反射光譜（n 固定）' },
        { pts: curves.map((q) => [Math.log10(q[0]), q[3]]), color: 'var(--accent)', label: '橢偏（n 擬合）' },
        { pts: [[Math.log10(d), r.sdD]], color: 'var(--sig)', dotsOnly: true, r: 5 }],
      { h: 230, logY: true, xLabel: '厚度（對數）', yLabel: 'σ_t (nm)', xTicks: [0, 1, 2, 3, 4], xFmt: (v) => ['1 nm', '10 nm', '100 nm', '1 µm', '10 µm'][v] || '', vlines: [{ x: 2, label: '1000 Å' }], aria: '厚度精度對厚度' }),
      u.el('p', { class: 'note' }, '雜訊：反射率 0.1%、Ψ 0.01°、Δ 0.02°（示意）。反射光譜在約 100–150 nm（約一條條紋）最好；更薄時 n、t 分不開，更厚時常數 n 誤差被乘上厚度。'));
      const R = X.rSpec(d);
      specBox.replaceChildren(V.chart([{ pts: X.WLR.map((l, i) => [l, R[i] * 100]), color: 'var(--accent)', label: `R(λ)，t = ${d >= 100 ? d.toFixed(0) : d.toFixed(1)} nm` }], { h: 230, xLabel: '波長 nm', yLabel: 'R (%)', yFmt: (v) => v.toFixed(0), aria: '反射光譜' }));
      if (d >= 800) {
        const f = X.fftThickness(d);
        const pk = Math.max(...f.spec.map((q) => q[1]));
        fftBox.replaceChildren(V.chart([{ pts: f.spec.filter((q) => q[0] <= 4500).map((q) => [q[0], q[1] / pk]), color: 'var(--accent)', label: 'FFT 振幅' }], { h: 210, xLabel: '厚度 (nm)', yLabel: '相對振幅', vlines: [{ x: f.d, label: `峰 ${f.d.toFixed(0)} nm` }], yFmt: (v) => v.toFixed(1), aria: 'FFT 厚度譜' }),
          V.kvGrid([['FFT 厚度', `${f.d.toFixed(0)} nm`], ['真實', `${d.toFixed(0)} nm`], ['FFT 解析度 ≈ 1/(2nΔk)', `${f.resolution.toFixed(0)} nm`]]),
          u.el('p', { class: 'note' }, 'R 對波數 k = 1/λ 是週期函數，週期 1/(2nt)；做 FFT，峰值位置就是光學厚度 2nt。FTIR 用 Michelson 干涉儀取得光譜，厚磊晶（µm 級）就用這個方法。FFT 只給起始值，最後仍用模型擬合精修。'));
      } else {
        fftBox.replaceChildren(u.el('p', { class: 'note' }, `目前 ${d.toFixed(1)} nm：400–900 nm 視窗內只有 ${fr.toFixed(2)} 條條紋，FFT 沒有峰可找。把厚度拉到 800 nm 以上看 FFT 法。`));
      }
    }
    S.subscribe(draw);
  }
  root.DMS.t1b = { mount };
})(typeof globalThis !== 'undefined' ? globalThis : this);
