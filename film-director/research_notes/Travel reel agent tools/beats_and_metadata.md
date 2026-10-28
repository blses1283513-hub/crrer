# Travel Reel Agent Tools: Beat Detection and Photo/Video Metadata + Offline Reverse Geocoding

Method note: Star counts, licenses and last-push dates come from one GitHub Search API query fetched on 2026-10-28. The numbers were summarized by a fetch tool, so treat them as approximate (~). PyPI versions, upload dates, `requires_python` and wheel tags come straight from the PyPI JSON API on 2026-10-28. Some hosts were blocked in this sandbox: arxiv.org, zenodo.org (the ISMIR PDF), operations.osmfoundation.org, and the GitHub REST API outside search. Claims that needed those pages are cited through secondary sources or listed under Gaps.

## (A) Music beat / tempo / onset / downbeat / section detection: stars, license, maintenance, install pain, and fit for 60s reels

### Takeaway
For a pip-only Linux pipeline on Python 3.11/3.12, use **beat_this** (CPJKU, MIT code and weights, pip-installable, beats and downbeats, about 89 beat F1 / 78 downbeat F1 on held-out GTZAN). Pair it with **librosa** for onsets, RMS/energy and tempo curves, which can serve as "drop" heuristics. **allin1** is the only candidate that also gives sections (intro/verse/chorus), but it has been unmaintained since 2024 and its NATTEN and madmom dependencies break often, so treat it as optional, run in Docker or a pinned environment. Avoid **madmom** and **BeatNet** as direct dependencies: their PyPI releases are from 2018 and 2023 and break on Python 3.10+ and NumPy ≥1.24. Avoid **essentia** and **aubio** for anything commercial or closed-source because of AGPL and GPL.

### Cited Findings

**Star / license / activity snapshot (GitHub Search API, 2026-10-28; ~approximate)**

| Repo | Stars (~) | Forks | License (GitHub) | Last push | Open issues |
|---|---|---|---|---|---|
| librosa/librosa | ~8.7k (8,713) | 1,093 | ISC | 2026-10-06 | 50 |
| MTG/essentia | ~3.8k (3,782) | 641 | AGPL-3.0 | 2026-10-22 | 441 |
| aubio/aubio | ~3.8k (3,775) | 430 | GPL-3.0 | 2026-04-10 | 160 |
| CPJKU/madmom | ~1.7k (1,732) | 291 | "Other" (NOASSERTION) | 2026-03-20 | 82 |
| mir-aidj/all-in-one (allin1) | ~0.87k (868) | 138 | MIT | 2024-05-09 | 20 |
| mjhydri/BeatNet | ~0.53k (525) | 83 | CC-BY-4.0 | 2026-04-13 | 15 |
| CPJKU/beat_this | ~0.45k (450) | 77 | MIT | 2026-05-28 | 5 |

Source for all rows: [GitHub Search API query](https://api.github.com/search/repositories?q=repo:librosa/librosa+repo:CPJKU/madmom+repo:aubio/aubio+repo:MTG/essentia+repo:mjhydri/BeatNet+repo:CPJKU/beat_this+repo:mir-aidj/all-in-one)

**PyPI release / Python-compat facts (PyPI JSON API, 2026-10-28)**
- librosa: latest is **1.0.0 (2026-08-11)**, with `requires_python >=3.12` and a pure-Python wheel. The previous line, **0.11.0 (2025-03-11)**, requires `>=3.8`. Python 3.11 users therefore get 0.11.x and 3.12 users get 1.0. PyPI lists the license as ISC. — [PyPI librosa](https://pypi.org/pypi/librosa/json)
- madmom: the latest PyPI release is still **0.16.1 (2018-11-14)**, sdist only (no wheels, so it compiles Cython on install). PyPI classifiers list "BSD" plus "CC BY-NC-SA" / "Free for non-commercial use": the code is BSD and the model/data files are non-commercial. — [PyPI madmom](https://pypi.org/pypi/madmom/json)
- madmom on Python 3.10+: `from collections import MutableSequence` breaks because Python 3.10 moved it to `collections.abc`. — [madmom-users Google Group](https://groups.google.com/g/madmom-users/c/uDTvNLXYHbI)
- madmom also uses `np.float`, which NumPy removed, so it raises AttributeError. — [madmom issue #527 mirror](https://git.tdem.in/CPJKU/madmom/issues/527)
- A BeatNet Hugging Face Space ships a `patch_madmom.py` that rewrites both lines. — [HF BeatNet patch commit](https://huggingface.co/spaces/teamup-tech/BeatNet/commit/ea8b7ecfccd94d5912c7472a601ffebce71dce72), [patch_madmom.py](https://huggingface.co/spaces/teamup-tech/BeatNet/blob/main/patch_madmom.py)
- madmom from GitHub: the beat_this README says the PyPI madmom "doesn't support newer Python and numpy versions" and installs it from GitHub instead (`pip install git+https://github.com/CPJKU/madmom`). — [beat_this README](https://github.com/CPJKU/beat_this)
- aubio: the latest PyPI release is **0.4.9 (2019-02-08)**, sdist only (compiles a C extension), GPLv3+. — [PyPI aubio](https://pypi.org/pypi/aubio/json)
- essentia / essentia-tensorflow: the latest PyPI build is **2.1b6.dev1438 (2026-05-19)**, but it has **cp314 wheels only**. The previous build, **2.1b6.dev1389 (2025-07-24)**, has cp39–cp313 manylinux wheels. Both are licensed **AGPL-3.0-only**, and there is no sdist. — [PyPI essentia](https://pypi.org/pypi/essentia/json)
- BeatNet: PyPI **1.1.3 (2023-11-28)**, with no license string on PyPI. GitHub reports CC-BY-4.0. — [PyPI BeatNet](https://pypi.org/pypi/BeatNet/json)
- beat-this: PyPI **1.1.0 (2026-04-14)**, MIT, pure-Python wheel. — [PyPI beat-this](https://pypi.org/pypi/beat-this/json)
- allin1: PyPI **1.1.0 (2023-10-10)**, `requires_python >=3.8`. — [PyPI allin1](https://pypi.org/pypi/allin1/json)
- natten, allin1's dependency, has **no wheels on PyPI** (0.21.7, 2026-07-26; sdist only). A plain pip install compiles it against torch, or needs a wheel from natten.org. — [PyPI natten](https://pypi.org/pypi/natten/json)

**beat_this (CPJKU, ISMIR 2024)**
- It is the official implementation of "Beat This! Accurate Beat Tracking Without DBN Postprocessing" (Foscarin, Schlüter, Widmer, ISMIR 2024, arXiv:2407.21658). It predicts **beats and downbeats** and can save `.beats` files. The Python API also exposes framewise logits. — [beat_this README](https://github.com/CPJKU/beat_this)
- Dependencies: PyTorch ≥2.0, tqdm, einops, soxr and rotary-embedding-torch, plus ffmpeg or another torchaudio backend for formats other than WAV. madmom is optional and needed only for `--dbn`. The code uses the GPU by default, falls back to CPU, and `--gpu=-1` forces CPU. — [beat_this README](https://github.com/CPJKU/beat_this)
- License: "The code and the published model weights are released under the MIT license", with a caveat that some training data carries restrictive copyright or CC licenses. — [beat_this README](https://github.com/CPJKU/beat_this)
- Models: `final0–2` are about 78 MB each and `small0–2` about 8.1 MB each. They download automatically. — [beat_this README](https://github.com/CPJKU/beat_this)
- Accuracy: **GTZAN F1 89.1 for beats and 78.3 for downbeats**, held out because the final models were trained on everything except GTZAN. These figures come from aggregator summaries, not the PDF itself. — [Moonlight review](https://www.themoonlight.io/review/beat-this-accurate-beat-tracking-without-dbn-postprocessing), [JKU publication page](https://research.jku.at/en/publications/beat-this-accurate-beat-tracking-without-dbn-postprocessing/)
- The paper claims it surpasses the state of the art in F1 without a DBN, but does worse on continuity metrics. — [Moonlight review](https://www.themoonlight.io/review/beat-this-accurate-beat-tracking-without-dbn-postprocessing)

**allin1 (All-In-One music structure analyzer, mir-aidj)**
- Outputs: tempo (BPM), beats, downbeats, beat positions, and **functional segment boundaries with labels ("intro, verse, chorus, bridge, outro")**. Results are JSON, with optional activations and embeddings at 100 FPS. — [allin1 README](https://github.com/mir-aidj/all-in-one)
- Install has four steps: (1) install PyTorch manually, (2) install NATTEN manually on Linux, (3) `pip install git+https://github.com/CPJKU/madmom`, then (4) `pip install allin1`. Demucs source separation is used internally. MIT license. — [allin1 README](https://github.com/mir-aidj/all-in-one)
- Speed and timing: on an RTX 4090 it processes 10 songs (33 min) in 73 s. The author has seen MP3 timing offsets of "about 20~40ms" and recommends converting to WAV first. — [allin1 README](https://github.com/mir-aidj/all-in-one)
- NATTEN breakage: NATTEN **v0.17.5 breaks allin1** through API renames (issue #30, May 2025). `pip install allin1` failing to build NATTEN 0.17.5 on Python 3.12 is reported in #28. Ubuntu install failures are in #32. NATTEN 0.20/0.21 compatibility shims and PRs (#33, #36, #37) are unmerged or closed. An open PR #39 (2026-09-20) would make NATTEN optional with a pure-PyTorch CPU fallback. — [GitHub issue search: allin1 + natten](https://api.github.com/search/issues?q=repo:mir-aidj/all-in-one+natten)
- Activity: the last push to the repo was 2024-05-09 and the last PyPI release was 2023-10-10, so the project is effectively unmaintained as of late 2026. — [GitHub Search API](https://api.github.com/search/repositories?q=repo:mir-aidj/all-in-one), [PyPI allin1](https://pypi.org/pypi/allin1/json)

**essentia licensing**
- Essentia is available under AGPLv3, and a commercial license is available from MTG-UPF. Some algorithms depend on third-party GPL/LGPL libraries that UPF cannot sublicense, so a product must clear those separately or compile Essentia with reduced dependencies. — [Essentia licensing page](https://essentia.upf.edu/licensing_information.html)

### Inferences
- **Ranking for this use case** (60s reel, pip install, Python 3.11/3.12, Linux):
  1. **beat_this** has the best accuracy, a permissive license for both code and weights, a clean pip install, and active maintenance. It gives beats and downbeats; the 8 MB `small` model is fine on CPU for a 60s clip.
  2. **librosa** is the most-starred, ISC-licensed, pure Python and trivial to install. It is the right tool for onset strength, RMS energy, spectral flux and tempo, which are needed for drop detection and cutting on transients. Its `beat_track` is a classic DP beat tracker that, as far as I know, has no downbeat output (see Gaps). Pin `librosa<1` on 3.11, or 1.0 on 3.12.
  3. **allin1** is the only option that also gives sections and is well suited to "start the reel at the chorus". Install friction is very high (NATTEN, git madmom, PyTorch/CUDA matching) and the project is unmaintained. Run it only inside a pinned Docker image, if at all.
  4. **madmom** is the reference DBN beat/downbeat tracker and is BSD for code, but its model files are CC BY-NC-SA (non-commercial), its PyPI release is from 2018, and it needs a git install or patches. Use it only indirectly, for example `beat_this --dbn`.
  5. **essentia** has good algorithms (RhythmExtractor2013, onset detection) and wheels for 3.11/3.12 via build dev1389. Its AGPL license is viral for network services and distributed apps, and commercial use needs an MTG license.
  6. **aubio** is lightweight and real-time capable, but GPL-3, last released in 2019, and compile-only on pip.
  7. **BeatNet** is aimed at online/real-time joint beat, downbeat and meter tracking. It depends on madmom (so inherits the patching) and is CC-BY-4.0. It is less accurate offline than beat_this. The real-time focus and the accuracy comparison come from general knowledge, not a fetched source.
- **On "drops":** none of these tools labels EDM-style drops directly. A practical approach is to combine allin1 segment boundaries, or librosa RMS/onset-strength novelty peaks, with beat_this downbeats, and snap each drop to the nearest downbeat.
- **Licensing:** for a closed-source or commercial SaaS editor, the clean stack is beat_this + librosa (MIT + ISC). Avoid shipping essentia (AGPL), aubio (GPL) or madmom's model files (non-commercial).
- **Install on 3.11/3.12:** on Python 3.11/3.12, pip may resolve essentia to the older dev1389 wheel, because the newest dev1438 has cp314 wheels only. This is inferred from the PyPI wheel tags.

### Gaps
- I could not retrieve the madmom/Böck and BeatNet GTZAN F1 numbers from the Beat This paper's Table 2 (arXiv and zenodo were blocked), and found no independent 2025–2026 benchmark such as MIREX across all seven tools.
- No MIREX 2025/2026 beat-tracking results were found.
- I did not verify whether madmom's GitHub master now ships Python 3.12 / NumPy 2 support or a new PyPI release. It was pushed in March 2026, but the commits API was blocked.
- librosa's lack of downbeat tracking is from general knowledge; I did not re-verify it in the docs.
- No source verified "drop" detection quality for any tool.

## (B) Photo/video metadata extraction (capture time, GPS) and offline reverse geocoding: stars, license, and how to handle iPhone QuickTime metadata

### Takeaway
Use **ExifTool**, called through **PyExifTool** or `exiftool -json` via subprocess, as the single source of truth for both photos (JPEG/HEIC EXIF GPS and DateTimeOriginal with OffsetTime) and videos (QuickTime `CreationDate` with offset, and `GPSCoordinates` from `com.apple.quicktime.location.ISO6709`). Use **ffprobe** as a fallback for video. Use Pillow plus pillow-heif or exifread only for a lightweight pure-Python path. For place labels, use offline **reverse_geocode** (richardpenman; maintained, has a wheel) or **reverse_geocoder** (thampiman; more stars, but its last release was in 2016 and it has multiprocessing quirks). Use geopy/Nominatim only for occasional, rate-limited (≤1 request/s) enrichment, with a custom User-Agent.

### Cited Findings

**Star / license / activity snapshot (GitHub Search API, 2026-10-28; ~approximate)**

| Repo | Stars (~) | License (GitHub) | Last push |
|---|---|---|---|
| FFmpeg/FFmpeg (ffprobe) | ~65.9k | "Other" (LGPL/GPL mix) | 2026-10-28 |
| python-pillow/Pillow | ~13.9k | "Other" (MIT-CMU per PyPI) | 2026-10-28 |
| exiftool/exiftool (Phil Harvey) | ~5.2k | GPL-3.0 (as detected by GitHub) | 2026-05-27 |
| geopy/geopy | ~4.9k | MIT | 2026-07-12 |
| thampiman/reverse-geocoder | ~1.9k | LGPL-2.1 | 2023-03-19 |
| ianare/exif-py (exifread) | ~1.0k (973) | BSD-3-Clause | 2026-06-10 |
| vstinner/hachoir | ~0.67k | GPL-2.0 | 2026-10-14 |
| hMatoba/Piexif | ~0.39k | MIT | 2023-11-22 |
| richardpenman/reverse_geocode | ~0.13k | none detected (PyPI says LGPL) | 2026-08-01 |
| smarnach/pyexiftool (original PyExifTool) | ~0.28k | "Other" | 2023-11-17 |

Sources: [GitHub Search API query](https://api.github.com/search/repositories?q=repo:exiftool/exiftool+repo:python-pillow/Pillow+repo:ianare/exif-py+repo:hMatoba/Piexif+repo:vstinner/hachoir+repo:thampiman/reverse-geocoder+repo:geopy/geopy+repo:richardpenman/reverse_geocode+repo:FFmpeg/FFmpeg); [GitHub search: pyexiftool](https://api.github.com/search/repositories?q=pyexiftool+in:name&sort=stars). The maintained PyExifTool fork, sylikc/pyexiftool, which is where PyPI points, did not appear in the search results (likely because GitHub search excludes forks), so its star count is unknown.

**PyPI facts (2026-10-28)**
- **PyExifTool 0.5.6 (2023-10-22)**, dual GPLv3+/BSD, `>=3.6`, pure Python. It needs the `exiftool` binary installed separately. — [PyPI PyExifTool](https://pypi.org/pypi/PyExifTool/json)
- **Pillow 13.0.0 (2026-10-16)**, MIT-CMU, `requires_python >=3.11`, with cp311–cp315 manylinux wheels. — [PyPI pillow](https://pypi.org/pypi/pillow/json)
- **pillow-heif 1.8.1 (2026-10-11)**, BSD-3-Clause, with cp310–cp315 wheels. It is needed for Pillow to open iPhone HEIC files. — [PyPI pillow-heif](https://pypi.org/pypi/pillow-heif/json)
- **exifread 3.5.1 (2025-08-23)**, pure Python, `>=3.7`. — [PyPI exifread](https://pypi.org/pypi/exifread/json)
- **piexif 1.1.3 (2019-07-01)**, MIT. It has had no release since 2019 and GitHub's last push was 2023. — [PyPI piexif](https://pypi.org/pypi/piexif/json)
- **hachoir 3.4.0 (2026-09-13)**, GPL-2, pure Python. — [PyPI hachoir](https://pypi.org/pypi/hachoir/json)
- **reverse_geocoder 1.5.1 (2016-09-15)**, LGPL, **sdist only** (no wheel); it depends on numpy and scipy. — [PyPI reverse_geocoder](https://pypi.org/pypi/reverse_geocoder/json)
- **reverse-geocode 1.6.6 (2025-05-15)**, LGPL, with a pure-Python wheel. — [PyPI reverse-geocode](https://pypi.org/pypi/reverse-geocode/json)
- **geopy 2.5.0 (2026-07-12)**, MIT, `>=3.8`. — [PyPI geopy](https://pypi.org/pypi/geopy/json)
- **pymediainfo 7.0.1 (2025-02-12)**, MIT. It is an alternative video-metadata reader. — [PyPI pymediainfo](https://pypi.org/pypi/pymediainfo/json)
- **python-exiv2 0.19.2 (2026-08-31)**, GPL-3.0-or-later, wheels cp36–cp315; and **pyexiv2 2.16.0 (2026-08-02)**, GPLv3. These are exiv2 bindings. — [PyPI exiv2](https://pypi.org/pypi/exiv2/json), [PyPI pyexiv2](https://pypi.org/pypi/pyexiv2/json)
- **timezonefinder 9.2.0 (2026-10-22)**, MIT. It now requires **`>=3.12`**; 9.0.0 (2026-09-11) is the last release supporting 3.11. It is useful for converting UTC video timestamps to local time from GPS. — [PyPI timezonefinder](https://pypi.org/pypi/timezonefinder/json)

**iPhone video (QuickTime/MOV) metadata via ffprobe**
- iPhone MOV files store GPS under `com.apple.quicktime.location.ISO6709` as an ISO 6709 string with latitude, longitude and altitude. Creation time with a UTC offset is stored in `com.apple.quicktime.creationdate`. — [addpipe: Geolocation metadata in iOS/Android video](https://blog.addpipe.com/geolocation-metadata-ios-android-video-files/)
- FFmpeg's MOV demuxer maps the ISO6709 key to a plain `location` tag and strips the `com.apple.quicktime.` prefix from other meta keys. — [FFmpeg-devel patch: strip com.apple.quicktime prefix; parse creation date](https://lists.ffmpeg.org/pipermail/ffmpeg-devel/2016-September/199389.html)
- Long-standing FFmpeg ticket #4209: iOS GPS/location metadata **is not copied when remuxing MOV to MP4**. Read metadata from the original files before any transcode. — [FFmpeg trac #4209 (2024 update)](https://ffmpeg.org/pipermail/ffmpeg-trac/2024-April/069027.html)

**geopy / Nominatim (online)**
- The public Nominatim server allows an absolute maximum of 1 request per second. It requires an identifying User-Agent (and Referer), discourages bulk geocoding, and counts periodic app requests as bulk. The limits apply per application across all its users. The policy does not apply to self-hosted Nominatim. — [OSMF Nominatim Usage Policy](https://operations.osmfoundation.org/policies/nominatim/) (direct fetch blocked; points corroborated via search snippet and [OSM diary](https://api.openstreetmap.org/user/pnorman/diary/398773))
- A generic default User-Agent gets blocked with HTTP 429. — [Elabore partner-tools PR #21](https://git.elabore.coop/Elabore/partner-tools/pulls/21/files)

**reverse_geocoder (thampiman) known issues**
- Several open issues report multiprocessing problems. Spawn-mode RuntimeErrors appear on Windows and in Spyder on Python 3.10 (#53, #68, #48). It fails inside daemon multiprocessing pools (#40) and with eventlet (#55). There is an open request for wheels; a fork publishes Linux/macOS wheels (#74). Issue #37 reports "wrong" results for an offshore point, consistent with nearest-city behavior. — [GitHub issue search: reverse-geocoder](https://api.github.com/search/issues?q=repo:thampiman/reverse-geocoder+is:issue)

### Inferences
- **Ranking for metadata extraction:**
  1. **ExifTool + PyExifTool**: ExifTool is the most complete reader for HEIC, JPEG, MOV, MP4 and Android files. It handles QuickTime `CreationDate` with offset, `GPSCoordinates`, and EXIF `OffsetTimeOriginal` in one call (`exiftool -json -n -G`). The binary comes from the distro package (`apt install libimage-exiftool-perl`, general knowledge) because it is not on pip. PyExifTool itself is pure pip.
  2. **ffprobe**, which is already in the pipeline for rendering, is a good video fallback (`-show_entries format_tags`). Its top-level `creation_time` is UTC, so local time needs the creationdate offset or timezonefinder applied to the GPS.
  3. **Pillow (+ pillow-heif)** is fine for JPEG/HEIC EXIF in pure Python with wheels. **exifread** is a pure-Python alternative with good maker-note coverage.
  4. **piexif** is stale (2019) and write-oriented. **hachoir** is GPL-2 and less complete. Neither is recommended as the primary reader.
- **Ordering strategy:** sort by local capture time. For photos, use DateTimeOriginal plus OffsetTimeOriginal. For iPhone video, use QuickTime CreationDate (which includes an offset). Where only UTC is available, derive local time from the GPS with timezonefinder (pin `<9.1` on Python 3.11). Fall back to file mtime only as a last resort.
- **Reverse geocoding:** for offline city/country labels, **reverse-geocode** (maintained, wheel) is lower-risk to install. **reverse_geocoder** has more stars and is k-d-tree fast for batches, but its last release was in 2016, it is sdist only, and it has multiprocessing quirks, so call it with `mode=1` (single process) inside workers. Both give nearest-populated-place labels, which are coarse for travel POIs. For landmark-level labels, a self-hosted Nominatim/Photon instance, or occasional geopy calls rate-limited with geopy's `RateLimiter(min_delay_seconds=1)`, is the compliant path.
- **Licensing:** ExifTool is free software under GitHub's GPL-3.0 detection (Perl "same terms as Perl" is general knowledge). Calling it as a separate binary keeps GPL obligations out of the app code. The reverse geocoders are LGPL, which is fine to import as a library.

### Gaps
- No star count was available for sylikc/pyexiftool, the maintained PyPI fork, because it is missing from the search results.
- I did not confirm reverse_geocoder's and reverse_geocode's underlying datasets (GeoNames cities with population > 1000 or > 15000) or their accuracy from their READMEs.
- The exact Nominatim policy wording could not be fetched directly (host blocked).
- I found no source comparing the accuracy or coverage of ExifTool, exifread, Pillow and hachoir on HEIC or Android MP4 GPS.
- I did not verify how Android and GoPro/DJI store GPS in video (for example Android `location` / `©xyz` atoms, or DJI SRT telemetry).
