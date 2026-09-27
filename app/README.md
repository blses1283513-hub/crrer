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

## Modes
- 快速 (default): memory check + mentor answer (1–2 Claude calls). The answer shows 「開辯論」, which runs
  the four-critic debate on that same draft and stores the conclusion card.
- 嚴謹: every conclusion-point prompt runs the full debate. Prefixing a prompt with 「開辯論」 or 「重新辯論」
  forces it in either mode. Critics and round 2 run on the quick model tier.

## Animal models
Each thinking stage draws the next of 45 kinds from a shuffled deck.
- 40 procedural species (`app/src/animals.js`). Motion follows published locomotion studies
  (Muybridge's gait photographs, Hildebrand's footfall timing): legs use two-bone IK with planted feet,
  lateral-sequence walk, trot, pace (giraffe, camel), amble (elephant), rotary gallop with spine flex
  (cheetah); stabilized heads, lagging tails, countershading; birds with a longer downstroke, wrist fold
  on the upstroke, slotted primaries and flap-glide (eagle); owl head snaps and blinks; octopus jet
  strokes; jellyfish fast-squeeze/slow-refill; crouch-push-flight-landing hops.
- 5 rigged glTF models whose particles are re-sampled from the moving surface every frame. They ship as
  base64 `.txt` next to the page (artifacts don't serve `.glb`).
- Horse, Flamingo, Parrot, Stork: from the three.js examples (r128, `examples/models/gltf`), originally from the RO.ME project.
- Fox: Khronos glTF-Sample-Assets, CC-BY 4.0 (model by PixelMannen, rigging and animation by @tomkranis).
