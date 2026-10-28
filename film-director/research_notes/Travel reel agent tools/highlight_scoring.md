# Highlight Selection & Scoring Tools for a ≤60s Travel Reel (shot detection, quality/aesthetic scoring, dedup, zero-shot tagging)

Research date: 2026-10-28. Method note: the GitHub REST API and huggingface.co / scenedetect.com were not reachable from this session (blocked by the session's network policy), so star counts are taken from the rendered GitHub repo pages (GitHub rounds them, e.g. "5.3k"), and release dates come from the live PyPI JSON API (`https://pypi.org/pypi/<pkg>/json`, queried 2026-10-28). All star counts are **approximate (~) as of late Oct 2026**.

## Q1. Stars / license / last release / activity for each candidate tool (ranked)

### Takeaway
By stars the order is OpenCV (~91k) >> OpenAI CLIP (~34.5k) > open_clip (~14.2k) > imagededup (~5.7k) ≈ PySceneDetect (~5.3k) > IQA-PyTorch/pyiqa (~3.4k) > improved-aesthetic-predictor (~1.3k) ≈ TransNetV2 (~1.1k) > Katna (~400) ≈ UniVTG (~381) ≈ Moment-DETR (~356) > Lighthouse (~272) > aesthetic-predictor-v2-5 (~208). The most important licensing finding is that **pyiqa is non-commercial** (PolyForm Noncommercial 1.0.0 in its latest release; earlier CC BY-NC-SA 4.0). Actively maintained in 2026: PySceneDetect, open_clip, pyiqa, OpenCV, transformers. Stale: OpenAI CLIP, Katna, TransNetV2, UniVTG, Moment-DETR, aesthetic predictors.

### Cited Findings

**Summary table (approximate stars, late Oct 2026)**

| Tool | Repo | ~Stars | License | Latest release (PyPI / repo) | Activity |
|---|---|---|---|---|---|
| OpenCV | opencv/opencv | ~91.4k (57.1k forks) | Apache-2.0 | opencv-python 5.0.0.93, 2026-07-02; OpenCV 5.0 released ~June 4–6 2026 | Very active |
| OpenAI CLIP | openai/CLIP | ~34.5k (4.1k forks) | MIT | No PyPI package from OpenAI; repo has only 58 commits; community repack `clip-anytorch` last 2.6.0 on 2024-01-13 | Effectively frozen |
| open_clip | mlfoundations/open_clip | ~14.2k (1.3k forks) | MIT (per PyPI metadata) | open-clip-torch 3.3.0, 2026-02-27 | Active |
| imagededup | idealo/imagededup | ~5.7k | Apache-2.0 | 0.3.3.post2, 2025-08-15 | Low-moderate (maintenance releases) |
| PySceneDetect | Breakthrough/PySceneDetect | ~5.3k (543 forks) | BSD-3-Clause | scenedetect 0.7.2, 2026-10-12 (GitHub: v0.7.2 Oct 11 2026) | Active |
| IQA-PyTorch (pyiqa) | chaofengc/IQA-PyTorch | ~3.4k | **PolyForm Noncommercial 1.0.0** + NTU S-Lab (latest); earlier versions CC BY-NC-SA 4.0 | pyiqa 0.1.16, 2026-07-08 | Active (650 commits) |
| improved-aesthetic-predictor (LAION) | christophschuhmann/improved-aesthetic-predictor | ~1.3k | Apache-2.0 | No releases; 24 commits | Stale but stable |
| TransNetV2 | soCzech/TransNetV2 | ~1.1k (157 forks) | MIT | No GitHub releases; community `transnetv2-pytorch` 1.0.5, 2025-06-01 | Stale (official); PyTorch port maintained 2025 |
| Katna | keplerlab/katna | ~400 (70 forks) | MIT | katna 0.9.2, 2021-04-28 | Unmaintained since 2021 |
| UniVTG | showlab/UniVTG | ~381 | MIT | Last news entry 2023-10-15 | Stale research code |
| Moment-DETR | jayleicn/moment_detr | ~356 | MIT code; annotations CC BY-NC-SA 4.0 | 11 commits; NeurIPS 2021 | Stale research code |
| Lighthouse (LINE/LY Corp) | line/lighthouse | ~272 | Apache-2.0 | v1.2 (2025-11-20) | Moderately active |
| aesthetic-predictor-v2-5 | discus0434/aesthetic-predictor-v2-5 | ~208 (third-party index, possibly stale) | **AGPL-3.0** | Last push Dec 2024 (per index) | Stale |
| HF transformers (for SigLIP/SigLIP2) | huggingface/transformers | (not fetched) | Apache 2.0 | transformers 5.21.0, 2026-10-26 | Very active |

Sources per row:
- PySceneDetect: ~5.3k stars, 543 forks, BSD-3-Clause, v0.7.2 Oct 11 2026 — [GitHub](https://github.com/Breakthrough/PySceneDetect); scenedetect 0.7.2 uploaded 2026-10-12, license BSD-3-Clause — [PyPI](https://pypi.org/project/scenedetect/)
- TransNetV2: ~1.1k stars, 157 forks, MIT, 78 commits, no releases, PyTorch inference version in `inference-pytorch` — [GitHub](https://github.com/soCzech/TransNetV2); transnetv2-pytorch 1.0.5 (2025-06-01, MIT), "identical results as the original TensorFlow version" — [PyPI](https://pypi.org/project/transnetv2-pytorch/)
- OpenAI CLIP: ~34.5k stars, 4.1k forks, MIT, 58 commits — [GitHub](https://github.com/openai/CLIP); clip-anytorch 2.6.0 dated 2024-01-13 — [PyPI](https://pypi.org/project/clip-anytorch/)
- open_clip: ~14.2k stars, 1.3k forks — [GitHub](https://github.com/mlfoundations/open_clip); open-clip-torch 3.3.0 uploaded 2026-02-27, MIT — [PyPI](https://pypi.org/project/open-clip-torch/)
- pyiqa: ~3.4k stars; README says "PolyForm Noncommercial License 1.0.0" plus NTU S-Lab License — [GitHub](https://github.com/chaofengc/IQA-PyTorch); pyiqa 0.1.16 uploaded 2026-07-08 with license PolyForm-Noncommercial-1.0.0 — [PyPI](https://pypi.org/project/pyiqa/); older releases (0.1.0–0.1.13) were CC BY-NC-SA 4.0 (+ NTU S-Lab from 0.1.7) — [PyPI 0.1.13](https://pypi.org/project/pyiqa/0.1.13), [PyPI 0.1.1](https://pypi.org/project/pyiqa/0.1.1/)
- improved-aesthetic-predictor: ~1.3k stars, Apache-2.0, 24 commits, MLP over CLIP embeddings, checkpoint `sac+logos+ava1-l14-linearMSE.pth` — [GitHub](https://github.com/christophschuhmann/improved-aesthetic-predictor)
- aesthetic-predictor-v2-5: SigLIP-based, scores 1–10, "5.5+ is considered a great aesthetic score", default encoder `google/siglip-so400m-patch14-384`, AGPL-3.0, ~208 stars, last push Dec 2024 — [ecosyste.ms index](https://awesome.ecosyste.ms/projects/github.com%2Fdiscus0434%2Faesthetic-predictor-v2-5), [PyPI](https://pypi.org/project/aesthetic-predictor-v2-5)
- imagededup: ~5.7k stars, Apache-2.0, PHash/DHash/WHash/AHash/CNN, Python 3.9+ — [GitHub](https://github.com/idealo/imagededup); 0.3.3.post2 uploaded 2025-08-15 — [PyPI](https://pypi.org/project/imagededup/)
- OpenCV: ~91.4k stars, 57.1k forks, Apache-2.0 — [GitHub](https://github.com/opencv/opencv); opencv-python 5.0.0.93 uploaded 2026-07-02 — [PyPI](https://pypi.org/project/opencv-python/); OpenCV 5.0 released early June 2026 with rewritten (CPU-only for now) DNN engine — [AlternativeTo](https://alternativeto.net/news/2026/6/opencv-5-brings-new-deep-neural-network-engine-stronger-onnx-support-and-faster-core/), [ai-tldr](https://ai-tldr.dev/releases/opencv-5-0-release/)
- Katna: ~400 stars, MIT, newest changelog 0.9.0 — [GitHub](https://github.com/keplerlab/katna); katna 0.9.2 uploaded 2021-04-28 — [PyPI](https://pypi.org/project/katna/)
- UniVTG: ~381 stars, MIT, latest news 2023-10-15, tasks = moment retrieval, highlight detection, video summarization — [GitHub](https://github.com/showlab/UniVTG)
- Moment-DETR: ~356 stars, MIT code, annotations CC BY-NC-SA 4.0 — [GitHub](https://github.com/jayleicn/moment_detr)
- Lighthouse: ~272 stars, Apache-2.0, v1.2 2025-11-20; wraps Moment-DETR, QD-DETR, EaTR, TR-DETR, UVCOM, CG-DETR — [GitHub](https://github.com/line/lighthouse), [arXiv 2408.02901](https://arxiv.org/abs/2408.02901)
- transformers 5.21.0 uploaded 2026-10-26, Apache 2.0 — [PyPI](https://pypi.org/project/transformers/)
- SigLIP 2 (arXiv 2502.14786, Feb 2025) checkpoints in four sizes: ViT-B (86M), L (303M), So400m (400M), g (1B); NaFlex variants preserve native aspect ratio — [arXiv](https://arxiv.org/html/2502.14786v1); HF model cards show the `zero-shot-image-classification` pipeline — [HF siglip2-so400m-patch14-224](https://huggingface.co/google/siglip2-so400m-patch14-224)

### Inferences
- Fitness ranking for this use case (my judgement, combining stars, maintenance, license, CPU feasibility): 1) PySceneDetect, 2) open_clip (or transformers+SigLIP2), 3) OpenCV (blur/exposure heuristics), 4) imagededup, 5) improved-aesthetic-predictor, 6) TransNetV2 (PyTorch port), 7) pyiqa (only if non-commercial use is acceptable), 8) Lighthouse, 9) Katna, 10) UniVTG / Moment-DETR (research code, not recommended as dependencies).
- OpenAI CLIP has the most stars but is frozen; use the same weights (or better ones) through open_clip, which is MIT and maintained.
- If the reel agent may ever be used commercially, avoid pyiqa (PolyForm NC) and aesthetic-predictor-v2-5 (AGPL-3.0 copyleft). improved-aesthetic-predictor (Apache-2.0) is the license-safe aesthetic option.

### Gaps
- Exact (unrounded) star counts and last-commit dates could not be retrieved; the GitHub API was blocked in this session. Star counts for huggingface/transformers and google-research/big_vision were not collected.
- SigLIP/SigLIP2 checkpoint license: I could not open the official HF model cards (huggingface.co blocked). A third-party repack says Apache 2.0, but this is unconfirmed — [search summary](https://huggingface.co/google/siglip2-so400m-patch14-224). Check the official card before shipping.
- open_clip's GitHub page did not show its license name in the fetch; MIT comes from PyPI metadata.
- MobileCLIP/MobileCLIP2 weights use Apple's "apple-amlr" license per one HF card — [HF](https://huggingface.co/apple/mobileclip2_coca_dfn2b_s13b_context77). I did not confirm whether commercial use is allowed.

## Q2. Which tools run reasonably on CPU, and model sizes

### Takeaway
Everything needed for photo/clip selection runs on CPU at personal-trip scale (hundreds of photos, tens of short clips). PySceneDetect, OpenCV Laplacian blur and imagededup hashing are classical CV and need no model. TransNetV2 is a small CNN on downscaled frames and is documented to work on CPU. CLIP/SigLIP base models (~86–150M params) take a fraction of a second per image on CPU. ViT-L/14 (used by the LAION aesthetic predictor) is ~428M params and SigLIP So400m is ~400M (vision tower). Both are slower but still usable for a few hundred frames. Highlight-detection DETR models are CPU-capable only through Lighthouse with CLIP-only features.

### Cited Findings
- PySceneDetect detectors: `ContentDetector` (content-aware, default), `AdaptiveDetector` (two-pass, "handles fast camera movement better") and `ThresholdDetector` (fades). The repo points to scenedetect.com/benchmarks for speed and accuracy numbers. That page was unreachable here — [GitHub](https://github.com/Breakthrough/PySceneDetect)
- TransNetV2 F1: ClipShots 77.9, BBC Planet Earth 96.2, RAI 93.9 (vs. TransNet 73.5/92.9/94.3) — [GitHub](https://github.com/soCzech/TransNetV2). The paper says it "employs dilated convolutions and operates just on small resized frames" — [arXiv 2008.04838 via search](https://vercel.hyper.ai/en/papers/1906.03363)
- The transnetv2-pytorch port supports CPU and recommends `--device cpu` for reproducible results (MPS can differ) — [PyPI](https://pypi.org/project/transnetv2-pytorch/)
- An aggregator claims TransNetV2 runs at "~200 fps" CPU-only on a single Xeon core. This is **unverified** and not traced to the paper — [EmergentMind](https://www.emergentmind.com/topics/transnet-v2)
- CLIP sizes: ViT-B/32 ≈ 151M params (87.8M vision + 63.1M text); ViT-L/14 ≈ 428M (304M vision + 123M text) — [Keras CLIP card](https://huggingface.co/keras/clip_vit_base_patch32/raw/main/README.md), [CLIP paper](https://arxiv.org/pdf/2103.00020)
- open_clip: ViT-B-32 int8 (bitsandbytes) halves MLP memory but is slightly slower (53.9 ms vs 56.9 ms per batch of 128, GPU). Higher-resolution models (336/384/448px) cost more. Notable zero-shot ImageNet scores: ViT-B-32-256 DataComp 72.8%, ViT-B-16 DataComp 73.5%, ViT-L-14 DataComp 79.2%, ViT-SO400M-14-SigLIP-384 83.1%, PE-Core-L-14-336 83.5% — [GitHub](https://github.com/mlfoundations/open_clip)
- MobileCLIP2-S0: 11.4M (image) + 42.4M (text) params, 1.5 + 1.6 ms latency (mobile). Natively supported in OpenCLIP — [HF MobileCLIP2 card / search](https://huggingface.co/apple/MobileCLIP2-B/blob/main/README.md), [apple/ml-mobileclip](https://github.com/apple/ml-mobileclip)
- SigLIP 2 sizes: B 86M, L 303M, So400m 400M, g 1B. Smaller B/16 and B/32 were improved via distillation — [arXiv 2502.14786](https://arxiv.org/html/2502.14786v1)
- pyiqa runs on `--device cuda or cpu`. The newest `qrealign` (Q-Align-style on a Qwen3.5-VL backbone) is 0.8B / 4B / 9B params and needs transformers>=5.0. Other NR metrics in the toolbox: NIMA, MUSIQ, TOPIQ-NR, DBCNN, BRISQUE, NIQE, HyperIQA, CNNIQA, QualiCLIP, MA-CLIP, AFINE — [GitHub](https://github.com/chaofengc/IQA-PyTorch)
- Katna's keyframe pipeline: LUV frame differencing, then brightness and entropy/contrast filters, K-Means on histograms, then the sharpest frame per cluster by variance of Laplacian. Uses Python multiprocessing, no GPU — [GitHub](https://github.com/keplerlab/katna)
- Lighthouse: "the inference API is available for CPU environments". For CPU it recommends `feature_name='clip'` because CLIP+SlowFast is very slow without a GPU — [GitHub](https://github.com/line/lighthouse)
- UniVTG demo "can be run on a single GPU with less than 4GB memory". It uses CLIP-B/16 features. Checkpoints are on Google Drive — [GitHub](https://github.com/showlab/UniVTG)
- Moment-DETR was tested on PyTorch 1.9 / CUDA 11.0. Pre-extracted features are ~8GB. Defaults are SlowFast + CLIP features. No CPU guidance — [GitHub](https://github.com/jayleicn/moment_detr)
- OpenCV 5.0's new DNN engine is CPU-only for now, with 80%+ ONNX coverage — [AlternativeTo](https://alternativeto.net/news/2026/6/opencv-5-brings-new-deep-neural-network-engine-stronger-onnx-support-and-faster-core/), [ai-tldr](https://ai-tldr.dev/releases/opencv-5-0-release/)

### Inferences
- Rough CPU cost tiers (inferred from parameter counts; not benchmarked):
  - Near-free: PySceneDetect ContentDetector/AdaptiveDetector, Laplacian variance, perceptual hashes.
  - Cheap: TransNetV2, MobileCLIP2-S0, CLIP/SigLIP2 base (~86–150M).
  - Moderate: ViT-L/14 (~428M; needed by improved-aesthetic-predictor), SigLIP So400m (~400M; needed by aesthetic-predictor-v2-5).
  - Heavy / GPU-advised: Q-Align-class VLM scorers (0.8–9B), SlowFast-based highlight models.
- To keep CPU cost down, run the expensive models only on 1–3 representative frames per shot (e.g., the sharpest frame by Laplacian), not on every frame.
- Compute one CLIP-family embedding per candidate frame and reuse it three ways: (1) aesthetic MLP input, (2) zero-shot tags, (3) near-duplicate cosine similarity. With ViT-L/14 this covers the LAION aesthetic predictor and tagging in one forward pass.

### Gaps
- No primary CPU throughput numbers were found for TransNetV2, PySceneDetect (benchmarks page blocked), CLIP/SigLIP on CPU, or pyiqa metrics (its efficiency benchmark numbers were not on the README).
- Parameter counts for NIMA/MUSIQ/TOPIQ inside pyiqa were not collected.

## Q3. Video highlight detection models (UniVTG, Moment-DETR, etc.): are they practical?

### Takeaway
Mostly no as a core dependency. These models are query-conditioned (text query → moments and saliency) and trained on QVHighlights-style YouTube data. Their codebases are 2021–2023 research code with Google Drive checkpoints and GPU-oriented setups. If query-driven saliency is wanted (e.g., "sunset over the ocean"), the one practical route is Lighthouse (Apache-2.0, pip-style API, CPU with CLIP features). For a personal travel trip, CLIP similarity to a few prompts plus quality scores gives a similar signal with far less machinery.

### Cited Findings
- Moment-DETR predicts moment coordinates and saliency scores from a text query on QVHighlights. Annotation data is CC BY-NC-SA 4.0 — [GitHub](https://github.com/jayleicn/moment_detr)
- UniVTG unifies moment retrieval (interval), highlight detection (curve) and video summarization (point). It has an HF Space and a Gradio demo. Last news Oct 2023 — [GitHub](https://github.com/showlab/UniVTG)
- Lighthouse: unified library for six MR-HD models (Moment-DETR, QD-DETR, EaTR, TR-DETR, UVCOM, CG-DETR). It reproduces published scores and has an inference API (`CGDETRPredictor(...).encode_video(); predict(query, video)`) — [arXiv 2408.02901](https://arxiv.org/abs/2408.02901), [GitHub](https://github.com/line/lighthouse)
- Lighthouse datasets include QVHighlights, ActivityNet Captions, Charades-STA, TaCoS and TVSum — [ACL Anthology](https://aclanthology.org/2024.emnlp-demo.6)

### Inferences
- For ≤60s reels built from short phone clips (typically 3–30s each), shot-level selection (pick the best 1–3s per shot) matters more than finding moments within long videos. These models were designed for the long-video case.
- A reasonable optional use is Lighthouse CG-DETR with `feature_name='clip'` on CPU to score saliency inside longer clips (>30s) against prompts such as "scenic view" or "people celebrating". Treat it as an add-on, not a requirement.

### Gaps
- No benchmark of these models on travel/vlog footage was found. QVHighlights is from vlogs and news, so domain fit is plausible but unverified.
- Lighthouse checkpoint licenses: the code is Apache-2.0, but checkpoints trained on CC BY-NC-SA data may carry non-commercial restrictions. Not confirmed.

## Q4. Recommended stack: (a) shot splitting, (b) quality scoring, (c) dedup, (d) zero-shot scene tagging for storyboard ordering

### Takeaway
A CPU-only, permissively licensed stack:
- (a) **PySceneDetect AdaptiveDetector** (BSD-3), with TransNetV2-PyTorch (MIT) as an optional upgrade for gradual transitions.
- (b) **OpenCV** Laplacian variance + exposure/brightness gates as hard filters, then the **LAION improved-aesthetic-predictor** (Apache-2.0, CLIP ViT-L/14 MLP) as the ranking score. pyiqa metrics (MUSIQ/TOPIQ/NIMA) only if non-commercial use is acceptable.
- (c) **imagededup PHash/DHash** for exact and near-duplicate bursts, plus CLIP-embedding cosine similarity for semantic near-duplicates.
- (d) **open_clip** (or transformers SigLIP2) zero-shot prompts ("a photo of a beach", "food", "city street", "mountain landscape", …) for tags that drive storyboard grouping and ordering.

### Cited Findings
- (a) AdaptiveDetector handles fast camera motion better than ContentDetector, which suits handheld travel footage. ThresholdDetector targets fades — [PySceneDetect](https://github.com/Breakthrough/PySceneDetect). TransNetV2 reaches 96.2 F1 on BBC Planet Earth (nature documentary), close to travel/landscape content — [TransNetV2](https://github.com/soCzech/TransNetV2)
- (b) Variance of Laplacian as a blur measure for picking the sharpest frame is an established approach; Katna uses it as its final selection step — [Katna](https://github.com/keplerlab/katna). The LAION predictor is an MLP on CLIP embeddings trained on SAC + LAION-Logos + AVA — [improved-aesthetic-predictor](https://github.com/christophschuhmann/improved-aesthetic-predictor). The SigLIP-based v2.5 predictor scores 1–10, with 5.5+ meaning "great", but it is AGPL-3.0 — [index](https://awesome.ecosyste.ms/projects/github.com%2Fdiscus0434%2Faesthetic-predictor-v2-5). pyiqa offers MUSIQ, TOPIQ-NR, NIMA, BRISQUE, NIQE, CLIP-based QualiCLIP, etc., under a non-commercial license — [IQA-PyTorch](https://github.com/chaofengc/IQA-PyTorch), [PyPI](https://pypi.org/project/pyiqa/)
- (c) imagededup supports PHash, DHash, WHash, AHash and CNN-based dedup. "Difference hashing is the fastest" — [imagededup](https://github.com/idealo/imagededup)
- (d) open_clip offers many pretrained zero-shot models. SigLIP-SO400M-384 reaches 83.1% and DataComp ViT-B-16 73.5% ImageNet zero-shot — [open_clip](https://github.com/mlfoundations/open_clip). SigLIP 2 beats SigLIP at all scales on zero-shot classification and is usable through the transformers `zero-shot-image-classification` pipeline — [arXiv 2502.14786](https://arxiv.org/html/2502.14786v1), [HF card](https://huggingface.co/google/siglip2-so400m-patch14-224)
- Katna bundles shot-agnostic keyframe extraction with blur filtering but has had no release since April 2021 — [Katna](https://github.com/keplerlab/katna), [PyPI](https://pypi.org/project/katna/)

### Inferences
Proposed pipeline (my synthesis, not from a single source):
1. **Ingest.** Read EXIF/creation time and GPS for photos and video so chronology can drive the story.
2. **Shots.** Split videos with `scenedetect` AdaptiveDetector. Drop shots under ~0.7s. Long single-take clips (common on phones) won't split, so window them into 2–4s sub-segments.
3. **Sample frames.** For each shot/sub-segment, take 3–5 frames, keep the sharpest by Laplacian variance, and reject frames that are too dark, too bright or too blurry. Thresholds need calibration per resolution: downscale to a fixed width first, because Laplacian variance depends on scale.
4. **Embed once.** Run one CLIP ViT-L/14 (open_clip, OpenAI weights) forward pass per kept frame or photo. This feeds the LAION aesthetic MLP (score) and zero-shot tag prompts (labels plus a "people / landmark / food / landscape" prior). If ViT-L/14 is too slow on CPU, use ViT-B-16 or MobileCLIP2 for tags and dedup, and run ViT-L/14 only on the top-N candidates for aesthetics.
5. **Dedup.** PHash/DHash (imagededup) at a tight Hamming threshold catches bursts and near-identical photos. Then greedily remove items whose CLIP cosine similarity to an already-selected item exceeds ~0.9 (tune it). This is effectively MMR-style diversity selection.
6. **Score and select.** Combine aesthetic score, sharpness, motion/stability (optional: optical-flow magnitude via OpenCV) and a tag-diversity bonus. Fill a 60s budget at ~1.5–3s per shot, which gives roughly 20–35 shots.
7. **Order.** Group by day/location (EXIF time/GPS), then by tag (e.g., arrival/city → food → beach/mountain → sunset/night). Tag confidence from zero-shot softmax over the prompt set decides the group.
- Swap-ins if licensing allows non-commercial use: pyiqa `topiq_nr` or `musiq` as an extra technical-quality signal. If AGPL is fine: aesthetic-predictor-v2-5 on SigLIP So400m, which reuses the same SigLIP embedding for tagging.

### Gaps
- No published evaluation was found that compares LAION aesthetic scores against human picks on personal travel photos specifically. Calibration on the user's own footage is recommended.
- The zero-shot tagging accuracy of CLIP vs. SigLIP2 on travel-scene categories (beach/food/city/mountain) was not found as a benchmark. ImageNet zero-shot is a proxy only.
- The thresholds suggested above (cosine ~0.9, shot length) are heuristics, not sourced values.
