// The Lin Brain pipeline: every prompt runs the vault's rules end to end.
// memory index check → mentor derivation (moves opened on demand) → 4 blind critics
// → concede/refute revision → optional round 2 → fixed confidence rule → card + record.
const Brain = (() => {
  const K = window.LIN;
  const P = K.prompts;
  const ROLES = [
    { key: "skeptic", name: "Skeptic", animal: "horse", task: P["role-skeptic"] },
    { key: "bridge", name: "Bridge auditor", animal: "flamingo", task: P["role-bridge"] },
    { key: "practitioner", name: "Practitioner", animal: "foxWalk", task: P["role-practitioner"] },
    { key: "insider", name: "Field insider", animal: "parrot", task: P["role-insider"] },
  ];
  const SEV = { fatal: 3, major: 2, minor: 1 };
  const FINAL = "### 最終回答";
  let sample = null, db = null, downloads = null, canTools = false;
  const cards = new Map();
  let meta = { debates_since_review: 0, reviews: 0 };
  const listeners = new Set();

  const today = () => new Date().toISOString().slice(0, 10);
  const fill = (tpl, vars) => tpl.replace(/\{\{(\w+)\}\}/g, (_, k) => (k in vars ? String(vars[k]) : ""));

  async function connect() {
    if (!window.claude) return { sample: false, db: false };
    [sample, db, downloads] = await Promise.all([claude.use("sample"), claude.use("db"), claude.use("downloads")]);
    if (sample) canTools = !!(await sample.limits().catch(() => null))?.tools;
    if (db) {
      db.collection("cards").onSnapshot((snap) => {
        cards.clear();
        for (const d of snap.docs) cards.set(d.id, d.data());
        listeners.forEach((fn) => fn());
      }, () => {});
      const m = await db.doc("meta/state").get().catch(() => null);
      if (m?.exists) meta = { ...meta, ...m.data() };
    }
    return { sample: !!sample, db: !!db };
  }

  const onCards = (fn) => { listeners.add(fn); return () => listeners.delete(fn); };
  const activeCards = () => [...cards.values()].filter((c) => !c.archived).sort((a, b) => b.id.localeCompare(a.id));

  function indexLine(c) {
    return `- ${c.id} · kw: ${(c.keywords || []).join(", ")} · ${c.claim} · conf: ${c.confidence} · used: ${c.last_used} · recheck: ${c.recheck || "none"} · Q: ${c.question}`;
  }

  function cardText(c) {
    return [
      `Question: ${c.question}`, `Claim: ${c.claim}`, `Scope: ${c.scope}`, `Break points: ${c.break_points}`,
      `Decisive objections: ${c.decisive}`, `Open objections: ${c.open || "none"}`, `Confidence: ${c.confidence}`,
    ].join("\n");
  }

  function mentorSystem(related) {
    let s = K.mentor + "\n\n" + fill(P["app-preamble"], { ARXIV: K.arxiv.join(", ") }) +
      "\n\n## Lin Thinking Hub (loaded at boot)\n" + K.hub;
    if (related.length) s += "\n\n## Memory: related conclusion cards\n" + related.map((c) => `### ${c.id}\n${cardText(c)}`).join("\n\n");
    return s;
  }

  // The block is its heading plus the "- field:" lines (and their continuation lines) under it.
  function blockRange(text) {
    const at = text.lastIndexOf("## 結論草稿");
    if (at < 0) return null;
    const lines = text.slice(at).split("\n");
    let n = 1;
    while (n < lines.length && (/^\s*$/.test(lines[n]) || /^\s*[-\d(（]/.test(lines[n]) || /^\s{2,}\S/.test(lines[n]))) n++;
    const end = at + lines.slice(0, n).join("\n").length;
    return { at, end };
  }

  function parseBlock(text) {
    const r = blockRange(text);
    if (!r) return null;
    const at = r.at;
    const raw = text.slice(r.at, r.end).trim();
    const get = (label) => (raw.match(new RegExp(`-\\s*${label}\\s*[:：]\\s*([\\s\\S]*?)(?=\\n-\\s*\\S+\\s*[:：]|$)`)) || [, ""])[1].trim();
    return {
      raw, at, claim: get("主張"), steps: get("推理步驟"), factors: get("因子分類"),
      moves: get("使用招式"), bridges: get("跨域橋接"), selfConf: get("自評信心"),
    };
  }

  function parseObjections(text, role) {
    if (/^\s*NO OBJECTIONS\s*$/m.test(text) && !/OBJECTION\s*1/.test(text)) return [];
    return text.split(/(?=^OBJECTION\s*\d+)/m).filter((b) => /^OBJECTION\s*\d+/.test(b)).map((b) => {
      const f = (k) => (b.match(new RegExp(`-\\s*${k}\\s*[:：]\\s*([\\s\\S]*?)(?=\\n-\\s*[a-z ]+\\s*[:：]|$)`, "i")) || [, ""])[1].trim();
      const sev = (f("severity").match(/fatal|major|minor/i) || ["minor"])[0].toLowerCase();
      return { role: role.name, roleKey: role.key, type: f("type"), target: f("target step"), failure: f("failure case"), source: f("source"), severity: sev, resolve: f("would resolve it") };
    }).filter((o) => o.failure.length >= 12).sort((a, b) => SEV[b.severity] - SEV[a.severity]).slice(0, 3);
  }

  function objectionText(o, i) {
    return `O${i + 1} [${o.role} · ${o.severity}${o.type ? " · " + o.type : ""}]\n- target step: ${o.target}\n- failure case: ${o.failure}${o.source ? "\n- source: " + o.source : ""}\n- would resolve it: ${o.resolve}`;
  }

  async function ask(input, opts, emit, label) {
    const res = await sample(input, {
      ...opts,
      onText: ({ text }) => emit({ type: "tick", label, text: text.slice(-160) }),
    });
    return res;
  }

  // Step 0 — index check (exact / related / none).
  async function indexCheck(question, emit) {
    const list = activeCards();
    if (!list.length) return { route: "none", related: [], keywords: [] };
    emit({ type: "stage", step: "memory", animal: "foxSurvey", label: "狐狸 · 翻閱結論索引" });
    let r;
    try {
      r = await sample.json(fill(P["index-check"], { QUESTION: question, INDEX: list.map(indexLine).join("\n") }), { modelTier: "quick", cache: false, signal: emit.signal });
    } catch (e) {
      if (e.code === "cancelled") throw e;
      return { route: "none", related: [], keywords: [] };
    }
    const hit = (Array.isArray(r?.cards) ? r.cards : []).map((id) => cards.get(String(id))).filter((c) => c && !c.archived);
    if (!hit.length || r.match === "none") return { route: "none", related: [], keywords: r?.keywords || [] };
    const c = hit[0];
    const fresh = !c.recheck || c.recheck === "none" || c.recheck > today();
    if (r.match === "exact" && c.confidence === "high" && fresh && !c.disputed && String(r.same_reason || "").trim()) {
      return { route: "exact", card: c, reason: r.same_reason, related: [c], keywords: r.keywords || [] };
    }
    return { route: "related", related: hit.slice(0, 3), exactCard: r.match === "exact" ? c : null, keywords: r.keywords || [] };
  }

  async function run(question, ctx) {
    const emit = (ev) => ctx.on(ev);
    emit.signal = ctx.signal;
    const trace = { moves: [], route: "none", notes: [] };
    let force = false;
    const q = question.replace(/^\s*重新辯論[\s:：,，]*/, () => { force = true; return ""; }).trim() || question;

    // Step 0
    const idx = force ? { route: "none", related: [], keywords: [] } : await indexCheck(q, emit);
    if (force) trace.notes.push("重新辯論：略過索引重用，跑完整辯論");
    if (idx.route === "exact") {
      emit({ type: "stage", step: "memory", animal: "foxSurvey", label: `狐狸 · 重用結論卡 ${idx.card.id}` });
      const res = await sample(fill(P.reuse, { QUESTION: q, ID: idx.card.id, CARD: cardText(idx.card) }), {
        modelTier: "default", cache: false, signal: ctx.signal, onText: ({ text }) => emit({ type: "final", text }),
      });
      await touchCards([idx.card]);
      return { answer: res.text, route: "reused", block: { claim: idx.card.claim }, card: idx.card.id, confidence: idx.card.confidence, reason: idx.reason, trace };
    }
    trace.route = idx.route === "related" ? `delta (cards: ${idx.related.map((c) => c.id).join(", ")})` : "full";
    if (idx.related.length) await touchCards(idx.related);

    // Step 1 — mentor draft.
    emit({ type: "stage", step: "mentor", animal: "stork", label: "白鸛 · 導師推導中" });
    const sys = mentorSystem(idx.related);
    const turns = [{ role: "user", content: sys }];
    for (const t of ctx.history.slice(-4)) {
      turns.push({ role: "user", content: t.q }, { role: "assistant", content: t.answer.slice(0, 5000) });
    }
    turns.push({ role: "user", content: "## Student prompt\n" + q });
    const tools = canTools ? [
      {
        name: "open_move",
        description: "Open the branch note of one reasoning move (M1–M11) with its concrete sub-tactics, trigger signals and evidence. Call only when that move fires. Returns the note text.",
        inputSchema: { type: "object", properties: { id: { type: "string", description: "Move id, e.g. M9" } }, required: ["id"] },
        execute: ({ id }) => {
          const key = "M" + Number(String(id).replace(/\D/g, ""));
          if (!K.moves[key]) throw new Error("No such move. Valid: " + Object.keys(K.moves).join(", "));
          trace.moves.push(key);
          emit({ type: "stage", step: "mentor", animal: "stork", label: `白鸛 · 展開 ${key}` });
          return K.moves[key];
        },
      },
      {
        name: "open_lessons",
        description: "Open the D0–D9 deployment lessons for designing ~10 classic questions in a new field. Returns the text.",
        execute: () => { trace.moves.push("D0–D9"); return K.lessons; },
      },
    ] : undefined;
    const draftRes = await ask(turns, { modelTier: "complex", cache: false, signal: ctx.signal, tools }, emit, "mentor");
    const draft = draftRes.text.trim();
    const block = parseBlock(draft);
    if (!block) {
      emit({ type: "final", text: draft });
      return { answer: draft, route: "no-conclusion", trace };
    }

    // Step 2 — four blind critics in parallel.
    emit({ type: "stage", step: "critics", animal: "horse", label: "四位審查者平行審問", cycle: ROLES.map((r) => ({ animal: r.animal, label: `${animalName(r.animal)} · ${r.name}` })) });
    const scope = idx.related.length
      ? "delta only — judge only what this draft adds or changes relative to these stored cards:\n" + idx.related.map((c) => `${c.id}: ${c.claim}`).join("\n")
      : "full";
    const critics = await Promise.all(ROLES.map(async (role) => {
      const [task, types] = role.task.split(/\nTYPES:\s*/);
      const prompt = fill(P["critic-common"], {
        ROLE: role.name, SCOPE: scope, QUESTION: q, DRAFT: draft, TASK: task, TYPES: types || "",
        SOURCE_LINE: role.key === "insider" ? "- source: <URL or none>\n" : "",
      });
      try {
        const r = await ask(prompt, { modelTier: "default", cache: false, signal: ctx.signal }, emit, role.key);
        emit({ type: "critic-done", role: role.name });
        return { role, text: r.text, objections: parseObjections(r.text, role) };
      } catch (e) {
        if (e.code === "cancelled") throw e;
        trace.notes.push(`${role.name} 未完成（${e.code}）`);
        return { role, text: "", objections: [] };
      }
    }));
    const objections = critics.flatMap((c) => c.objections);
    objections.forEach((o) => { o.outcome = "open"; o.reply = ""; });

    // Step 3 — revision (concede / refute).
    let finalText = draft, finalBlock = block;
    if (objections.length) {
      emit({ type: "stage", step: "revision", animal: "flamingo", label: "紅鶴 · 逐條承認或反駁，改寫結論" });
      const rev = fill(P.revision, { QUESTION: q, DRAFT: draft, OBJECTIONS: objections.map(objectionText).join("\n\n") });
      const revRes = await sample([{ role: "user", content: K.mentor + "\n\n" + rev }], {
        modelTier: "complex", cache: false, signal: ctx.signal,
        onText: ({ text }) => {
          const at = text.indexOf(FINAL);
          if (at >= 0) emit({ type: "final", text: stripBlock(text.slice(at + FINAL.length)) });
          else emit({ type: "tick", label: "revision", text: text.slice(-160) });
        },
      });
      const txt = revRes.text;
      for (const m of txt.matchAll(/^\s*O(\d+)\s*[:：]\s*(CONCEDE|REFUTE)\s*[—–\-:：]*\s*(.*)$/gim)) {
        const o = objections[Number(m[1]) - 1];
        if (o) { o.outcome = m[2].toUpperCase() === "CONCEDE" ? "conceded" : "refuted"; o.reply = m[3].trim(); }
      }
      const at = txt.indexOf(FINAL);
      finalText = (at >= 0 ? txt.slice(at + FINAL.length) : txt).trim();
      finalBlock = parseBlock(finalText) || block;
      if (revRes.truncated) trace.notes.push("修訂稿達長度上限而截斷");
    }

    // Step 4 — round 2, only for refuted fatal objections.
    const refutedFatal = objections.filter((o) => o.outcome === "refuted" && o.severity === "fatal");
    if (refutedFatal.length) {
      emit({ type: "stage", step: "revision", animal: "horse", label: "駿馬 · 第二回合：致命反對是否仍成立" });
      await Promise.all(refutedFatal.map(async (o) => {
        try {
          const r = await sample.json(fill(P.round2, { ROLE: o.role, QUESTION: q, OBJECTION: objectionText(o, 0), REFUTATION: o.reply, BLOCK: finalBlock.raw }), { modelTier: "default", cache: false, signal: ctx.signal });
          if (r?.stands) { o.outcome = "open"; o.round2 = r.failure_case || ""; } else o.round2 = "withdrawn";
        } catch (e) { if (e.code === "cancelled") throw e; }
      }));
    }

    // Step 5 — judge (recorder call + fixed confidence rule).
    emit({ type: "stage", step: "judge", animal: "stork", label: "白鸛 · 裁判評定信心" });
    const ledger = objections.map((o, i) => `O${i + 1} | ${o.role} | ${o.failure.slice(0, 200)} | ${o.severity} | ${o.outcome}${o.reply ? " — " + o.reply : ""}`).join("\n") || "(no objections survived the filter)";
    let j = {};
    try {
      j = await sample.json(fill(P.judge, { TODAY: today(), QUESTION: q, DRAFT_BLOCK: block.raw, FINAL_BLOCK: finalBlock.raw, LEDGER: ledger }), { modelTier: "default", cache: false, signal: ctx.signal });
    } catch (e) { if (e.code === "cancelled") throw e; trace.notes.push("裁判紀錄呼叫失敗，以草稿欄位存卡"); }
    const unreviewed = Array.isArray(j.unreviewed_new_claims) ? j.unreviewed_new_claims.filter(Boolean) : [];
    const open = objections.filter((o) => o.outcome === "open");
    const confidence = open.some((o) => o.severity === "fatal") ? "low"
      : open.some((o) => o.severity === "major") || unreviewed.length ? "medium" : "high";

    // Step 6 — store (record, card, index, insight) and step 7 review every 5 debates.
    emit({ type: "stage", step: "store", animal: "foxRun", label: "狐狸 · 收藏結論卡" });
    const stored = await store({ q, route: trace.route, block, finalBlock, finalText, objections, critics, j, unreviewed, confidence, exactCard: force ? idx.exactCard : null });
    if (stored?.review) {
      emit({ type: "stage", step: "store", animal: "foxWalk", label: "狐狸 · 每五場回顧" });
      trace.review = await review();
    }
    return {
      answer: stripBlock(finalText), block: finalBlock, route: trace.route, confidence, card: stored?.card, slug: stored?.slug,
      objections, open, unreviewed, diff: Array.isArray(j.diff) ? j.diff : [], insight: j.insight || null, trace,
    };
  }

  function stripBlock(text) {
    const r = blockRange(text);
    return (r ? text.slice(0, r.at) + text.slice(r.end) : text).trim();
  }
  function animalName(a) { return { horse: "駿馬", flamingo: "紅鶴", parrot: "鸚鵡", stork: "白鸛", foxSurvey: "狐狸", foxWalk: "狐狸", foxRun: "狐狸" }[a] || a; }

  async function touchCards(list) {
    if (!db) return;
    await Promise.all(list.map((c) => db.doc("cards/" + c.id).update({ last_used: today() }).catch(() => {})));
  }

  function nextCardId() {
    let max = 0;
    for (const id of cards.keys()) max = Math.max(max, Number(id.replace(/\D/g, "")) || 0);
    return "C" + String(max + 1).padStart(3, "0");
  }

  function recordMarkdown(r) {
    const esc = (s) => String(s || "").replace(/\|/g, "\\|").replace(/\n+/g, " ");
    return [
      "---", `question: ${r.q}`, `route: ${r.route}`, `confidence: ${r.confidence}`, `card: ${r.card}`, "---", "",
      "## Final conclusion", r.finalBlock.raw.replace(/^## 結論草稿\s*/, ""), "",
      `**Confidence: ${r.confidence}**${r.unreviewed.length ? " (unreviewed-revision rule: " + r.unreviewed.join("；") + ")" : ""}`, "",
      "## Objection ledger", "| role | objection | severity | outcome (conceded/refuted/open) |", "|---|---|---|---|",
      ...r.objections.map((o) => `| ${o.role} | ${esc(o.failure)} | ${o.severity} | ${o.outcome}${o.reply ? " — " + esc(o.reply) : ""} |`), "",
      "## Draft → final diff", ...(r.j.diff || []).map((d) => `- ${d.change} (${d.cause})`), "",
      "## Open objections", ...(r.objections.filter((o) => o.outcome === "open").map((o) => `- ${o.role}: ${o.failure}`)), ...(r.unreviewed.map((u) => `- unreviewed: ${u}`)), "",
      "## Verbatim critic outputs", ...r.critics.flatMap((c) => [`### ${c.role.name}`, c.text || "(no output)", ""]),
    ].join("\n");
  }

  async function store(r) {
    if (!db) return null;
    const date = today();
    const slug = `${date}-${String(r.j.slug || "debate").toLowerCase().replace(/[^a-z0-9-]+/g, "-").replace(/^-|-$/g, "").slice(0, 48) || "debate"}`;
    const id = r.exactCard ? r.exactCard.id : nextCardId();
    const open = r.objections.filter((o) => o.outcome === "open").map((o) => `${o.role}: ${o.failure.slice(0, 160)}`);
    if (r.unreviewed.length) open.push("修訂新增、未經 critic 複審（unreviewed）：" + r.unreviewed.join("；"));
    const card = {
      id, question: r.q, keywords: (r.j.keywords || []).slice(0, 6), confidence: r.confidence,
      created: r.exactCard?.created || date, last_used: date, recheck: /^\d{4}-\d{2}-\d{2}$/.test(r.j.recheck || "") ? r.j.recheck : "none",
      archive: slug, claim: r.j.claim || r.finalBlock.claim, scope: r.j.scope || "", break_points: r.j.break_points || "",
      decisive: r.j.decisive_objections || "", open: open.join("；") || "none", moves_used: r.j.moves_used || r.finalBlock.moves, disputed: false,
    };
    const changed = (r.j.diff || []).length > 0 || r.objections.some((o) => o.outcome === "conceded");
    const record = recordMarkdown({ ...r, card: id, confidence: r.confidence });
    await db.doc("debates/" + slug).set({ slug, question: r.q, route: r.route, confidence: r.confidence, card: id, date, final: r.finalBlock.raw, record, changed });
    await db.doc("cards/" + id).set(card);
    if (r.j.insight && r.j.insight.pattern) {
      await db.doc("insights/" + slug).set({ date, from: slug, kind: r.j.insight.kind === "D" ? "D" : "G", pattern: r.j.insight.pattern, status: "queued" });
    }
    meta.debates_since_review = (meta.debates_since_review || 0) + 1;
    await db.doc("meta/state").set(meta);
    return { card: id, slug, review: meta.debates_since_review >= 5 };
  }

  // Step 7: drop stale non-high cards, flag a debate trigger that changes nothing.
  async function review() {
    const date = today(), cutoff = new Date(Date.now() - 90 * 864e5).toISOString().slice(0, 10);
    const dropped = [];
    for (const c of activeCards()) {
      if (c.confidence !== "high" && (c.last_used || c.created) < cutoff) {
        await db.doc("cards/" + c.id).update({ archived: true });
        dropped.push(c.id);
      }
    }
    const recent = await db.collection("debates").orderBy("date", "desc").limit(5).get().catch(() => null);
    const unchanged = recent ? recent.docs.filter((d) => d.data().changed === false).length : 0;
    const insights = await db.collection("insights").get().catch(() => null);
    const pending = insights ? insights.docs.filter((d) => d.data().status === "queued").length : 0;
    meta.reviews = (meta.reviews || 0) + 1;
    meta.debates_since_review = 0;
    const row = { n: meta.reviews, date, dropped, unchanged_of_5: unchanged, insights_pending: pending,
      note: unchanged >= 5 ? "連續 5 場辯論未改變任何結論：辯論觸發範圍應縮小" : "" };
    await db.doc("reviews/R" + String(meta.reviews).padStart(3, "0")).set(row);
    await db.doc("meta/state").set(meta);
    return row;
  }

  async function dispute(id) {
    if (!db) return;
    await db.doc("cards/" + id).update({ confidence: "medium", disputed: true });
  }

  function cardMarkdown(c) {
    return [
      "---", `id: ${c.id}`, `question: ${c.question}`, `keywords: [${(c.keywords || []).join(", ")}]`, `confidence: ${c.confidence}`,
      `created: ${c.created}`, `last_used: ${c.last_used}`, `recheck: ${c.recheck || "none"}`, `archive: [[debates/${c.archive}]]`, "---",
      `**Claim:** ${c.claim}`, `**Scope:** ${c.scope}`, `**Break points:** ${c.break_points}`,
      `**Decisive objections (imprint):** ${c.decisive}`, `**Open objections:** ${c.open}`, `**Moves used:** ${c.moves_used}`, "",
    ].join("\n");
  }

  async function exportCard(id) {
    const c = cards.get(id);
    if (!c || !downloads) throw { code: "unavailable" };
    let data = cardMarkdown(c);
    const d = c.archive && db ? await db.doc("debates/" + c.archive).get().catch(() => null) : null;
    if (d?.exists && d.data().record) data += "\n\n<!-- debate record: debates/" + c.archive + ".md -->\n\n" + d.data().record;
    return downloads.save({ filename: `${c.id}.md`, data });
  }

  return { connect, run, onCards, activeCards, dispute, exportCard, hasDownloads: () => !!downloads, hasDb: () => !!db };
})();
