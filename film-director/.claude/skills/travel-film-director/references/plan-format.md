# plan.json format (version 1)

All times are seconds on the film's timeline, rounded to whole frames (1/30 s).

```jsonc
{
  "version": 1,
  "style": "balanced",                 // informational
  "canvas": {"width": 1080, "height": 1920, "fps": 30,
             "frame": [1080, 720]},       // picture size; smaller than canvas = letterboxed (film style)
  "duration": 30.0,                    // film length; must equal last segment start + dur, <= 60
  "music": {
    "path": "/abs/path/music.wav",     // soundtrack file
    "start": 13.769,                   // where in the track the film starts (a downbeat)
    "tempo": 117.5
  },
  "grade": "eq=contrast=1.04:saturation=1.10",  // any FFmpeg video filter chain, or ""
  "end_fade": 0.8,                     // fade to black at the end (s)
  "audio_fade": 1.5,                   // music fade-out at the end (s)
  "segments": [
    {
      "cid": "m004s00",                // candidate id from analysis.json
      "kind": "video",                 // "photo" | "video"
      "src": "/abs/path/clip.mp4",     // photos: the normalized JPEG under work/photos/
      "name": "clip.mp4",
      "start": 0.0,                    // where the shot appears on the film timeline (a beat)
      "dur": 2.033,                    // how long it is on screen before the next cut
      "in": 1.25,                      // video only: source time to start from
      "freeze": 0.0,                   // video only: seconds of last-frame hold if the shot is too short
      "motion": "pan_lr",              // photo only: pan_lr | pan_rl | zoom_in | zoom_out
      "transition": {"type": "hblur", "dur": 0.27, "lead": 0.13, "why": "move"},
                                       // into the NEXT segment; runs from next.start - lead,
                                       // so lead = dur/2 centres it on the beat; cut: dur 0, lead 0
      "people": [0.18, 0.18, 0.9, 1.0], // whole-person region (fractions of the photo) that must
                                       // stay in frame; null = no people
      "width": 1086, "height": 1448,   // source size (used for people-safe video crops)
      "city": "Taipei", "time": "2026-10-01 09:10", "score": 0.71,
      "thumb": "work/thumbs/m004s00.jpg"
    }
  ],
  "captions": [
    {"text": "Taipei & Jiufen\nOct 2026", "start": 0.15, "end": 2.0, "kind": "title"},  // centered, large
    {"text": "Jiufen", "start": 13.15, "end": 15.0, "kind": "place"},                   // lower third
    // film style title: big yellow condensed text with a small spaced serif line above
    {"text": "TAIWAN", "kicker": "DAYS IN", "start": 0.8, "end": 5.0, "kind": "title", "look": "film"}
  ]
}
```

## Rules the renderer relies on

- Segments are contiguous: `segments[k+1].start == segments[k].start + segments[k].dur`.
- A transition overlaps the start of the next shot, beginning exactly at `next.start` (on the
  beat), so its `dur` must be smaller than the next segment's `dur` (keep it ≤ half).
- `type: "cut"` is a hard cut. Any other value must be an FFmpeg `xfade` transition name:
  fade, fadeblack, fadewhite, fadefast, fadeslow, dissolve, distance, wipeleft/right/up/down,
  slideleft/right/up/down, smoothleft/right/up/down, coverleft/…, revealleft/…, circleopen,
  circleclose, circlecrop, rectcrop, radial, vertopen/close, horzopen/close, diagtl/tr/bl/br,
  hlslice/hrslice/vuslice/vdslice, hblur, pixelize, fadegrays, squeezeh/v, zoomin,
  hlwind/hrwind/vuwind/vdwind.
- For video, `in` is the source time of the first visible frame (including the previous
  transition's lead); if the source runs out the renderer holds the last frame.
- If `people` is set, the crop and any pan or zoom keep that whole region in every frame; if it
  cannot fit the frame shape, the photo is shown whole over a blurred fill.
- Captions use `\n` for line breaks. Keep place captions to ~20 characters so they fit the width
  at the default size.
