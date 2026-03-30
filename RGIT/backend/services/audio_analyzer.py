"""Audio Signal Analyzer — librosa-based vocal energy, pitch, pacing, silence detection."""
from __future__ import annotations

import numpy as np
import librosa

from models.schemas import AudioSignal
from core.config import AUDIO_CHUNK_DURATION


def analyze_audio(audio_path: str, duration: float) -> list[dict]:
    """
    Analyze an audio file and return per-second audio signals.

    Returns a list of AudioSignal-compatible dicts with:
      - energy (RMS loudness, 0-100)
      - pitch_variation (Hz std dev in window)
      - pacing (onset rate)
      - silence_flag
      - audio_score (composite 0-100)
    """
    # Load audio — handle videos with no audio track gracefully
    try:
        y, sr = librosa.load(str(audio_path), sr=22050, mono=True)
    except Exception:
        # No audio track or unreadable audio — return zero scores
        total_seconds = int(duration)
        return [
            {
                "timestamp": float(t),
                "energy": 0.0,
                "pitch_variation": 0.0,
                "pacing": 0.0,
                "silence_flag": True,
                "audio_score": 0.0,
            }
            for t in range(total_seconds)
        ]

    if len(y) == 0:
        total_seconds = int(duration)
        return [
            {
                "timestamp": float(t),
                "energy": 0.0,
                "pitch_variation": 0.0,
                "pacing": 0.0,
                "silence_flag": True,
                "audio_score": 0.0,
            }
            for t in range(total_seconds)
        ]


    total_seconds = int(duration)

    # ── Pre-compute full-track features ──────────────────
    hop_length = 512
    frame_length = 2048

    # RMS energy per frame
    rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
    rms_times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop_length)

    # Pitch (F0) via pyin
    f0, voiced_flag, _ = librosa.pyin(
        y, fmin=librosa.note_to_hz("C2"), fmax=librosa.note_to_hz("C7"),
        sr=sr, hop_length=hop_length,
    )
    f0_times = librosa.frames_to_time(np.arange(len(f0)), sr=sr, hop_length=hop_length)

    # Onset strength (pacing)
    onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop_length)
    onset_times = librosa.frames_to_time(np.arange(len(onset_env)), sr=sr, hop_length=hop_length)

    # Global stats for normalization
    rms_mean = float(np.mean(rms)) if len(rms) > 0 else 1.0
    rms_max = float(np.max(rms)) if len(rms) > 0 else 1.0

    signals: list[dict] = []

    for t in range(total_seconds):
        t_start = float(t)
        t_end = t_start + AUDIO_CHUNK_DURATION

        # ── Energy (RMS) ─────────────────────────────────
        mask = (rms_times >= t_start) & (rms_times < t_end)
        chunk_rms = rms[mask]
        if len(chunk_rms) == 0:
            energy = 0.0
        else:
            energy = float(np.mean(chunk_rms))
        # Normalize to 0-100
        energy_score = min(100.0, (energy / max(rms_max, 1e-6)) * 100)

        # ── Pitch variation ──────────────────────────────
        mask_f0 = (f0_times >= t_start) & (f0_times < t_end)
        chunk_f0 = f0[mask_f0]
        chunk_f0_valid = chunk_f0[~np.isnan(chunk_f0)]
        if len(chunk_f0_valid) >= 2:
            pitch_std = float(np.std(chunk_f0_valid))
        else:
            pitch_std = 0.0
        # Normalize: 0-50 Hz std → 0-100
        pitch_score = min(100.0, (pitch_std / 50.0) * 100)

        # ── Pacing (onset rate) ──────────────────────────
        mask_onset = (onset_times >= t_start) & (onset_times < t_end)
        chunk_onset = onset_env[mask_onset]
        if len(chunk_onset) > 0:
            pacing = float(np.mean(chunk_onset))
        else:
            pacing = 0.0
        # Normalize against a reasonable max
        onset_max = float(np.max(onset_env)) if len(onset_env) > 0 else 1.0
        pacing_score = min(100.0, (pacing / max(onset_max, 1e-6)) * 100)

        # ── Silence detection ────────────────────────────
        silence_threshold = rms_mean * 0.15
        silence_flag = energy < silence_threshold

        # ── Composite audio score ────────────────────────
        # Weighted average of individual signals
        audio_score = (
            0.40 * energy_score
            + 0.30 * pitch_score
            + 0.20 * pacing_score
            + 0.10 * (0.0 if silence_flag else 100.0)
        )

        signals.append({
            "timestamp": t_start,
            "energy": round(energy_score, 1),
            "pitch_variation": round(pitch_score, 1),
            "pacing": round(pacing_score, 1),
            "silence_flag": silence_flag,
            "audio_score": round(audio_score, 1),
        })

    return signals
