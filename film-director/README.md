# Travel Film Director

An agent that turns trip **photos and short clips** into a **beat-synced vertical reel**
(1080×1920, 30 fps, ≤ 60 s) for Instagram Reels, TikTok or Shorts. There is no narration or
transcription: the story comes from where and when each shot was taken, and the rhythm comes
from the music.

Claude acts as the director through the skill in
`.claude/skills/travel-film-director/SKILL.md`. It chooses music with the Epidemic Sound
connector, reviews a storyboard with you and edits the plan. The `director` Python package does
the mechanical work.

```
photos + clips ──► ingest (ExifTool: time, GPS → city)
                 ──► analyze (PySceneDetect shots, OpenCV quality, perceptual-hash dedup)
music (Epidemic) ──► beats + energy (librosa)
                 ──► plan.json + storyboard.jpg   ◄── Claude / you review and edit
                 ──► render (FFmpeg: Ken Burns, xfade transitions, captions, grade) ──► reel.mp4
```

## Quick start

```bash
cd film-director
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
# system tools: ffmpeg, ffprobe, exiftool

.venv/bin/python -m director make --media ~/Pictures/taiwan-trip --music song.wav \
    --style punchy --out output/taiwan.mp4
```

Or step by step: `analyze` → `plan` (then look at `work/storyboard.jpg` and edit
`work/plan.json`) → `render`. Run `python -m director styles` to list the styles.

| Style | Cuts | Transitions |
|---|---|---|
| `punchy` | every 2 beats (4 when quiet) | hard cuts; punch-in, whip and flash on accents; white flash between places |
| `balanced` | every 2–4 beats | hard cuts; crossfade, slide and zoom on accents; flash between places |
| `cinematic` | every 4–8 beats | dissolves; dip to black between places |

Every cut lands on a detected beat. Shots get shorter when the music gets louder. The film opens
on the highest-scoring shot as a hook, then follows the trip in time order. It ends on a downbeat
with a fade.

## Try it without your own media

```bash
.venv/bin/python tools/make_sample_media.py samples      # synthetic 3-city trip + 120 BPM track
.venv/bin/python -m director make --media samples/media --music samples/music_120bpm.wav
```

## Files

| Path | What |
|---|---|
| `director/ingest.py` | Scans the folder and reads capture time and GPS with ExifTool, before any transcode. Reverse-geocodes offline. |
| `director/analyze.py` | Splits clips into shots, scores sharpness, exposure, colour and motion, removes duplicates, makes thumbnails |
| `director/music.py` | Finds beats, downbeats and per-beat energy, and picks the loudest window |
| `director/plan.py` | The director: beat grid, shot selection, order, transitions, captions → `plan.json` |
| `director/render.py` | FFmpeg renderer and output check |
| `director/storyboard.py` | Contact sheet for approval |
| `director/styles.json` | Editing styles (add your own) |
| `reports/` | Research report on the tools chosen and why |
| `requirements-ml.txt` | Optional: CLIP scene tags and beauty scores, beat_this downbeats (needs PyTorch) |

## Licensing notes

The Python dependencies are permissive (BSD, MIT, ISC, Apache), except reverse_geocode, which is
LGPL. FFmpeg and ExifTool run as separate programs. Music rights follow your Epidemic Sound plan.
The Creator plan covers personal posts; branded content needs a business plan.
