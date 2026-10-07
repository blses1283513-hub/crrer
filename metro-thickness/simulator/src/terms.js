/* DRAM Thickness Metro — Eudic-style term popups (shared 229-term glossary).
   wrap(el) marks the first occurrence of each term inside el; mount() wraps static text and wires the card. */
(function (root) {
  'use strict';
  const D = root.DMS;
  let TERMS = [], byKey = {}, lookup = {}, re = null, card = null, anchorEl = null, hist = [];
  const SKIP_KEYS = new Set(['model', 'fit', 'fitting', 'spec', 'standard', 'orders', 'poly', 'stack', 'spot', 'pad', 'offset', 'sigma', 'qual', 'correlation', 'interference', 'regression', 'oxidation', 'resist', 'kwh', 'oxide', 'nitride', 'epi', 'polish', 'leakage current', 'retention', 'tail cells', 'tetragonal']);
  const strict = (k) => /^[A-Z0-9][A-Za-z0-9&\/\-_]*$/.test(k) && k.length <= 5 || k.length <= 3;
  const SKIP_TAGS = new Set(['A', 'CODE', 'PRE', 'H2', 'H3', 'H4', 'BUTTON', 'SCRIPT', 'STYLE', 'INPUT', 'TEXTAREA', 'SELECT', 'OUTPUT', 'LABEL', 'svg', 'SVG', 'TEXT']);
  const h = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const esc = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

  function init() {
    const el = document.getElementById('termdata'); if (!el) return false;
    TERMS = JSON.parse(el.textContent);
    const keys = [];
    TERMS.forEach((t, i) => {
      [t.term, ...t.alt].forEach((k) => { lookup[k.toLowerCase()] = i; if (k.length < 2 || SKIP_KEYS.has(k.toLowerCase()) || /^[ΨΔεσαn]$/.test(k)) return; byKey[k.toLowerCase()] = { i, key: k }; keys.push(k); });
    });
    keys.sort((a, b) => b.length - a.length);
    re = new RegExp('(?<![A-Za-z0-9_\\-/])(' + keys.map(esc).join('|') + ')(?![A-Za-z0-9_\\-])', 'gi');
    card = document.getElementById('wcard');
    return true;
  }

  function wrap(scope) {
    if (!re || !scope) return;
    const used = new Set();
    const walker = document.createTreeWalker(scope, NodeFilter.SHOW_TEXT, { acceptNode(n) {
      if (!n.nodeValue.trim()) return NodeFilter.FILTER_REJECT;
      for (let p = n.parentNode; p && p !== scope.parentNode; p = p.parentNode) if (SKIP_TAGS.has(p.nodeName) || (p.classList && (p.classList.contains('term') || p.classList.contains('kv') || p.classList.contains('chain')))) return NodeFilter.FILTER_REJECT;
      return NodeFilter.FILTER_ACCEPT; } });
    const nodes = []; while (walker.nextNode()) nodes.push(walker.currentNode);
    for (const node of nodes) {
      const text = node.nodeValue; let last = 0, frag = null, m; re.lastIndex = 0;
      while ((m = re.exec(text))) {
        const hit = byKey[m[1].toLowerCase()]; if (!hit) continue;
        if (strict(hit.key) && m[1] !== hit.key) continue;
        if (used.has(hit.i)) continue; used.add(hit.i);
        frag = frag || document.createDocumentFragment();
        frag.append(document.createTextNode(text.slice(last, m.index)));
        const sp = document.createElement('span'); sp.className = 'term'; sp.tabIndex = 0; sp.dataset.t = hit.i; sp.textContent = m[1];
        frag.append(sp); last = m.index + m[1].length;
      }
      if (frag) { frag.append(document.createTextNode(text.slice(last))); node.parentNode.replaceChild(frag, node); }
    }
  }

  function render(i) {
    const t = TERMS[i];
    const rel = t.rel.map((r) => { const j = lookup[r.toLowerCase()]; return j === undefined ? `<span>${h(r)}</span>` : `<button type="button" data-go="${j}">${h(r)}</button>`; }).join('');
    card.innerHTML = `<button type="button" class="wc-close" aria-label="關閉">×</button><div class="wc-head"><span class="wc-term">${h(t.term)}</span><span class="wc-zh">${h(t.zh)}</span></div>` +
      (t.alt.length ? `<div class="wc-alt">also: ${t.alt.map(h).join(', ')}</div>` : '') +
      `<div class="wc-row"><span class="wc-lbl">EN</span><span>${h(t.en)}</span></div><div class="wc-row"><span class="wc-lbl">中</span><span>${h(t.zhdef)}</span></div>` +
      `<div class="wc-rel">${rel}</div><div class="wc-foot">${hist.length ? `<button type="button" class="back">← ${h(TERMS[hist[hist.length - 1]].term)}</button>` : '<span></span>'}<span class="note">Tools Book：${h(t.note.replace(/^\d\d /, ''))}</span></div>`;
    card.dataset.cur = i;
  }
  function place(a) {
    card.hidden = false;
    const r = a.getBoundingClientRect(), cw = card.offsetWidth, ch = card.offsetHeight, vw = document.documentElement.clientWidth, vh = root.innerHeight;
    let top = r.bottom + 8; if (top + ch > vh - 8 && r.top - ch - 8 > 8) top = r.top - ch - 8;
    card.style.left = Math.min(Math.max(16, r.left), vw - cw - 16) + 'px'; card.style.top = Math.max(8, top) + 'px';
  }
  function open(el) { if (document.body.classList.contains('no-terms')) return; hist = []; anchorEl = el; render(+el.dataset.t); place(el); }
  function close() { if (card) card.hidden = true; anchorEl = null; }

  function mount() {
    if (!init()) return;
    // toggle in the control bar
    const ctl = document.getElementById('controls');
    const cb = D.ui.el('input', { type: 'checkbox', id: 'termtoggle', checked: true });
    ctl.append(D.ui.el('label', { class: 'note', for: 'termtoggle' }, cb, ' 術語提示（停留或點選虛線字）'));
    let off = false; try { off = root.localStorage.getItem('dtms.terms') === 'off'; } catch (e) { /* storage blocked */ }
    cb.checked = !off; document.body.classList.toggle('no-terms', off);
    cb.addEventListener('change', () => { document.body.classList.toggle('no-terms', !cb.checked); if (!cb.checked) close(); try { root.localStorage.setItem('dtms.terms', cb.checked ? 'on' : 'off'); } catch (e) { /* storage blocked */ } });
    // static text: lede and every panel's intro, info boxes, footer
    document.querySelectorAll('.masthead .lede, .panel > .sub, .panel .info, #foot p, .card > p.note').forEach(wrap);

    const hoverable = root.matchMedia && root.matchMedia('(hover: hover)').matches;
    let showT, hideT;
    document.addEventListener('mouseover', (e) => {
      if (!hoverable || !e.target.closest) return;
      const el = e.target.closest('.term');
      if (el) { clearTimeout(hideT); clearTimeout(showT); showT = setTimeout(() => open(el), 220); }
      else if (e.target.closest('#wcard')) clearTimeout(hideT);
    });
    document.addEventListener('mouseout', (e) => {
      if (!hoverable || !e.target.closest) return;
      if (!(e.target.closest('.term') || e.target.closest('#wcard'))) return;
      const to = e.relatedTarget;
      if (to && to.closest && (to.closest('#wcard') || to.closest('.term') === anchorEl)) return;
      clearTimeout(showT); hideT = setTimeout(close, 280);
    });
    document.addEventListener('click', (e) => {
      const el = e.target.closest('.term'); if (el) { e.preventDefault(); open(el); return; }
      const go = e.target.closest('#wcard [data-go]'); if (go) { hist.push(+card.dataset.cur); render(+go.dataset.go); if (anchorEl) place(anchorEl); return; }
      if (e.target.closest('#wcard .back')) { render(hist.pop()); if (anchorEl) place(anchorEl); return; }
      if (e.target.closest('#wcard .wc-close') || !e.target.closest('#wcard')) close();
    });
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && card && !card.hidden) { const a = anchorEl; close(); if (a) a.focus(); }
      if ((e.key === 'Enter' || e.key === ' ') && e.target.classList && e.target.classList.contains('term')) { e.preventDefault(); open(e.target); }
    });
    root.addEventListener('scroll', () => { if (card && !card.hidden && anchorEl) place(anchorEl); }, { passive: true });
  }
  D.terms = { mount, wrap };
})(typeof globalThis !== 'undefined' ? globalThis : this);
