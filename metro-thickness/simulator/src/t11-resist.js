/* DRAM Thickness Metro — T11 photoresist thickness: swing curve (reflectance into the resist vs thickness,
   with and without BARC), CD response, and the dry-etch resist budget. */
(function (root) {
  'use strict';
  const D = root.DMS;
  function mount(sel) {
    const host = document.querySelector(sel);
    const u = D.ui, S = D.state, V = D.tui, P = D.proc;
    const K = [
      ['t', '光阻厚度（塗佈後量測）', 'resist thickness', 'nm', 120, 320, 1, 'red', '示意；ArF 光阻常見 100–250 nm'],
      ['barc', 'BARC 厚度', 'BARC thickness', 'nm', 0, 80, 1, 'red', '示意；有機 BARC n≈1.82, k≈0.34 @193 nm'],
      ['film', '要蝕刻的膜厚', 'film to etch', 'nm', 50, 400, 1, 'red', '示意'],
      ['erFilm', '膜的蝕刻速率', 'film ER', 'nm/s', 0.5, 5, 0.05, 'red', '示意'],
      ['selR', '膜：光阻選擇比', 'film:resist selectivity', ':1', 1, 10, 0.1, 'red', '示意；有硬罩時可大幅提高'],
      ['over', '過蝕刻比例', 'over-etch', '×', 0, 0.6, 0.01, 'red', '示意'],
      ['margin', '要求的剩餘光阻', 'required remaining resist', 'nm', 0, 80, 1, 'red', '示意：保護頂角、避免孔口圓化'],
    ];
    const sl = {};
    K.forEach(([k, zh, en, unit, mn, mx, st, tier, src]) => { sl[k] = V.knob({ key: k, zh, en, unit, min: mn, max: mx, step: st, tier, src }, 0, (v) => S.setExt({ resist: { [k]: v } })); });
    const swingBox = u.el('div'), budgetBox = u.el('div'), kv = u.el('div');
    host.append(
      u.el('h2', { id: 'h-t11' }, 'T11 光阻厚度：擺動曲線與蝕刻預算 ', u.el('span', { class: 'en' }, 'resist thickness · swing curve · etch budget')),
      u.el('p', { class: 'sub' }, '光阻塗佈後要量厚度，理由有兩個。第一，光阻本身是一層薄膜：曝光光在光阻上下界面來回反射形成駐波，耦合進光阻的能量隨厚度週期變化（擺動曲線，週期 λ/2n），CD 跟著擺動——BARC 吸掉底部反射，把擺動壓小。第二，光阻要撐過後面的乾蝕刻：膜越厚、選擇比越低、過蝕刻越多，被吃掉的光阻越多，剩下不夠就會削頂、孔口變大。'),
      u.el('div', { class: 'grid2' }, u.el('div', {}, ...K.map(([k]) => sl[k])), u.el('div', {}, kv)),
      u.el('div', { class: 'grid2', style: 'margin-top:10px' }, u.el('div', {}, u.el('h4', { class: 'grp' }, '擺動曲線：光阻內吸收的能量 1 − R（ArF 193 nm）'), swingBox), u.el('div', {}, u.el('h4', { class: 'grp' }, '蝕刻預算：光阻厚度隨蝕刻時間'), budgetBox)));
    function draw(s) {
      const e = s.ext.resist;
      K.forEach(([k]) => { if (!sl[k].contains(document.activeElement)) sl[k].sync(e[k]); });
      const ts = []; for (let t = 120; t <= 320; t += 1) ts.push(t);
      const noB = ts.map((t) => [t, 1 - P.resistR(t, 0)]), wB = ts.map((t) => [t, 1 - P.resistR(t, e.barc)]);
      const amp = (a) => Math.max(...a.map((q) => q[1])) - Math.min(...a.map((q) => q[1]));
      const ref = 200, cdNow = P.swingCD(e.t, e.barc, 40, ref), cdNo = P.swingCD(e.t, 0, 40, ref);
      swingBox.replaceChildren(V.chart([{ pts: noB, color: 'var(--text-dim)', dash: '5 4', label: '無 BARC' }, { pts: wB, color: 'var(--accent)', label: `BARC ${e.barc} nm` }, { pts: [[e.t, 1 - P.resistR(e.t, e.barc)]], color: 'var(--sig)', dotsOnly: true, r: 5, label: '目前' }],
        { h: 220, xLabel: '光阻厚度 (nm)', yLabel: '耦合能量 1 − R', yFmt: (v) => v.toFixed(2), aria: '擺動曲線' }),
        u.el('p', { class: 'note' }, `週期 λ/(2n) = 193/(2×1.70) ≈ ${P.swingPeriod().toFixed(1)} nm。擺幅：無 BARC ${amp(noB).toFixed(2)}，有 BARC ${amp(wB).toFixed(2)}。光阻厚度落在擺動曲線的極值（斜率為零）處最穩：塗佈厚度變動對 CD 影響最小。`));
      const b = P.resistBudget(e);
      const tl = []; for (let i = 0; i <= 40; i++) { const t = (b.tEtch * 1.3 * i) / 40; tl.push([t, Math.max(e.t - (e.erFilm / e.selR) * t, 0)]); }
      budgetBox.replaceChildren(V.chart([{ pts: tl, color: 'var(--accent)', label: '剩餘光阻' }], { h: 220, xLabel: '蝕刻時間 (s)', yLabel: '光阻 (nm)', yMin: 0, hlines: [{ y: e.margin, label: '要求下限', color: 'var(--sig)' }], vlines: [{ x: b.tEtch, label: '蝕刻結束（含過蝕刻）' }], xFmt: (v) => v.toFixed(0), yFmt: (v) => v.toFixed(0), aria: '光阻蝕刻預算' }));
      const ok = b.remain >= e.margin;
      kv.replaceChildren(V.kvGrid([['此厚度的 CD（有 BARC）', `${cdNow.toFixed(2)} nm`], ['此厚度的 CD（無 BARC）', `${cdNo.toFixed(2)} nm`], ['蝕刻時間', `${b.tEtch.toFixed(0)} s`], ['被吃掉的光阻', `${b.used.toFixed(0)} nm`], ['蝕刻後剩餘光阻', `${b.remain.toFixed(0)} nm`, ok ? 'goodtxt' : 'badtxt'], ['最低所需光阻', `${(b.used + e.margin).toFixed(0)} nm`]]),
        u.el('div', { class: 'row' }, V.chip(ok ? '蝕刻預算足夠' : '光阻不夠撐完蝕刻', ok ? 'good' : 'reject')),
        u.el('p', { class: 'note' }, ok ? '光阻有餘裕。但太厚會讓解析度與焦深變差、且高深寬比的光阻容易倒——厚度是兩邊的權衡。' : '光阻在蝕刻結束前就太薄：頂角被削、孔口變大（top CD 變大），嚴重時穿透到下面的膜。對策：塗厚一點（但要回到擺動曲線的極值）、提高選擇比，或改用硬罩。CD 是在顯影後量的，這個問題要到蝕刻後的 CD（T6、T8）才看得到。'));
    }
    S.subscribe(draw);
  }
  root.DMS.t11 = { mount };
})(typeof globalThis !== 'undefined' ? globalThis : this);
