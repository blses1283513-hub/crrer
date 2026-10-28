# Open-source video editing / compositing engines and transition libraries for a Python-driven 9:16 travel reel pipeline

Research date: 2026-10-28. Star counts and push dates come from the GitHub REST API (`api.github.com/repos/...`) as cached by the fetch tool. Each snapshot is dated 2026-09-23 to 2026-10-28 unless noted otherwise. Counts are approximate and move daily. The `gh` CLI was blocked in this session, so the data came through the public API via web fetch.

## Q1. Star counts, recent activity and licenses for each candidate

### Takeaway
FFmpeg (about 65.8k stars, LGPL/GPL, 9.0.2 released 2026-09-18) and Remotion (about 67.4k stars, source-available, v4.0.538 released 2026-10-22) are the two most-starred projects. Remotion is not OSI open source for companies with 4 or more people. MoviePy has about 15.0k stars and is MIT, but its last release, v2.2.1, came out in May 2025. The rest of the Python-native options (PyAV, VidGear, typed-ffmpeg) are active, but they are FFmpeg wrappers or I/O layers, not editors. Several JS-side options (editly, ffmpeg-gl-transition, Revideo, FFCreator) have stalled.

### Cited Findings

**Ranked summary table (stars as of the API snapshot date)**

| # | Tool | Stars | License | Latest release / last push | Language / runtime |
|---|---|---|---|---|---|
| 1 | Remotion | 67,446 | Custom "Remotion License" (GitHub reports NOASSERTION) | v4.0.538 on 2026-10-22; pushed 2026-10-25 | TypeScript/React, Node + headless Chrome |
| 2 | FFmpeg (GitHub mirror) | 65,775 | LGPL-2.1+ core with optional GPL parts | 9.0.2 "Lei" on 2026-09-18 (8.1.3 on 2026-09-21); pushed 2026-10-25 | C, CLI |
| 3 | Manim (Community) | 41,790 | MIT | pushed 2026-10-20 | Python (math animation, not an NLE) |
| 4 | Motion Canvas | 19,413 | MIT | pushed 2026-07-02 | TypeScript |
| 5 | Shotcut (MLT GUI) | 15,499 | GPL-3.0 | pushed 2026-10-25 | C++ GUI on MLT |
| 6 | MoviePy | 15,028 | MIT | v2.2.1 on 2025-05-21; pushed 2026-08-26 | Python |
| 7 | ffmpeg-python | 11,015 | Apache-2.0 | pushed 2024-08-04 (stale); 525 open issues | Python |
| 8 | auto-editor | 5,554 | Unlicense (public domain) | 31.7.2 on 2026-10-03 | Nim (formerly Python) |
| 9 | editly | 5,524 | MIT | v0.15.0-rc.1 on 2025-01-19; pushed 2025-05-12 | TypeScript/Node, ESM only |
| 10 | VidGear | 3,725 | Apache-2.0 | v0.3.6 on 2026-10-26 | Python |
| 11 | Revideo | ~3.5k (page snapshot Nov 2025) | MIT | last commit 2025-05-09 | TypeScript (Motion Canvas fork) |
| 12 | PyAV | 3,306 | BSD-3-Clause | v19.0.2 on 2026-10-21 | Python/Cython |
| 13 | FFCreator | 3,160 | MIT | pushed 2024-12-19 | Node |
| 14 | gl-transitions | 2,203 | MIT (each transition MIT except two BSD) | pushed 2026-10-25 | GLSL plus ports |
| 15 | MLT framework | 1,862 | LGPL-2.1 | v7.42.0 on 2026-10-03; pushed 2026-10-07 | C, `melt` CLI |
| 16 | libopenshot | 1,580 | LGPL-3.0, with commercial licenses available | v1.0.1 on 2026-09-27 | C++ with Python bindings |
| 17 | Diffusion Studio Core | 1,245 | MPL-2.0 | pushed 2025-11-18 | TypeScript (browser) |
| 18 | ffmpeg-concat | 989 | API reports null; README says MIT | pushed 2026-01-24 | Node |
| 19 | ffmpeg-gl-transition | 719 (page snapshot 2026-09-24) | API reports null; README says MIT | pushed 2024-07-23 | C FFmpeg filter patch |
| 20 | vidpy (MLT Python wrapper) | 132 | n/a | n/a | Python |
| 21 | xfade-easing | 125 | MIT | v3.6.6 on 2026-08-10; pushed 2026-09-09 | C/shell for FFmpeg |
| 22 | movielite | 73 | MIT | pushed 2026-07-23 | Python + Numba |

Sources by row:

- FFmpeg: 65,775 stars, pushed 2026-10-25. GitHub's license field reads "Other". [GitHub API](https://api.github.com/repos/FFmpeg/FFmpeg). The README says "FFmpeg codebase is mainly LGPL-licensed with optional components licensed under GPL". [GitHub](https://github.com/FFmpeg/FFmpeg)
- FFmpeg 9.0.2 "Lei" came out 2026-09-18 and is the latest stable release. 8.1.3 "Hoare" came out 2026-09-21 and 8.0.3 on 2026-06-18. [ffmpeg.org download](https://ffmpeg.org/download.html)
- MoviePy: 15,028 stars, MIT, pushed 2026-08-26. [GitHub API](https://api.github.com/repos/Zulko/moviepy). Latest GitHub release is v2.2.1, created 2025-05-21. [GitHub API releases](https://api.github.com/repos/Zulko/moviepy/releases/latest). PyPI also lists 2.2.1 (May 21, 2025) as the latest. [PyPI](https://pypi.org/project/moviepy/)
- MLT: 1,862 stars, LGPL-2.1, pushed 2026-10-07. [GitHub API](https://api.github.com/repos/mltframework/mlt). Release v7.42.0 was published 2026-10-03. [GitHub API releases](https://api.github.com/repos/mltframework/mlt/releases/latest)
- Shotcut: 15,499 stars, GPL-3.0. [GitHub API](https://api.github.com/repos/mltframework/shotcut)
- Remotion: 67,446 stars, license "Other/NOASSERTION", pushed 2026-10-25. [GitHub API](https://api.github.com/repos/remotion-dev/remotion). v4.0.538 was published 2026-10-22. [GitHub API releases](https://api.github.com/repos/remotion-dev/remotion/releases/latest)
- editly: 5,524 stars, MIT, last push 2025-05-12. [GitHub API](https://api.github.com/repos/mifi/editly). Latest release is v0.15.0-rc.1 (2025-01-19). Its notes begin "After a couple years of inactivity, editly now has a new…" [GitHub API releases](https://api.github.com/repos/mifi/editly/releases/latest)
- auto-editor: 5,554 stars, Unlicense, primary language Nim. [GitHub API](https://api.github.com/repos/WyattBlue/auto-editor). Release 31.7.2 came out 2026-10-03 with prebuilt linux-x86_64, aarch64 and armv7 binaries. [GitHub API releases](https://api.github.com/repos/WyattBlue/auto-editor/releases/latest). The README describes it as an application that edits "by analyzing a variety of methods, most notably audio loudness". [GitHub](https://github.com/WyattBlue/auto-editor)
- gl-transitions: 2,203 stars, pushed 2026-10-25. [GitHub API](https://api.github.com/repos/gl-transitions/gl-transitions). The project describes "100+ transitions… translated to SkSL, GLSL ES 3.00, WGSL, Metal and AGSL". Licensing is "MIT… all are MIT except two under BSD licenses". [GitHub](https://github.com/gl-transitions/gl-transitions)
- ffmpeg-gl-transition: 719 stars. [GitHub page](https://github.com/transitive-bullshit/ffmpeg-gl-transition). Last push was 2024-07-23 and there are 36 open issues. [GitHub API](https://api.github.com/repos/transitive-bullshit/ffmpeg-gl-transition)
- ffmpeg-concat: 989 stars, last push 2026-01-24, 52 open issues. [GitHub API](https://api.github.com/repos/transitive-bullshit/ffmpeg-concat)
- xfade-easing: 125 stars, MIT. [GitHub API](https://api.github.com/repos/scriptituk/xfade-easing). v3.6.6 came out 2026-08-10. [GitHub API releases](https://api.github.com/repos/scriptituk/xfade-easing/releases/latest)
- VidGear: 3,725 stars, Apache-2.0. [GitHub API](https://api.github.com/repos/abhiTronix/vidgear). v0.3.6 came out 2026-10-26. [GitHub API releases](https://api.github.com/repos/abhiTronix/vidgear/releases/latest)
- PyAV: 3,306 stars, BSD-3. [GitHub API](https://api.github.com/repos/PyAV-Org/PyAV). v19.0.2 came out 2026-10-21 and ships abi3 wheels. [GitHub API releases](https://api.github.com/repos/PyAV-Org/PyAV/releases/latest). The README says "This release supports FFmpeg 9.x". [GitHub](https://github.com/PyAV-Org/PyAV)
- ffmpeg-python: 11,015 stars, Apache-2.0, last push 2024-08-04, 525 open issues. [GitHub API](https://api.github.com/repos/kkroening/ffmpeg-python)
- typed-ffmpeg: MIT. [GitHub API](https://api.github.com/repos/lucemia/typed-ffmpeg). The latest PyPI release is dated Aug 22, 2026. A separate `typed-ffmpeg-v8` package targets "FFmpeg 8.x". [PyPI typed-ffmpeg](https://pypi.org/project/typed-ffmpeg); [PyPI typed-ffmpeg-v8](https://pypi.org/project/typed-ffmpeg-v8)
- libopenshot: 1,580 stars, LGPL-3.0. [GitHub API](https://api.github.com/repos/OpenShot/libopenshot). v1.0.1 came out 2026-09-27. [GitHub API releases](https://api.github.com/repos/OpenShot/libopenshot/releases/latest). The README says commercial licenses are available. [GitHub](https://github.com/OpenShot/libopenshot)
- Motion Canvas: 19,413 stars, MIT. [GitHub API](https://api.github.com/repos/motion-canvas/motion-canvas)
- Revideo: 3.5k stars, MIT, last commit May 9, 2025. This comes from a page snapshot dated 2025-11-19. [GitHub](https://github.com/redotvideo/revideo)
- Manim: 41,790 stars, MIT. [GitHub API](https://api.github.com/repos/ManimCommunity/manim)
- FFCreator: 3,160 stars, MIT, last push 2024-12-19. [GitHub API](https://api.github.com/repos/tnfe/FFCreator)
- Diffusion Studio Core: 1,245 stars, MPL-2.0. [GitHub API](https://api.github.com/repos/diffusionstudio/core)
- movielite: 73 stars, MIT. It describes itself as a "Performance-focused Python video editing library. Alternative to MoviePy, powered by Numba". [GitHub API](https://api.github.com/repos/francozanardi/movielite)
- vidpy: 132 stars. [GitHub API](https://api.github.com/repos/antiboredom/vidpy)

**Remotion license terms (not OSI open source)**
- The free license covers "an individual", "a for-profit organization with up to 3 employees", non-profits, and evaluation. Everyone else needs a Company License. The license text also says "In Remotion 5.0, the license will slightly change." [Remotion LICENSE](https://www.remotion.dev/license)
- Company License pricing as of 2026-10-27:
  - "Remotion for Automators" costs $0.01 per render with a $100/mo minimum. It covers batch rendering and automated video products.
  - "Remotion for Creators" costs $25/mo per seat.
  - Enterprise starts at $500/month.

  [remotion.pro/license](https://www.remotion.pro/license)
- The editly README calls Remotion a "React based alternative to editly (not open source)". [editly README](https://raw.githubusercontent.com/mifi/editly/master/README.md)
- `@remotion/transitions` is itself under the "Remotion License". [Remotion docs](https://www.remotion.dev/docs/transitions)

**Shotstack-style (JSON timeline to render) self-hosted alternatives**
- shottower is "An open source, self-hosted implementation of the Shotstack API backend". Its "backend server translate[s] JSON to FFMPEG commands". [GitHub](https://github.com/DblK/shottower)
- CutEngine is a "Self-hosted, Shotstack API v1-compatible video render engine. Hybrid Puppeteer + FFmpeg pipeline", MIT. It claims "Ken Burns effects, transitions, and text overlays" and was "Built for high-volume automated video production". [GitHub](https://github.com/jjjames38/cutengine). The marketing site claims "14 asset types, 20+ transitions". These are vendor claims. [cutengine.dev](https://cutengine.dev/)
- VidAPI is a "Self-hosted Python FastAPI service… Accepts JSON timeline compositions and renders video via Editly, native FFmpeg, or HyperFrames". It positions itself as an alternative to Creatomate/JSON2Video. [GitHub](https://github.com/moshehbenavraham/vidapi)

### Inferences
- Ranking by stars alone is misleading here. Manim and Motion Canvas are animation tools, Shotcut is a GUI, and Remotion is browser-based. Among tools that actually edit or composite video and can be scripted, the order by stars is FFmpeg, then MoviePy, then editly and auto-editor, then MLT.
- On maintenance as of late 2026, the most active projects are FFmpeg, Remotion, MLT, PyAV, VidGear, auto-editor, libopenshot and gl-transitions. Projects to treat as stalled or at risk are editly (last push May 2025), ffmpeg-gl-transition (July 2024), ffmpeg-python (Aug 2024), FFCreator (Dec 2024) and Revideo (May 2025). MoviePy's code is still pushed to, but it has had no release for about 17 months.
- auto-editor is not a compositing engine. It cuts silence and dead air automatically, so it is irrelevant to building a reel unless the pipeline needs to trim talking-head clips.
- The Shotstack-compatible clones (shottower, CutEngine, VidAPI) are small or young projects. I could not retrieve star counts for them, so treat them as references for schema design rather than as dependencies.

### Gaps
- I could not retrieve star counts for typed-ffmpeg, CutEngine, shottower or VidAPI (the API excerpts left them out).
- Revideo's star count dates from November 2025, so a current count is missing.
- The ffmpeg-gl-transition count comes from a page snapshot (2026-09-24), not the API.
- I did not retrieve the exact typed-ffmpeg version number (a PyPI page mentions "4.5" as newer than 1.0.2, but the current version string was not confirmed).

## Q2. Which tools are pip-installable and headless-friendly, and how does performance compare?

### Takeaway
MoviePy, PyAV, VidGear and typed-ffmpeg/ffmpeg-python all install with pip, and they all ultimately need an FFmpeg binary or FFmpeg libraries. MoviePy pipes every frame through Python and numpy. One measured run on a 30-second 1080p template took 86.6 s with MoviePy against 7.5 s with one FFmpeg filtergraph, about 11x slower. MLT/melt (10.2 s) runs headless and close to FFmpeg speed. Remotion (18.2 s) and Revideo (21.8 s) need Node plus headless Chrome. Editly failed to build at all on a current Node.

### Cited Findings
- **Single benchmark (videobycode, measured 2026-08-09, one run each, Apple arm64 Homebrew ffmpeg 8.0.1).** The template was 1920x1080, 30 fps, 30 s, with 3 scenes and a caption bar. Results:

  | Tool | Wall-clock time |
  |---|---|
  | Diffusion Studio Core | 6.4 s, but watermarked and "unsupported" |
  | FFmpeg | 7.5 s |
  | MLT | 10.2 s |
  | Editframe | 17.9 s |
  | Remotion | 18.2 s |
  | Revideo | 21.8 s |
  | MoviePy | 86.6 s |
  | Editly | error, no output |

  The authors caution that browser-based tools include Chrome-launch overhead and that no repeat runs were taken. [videobycode JSON article](https://videobycode.com/articles/generating-video-from-json-schema-payload-and-render/); [videobycode MoviePy vs FFmpeg](https://videobycode.com/articles/automating-video-editing-with-python-moviepy-and-ffmpeg-pipelines)
- In that benchmark, MoviePy and FFmpeg used the same ffmpeg encoder (`FFMPEG_BINARY` was set). The 86.6 s therefore "reflects MoviePy's own composition and pipe-streaming cost". [videobycode](https://videobycode.com/articles/automating-video-editing-with-python-moviepy-and-ffmpeg-pipelines)
- The same article found that MoviePy's installed distribution was 2.2.1 while `moviepy.__version__` reported 2.1.2. Version checks in code can be misleading as a result. [videobycode](https://videobycode.com/articles/automating-video-editing-with-python-moviepy-and-ffmpeg-pipelines)
- MoviePy's own README says it is "slower than using ffmpeg directly due to heavier data import/export operations". It installs with `pip install moviepy`. [PyPI](https://pypi.org/project/moviepy/)
- GitHub issue #2395 is titled "v1 is 10x faster than v2 for this example" and carries a performance label. One commenter reports slow renders "especially when using nested CompositeVideoClips". [GitHub issue](https://github.com/Zulko/moviepy/issues/2395)
- Another commenter blames much of the slowness on "a LOT of redundant 'inspection' going on while rendering", citing issue #2094. [GitHub issue #2231](https://github.com/Zulko/moviepy/issues/2231)
- Editly broke on Node 25. "gl 5.0.3, the version editly 0.14.2 pins, builds its bundled ANGLE… which fails against Node 25's V8 headers". The library "imports gl (headless-gl) unconditionally at module load". The suggested workaround is an older Node with prebuilt gl binaries. [videobycode](https://videobycode.com/articles/generating-video-from-json-schema-payload-and-render/)
- Editly's requirements are Node.js, ffmpeg/ffprobe on PATH, "(Linux) may require some extra steps. See headless-gl", and "Editly is now ESM only". [editly GitHub](https://github.com/mifi/editly)
- Remotion on Linux needs shared libraries for "Chrome Headless Shell". NixOS is not supported because "Remotion ships with its own binaries of Chrome and FFmpeg". [Remotion docs](https://www.remotion.dev/docs/miscellaneous/linux-dependencies)
- Headless MLT use:
  - `melt` renders MLT XML from the command line.
  - The Shotcut forum recommends that scripts "author MLT XML files and then pass those files to Melt". It notes MLT has "SWIG bindings for Python… very little documentation". [Shotcut forum](https://forum.shotcut.org/t/command-line-script-control-for-batching-videos/37732)
  - Kdenlive can export a script plus MLT XML for rendering on a headless server. [salivity guide](https://salivity.github.io/kdenlive/article/render-kdenlive-projects-on-headless-linux-server)
- `mlt-python` 0.1.0 (May 2026) is a "Pure Python library for creating, modifying, and parsing MLT XML files". It has "No MLT framework dependency" and provides `Transitions.luma()` and `Transitions.mix()`. [PyPI mlt-python](https://pypi.org/project/mlt-python)
- PyAV gives "direct and precise access to your media via containers, streams, packets, codecs, and frames". It hands data to and from NumPy/Pillow. [GitHub](https://github.com/PyAV-Org/PyAV)
- VidGear's WriteGear is "a complete, flexible, and robust wrapper around FFmpeg" for writing frames to files. VidGear is a multi-threaded I/O and streaming framework. [GitHub](https://github.com/abhiTronix/vidgear)
- typed-ffmpeg advertises:
  - "Zero Dependencies"
  - "Full type hints for all FFmpeg filters"
  - "JSON serialization" of filter graphs
  - validation and graph visualization
  - a Python 3.10+ requirement

  [PyPI typed-ffmpeg](https://pypi.org/project/typed-ffmpeg); [GitHub](https://github.com/lucemia/typed-ffmpeg)
- ffmpeg-python "works well for simple as well as complex signal graphs", but it has not been pushed since Aug 2024. [GitHub](https://github.com/kkroening/ffmpeg-python); [GitHub API](https://api.github.com/repos/kkroening/ffmpeg-python)
- drawtext text often needs "up to four levels of escaping". The docs recommend `textfile` to avoid this. [FFmpeg filters docs](https://ffmpeg.org/ffmpeg-filters.html)
- Excluded source: a johal.in article cites a "2025 MLPerf Multimedia Benchmark" comparing MoviePy, FFmpeg and DaVinci. I could not verify that benchmark exists, so I treated the article as unreliable and did not use its numbers. [johal.in](https://johal.in/multimedia-python-moviepy-ffmpeg-audio-video-edits-2025)

### Inferences
- For a reel of 60 s or less at 1080x1920 30 fps (at most 1,800 frames), MoviePy's roughly 11x overhead probably means minutes rather than seconds per render, extrapolating from 86.6 s for 30 s at 1080p. That is tolerable for a one-off but painful for an iterative agent loop. FFmpeg should finish in seconds.
- "Headless-friendly" rankings for a Linux Python pipeline:
  - FFmpeg CLI driven by `subprocess` or typed-ffmpeg: best. One static binary and no GPU or display.
  - MLT/melt: good. Needs the apt package, then generate XML from Python.
  - MoviePy: pip-only, easy.
  - Remotion/Revideo: heavier. Node plus Chrome, and a second language.
  - Editly: fragile on modern Node because of native headless-gl.
  - ffmpeg-gl-transition: needs a custom FFmpeg build plus an OpenGL/EGL context.
- PyAV and VidGear are building blocks, not editors. PyAV fits frame-accurate probing or custom per-frame compositing. VidGear's WriteGear fits writing numpy frames to an encoder. Neither offers a timeline or transitions.

### Gaps
- I found no independent benchmark at 1080x1920 portrait resolution, and none that includes Ken Burns (zoompan) cost.
- The benchmark is a single run on one Apple arm64 machine. I found no Linux x86 numbers.
- I did not verify whether `pip install moviepy` bundles an FFmpeg binary via imageio-ffmpeg in v2.2.1. The install docs mention "a custom FFMPEG" option but I did not fetch the details.

## Q3. Which tools give the best transition vocabulary (crossfade, slide/whip, zoom, flash/fade-to-white)?

### Takeaway
Stock FFmpeg `xfade` alone covers almost every reel staple: fade/dissolve, fadewhite (flash), fadeblack, slides, wipes, covers and reveals, zoomin, smooth wipes, squeezes, plus a custom expression mode. It has 58 named transitions plus `custom`. gl-transitions (100+ GLSL effects) is the richest library. On a stock FFmpeg you can reach it through xfade-easing's expression port, which also adds easing curves. A true "whip pan" is not built in anywhere. You have to compose it, for example from a slide plus motion blur.

### Cited Findings
- **FFmpeg xfade built-in transitions**, per the current official docs:
  - `custom`
  - Fades: `fade` (default), `fadeblack`, `fadewhite`, `fadegrays`, `fadefast`, `fadeslow`, `dissolve`, `distance`
  - Wipes: `wipeleft`, `wiperight`, `wipeup`, `wipedown`, `wipetl`, `wipetr`, `wipebl`, `wipebr`
  - Slides: `slideleft`, `slideright`, `slideup`, `slidedown`
  - Smooth wipes: `smoothleft`, `smoothright`, `smoothup`, `smoothdown`
  - Shapes: `circlecrop`, `rectcrop`, `circleopen`, `circleclose`, `vertopen`, `vertclose`, `horzopen`, `horzclose`, `radial`
  - Diagonals: `diagtl`, `diagtr`, `diagbl`, `diagbr`
  - Slices: `hlslice`, `hrslice`, `vuslice`, `vdslice`
  - Winds: `hlwind`, `hrwind`, `vuwind`, `vdwind`
  - Blur, squeeze, zoom and pixel effects: `hblur`, `squeezeh`, `squeezev`, `zoomin`, `pixelize`
  - Covers: `coverleft`, `coverright`, `coverup`, `coverdown`
  - Reveals: `revealleft`, `revealright`, `revealup`, `revealdown`

  [FFmpeg filters docs](https://ffmpeg.org/ffmpeg-filters.html). The trac wiki has an animated gallery of each one. [FFmpeg wiki Xfade](https://trac.ffmpeg.org/wiki/Xfade)
- **xfade constraints and parameters:**
  - "Both inputs must be constant frame-rate and have the same resolution, pixel format, frame rate and timebase."
  - `duration` runs 0–60 s (default 1).
  - `offset` is the start time relative to the first input.
  - `expr` defines custom transitions using variables X, Y, W, H, P (progress), A and B.

  [FFmpeg filters docs](https://ffmpeg.org/ffmpeg-filters.html)
- Chained offsets must account for earlier crossfades: "offset… should not be greater than the duration of the first video minus the duration of the transition". [FFmpeg wiki Xfade](https://trac.ffmpeg.org/wiki/Xfade)
- `xfade_opencl` supports only a subset: fade, wipes and slides, plus custom kernels. [FFmpeg filters docs](https://ffmpeg.org/ffmpeg-filters.html)
- Related FFmpeg building blocks:
  - `zoompan` does Ken Burns. It takes zoom expressions with z (1–10), x/y expressions, d (frames per input image), s (output size) and fps. Its documented example is `zoompan=z='min(zoom+0.0015,1.5)':d=700:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'`.
  - `fade` accepts `color` (default black), so fades to white are possible.
  - `acrossfade` and `afade` crossfade and fade audio, with selectable curves.

  [FFmpeg filters docs](https://ffmpeg.org/ffmpeg-filters.html)
- **xfade-easing** (MIT, v3.6.6) addresses the fact that "the progress rate is linear, starting and stopping abruptly". It has two variants:
  - A *custom-expression* variant that generates `expr` strings for stock ffmpeg.
  - A *custom ffmpeg* variant that adds `easing=` (CSS easings including `cubic-bezier()`) and `reverse=` options.

  "Most of the transitions at gl-transitions… have been transpiled into native C transitions… and custom expressions". Examples include gl_Bars, gl_BookFlip, gl_Bounce, gl_CrossOut, gl_Diamond, gl_DirectionalScaled, gl_StageCurtains, gl_PolkaDotsCurtain and gl_perlin. [GitHub](https://github.com/scriptituk/xfade-easing)
- xfade-easing performance caveat: in custom-expression mode "most GL transitions take around ½ minute for SD and 1½ for HD, however some take considerably longer". [GitHub](https://github.com/scriptituk/xfade-easing)
- **gl-transitions** is "An open collection of 100+ transitions between two images". It is used by editly, ffmpeg-gl-transition and xfade-easing, and has an official `@gl-transitions/remotion` package. [GitHub](https://github.com/gl-transitions/gl-transitions)
- **ffmpeg-gl-transition** is a native FFmpeg filter for GLSL transitions, for example crosswarp. It "requires building ffmpeg from source". [GitHub](https://github.com/transitive-bullshit/ffmpeg-gl-transition); [xfade-easing README](https://github.com/scriptituk/xfade-easing)
- **editly** transitions: "transition.name can be any of gl-transitions, or any of the following: directional-left, directional-right, directional-up, directional-down, random or dummy". Editly also has "Automatic audio crossfading" and "Automatic audio ducking and normalization", and it outputs any aspect ratio, including "Instagram story (9:16)". [editly README](https://raw.githubusercontent.com/mifi/editly/master/README.md)
- **MoviePy v2** effects include CrossFadeIn, CrossFadeOut, SlideIn ("Makes the clip arrive from one side of the screen"), Resize, Freeze, MirrorX/Y and AccelDecel. [MoviePy fx reference](https://zulko.github.io/moviepy/reference/reference/moviepy.video.fx.html)
- **MLT** uses the `luma` transition: "a video wipe processor that takes a greyscale bitmap for the wipe definition. When one does not specify a bitmap, luma performs a dissolve". [MLT XML docs](https://www.mltframework.org/docs/mltxml). Audio cross-fades use `-mixer mix`, for example `melt foo.dv bar.dv -mix 25 -mixer luma -mixer mix:-1`. [MLT FAQ](https://mltframework.github.io/mlt_web/faq)
- **Remotion** has `<TransitionSeries>` with presentations such as `slide()` ("the entering slide pushes out the exiting slide"). `cube()` is "a paid item". [Remotion slide](https://www.remotion.dev/docs/transitions/presentations/slide); [Remotion cube](https://www.remotion.dev/docs/transitions/presentations/cube)

### Inferences
Mapping the four required transition families to stock FFmpeg xfade:

- **Crossfade:** `fade` or `dissolve`.
- **Slide/whip:** `slideleft`/`slideright`/`slideup`/`slidedown`, `coverX`/`revealX` and `smoothX`. A whip feel could plausibly come from a short `slideleft` (about 0.2–0.3 s) combined with `hblur`, or from a custom `expr` that adds horizontal blur. I found no built-in "whip".
- **Zoom:** `zoomin` for the transition, plus `zoompan` for Ken Burns on photos.
- **Flash:** `fadewhite`, or a short `fade=...:color=white`.

Comparing vocabularies:

- Remotion's free presentation set is smaller than xfade's 58 names. The extra or premium ones (cube) are paid.
- MoviePy's built-in set is the thinnest: crossfade and slide-in only. Everything else must be hand-written as per-frame numpy functions, which compounds its speed problem.
- gl-transitions gives the widest creative range. For a Python/FFmpeg pipeline, the practical route on stock FFmpeg is xfade-easing's expression output. That costs heavy CPU per transition, but with roughly 10–15 transitions in a 60 s reel the cost is bounded. The alternative is a custom FFmpeg build, either xfade-easing's patched build or ffmpeg-gl-transition with OpenGL.

### Gaps
- I did not fetch Remotion's full list of free presentations. Only slide (free) and cube (paid) were confirmed. From memory there are also fade, wipe, flip, clockWipe, iris and none, but this is unverified.
- I did not verify whether editly image layers support built-in Ken Burns (`zoomDirection`) in the current version. The README excerpt retrieved did not show it.
- I found no source that measures `zoompan` jitter or smoothness. Practitioners often pre-upscale stills before zoompan to reduce sub-pixel jitter, but I found no authoritative source for this.

## Q4. Recommendation: one primary engine plus a fallback

### Takeaway
**Primary: FFmpeg (8.x/9.x), driven from Python.** Generate a single `-filter_complex` graph, either as plain strings via `subprocess` or with typed-ffmpeg for typed, JSON-serializable graphs. Build it from `trim`/`setpts`, `zoompan`, `xfade`, `drawtext`/subtitles, and `acrossfade`/`afade` plus audio mixing. Output 1080x1920 directly. Add xfade-easing expressions where the reel needs eased or gl-style transitions.

**Fallback: MoviePy v2 (MIT, pip-only)** for anything awkward to express as a filtergraph: custom per-frame effects, PIL-rendered text styling, debugging. Accept that it renders roughly 10x slower. **MLT/melt** is the alternative fallback if an NLE-style XML timeline (luma wipes, editable in Shotcut/Kdenlive) is preferred. Avoid Remotion unless the team accepts Node/Chrome and the company-license terms.

### Cited Findings
- In one benchmark FFmpeg was the fastest non-watermarked engine (7.5 s for 30 s at 1080p). MLT followed at 10.2 s and MoviePy took 86.6 s. [videobycode](https://videobycode.com/articles/generating-video-from-json-schema-payload-and-render/)
- That benchmark's FFmpeg run used one filter graph with `enable` expressions to switch overlays "at the right timestamp instead of cutting three files and joining them with concat". [videobycode](https://videobycode.com/articles/automating-video-editing-with-python-moviepy-and-ffmpeg-pipelines)
- The same source concludes that keeping logic in MoviePy is worth it when "the composition needs to branch on data before a single frame renders". [videobycode](https://videobycode.com/articles/automating-video-editing-with-python-moviepy-and-ffmpeg-pipelines)
- xfade offers 58 named transitions plus custom expressions, and zoompan provides Ken Burns. [FFmpeg filters docs](https://ffmpeg.org/ffmpeg-filters.html)
- MoviePy v2 breaking changes to plan for:
  - `.set_` methods became `.with_`, which work out-of-place.
  - Effects became classes applied via `with_effects()`.
  - `moviepy.editor` was removed.
  - It "dropp[ed]… ImageMagick, PyGame, OpenCV, scipy" in favor of Pillow, so `TextClip` now uses Pillow and not ImageMagick.
  - Python 2 support was dropped.

  [MoviePy v2 migration guide](https://zulko.github.io/moviepy/getting_started/updating_to_v2.html)
- MoviePy says v1 "is no longer maintained". [GitHub](https://github.com/Zulko/moviepy)
- Shotcut users "author MLT XML files and then pass those files to Melt". [Shotcut forum](https://forum.shotcut.org/t/command-line-script-control-for-batching-videos/37732)
- Remotion requires a paid Company License for for-profit organizations with more than 3 employees ($100/mo minimum for automation). [remotion.pro](https://www.remotion.pro/license)

### Inferences
- Engineering notes for the FFmpeg-primary design:
  1. Normalize every input to the same size (scale plus crop or pad to 1080x1920), the same fps (for example 30), the same pixel format (`format=yuv420p`) and the same timebase (`settb`) before `xfade`. xfade rejects mismatched inputs.
  2. Turn photos into fixed-length CFR clips with `zoompan` (`d` = seconds × fps, `s=1080x1920`, `fps=30`).
  3. Compute each xfade `offset` cumulatively in Python as the sum of earlier clip durations minus the earlier transition durations.
  4. Burn text with `drawtext` using `textfile=`, which avoids the escaping problem, or render captions as ASS subtitles.
  5. Mix the music bed and clip audio with `afade` and `acrossfade`, plus a mixing filter. The `amix` filter is standard, but I did not fetch its docs here.
  6. Encode with libx264, `-pix_fmt yuv420p` and `-movflags +faststart`.
- typed-ffmpeg looks preferable to ffmpeg-python as a Python graph builder, because ffmpeg-python has been stale since 2024 while typed-ffmpeg released in Aug 2026 with FFmpeg 8 typing and JSON serialization. Raw string generation with `subprocess` is equally valid and has no dependency.
- Use PyAV only if the pipeline needs frame-accurate probing or decoding inside Python, for example to pick the best frames from clips. Use ffprobe via subprocess for simple metadata.
- Licensing: an FFmpeg build that uses libx264 is GPL. That is fine for an internal pipeline that runs FFmpeg as a separate process, but worth noting if the engine is ever shipped to others. The LGPL/GPL split comes from the FFmpeg README.

### Gaps
- I found no head-to-head benchmark of MLT against FFmpeg for photo-heavy (Ken Burns) timelines in portrait 1080x1920.
- I did not test xfade-easing's expression-mode cost at 1080x1920 for a 0.3–0.5 s transition. The README's timing table is for its own test setup.
