# Open-source AI video-director / auto-montage projects, video-editing MCP servers, and music sourcing for a Claude travel-reel agent

Research date: 2026-10-28. Star counts are approximate snapshots, mostly from GStars.dev daily snapshots dated 2026-10-27/28 (the GitHub API was not reachable from this session, so counts could not be read directly). Where trackers disagree, both values are given.

## Key Question 1: Which open-source projects and MCP servers are most relevant, and how popular, active and licensed are they?

### Takeaway
The most-starred projects (MoneyPrinterTurbo ~134K, Remotion ~68K, HyperFrames ~73K, NarratoAI ~11.6K, ShortGPT ~8K) are **topic-to-video narration generators or rendering frameworks**, not music-driven montage editors. The projects that actually do "user photos and clips plus music, beat-synced, 9:16" are small, recent repos, several of them packaged as **Claude Code / Codex skills** (beat-synced-edit, beat-sync-video-editor, vlog-auto-edit), plus Montage AI and Immich Memories. Among MCP servers, DaVinci Resolve MCP (~3.8K stars, very active) is the mature one. The FFmpeg MCP servers are small and partly stale.

### Cited Findings

**A. Topic-to-short-video generators (high stars; narration-led)**
- **MoneyPrinterTurbo** (harry0703): ~134.2K stars, 21.2K forks, MIT, last commit Oct 2026, 134 contributors, 5 releases in the last 90 days — [GStars](https://www.gstars.dev/repo/harry0703/MoneyPrinterTurbo). Another tracker shows ~135.5K stars as of mid/late Oct 2026 — [EvanLi Github-Ranking](https://github.com/EvanLi/Github-Ranking/blob/master/Top100/Top-100-stars.md); [git-leaderboard](https://git-leaderboard.dev/).
  - Pipeline: an LLM writes the script (supports Claude, OpenAI, Gemini, DeepSeek, Kimi, and others) → footage from the user's **own local images and videos**, or stock from Pexels/Pixabay/Coverr, or AI text-to-video → TTS (Edge TTS free, ElevenLabs, and others) → auto subtitles → background music (random, local, or AI-generated, with its own volume control) → export at 9:16 (1080×1920), 16:9 or 1:1, with one-click publishing to TikTok, Instagram and YouTube Shorts — [README](https://github.com/harry0703/MoneyPrinterTurbo).
  - It is Python/FastAPI/Streamlit with WebUI, REST API, CLI and AI-agent interfaces. A security review flagged that it has no built-in authentication — [daily.dev](https://daily.dev/posts/gqwcgayde).
- **NarratoAI** (linyqh): ~11.6K stars, MIT, last commit Oct 2026 — [GStars](https://www.gstars.dev/repo/linyqh/NarratoAI).
  - A film and short-drama **commentary** tool: LLM copywriting, vision understanding (Qwen-VL, optional TwelveLabs Pegasus), TTS/voice cloning, subtitles, and export to JianYing (CapCut CN) drafts. v0.8.6 (Jul 2026) added optional "Sonilo AI" scoring.
  - It is a refactor of MoneyPrinter and MoneyPrinterTurbo — [README](https://github.com/linyqh/NarratoAI).
- **ShortGPT** (RayVentura): ~8.1K stars, MIT, **last commit Feb 2025** (stale) — [GStars](https://www.gstars.dev/repo/RayVentura/ShortGPT). Other trackers report 5.5K ([VisLane](https://vislane.com/en/open-source/shortgpt)) and 7.9K ([zgba](https://tools.zgba.com/tools/shortgpt)), so the counts conflict.
  - Architecture: an "LLM oriented video editing language", MoviePy rendering, EdgeTTS/ElevenLabs, Pexels/Bing asset sourcing, TinyDB persistence, and `ContentShortEngine` / `ContentVideoEngine` classes — [README](https://github.com/RayVentura/ShortGPT).
- **short-video-maker** (gyoridavid): ~1.4K stars, MIT, TypeScript, **last commit Jun 2025** (no commits in over a year) — [GStars](https://www.gstars.dev/repo/gyoridavid/short-video-maker).
  - It exposes **both an MCP server and a REST API**. It does TTS, auto captions, Pexels background video, and background music with genre/mood selection. Docker images come in tiny, normal and CUDA variants — [README](https://github.com/gyoridavid/short-video-maker).

**B. Agentic video frameworks**
- **Director** (video-db): ~1.6K stars, MIT, last commit Jan 2026 — [GStars](https://www.gstars.dev/repo/video-db/Director).
  - A "Reasoning Engine" orchestrates multiple agents (summarize, search, clip, overlay) and includes a chat UI and a video player.
  - It is built on the hosted **VideoDB** "video-as-data" infrastructure, so it depends on that service — [README](https://github.com/video-db/Director).
- **VideoAgent** (HKUDS, EMNLP 2026): ~2.0K stars, MIT, last commit Jul 2026, no releases — [GStars](https://www.gstars.dev/repo/HKUDS/VideoAgent).
  - Its README claims "Beat-synced Edits", storytelling video, song remixes and sound-effect tools.
  - It requires several LLM keys: "Claude is required as it powers the Agentic Graph Router", with GPT for editing and Gemini for captioning — [README](https://github.com/HKUDS/VideoAgent).
- **FunClip** (modelscope): ~6.5K stars, MIT, active (v2.2.1, Sep 2026). It does ASR (FunASR) transcription, subtitles and LLM-assisted clipping in a Gradio UI. It is speech-centric, not a montage tool — [GStars](https://www.gstars.dev/repo/modelscope/FunClip); [README](https://github.com/modelscope/FunClip).

**C. Music-driven montage / beat-sync / travel-vlog projects (closest to the use case; mostly small)**
- **beat-synced-edit** (ZiadAbdelkarim): MIT, created Aug 2026, ~30 commits. Star count not found. It ships a **Claude Code skill** at `.claude/skills/beat-sync-edit/SKILL.md`.
  - Pipeline:
    - `beat_map.py` (librosa: beats, tempo, energy curve, peaks/valleys, highlight segments)
    - `clip_tag.py` (PySceneDetect scenes plus motion/energy/brightness scores, with a contact sheet)
    - `plan_edit.py` (matches high-energy clips to energy peaks and calm clips to valleys, with anti-repetition and black-frame filtering)
    - `render_edit.py` (ffmpeg extract → concat → mux audio)
    - `vertical_style.py` (9:16)
    - `flash_montage.py` (stills and/or clips with `fadewhite` transitions, punch-ins, handheld sway)
  - Effects are applied at beat-accurate timestamps: flashes, speed ramps, shakes, RGB split, grades, and "grade it like this reference" — [README](https://github.com/ZiadAbdelkarim/beat-synced-edit).
- **beat-sync-video-editor** (330312): a Codex skill (SKILL.md plus scripts) that turns "a folder of photos and videos plus a music track" into a beat-synced montage. Created Oct 2026, 1 commit, license not shown. It builds a **human-approved beat map before rendering** and preserves full frames with padding.
  - Stated editing principles: "Do not distribute cuts uniformly from BPM alone"; place an action climax "roughly 0.20–0.30 seconds before the interval ends"; "End music only after a complete lyrical or musical phrase" — [README](https://github.com/330312/beat-sync-video-editor).
- **ai-video-editing-skill / "vlog-auto-edit"** (znyupup): MIT, created Apr 2026, 13 commits. An agent skill for **travel vlog** auto-editing using ffmpeg, Whisper and a vision API (GLM-4.6V-Flash free, GPT-4o, Qwen-VL).
  - Flow: analyze → LLM narrative plan → a **browser dashboard preview for user approval** → cut, title, concat, BGM.
  - It documents 24 pitfalls, including "xfade chain merges drop frames — use concat instead", "Whisper hallucinates on ambient audio", "JianYing v10.4+ project files are encrypted" and "verify on 5–8 s test segments first" — [README](https://github.com/znyupup/ai-video-editing-skill). It was also submitted as a community skill to Hermes Agent with a 7-stage pipeline — [GitHub issue](https://github.com/NousResearch/hermes-agent/issues/11036).
- **Montage AI** (mfahsold): ~60 stars, license NOASSERTION, last commit Mar 2026 — [GStars](https://www.gstars.dev/repo/mfahsold/montage-ai).
  - Pipeline: "Input Videos + Music → Beat Detection → Scene Analysis → Clip Assembly → FFmpeg Render", with an optional LLM "Creative Director" and JSON style templates (7 built in).
  - Also: smart reframing 16:9→9:16, OTIO/EDL export to DaVinci/Premiere, a story engine with a narrative arc, color grading, and caption styles — [README](https://github.com/mfahsold/montage-ai).
- **BeatSync Engine** (Merserk): **AGPL-3.0**, Windows portable app.
  - Features: beat-grid cutting, "energy-wave cut density" (calm sections hold longer, drops cut faster), song-structure detection (intro/verse/chorus/drop), kick/clap/hi-hat analysis, and optional Qwen3-VL semantic scene tags — [README](https://github.com/Merserk/BeatSync-Engine).
- **easy-beat-sync** (jort-dev): photos and videos synced to user-marked beat timestamps (manual marker tool). Simple and older — [README](https://github.com/jort-dev/easy-beat-sync).
- **Immich Memories** (sam-dumont; the "Google Photos memories" equivalent): MIT, ~10 stars (Sep 2026), 526 commits, PyPI release 0.53.11 (Aug 2026).
  - It selects best moments from photos and videos, uses Ken Burns / face-aware pans on photos and supports Live Photos.
  - It renders "titles, maps and music". The user reviews every shot (remove, trim, swap) before rendering, and LLM titles and AI music are optional — [GitHub](https://github.com/sam-dumont/immich-video-memory-generator); [docs](https://sam-dumont.github.io/immich-video-memory-generator/); [PyPI](https://pypi.org/project/immich-memories/0.53.11).

**D. Rendering frameworks for agents**
- **Remotion**: ~67.9K stars, releases every few days (v4.0.539 on Oct 26, 2026) — [GStars](https://www.gstars.dev/repo/remotion-dev/remotion); "68K stars" per [remotion.dev](https://www.remotion.dev/).
  - It maintains official **Agent Skills** (`/remotion-markup` covering compositions, animations, audio and timing; `/remotion-multimedia`) and has Transitions and SFX component libraries — [Remotion Agent Skills docs](https://www.remotion.dev/docs/ai/skills); [README](https://github.com/remotion-dev/remotion).
  - License: free for individuals and companies of up to 3 people. Larger companies need a Company License ("Remotion for Creators" costs $25/seat/month) — [Remotion license](https://www.remotion.dev/license); [Terms v5](https://www.remotion.dev/docs/terms).
- **HyperFrames** (HeyGen): **Apache-2.0**, ~73K stars, 221K weekly npm downloads. "Turns HTML into video": an agent writes HTML/CSS/JS, and rendering is frame-exact. A Studio app launched Oct 2026 and works with Claude Code and Codex. Skills install via `npx skills add heygen-com/hyperframes` — [hyperframes.dev](https://www.hyperframes.dev/); [intro](https://hyperframes.heygen.com/introduction); [HeyGen on X](https://x.com/HeyGen/status/2107152038090174699). The default resolution is 1920×1080 at 30fps, so vertical output must be requested explicitly — [prompting docs](https://hyperframes.heygen.com/prompting/overview).
- **MoviePy**: ~15.0K stars, MIT, last commit Aug 2026. The v2.0 API breaking changes matter for older code (ShortGPT and similar are built on it) — [GStars](https://www.gstars.dev/repo/Zulko/moviepy); [README](https://github.com/Zulko/moviepy).

**E. MCP servers for video editing**
- **DaVinci Resolve MCP** (samuelgursky): ~3.8K stars, MIT, last commit Oct 2026 — [GStars](https://www.gstars.dev/repo/samuelgursky/davinci-resolve-mcp).
  - Scale: 37 compound / 390 granular tools, 361/361 API methods covered.
  - Capabilities: media pool, Fusion, Fairlight audio, media analysis with vision, and transcription.
  - Tested on Resolve 19.1.3–21.0.3 Studio, and on Resolve 21.0.3 **free** via an in-app bridge — [README](https://github.com/samuelgursky/davinci-resolve-mcp).
- **video-audio-mcp** (misbahsy): ~89 stars, MIT, last commit May 2025.
  - Over 30 FFmpeg tools, including `trim_video`, `change_aspect_ratio` (pad or crop, e.g. 9:16), concatenation with transitions, `add_b_roll` with fade, text overlay, subtitle burning, speed and silence removal — [GStars](https://www.gstars.dev/repo/misbahsy/video-audio-mcp); [README](https://github.com/misbahsy/video-audio-mcp).
- **ffmpeg-mcp-lite** (kevinwatt): MIT, created Jan 2026, 9 commits. Tools: `ffmpeg_trim`, `ffmpeg_merge` (same-codec concat only), audio extraction, subtitles, compression — [README](https://github.com/kevinwatt/ffmpeg-mcp-lite).
- **Other FFmpeg MCP servers**: yubraaj11/ffmpeg-mcp (~12 stars, fastmcp + ffmpeg-python), conneroisu/vfx-mcp, and maoxiaoke/mcp-media-processor (~29 stars, FFmpeg + ImageMagick) — [mcpservers.org](https://mcpservers.org/servers/yubraaj11/ffmpeg-mcp); [mcpservers.org](https://mcpservers.org/servers/maoxiaoke/mcp-media-processor).
- **video-editing-mcp** (burningion): ~294 stars, no license listed, last commit Oct 2025. It requires a **Video Jungle** SaaS account. Tools include add-video, search-videos, generate-edit-from-videos, and edit-locally (OpenTimelineIO export into Resolve). It can optionally search the macOS Photos library — [GStars](https://www.gstars.dev/repo/burningion/video-editing-mcp); [README](https://github.com/burningion/video-editing-mcp).
- **Remotion MCP servers** (community):
  - ivalenzuela/remotion-mcp-server (MIT) scaffolds and renders Remotion projects. It includes "Librosa Audio Beat Sync" (BPM, beat boundaries, RMS energy rises and drops) and word-level timecodes for kinetic subtitles — [README](https://github.com/ivalenzuela/remotion-mcp-server).
  - PratyushChauhan/remotion-mcp-server: template-based scaffold, render and preview (1 commit) — [README](https://github.com/PratyushChauhan/remotion-mcp-server).
  - mcp-use/remotion-mcp-app: MIT, with Remotion's own license still applying — [LICENSE](https://github.com/mcp-use/remotion-mcp-app/blob/main/LICENSE).
- **CapCut MCP servers**: community servers exist (e.g. JmsLdrn/capcut-mcp, updated Jun 2026, plus capcut-mcp-server) that automate CapCut drafts. Quality was graded low — [Glama](https://glama.ai/mcp/servers/JmsLdrn/capcut-mcp).

### Inferences
- Popularity is concentrated in "faceless channel" narration generators. Their reusable parts for a travel reel are their **asset ingest, TTS, subtitle and 9:16 render plumbing**, not their editing logic. None of the high-star projects lists beat-synced cutting of user footage as a feature (MoneyPrinterTurbo's music is background-only).
- The design pattern that fits best has emerged in 2026 as **agent skills** (SKILL.md plus Python/ffmpeg scripts) rather than monolithic apps: beat-synced-edit, beat-sync-video-editor and vlog-auto-edit. This maps directly onto a Claude-based director agent.
- The small community repos are useful mainly as design references. Low commit counts and missing or unclear licenses (beat-sync-video-editor, Montage AI's NOASSERTION, BeatSync Engine's AGPL) argue for reimplementing their ideas, not vendoring their code.
- DaVinci Resolve MCP is the only mature, high-activity editing MCP. It is overkill for an automated pipeline that has to run without a person at the controls, and it needs Resolve installed. It could serve as an optional "hand off to a pro editor" path, along with OTIO export.

### Gaps
- Exact live GitHub star counts could not be read from the GitHub API (blocked in this environment). Counts come from third-party trackers on 2026-10-27/28, and they disagree for ShortGPT.
- No star counts were found for beat-synced-edit, beat-sync-video-editor, ai-video-editing-skill, BeatSync Engine, ffmpeg-mcp-lite or the Remotion MCP servers.
- **OpenShot/Shotcut automation** (libopenshot Python bindings, MLT XML generation) was not researched in this pass. No sourced findings.
- I did not verify which renderer short-video-maker uses internally, or whether VideoAgent's "beat-synced edits" work on arbitrary user photos.
- I found no official Remotion- or Anthropic-maintained MCP server for video editing. Remotion offers Agent Skills, not an MCP server.

## Key Question 2: How should the agent source music — what can the Epidemic Sound MCP connector do, and what free alternatives are licensed for Instagram use?

### Takeaway
The Epidemic Sound MCP connector is the strongest fit. It is official, it is in Claude's connector directory, and it covers the core music steps a reel needs: search by mood/BPM/genre/key/instrument or a Spotify reference, download full tracks or stems, and **auto-edit a track to an exact duration** with anchored regions (e.g. "chorus at 0:15"). It returns BPM but **no beat timestamps**, so beat detection still has to run locally. Licensing depends on the user's own Epidemic plan (the Creator plan covers Instagram for non-commercial creators). Free alternatives carry weaker guarantees. Pixabay music is commercially usable but has no music API and can trigger Content ID claims. FMA and Jamendo are per-track Creative Commons, and Jamendo's API is non-commercial only. Instagram's own Sound Collection is the safest free option but can only be added inside Instagram.

### Cited Findings

**Epidemic Sound MCP**
- Launched in Claude's connector directory on Aug 31 / Sep 1, 2026. Users can "search Epidemic Sound's full catalog, preview and download tracks, and create recuts, loops, and stems directly inside Claude, using their existing subscription." Search can be driven by "a brief, a mood, a BPM, a genre, a key, an instrument, a reference track" — [Epidemic Sound press release](https://corporate.epidemicsound.com/press-and-media/press-releases/2026/epidemic-sound-launches-mcp-connector-in-claudes-directory).
- Catalog: 55,000+ tracks and 250,000 sound effects. "Ask for an exact length, and the MCP Server shapes the track to it." Works with Claude Desktop, Claude Code, ChatGPT, Cursor and Codex — [Epidemic blog](https://www.epidemicsound.com/blog/mcp-server); [tools page](https://www.epidemicsound.com/tools/mcp) (example: "A 47-second version with the chorus at 0:15").
- Official tool list:
  - Search: `SearchRecordings` (filters for BPM, mood, duration, instruments, key, vocals, plus sorting), `SearchSimilarToRecording`, `SearchExternalReferences` (resolves a Spotify reference to find the closest Epidemic Sound match)
  - SFX: `SearchSoundEffects`, `SearchSimilarToSoundEffect`
  - Editing: `EditRecording`, `PollEditRecordingJob` ("May not be available on all connections (e.g. OAuth)"), `DownloadRecordingEdit`
  - Downloads: `DownloadRecording` (full track or individual stems), `DownloadSoundEffect` (MP3/WAV)
  - Voiceover tools, which are **not** in the Claude directory connector
  — [Epidemic developer docs (MCP)](https://developers.epidemicsound.com/docs/mcp)
- Authentication: OAuth only for allowlisted clients (Claude, Cursor). For custom apps, each end user needs their own Epidemic account and API key; keys last 1 year and "must never be shipped to" a browser. In Claude Code, OAuth is "not yet supported", so use an API key header. The directory connector is, however, automatically available in Claude Code — [Epidemic developer docs (MCP)](https://developers.epidemicsound.com/docs/mcp).
- The MCP server has its own Software License Agreement. The separate Partner API free tier allows "up to 50 downloads and no commercial licence" — [Epidemic developer docs](https://developers.epidemicsound.com/docs/); [MCP terms link](https://www.epidemicsound.com/policy/epidemic-sound-mcp-server-software-license-agreement/).
- `EditRecording` parameters, observed in this session's connected tool schema (consistent with the docs above):
  - `targetDurationMs` (max 300,000 ms)
  - `forceDuration` (exact length)
  - `loopable`
  - `preferenceRegions` (PREFER/AVOID time ranges)
  - `requiredRegionsAtOffsets` (place a source region at a given offset in the edit, i.e. anchor the drop or chorus)
  - `maxResults`, `skipStems`, MP3/WAV output
  — [Epidemic developer docs (MCP)](https://developers.epidemicsound.com/docs/mcp) (parameter names from the live tool schema in this session)
- **Live test in this session (2026-10-28):** `SearchRecordings` with term "upbeat summer travel adventure", BPM 110–130, no vocals, returned 500 matches.
  - The top 3 had BPMs of 114/112/118 and durations of 174–204 s.
  - Each returned 4 stems (DRUMS/BASS/MELODY/INSTRUMENTS), mood tags (happy/hopeful/dreamy), a low-quality MP3 preview URL and a **waveform JSON URL**.
  - No beat or downbeat timestamps were returned — [Epidemic developer docs (MCP)](https://developers.epidemicsound.com/docs/mcp) (observed via the connected MCP tool).
- **Plan coverage:** the Creator Plan is "for non-commercial users" publishing on YouTube, Facebook, **Instagram**, TikTok and Twitch, with one linked account per platform. Content published while subscribed stays covered after cancelling. TikTok limits in-app music to 60 s, so add music in an external editor — [Epidemic Help: Creator Plan](https://help.epidemicsound.com/hc/en-us/articles/26247405706386-Creator-Plan). The catalog is marketed as "fully licensed for commercial use" for brands, on business plans — [Epidemic blog](https://www.epidemicsound.com/blog/brands-using-music-on-social-media).

**Free alternatives**
- **Instagram itself:** the licensed music library "is intended for personal, non-commercial use", and some business accounts are restricted. Instagram's **Sound Collection** (14,000+ royalty-free songs and sounds) is "safe to use in Reels" and usable for commercial purposes, including ads — [Instagram Help](https://help.instagram.com/402084904469945?helpref=faq_content). Licensed audio must be attributed to the artist and track — [Instagram Help](https://help.instagram.com/329208821595430/).
- **Pixabay Music:**
  - The Content License allows free use, commercial use, no attribution, and modification. It prohibits "Standalone" redistribution — [Pixabay license summary](https://pixabay.com/service/license-summary); [Pixabay Terms](https://pixabay.com/service/terms/).
  - Some contributors register their tracks with Content ID, so "automated claims" can happen "even when the track is used legally" — [Pixabay FAQ](https://pixabay.com/service/faq).
  - The **Pixabay API only covers images and videos**; there is no music endpoint — [Pixabay API docs](https://pixabay.com/api/docs/).
- **Free Music Archive:**
  - Most tracks are under various Creative Commons licenses. Each track's license is shown on its page, and users must check it — [FMA Terms](https://freemusicarchive.org/terms_of_use); [FMA FAQ](https://freemusicarchive.org/faq).
  - FMA "cannot address Content ID claims" — [FMA FAQ](https://freemusicarchive.org/faq).
  - Some tracks use the "FMA License", which grants only "personal, non-commercial use" — [FMA License](https://freemusicarchive.org/FMA_Licenselegalcode).
- **Jamendo:** the API "may be used freely for non-commercial uses"; commercial use requires contacting licensing@jamendo.com — [Jamendo API Terms](https://devportal.jamendo.com/api_terms_of_use).
- **YouTube Audio Library:** "copyright-safe" and won't be Content-ID-claimed on YouTube. CC-licensed tracks need attribution in the description. YouTube notes it "can't give legal guidance, including guidance on issues with music that can occur off the platform" — [YouTube Help](https://support.google.com/youtube/answer/3376882?hl=en).
- **Freesound (SFX):** community MCP servers (johnkimdw/freesound-mcp-server, MIT; MuShan-bit/freesound-mcp) search and download CC-licensed sounds, with the license returned per sound. They need a free API key — [GitHub](https://github.com/johnkimdw/freesound-mcp-server); [mcp.film](https://mcp.film/mcps/freesound); [GitHub](https://github.com/MuShan-bit/freesound-mcp).

### Inferences
- For a Claude-based director, Epidemic's `EditRecording` with `targetDurationMs` ≤ 60,000 and `requiredRegionsAtOffsets` (put the drop or hook on the reveal shot) removes the hardest audio step: a musically clean cut to length. The agent still needs local beat and downbeat detection (e.g. librosa) on the **edited** file to place cuts, because the API returns only a single BPM value.
- The stems (DRUMS) could make beat and onset detection more reliable than running it on the full mix.
- Because licensing follows the user's own Epidemic subscription and account linking, the agent should ask about or record the user's plan type (Creator = non-commercial). It should flag branded or sponsored travel reels as needing a commercial plan.
- A free fallback chain might be: user-supplied music → Pixabay music (manual download, no API; warn about possible claims) → CC-BY tracks from FMA with attribution text generated for the caption. Alternatively, export without music and let the user add a Sound Collection track inside Instagram.
- YouTube Audio Library tracks should not be presented as cleared for Instagram. YouTube's guarantee covers only YouTube's Content ID.

### Gaps
- I did not read the full text of the Epidemic MCP Server Software License Agreement, so whether MCP-generated edits carry any extra restrictions is unconfirmed.
- I did not verify whether `PollEditRecordingJob` is available on the Claude directory (OAuth) connector. The docs say it "may not be available" on OAuth.
- I did not check whether Epidemic's waveform JSON contains enough resolution to derive onsets.
- No authoritative source was found stating whether YouTube Audio Library "standard license" tracks may be used on Instagram.
- I did not check whether Meta's Rights Manager flags Pixabay or FMA tracks on Instagram (the sources discuss YouTube Content ID).

## Key Question 3: Which projects handle beat-sync, 9:16, ≤60 s, and transitions?

### Takeaway
Only the small montage-focused projects do true beat-synced cutting of user media. These are beat-synced-edit, beat-sync-video-editor, Montage AI, BeatSync Engine and the Remotion MCP server by ivalenzuela (beat analysis only); VideoAgent claims it. Almost every project supports 9:16. Transitions are basic everywhere: xfade/fade, white flash, punch-ins. None enforces a ≤60 s cap natively, but every one can trim to a target duration.

### Cited Findings
| Project | Beat-sync | 9:16 | Duration control | Transitions / effects | User photos+clips | Source |
|---|---|---|---|---|---|---|
| MoneyPrinterTurbo | Not claimed (BGM is a background layer) | Yes, 1080×1920 | Script/clip-length driven | Not highlighted | Yes (local images/videos) | [README](https://github.com/harry0703/MoneyPrinterTurbo) |
| ShortGPT | Not claimed | Yes (per tracker) | — | — | Mainly stock | [README](https://github.com/RayVentura/ShortGPT); [VisLane](https://vislane.com/en/open-source/shortgpt) |
| short-video-maker | Not claimed; music by mood | Designed for TikTok/Reels/Shorts | — | — | Pexels backgrounds | [README](https://github.com/gyoridavid/short-video-maker) |
| VideoAgent (HKUDS) | Claimed ("Beat-synced Edits ✅") | Not stated | — | SFX tools | — | [README](https://github.com/HKUDS/VideoAgent) |
| beat-synced-edit | Yes (librosa beats + energy) | Yes (`vertical_style.py`) | Can cut to chorus/section | White flash, punch-in, speed ramp, shake, RGB split, grade | Yes (clips and stills) | [README](https://github.com/ZiadAbdelkarim/beat-synced-edit) |
| beat-sync-video-editor | Yes, human-audited beat/lyric map | Any (padding preserves frames) | Target duration supported | Retiming push-ins, gentle fades | Yes (photos + videos) | [README](https://github.com/330312/beat-sync-video-editor) |
| vlog-auto-edit skill | Not beat-sync (narrative-led, BGM added) | Not stated | — | Titles; advises concat over xfade chains | Yes (travel footage) | [README](https://github.com/znyupup/ai-video-editing-skill) |
| Montage AI | Yes | Yes (smart reframe) | "Shorts Studio" | Color presets, film grain, captions | Clips | [README](https://github.com/mfahsold/montage-ai); [site](https://mfahsold.github.io/montage-ai/) |
| BeatSync Engine | Yes (beat grid, song structure, energy-wave density) | Not stated | — | Frame-locked cuts | Video clips | [README](https://github.com/Merserk/BeatSync-Engine) |
| Immich Memories | "Smart cuts" with music (beat-sync not stated) | Not stated | Month/trip/person scoping | Titles, maps, Ken Burns | Yes (photos, videos, Live Photos) | [GitHub](https://github.com/sam-dumont/immich-video-memory-generator) |
| ivalenzuela/remotion-mcp-server | Beat analysis (BPM, beat boundaries, RMS energy) | Remotion (any size) | Programmatic | Remotion components | Programmatic | [README](https://github.com/ivalenzuela/remotion-mcp-server) |
| video-audio-mcp | No | Yes (`change_aspect_ratio`) | `trim_video` | Concat with transitions, B-roll fade, text overlay | Any files | [README](https://github.com/misbahsy/video-audio-mcp) |
| Remotion | Not built in (needs audio analysis) | Any composition size | Frame-exact | Official Transitions library | Any | [Remotion](https://github.com/remotion-dev/remotion) |
| HyperFrames | Not stated | Must be requested (default 1920×1080) | Frame-exact render | HTML/CSS/JS | Any | [docs](https://hyperframes.heygen.com/prompting/overview) |

- Epidemic Sound `EditRecording` can produce music at an exact length (e.g. ≤60 s) with anchored regions — [Epidemic developer docs (MCP)](https://developers.epidemicsound.com/docs/mcp).
- Practical rendering caveat: chaining ffmpeg `xfade` filters drops frames, so use concat instead. Overlaying a single-frame PNG with `shortest=1` truncates the video — [vlog-auto-edit README](https://github.com/znyupup/ai-video-editing-skill).

### Inferences
- The best technical template for "beat-sync + 9:16 + ≤60 s + transitions" is the beat-synced-edit pipeline (beat_map → clip_tag → plan_edit → render). Add the human-approval checkpoint from beat-sync-video-editor and vlog-auto-edit, and use Epidemic `EditRecording` to fix the music length first.
- Energy-aware cut density (BeatSync Engine's "calm holds longer, drops cut faster") and "don't cut uniformly on every beat" (330312) are the main craft rules to encode in the director's planning prompt.

### Gaps
- None of these was tested hands-on, so output quality is unverified.
- I found no project that explicitly enforces Instagram's duration or safe-zone constraints (UI overlays at top and bottom of a 9:16 frame).

## Key Question 4: What should be built versus reused?

### Takeaway
Reuse commodity layers: ffmpeg/MoviePy (or Remotion/HyperFrames) for rendering, librosa and PySceneDetect for analysis, the Epidemic Sound MCP for music search, length-editing and stems, and Freesound MCP for SFX. Build the director layer: shot selection and scoring of user photos and clips, a beat- and energy-aware edit plan (EDL), the narrative arc for a travel story, a review/approval loop, and Instagram-specific packaging. The open-source landscape has no mature, permissively licensed project that does this end to end for user media.

### Cited Findings
- Reusable analysis building blocks are proven in practice: librosa beat/energy maps and PySceneDetect scene and motion tagging, matched by an energy-peak planner — [beat-synced-edit](https://github.com/ZiadAbdelkarim/beat-synced-edit).
- A JSON style-template plus optional LLM "Creative Director" design that works without an LLM for the core beat-sync — [Montage AI](https://github.com/mfahsold/montage-ai).
- A plan → human preview dashboard → render workflow, with an LLM edit-plan prompt template and example `clip_analysis.json` / `edit_plan.json` schemas — [vlog-auto-edit](https://github.com/znyupup/ai-video-editing-skill).
- A human-approved beat map before rendering, plus explicit craft rules — [beat-sync-video-editor](https://github.com/330312/beat-sync-video-editor).
- Photo handling (Ken Burns / face-aware pan, Live Photos) and the "review every shot, nothing re-chosen behind your back" revision model — [Immich Memories](https://sam-dumont.github.io/immich-video-memory-generator/).
- 9:16 rendering, subtitles, TTS and direct Instagram publishing plumbing (MIT) — [MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo).
- Remotion's official agent skills and Transitions library suit animated titles and maps. The license is free only for teams of 3 or fewer — [Remotion skills](https://www.remotion.dev/docs/ai/skills); [license](https://www.remotion.dev/license). HyperFrames is a permissive Apache-2.0 alternative designed for agent-written HTML video — [hyperframes.dev](https://www.hyperframes.dev/).
- Optional pro handoff: OTIO/EDL export (Montage AI, Video Jungle MCP) or DaVinci Resolve MCP — [Montage AI](https://github.com/mfahsold/montage-ai); [video-editing-mcp](https://github.com/burningion/video-editing-mcp); [davinci-resolve-mcp](https://github.com/samuelgursky/davinci-resolve-mcp).

### Inferences
- **Reuse (as libraries or tools):**
  - ffmpeg (directly, or through a thin custom MCP/skill; the existing FFmpeg MCPs are small or stale, so wrapping your own small set of ffmpeg calls is likely more reliable)
  - librosa (beats/onsets/energy, ideally on the Epidemic DRUMS stem)
  - PySceneDetect
  - Epidemic Sound MCP (search, EditRecording to the target length, DownloadRecording/stems)
  - Freesound MCP (whooshes and ambience)
  - optionally Remotion or HyperFrames for title cards and map animations
- **Learn from, don't vendor:** beat-synced-edit (planner logic, effects cookbook), beat-sync-video-editor (craft rules), vlog-auto-edit (pitfalls list, approval dashboard), BeatSync Engine (energy-wave density, song-structure detection; AGPL, so do not copy code), Immich Memories (photo motion, trip scoping, review loop).
- **Build:**
  1. Media ingest and scoring of user photos and clips: EXIF time/GPS for trip chronology and locations; vision-model tagging of scenery, people, food and motion; quality and blur filters.
  2. A director/planner that maps shots to song sections and beats, following an arc of hook in the first 1–3 s → journey → climax on the drop → outro.
  3. A deterministic EDL JSON schema as the contract between Claude's plan and the renderer.
  4. A renderer for 1080×1920, ≤60 s, with Ken Burns for stills and a curated small transition set aligned to beats.
  5. A preview/approval step.
  6. License bookkeeping: the track ID, the plan type, and attribution text for CC tracks.
- Avoid building on high-star but stale or SaaS-bound projects (ShortGPT, short-video-maker, Director/VideoDB, Video Jungle MCP) when they would be core dependencies.

### Gaps
- No benchmark or user study compares the output quality of these montage tools.
- I did not evaluate open-source aesthetic or "best shot" scoring models for photo selection; this needs separate research.
- Instagram Reels technical specs (max length, safe zones, bitrate) were outside this note's sources.
