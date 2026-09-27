// Compiles the Lin Brain vault (this repo) into one self-contained Artifact page
// plus a seed file for the app's memory store.  Run: node app/build.mjs
import { readFileSync, writeFileSync, readdirSync, mkdirSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const APP = dirname(fileURLToPath(import.meta.url));
const ROOT = join(APP, "..");
const read = (p) => readFileSync(join(ROOT, p), "utf8");
const src = (p) => readFileSync(join(APP, "src", p), "utf8");

function splitFrontMatter(text) {
  const m = text.match(/^---\n([\s\S]*?)\n---\n?([\s\S]*)$/);
  if (!m) return { meta: {}, body: text };
  const meta = {};
  for (const line of m[1].split("\n")) {
    const kv = line.match(/^([\w-]+):\s*(.*?)\s*(#.*)?$/);
    if (!kv) continue;
    let v = kv[2];
    if (/^\[(?!\[).*\]$/.test(v)) v = v.slice(1, -1).split(",").map((s) => s.trim()).filter(Boolean);
    meta[kv[1]] = v;
  }
  return { meta, body: m[2] };
}

const unlink = (s) => s.replace(/\[\[([^\]|]+)(\|[^\]]+)?\]\]/g, "$1");

// Mentor prompt: the agent body, minus the file-system boot paragraph and the
// protocol routing table (the app replaces both with tools + its own preamble).
function mentorPrompt() {
  const { body } = splitFrontMatter(read("_backup-2026-09-27/pre-final-fix/lin-hsiu-hau-mentor.md"));
  let b = body.trim();
  b = b.replace(/\*\*Boot sequence:\*\*[\s\S]*?(?=\*\*Core Worldview)/, "");
  b = b.replace(/\*\*Routing[\s\S]*?(?=\*\*Language:\*\*)/, "");
  b = b.replace(
    "The main conversation runs the `lin-debate` skill on this block. You cannot start subagents; never simulate the debate yourself.",
    "The app runs the lin-debate procedure on this block after you answer. Never simulate the debate yourself.",
  );
  b = b.replace(/\*\*Language:\*\*[^\n]*/, "**Language:** Respond in Traditional Chinese (Taiwan), keeping English technical terms untranslated, matching Prof. Lin's lecturing style. Use LaTeX ($...$, $$...$$) for all mathematics.");
  b = b.replace(/- News: [^\n]*\n/, "");
  return b;
}

function moves() {
  const out = {};
  for (const f of readdirSync(join(ROOT, "moves")).sort()) {
    const id = "M" + Number(f.match(/^M(\d+)/)[1]);
    const { body } = splitFrontMatter(read(join("moves", f)));
    out[id] = unlink(body.trim());
  }
  return out;
}

function arxivIds() {
  const files = ["curriculum.md", ...readdirSync(join(ROOT, "moves")).map((f) => join("moves", f))];
  const ids = new Set();
  for (const f of files) for (const m of read(f).matchAll(/\b(cond-mat\/\d{7}|\d{4}\.\d{4,5})\b/g)) ids.add(m[1]);
  return [...ids].sort();
}

const today = new Date().toISOString().slice(0, 10);

const knowledge = {
  builtFrom: "blses1283513-hub/crrer",
  builtAt: today,
  mentor: mentorPrompt(),
  hub: unlink(splitFrontMatter(read("00 - Lin Thinking Hub.md")).body.trim()),
  moves: moves(),
  lessons: unlink(splitFrontMatter(read("deployment-lessons.md")).body.trim()),
  arxiv: arxivIds(),
  prompts: Object.fromEntries(
    readdirSync(join(APP, "src", "prompts")).sort().map((f) => [f.replace(/\.md$/, ""), src(join("prompts", f)).trim()]),
  ),
};

// Seed for the memory store: conclusion cards, insights queue, debate archive.
function parseCard(file) {
  const { meta, body } = splitFrontMatter(read(file));
  const field = (label) => (body.match(new RegExp(`\\*\\*${label}:\\*\\*\\s*([^\\n]*)`)) || [, ""])[1].trim();
  return {
    id: meta.id,
    question: meta.question,
    keywords: meta.keywords || [],
    confidence: meta.confidence,
    created: meta.created,
    last_used: meta.last_used,
    recheck: meta.recheck || "none",
    archive: unlink(meta.archive || "").replace(/^debates\//, ""),
    claim: field("Claim"),
    scope: field("Scope"),
    break_points: field("Break points"),
    decisive: field("Decisive objections \\(imprint\\)"),
    open: field("Open objections"),
    moves_used: field("Moves used"),
    disputed: false,
  };
}

const seed = { cards: {}, insights: {}, debates: {} };
for (const f of readdirSync(join(ROOT, "memory", "cards")).sort()) {
  const c = parseCard(join("memory", "cards", f));
  seed.cards[c.id] = c;
}
let n = 0;
for (const line of read("memory/insights-queue.md").split("\n")) {
  const m = line.match(/^- (\d{4}-\d{2}-\d{2}) · from \[\[debates\/([^\]]+)\]\] · (G|D) candidate · (.+)$/);
  if (!m) continue;
  n += 1;
  seed.insights["I" + String(n).padStart(3, "0")] = { date: m[1], from: m[2], kind: m[3], pattern: m[4], status: "queued" };
}
for (const f of readdirSync(join(ROOT, "debates")).filter((f) => /^\d{4}-/.test(f))) {
  const slug = f.replace(/\.md$/, "");
  const { meta, body } = splitFrontMatter(read(join("debates", f)));
  const final = (body.match(/## Final conclusion\n([\s\S]*?)\n## /) || [, ""])[1].trim();
  seed.debates[slug] = {
    slug, question: meta.question, route: meta.route, confidence: meta.confidence, card: meta.card,
    date: slug.slice(0, 10), final, record: body.trim(), changed: true,
  };
}
seed.meta = { state: { debates_since_review: Object.keys(seed.debates).length, reviews: 0 } };

let html = src("index.html");
const inject = {
  "/*@STYLE*/": src("style.css"),
  "/*@KNOWLEDGE*/": "window.LIN = " + JSON.stringify(knowledge).replace(/</g, "\\u003c") + ";",
  "/*@ORB*/": src("orb.js"),
  "/*@BRAIN*/": src("brain.js"),
  "/*@UI*/": src("ui.js"),
};
for (const [k, v] of Object.entries(inject)) {
  if (!html.includes(k)) throw new Error("template marker missing: " + k);
  html = html.split(k).join(v);
}
writeFileSync(join(APP, "dist", "lin-brain.html"), html);
writeFileSync(join(APP, "dist", "seed.json"), JSON.stringify(seed, null, 1));
mkdirSync(join(APP, "dist", "animals"), { recursive: true });
for (const f of readdirSync(join(APP, "assets", "animals")).filter((f) => f.endsWith(".glb"))) {
  writeFileSync(join(APP, "dist", "animals", f.replace(/\.glb$/, ".txt")), readFileSync(join(APP, "assets", "animals", f)).toString("base64"));
}
console.log(`lin-brain.html ${Buffer.byteLength(html)} B · moves ${Object.keys(knowledge.moves).length} · arXiv ids ${knowledge.arxiv.length} · cards ${Object.keys(seed.cards).length} · debates ${Object.keys(seed.debates).length} · insights ${n}`);
