(() => {
  const $ = (s) => document.querySelector(s);
  const app = $("#app"), thread = $("#thread"), prompt = $("#prompt"), send = $("#send"), stop = $("#stop");
  const status = $("#status"), ticker = $("#ticker"), steps = $("#steps"), orbEl = $("#orb");
  const IDLE = "待命 · 林秀豪式思考";
  const STEP_ORDER = ["memory", "mentor", "critics", "revision", "judge", "store"];
  const EXAMPLES = [
    "醫院停用某種抗生素後，抗藥菌為什麼不一定會消失？",
    "一個劇種爆紅後幾年內就退燒，怎麼分辨是題材疲乏還是平台演算法改變？",
    "把語言或迷因傳播當成演化來分析，什麼時候有解釋力、什麼時候只是換詞？",
  ];
  const ERR = {
    not_granted: "這個頁面還沒獲准使用 Claude，所以 Lin Brain 無法思考。重新整理頁面，在詢問時選擇允許。",
    sampling_disabled: "這個帳號無法在頁面中使用 Claude。",
    rate_limited: "Claude 用量暫時到上限。稍後再按一次「思考」。",
    session_expired: "登入已過期。請重新登入 claude.ai 後再試。",
    refused: "Claude 拒絕回答這個提問。換個問法再試一次。",
    prompt_too_large: "這段對話太長了。按「新對話」後再問一次。",
    empty_completion: "這次沒有產生任何內容。把問題縮小一點再試。",
    tools_unavailable: "這個檢視不支援導師工具。重新整理後再試。",
    cancelled: "已停止。已完成的部分保留在上方。",
  };

  let history = load();
  let ctl = null, cycleTimer = null, running = false;

  const webgl = Orb.init(orbEl);
  if (!webgl) orbEl.classList.add("no-webgl");

  for (const text of EXAMPLES) {
    const b = document.createElement("button");
    b.type = "button"; b.className = "example"; b.textContent = text;
    b.onclick = () => { prompt.value = text; grow(); prompt.focus(); };
    $("#examples").append(b);
  }
  history.forEach((t) => { const el = addTurn(t.q); renderAnswer(el, t.answer, true); renderVerdict(el, t.meta || {}); });
  syncThread();

  Brain.connect().then(({ sample }) => {
    if (!sample) {
      status.textContent = "請在 claude.ai 開啟這個頁面，Lin Brain 才能思考。";
      send.disabled = true;
    }
    renderMemory();
    Brain.onCards(renderMemory);
  });

  function load() { try { return JSON.parse(localStorage.getItem("lin-brain-thread") || "[]"); } catch { return []; } }
  function save() { try { localStorage.setItem("lin-brain-thread", JSON.stringify(history.slice(-20))); } catch {} }
  function syncThread() { app.classList.toggle("has-thread", thread.querySelectorAll(".turn").length > 0); }

  function grow() { prompt.style.height = "auto"; prompt.style.height = Math.min(prompt.scrollHeight, innerHeight * 0.34) + "px"; }
  prompt.addEventListener("input", grow);
  prompt.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); $("#composer").requestSubmit(); }
  });
  $("#composer").addEventListener("submit", (e) => {
    e.preventDefault();
    const text = prompt.value.trim();
    if (text && !running && !send.disabled) go(text);
  });
  stop.onclick = () => ctl?.abort();
  $("#btn-new").onclick = () => {
    if (running) return;
    history = []; save();
    thread.querySelectorAll(".turn").forEach((n) => n.remove());
    syncThread();
    window.scrollTo({ top: 0 });
  };

  // Markdown with math kept out of the parser, sanitized, then typeset by MathJax.
  function toHTML(md) {
    if (!window.marked || !window.DOMPurify) return null;
    const math = [];
    const safe = md.replace(/(\$\$[\s\S]+?\$\$|\\\[[\s\S]+?\\\]|\\\([\s\S]+?\\\)|\$[^$\n]+?\$)/g, (m) => `MATHSLOT${math.push(m) - 1}Z`);
    let html = DOMPurify.sanitize(marked.parse(safe, { breaks: false, gfm: true }));
    const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    return html.replace(/MATHSLOT(\d+)Z/g, (_, i) => esc(math[+i]));
  }

  function renderAnswer(turn, md, final) {
    const a = turn.querySelector(".a");
    a.classList.remove("pending");
    const html = toHTML(md);
    if (html === null) a.textContent = md; else a.innerHTML = html;
    if (final && window.MathJax?.typesetPromise) MathJax.typesetPromise([a]).catch(() => {});
  }

  function addTurn(q) {
    const el = document.createElement("article");
    el.className = "turn";
    const qe = document.createElement("p"); qe.className = "q"; qe.textContent = q;
    const a = document.createElement("div"); a.className = "a pending"; a.textContent = "";
    const v = document.createElement("footer"); v.className = "verdict"; v.hidden = true;
    el.append(qe, a, v);
    thread.append(el);
    syncThread();
    return el;
  }

  const ROUTE = { full: "完整辯論", reused: "重用記憶", "no-conclusion": "直接回答" };
  function routeLabel(r) { return ROUTE[r] || (String(r).startsWith("delta") ? "差分辯論 · " + r.replace(/^delta\s*/, "") : r || ""); }
  const OUT = { open: "未解", conceded: "承認並修正", refuted: "已反駁" };

  function renderVerdict(turn, m) {
    const v = turn.querySelector(".verdict");
    v.replaceChildren();
    if (!m.route) { v.hidden = true; return; }
    v.hidden = false;
    if (m.claim) {
      const c = document.createElement("p"); c.className = "claim";
      const b = document.createElement("b"); b.textContent = "結論";
      c.append(b, document.createTextNode(m.claim)); v.append(c);
    }
    if (m.confidence) {
      const p = document.createElement("span"); p.className = "pill conf-" + m.confidence; p.textContent = "信心 " + m.confidence; v.append(p);
    }
    const bits = [routeLabel(m.route)];
    if (m.card) bits.push("結論卡 " + m.card);
    if (m.objections?.length) bits.push(`${m.objections.length} 項反對 · ${m.objections.filter((o) => o.outcome === "open").length} 項未解`);
    const s = document.createElement("span"); s.textContent = bits.join(" · "); v.append(s);
    if (!m.objections?.length && !m.moves?.length && !m.notes?.length && !m.diff?.length) return;

    const d = document.createElement("details"); d.className = "trace";
    const sum = document.createElement("summary"); sum.textContent = "思考紀錄"; d.append(sum);
    const body = document.createElement("div"); body.className = "trace-body"; d.append(body);
    const section = (title, node) => { const h = document.createElement("h4"); h.textContent = title; body.append(h, node); };
    const para = (t) => { const p = document.createElement("p"); p.style.margin = "0"; p.textContent = t; return p; };
    if (m.moves?.length) section("展開的招式", para(m.moves.join(" · ")));
    if (m.objections?.length) {
      const wrap = document.createElement("div"); wrap.className = "ledger";
      const tb = document.createElement("table");
      tb.innerHTML = "<thead><tr><th>審查者</th><th>反例</th><th>嚴重度</th><th>結果</th></tr></thead>";
      const tbody = document.createElement("tbody");
      for (const o of m.objections) {
        const tr = document.createElement("tr");
        const cells = [o.role, o.failure, o.severity, OUT[o.outcome] + (o.reply ? "：" + o.reply : "")];
        cells.forEach((t, i) => {
          const td = document.createElement("td"); td.textContent = t;
          if (i === 2) td.className = "sev-" + o.severity;
          if (i === 3) td.className = "out-" + o.outcome;
          tr.append(td);
        });
        tbody.append(tr);
      }
      tb.append(tbody); wrap.append(tb); section("反對帳本", wrap);
    }
    if (m.diff?.length) {
      const ul = document.createElement("ul"); ul.style.margin = "0"; ul.style.paddingLeft = "1.2em";
      m.diff.forEach((x) => { const li = document.createElement("li"); li.textContent = `${x.change}（${x.cause}）`; ul.append(li); });
      section("草稿 → 定稿", ul);
    }
    if (m.unreviewed?.length) section("修訂新增、未經複審", para(m.unreviewed.join("；")));
    if (m.notes?.length) section("備註", para(m.notes.join("；")));
    v.append(d);
  }

  function setStage(ev) {
    clearInterval(cycleTimer);
    status.textContent = ev.label;
    const idx = STEP_ORDER.indexOf(ev.step);
    steps.querySelectorAll("li").forEach((li, i) => {
      li.classList.toggle("now", i === idx);
      li.classList.toggle("done", i < idx);
    });
    if (ev.cycle) {
      let k = 0;
      const show = () => { const c = ev.cycle[k++ % ev.cycle.length]; Orb.setShape(c.animal); orbEl.querySelector(".orb-fallback-face").textContent = Orb.ANIMALS[c.animal]; status.textContent = c.label + " 審問中"; };
      show();
      cycleTimer = setInterval(show, 2600);
    } else {
      Orb.setShape(ev.animal);
      orbEl.querySelector(".orb-fallback-face").textContent = Orb.ANIMALS[ev.animal] || "";
    }
  }

  async function go(text) {
    running = true;
    prompt.value = ""; grow();
    send.hidden = true; stop.hidden = false; steps.hidden = false;
    steps.querySelectorAll("li").forEach((li) => li.classList.remove("now", "done"));
    const turn = addTurn(text);
    turn.querySelector(".a").textContent = "思考中…";
    turn.scrollIntoView({ behavior: "smooth", block: "start" });
    Orb.setBusy(true);
    ctl = new AbortController();
    let partial = "", lastPaint = 0;
    const on = (ev) => {
      if (ev.type === "stage") setStage(ev);
      else if (ev.type === "tick") ticker.textContent = ev.text.replace(/\s+/g, " ").slice(-90);
      else if (ev.type === "final") {
        partial = ev.text;
        const now = performance.now();
        if (now - lastPaint > 120) { lastPaint = now; renderAnswer(turn, partial, false); }
      }
    };
    try {
      const r = await Brain.run(text, { history, signal: ctl.signal, on });
      const meta = {
        route: r.route, confidence: r.confidence, card: r.card, claim: r.block?.claim,
        objections: (r.objections || []).map(({ role, failure, severity, outcome, reply }) => ({ role, failure, severity, outcome, reply })),
        diff: r.diff, unreviewed: r.unreviewed, moves: r.trace?.moves, notes: [...(r.trace?.notes || []), ...(r.trace?.review?.note ? [r.trace.review.note] : [])],
      };
      renderAnswer(turn, r.answer, true);
      renderVerdict(turn, meta);
      history.push({ q: text, answer: r.answer, meta });
      save();
    } catch (e) {
      const a = turn.querySelector(".a");
      if (partial || e?.text) renderAnswer(turn, partial || e.text, true); else a.textContent = "";
      const p = document.createElement("p"); p.className = "error";
      p.textContent = ERR[e?.code] || "連線中斷。已保留目前的內容，可以再按一次「思考」。";
      turn.append(p);
    } finally {
      clearInterval(cycleTimer);
      running = false; ctl = null;
      send.hidden = false; stop.hidden = true; steps.hidden = true;
      ticker.textContent = ""; status.textContent = IDLE;
      Orb.setBusy(false);
      orbEl.querySelector(".orb-fallback-face").textContent = "";
    }
  }

  // Memory drawer
  const drawer = $("#memory");
  $("#btn-memory").onclick = () => { drawer.hidden = false; $("#memory-close").focus(); };
  $("#memory-close").onclick = () => { drawer.hidden = true; };
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") drawer.hidden = true; });

  function renderMemory() {
    const list = Brain.activeCards();
    $("#card-count").textContent = list.length ? String(list.length) : "";
    const box = $("#memory-list");
    box.replaceChildren();
    if (!Brain.hasDb()) { box.append(Object.assign(document.createElement("p"), { className: "drawer-note", textContent: "記憶庫只在 claude.ai 中可用。" })); return; }
    if (!list.length) { box.append(Object.assign(document.createElement("p"), { className: "drawer-note", textContent: "還沒有結論卡。問一個問題，辯論結束後會自動存下。" })); return; }
    for (const c of list) {
      const el = document.createElement("div"); el.className = "card";
      const top = document.createElement("div"); top.className = "card-top";
      const id = document.createElement("span"); id.className = "card-id"; id.textContent = c.id;
      const pill = document.createElement("span"); pill.className = "pill conf-" + c.confidence; pill.textContent = c.confidence + (c.disputed ? " · 有異議" : "");
      const used = document.createElement("span"); used.textContent = "用於 " + (c.last_used || "—") + (c.recheck && c.recheck !== "none" ? " · 複查 " + c.recheck : "");
      top.append(id, pill, used);
      const claim = document.createElement("p"); claim.className = "card-claim"; claim.textContent = c.claim;
      const q = document.createElement("p"); q.className = "card-q"; q.textContent = "問：" + c.question;
      const acts = document.createElement("div"); acts.className = "card-actions";
      if (!c.disputed) {
        const b = document.createElement("button"); b.type = "button"; b.className = "ghost"; b.textContent = "我不同意";
        b.title = "信心降為 medium，之後不會不經辯論就重用";
        b.onclick = async () => { b.disabled = true; await Brain.dispute(c.id).catch(() => {}); };
        acts.append(b);
      }
      const redo = document.createElement("button"); redo.type = "button"; redo.className = "ghost"; redo.textContent = "重新辯論";
      redo.onclick = () => { drawer.hidden = true; prompt.value = "重新辯論 " + c.question; grow(); prompt.focus(); };
      acts.append(redo);
      if (Brain.hasDownloads()) {
        const dl = document.createElement("button"); dl.type = "button"; dl.className = "ghost"; dl.textContent = "下載 .md";
        dl.onclick = () => Brain.exportCard(c.id).catch(() => {});
        acts.append(dl);
      }
      el.append(top, claim, q, acts);
      box.append(el);
    }
  }
})();
