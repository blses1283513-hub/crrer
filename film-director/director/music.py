"""Beat, downbeat and energy analysis of the soundtrack (librosa, CPU only)."""
from __future__ import annotations

import numpy as np


def analyze_music(path: str) -> dict:
    import librosa

    y, sr = librosa.load(path, sr=22050, mono=True)
    duration = len(y) / sr
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    tempo, beat_frames = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr)
    beats = librosa.frames_to_time(beat_frames, sr=sr)
    if len(beats) < 8:
        raise SystemExit(f"Could not find a steady beat in {path}; pick a track with a clearer rhythm.")

    # Downbeats: choose the 4-beat phase whose beats carry the strongest onsets.
    strength = onset_env[np.clip(beat_frames, 0, len(onset_env) - 1)]
    phase = int(np.argmax([strength[p::4].sum() for p in range(4)]))
    downbeats = beats[phase::4]

    # Loudness per beat, normalized 0-1, drives how fast the edit cuts.
    rms = librosa.feature.rms(y=y)[0]
    rms_t = librosa.frames_to_time(np.arange(len(rms)), sr=sr)
    edges = np.append(beats, duration)
    energy = np.array([rms[(rms_t >= a) & (rms_t < b)].mean() if np.any((rms_t >= a) & (rms_t < b)) else 0.0
                       for a, b in zip(edges[:-1], edges[1:])])
    if energy.max() > energy.min():
        energy = (energy - energy.min()) / (energy.max() - energy.min())

    return {
        "path": path,
        "duration": round(float(duration), 3),
        "tempo": round(float(np.atleast_1d(tempo)[0]), 1),
        "beats": [round(float(b), 3) for b in beats],
        "downbeats": [round(float(b), 3) for b in downbeats],
        "energy": [round(float(e), 3) for e in energy],
    }


def best_window(music: dict, length: float) -> float:
    """Start time (on a downbeat) of the loudest `length`-second window."""
    if music["duration"] <= length + 0.5:
        return 0.0
    beats, energy = np.array(music["beats"]), np.array(music["energy"])
    best, best_score = 0.0, -1.0
    for db in music["downbeats"]:
        if db + length > music["duration"]:
            break
        mask = (beats >= db) & (beats < db + length)
        score = energy[mask].mean() if mask.any() else 0
        score -= 0.002 * db  # prefer earlier windows when they are close
        if score > best_score:
            best, best_score = float(db), float(score)
    return best
