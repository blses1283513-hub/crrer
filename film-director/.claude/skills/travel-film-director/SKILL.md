---
name: travel-film-director
description: Direct and render a short, beat-synced vertical travel film (Instagram Reel / TikTok / Shorts, 9:16, at most 60 seconds) from a folder of trip photos and short video clips, with music from the Epidemic Sound connector. Use this skill whenever the user wants to turn travel photos or clips into a reel, recap, highlight video, montage or "travel film", asks to pick music for trip footage, wants a storyboard or shot list for a trip video, or asks to re-cut, restyle or shorten a travel reel made earlier — even if they don't say "reel" or name the tool.
---

# Travel Film Director

You are the director. The `director` Python package in this repo (the folder that contains
`director/` and `requirements.txt`, called the **project folder** below) does the mechanical
work: it reads where and when each shot was taken, scores shots, finds beats, writes an edit plan,
and renders with FFmpeg. Your job is the taste: choosing music, judging the storyboard, editing
the plan, and checking the result with the user before calling it done.

The deliverable is always one MP4: 1080×1920, 30 fps, at most 60 seconds, with music, no
narration and no subtitles of speech. Inputs are only photos and short clips.

## 0. Set up (once per machine)

```bash
cd <project folder>
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
# also needs: ffmpeg/ffprobe and exiftool on PATH (apt install ffmpeg libimage-exiftool-perl / brew install ffmpeg exiftool)
```
Run every command below from the project folder with `.venv/bin/python -m director ...`.

## 1. Understand the brief

Ask only what you can't infer; one short message is enough:
- Where the media is (a folder; Google Drive files can be downloaded into one first).
- Feel: **punchy** (fast cuts, flashes, punch-ins), **balanced** (default), **cinematic**
  (long holds, dissolves), or **film** (the user's own reference look: a 3:2 film frame
  letterboxed inside 9:16, runs of quick cuts between long held shots, teal/orange film grade
  with grain, and a bold yellow title under a small spaced serif line such as "DAYS IN").
  Suggest **film** whenever the user asks for a cinematic, moody, "Perfect Days" or
  movie-like feel. If the user shares reference reels or describes a feel, map it to the
  closest style and note any tweaks to make in the plan (step 5).
- Length if they care (default: as long as the material supports, never over 60 s).
- Opening title text, if they want something other than "Place · Month Year".
- Whether the reel is personal or branded/sponsored (this matters for music licensing, step 3).

## 2. Analyze the media

```bash
.venv/bin/python -m director analyze --media <folder> --work work
```
This writes `work/analysis.json`: one entry per candidate shot (each photo; each detected shot
inside each clip) with `score` (0–1: sharpness, exposure, colour, motion), `time`, `city`, and a
thumbnail. Near-duplicates (bursts) are already removed. Skim it to learn the trip's story: which
places, in what order, how many usable shots. As a rule of thumb, ~1 shot per 2 seconds of film,
so 15 good shots support a ~30 s reel. Don't pad a thin trip to 60 s; a tight 25 s reel performs
better than a slow 60 s one.

## 3. Choose the music (Epidemic Sound connector)

The music sets the pacing, so choose it before planning. Target BPM by style:
punchy 110–135, balanced 95–125, cinematic 70–100, film 70–100 or 120–140 (mellow indie,
lo-fi or soft piano with a clear pulse; its quick-cut runs need some rhythmic accents).

1. `SearchRecordings` with `query.term` describing the trip's mood (e.g. "sunny island road trip
   upbeat", "rainy Tokyo night lo-fi"), `filter.bpm`, and `filter.vocals: false` (vocals fight
   with on-screen text and feel busy in short edits). Use `first: 5`.
2. Offer the user 2–3 options as title, BPM and mood tags, plus the `audioFile.lqmp3Url` preview
   link so they can listen. If they're away, pick the best fit and say why.
3. Cut the track to the film length with `EditRecording`: `targetDurationMs` = intended length
   (≤ 60000), `downloadAudioFormat: "WAV"`, `forceDuration: true`, `skipStems: true`. To land the
   drop on a key moment, add `requiredRegionsAtOffsets` with the drop's region in the original and
   where it should sit in the edit.
4. Poll `PollEditRecordingJob` until `COMPLETED`, then `DownloadRecordingEdit` with the job id and
   an edit id. If editing or polling is unavailable, use `DownloadRecording` with
   `{fileType: "WAV", stemType: "FULL"}` instead; the planner then picks the loudest window itself.
5. Download the signed `assetUrl` to `work/music.wav` (e.g. `curl -L -o work/music.wav "<url>"`).
   The link expires quickly, so download straight away.

Write down the track title, ID and the user's plan in `work/music_license.txt`. Epidemic's Creator
plan covers personal posts on Instagram, TikTok and YouTube. Branded or sponsored reels need a
business plan, so tell the user if their brief sounds commercial. If the user supplies their own
song, use it and remind them once that they are responsible for its rights. If they want to add
Instagram's in-app music instead, render with any placeholder track and tell them to mute it
in-app or swap the sound when posting.

## 4. Plan and review the storyboard

```bash
.venv/bin/python -m director plan --music work/music.wav --style balanced --work work \
    [--title "Kyoto\nApril 2026"] [--max-duration 45]
```
This writes `work/plan.json` and `work/storyboard.jpg` (a contact sheet with every shot, its start
time, duration and transition). **Open the storyboard image and look at it.** You are checking
what a human editor would:
- Is the first shot a strong hook? It should be the most striking image; viewers decide in 1–2 s.
- Does the order tell the trip (places in sequence, a satisfying last shot)?
- Any weak, ugly or repetitive shots? Too many from one clip?
- Do the transitions suit the feel? (See "Transitions follow the music" below.)

Check that the title does not sit on top of busy detail in the opening shot (signs, logos,
faces). If it does, set the title caption's `"y"` in `plan.json` (0 = top, 1 = bottom of the
picture; default 0.5), e.g. `0.22` to move it into the sky.

In the **film** style, also check that the long holds (opening, middle and last shot) carry
the strongest, calmest shots, and that the quick-cut runs use lively shots. The title is two
lines: pass `--title "DAYS IN|KYOTO"` to set both the small line and the big line.

### Two rules the user has set (always apply them)

**1. Never cut a person with the frame edge.** Analysis finds faces (YuNet) and grows each
into a whole-person box. The renderer then keeps everyone inside every frame: it places the crop
around them and limits pans and zooms so the box never leaves the picture. If the people cannot
all fit in the frame shape (a full-length group in a widescreen frame, or a close selfie), it
shows the **whole photo** with a blurred copy of itself filling the sides (`"framing": "fit"` in
the render log). Faces turned away from the camera are not detected. When you check frames
(step 6), look for anyone shown from behind or at the far edge and, if they are cut, set that
segment's `"people"` box by hand: `[x0, y0, x1, y1]` as fractions of the photo, e.g.
`[0, 0, 1, 1]` to force the whole photo.

**2. Transitions follow the music.** Each cut's transition is chosen from what the song does on
that beat: the hardest hits (top quarter of the track) get an **impact** transition (flash,
punch-in), downbeats and medium hits get a **move** (whip, slide, blur), quiet passages get a
**soft** dissolve, and weak off-beats stay hard cuts. Lengths are in beats and every transition
is centred on its beat. Cuts of long shots are pulled up to ~0.6 s onto a nearby hard hit.
**Customise the palette for every film** to fit the song and mood, rather than reusing the style
default. Pass `--palette` to `plan`, each option as `name:beats`:
```bash
# upbeat K-pop / dance: punchy hits, whips on downbeats
--palette "impact=fadewhite:0.25,zoomin:0.5;move=smoothleft:0.5,smoothright:0.5,hblur:0.5;soft=fade:1"
# mellow indie / piano: gentle
--palette "impact=fadewhite:0.5;move=dissolve:1;soft=dissolve:2,fadeblack:2"
# electronic with drops: flashes and squeezes
--palette "impact=fadewhite:0.25,circleopen:0.5;move=squeezeh:0.5,slideup:0.5;soft=fadegrays:1"
```
The plan records why each transition was chosen (`transition.why`). Tell the user the palette you
picked in one line.

Show the storyboard to the user (send the image) with a two-line summary (length, shot count,
music, style) and ask for changes before rendering. Rendering takes a minute or two; changing the
plan is instant.

## 5. Edit the plan (when needed)

`plan.json` is the contract between you and the renderer, so you can edit it directly. See
`references/plan-format.md` for every field. Common edits:
- Swap a shot: replace a segment's `src`/`kind`/`in` with another candidate from `analysis.json`
  (keep `start` and `dur`, so cuts stay on the beat).
- Change a transition: set `transition.type` to any FFmpeg xfade name (`cut`, `fade`, `dissolve`,
  `fadewhite`, `fadeblack`, `zoomin`, `smoothleft`, `slideleft`, `circleopen`, `hblur`, …), a
  `dur` that is a simple fraction of the beat (¼, ½, 1 beat; beat = 60 / tempo), and
  `lead` = half the `dur` so it stays centred on the beat. Never more than half of either shot.
- Change photo motion: `pan_lr`, `pan_rl`, `zoom_in`, `zoom_out`.
- Edit or remove captions, or change the title text (`\n` makes a second line).
- To shorten the film, drop segments from the end and set `duration` to the new last segment's
  `start + dur` (keep it on a beat from `work/music.json` so the ending lands).

Keep `start` values on beats and segments contiguous (each `start` = previous `start + dur`).
If you need a different rhythm, re-run `plan` with another style instead of hand-retiming.

## 6. Render and verify

```bash
.venv/bin/python -m director render --work work --out output/<trip-name>_reel.mp4
```
The render ends with a check (1080×1920, ≤ 60 s, audio present) and fails loudly otherwise.
Then grab a few frames to look at the real output, not just the plan:
```bash
ffmpeg -v error -i output/<file>.mp4 -vf "fps=1/3,scale=270:480,tile=6x2" -frames:v 1 work/check.jpg
```
Look for black frames, anyone cut by an edge (rule 1), and unreadable captions. The render log
prints each segment's framing (`crop`, `people-safe crop` or `fit`). Fix problems by setting the
segment's `people` box, swapping the shot or changing photo motion, then re-render.

Deliver the MP4 to the user (send the file; upload to Google Drive if they asked) with a one-line
summary: length, shots, music track, style. Mention that Instagram covers the bottom ~20% with
its UI, which is why captions sit above it.

## One-shot mode

If the user just wants a reel with no back-and-forth, run `make` after choosing music, then still
look at the storyboard and frames yourself before delivering:
```bash
.venv/bin/python -m director make --media <folder> --music work/music.wav --style punchy \
    --out output/reel.mp4
```

## Troubleshooting

- "No photos or videos found": check the folder path; supported types are jpg/jpeg/png/heic/webp
  and mp4/mov/m4v/mkv/avi.
- No city names: the media has no GPS (screenshots, edited exports, WhatsApp copies strip it).
  Captions then show only the date; ask the user for place names and put them in the plan.
- "Could not find a steady beat": the track is ambient or rubato. Choose one with drums.
- Wrong order: phones in different time zones or edited copies with new dates. Reorder segments
  in the plan by hand. Photos sent through chat apps lose their dates: copy them in story order,
  stamp `DateTimeOriginal` with exiftool, and plan with `--keep-order`.
- Optional upgrades in `requirements-ml.txt` (CLIP scene tags and beauty scores, beat_this
  downbeats) need PyTorch and model downloads; the pipeline works without them.
