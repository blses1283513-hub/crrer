# Lin Brain app

A claude.ai Artifact that runs the vault's rules on every prompt:
memory index check → mentor derivation (moves opened on demand) → four blind critics
(Skeptic, Bridge auditor, Practitioner, Field insider) → concede/refute revision → round 2 for
refuted fatal objections → fixed confidence rule → conclusion card, debate record, insight line,
review every 5 debates.

- Live app: https://claude.ai/artifact/36BZitYR3w5pQLJ929tRvH
- `node app/build.mjs` compiles the vault (mentor prompt, Hub, `moves/`, `deployment-lessons.md`,
  arXiv IDs) plus `app/src/` into `app/dist/lin-brain.html`, and the memory seed into `app/dist/seed.json`.
- Critic role prompts in `app/src/prompts/role-*.md` were reconstructed from the lin-debate skill and the
  archived debate records; the originals (`references/roles/`) are not in this repo.
- Out of scope in the app (they need the web or vault files): news update, corpus refresh, weekly study,
  teaching material. Run those in Claude Code.
