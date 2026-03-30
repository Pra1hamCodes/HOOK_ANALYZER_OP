"""External API Client — calls the remote video analysis endpoints with graceful fallback.

Endpoints:
  POST /transcribe_and_summarize — Groq Whisper + Llama niche detection
  POST /analyze_video — 2s window analysis with visual_energy, motion_level, drop_risk
"""
from __future__ import annotations

import os
import logging
from pathlib import Path

logger = logging.getLogger("hook_architect.external_api")

EXTERNAL_API_URL = os.getenv("EXTERNAL_API_URL", "https://4hfvh1dh-5000.inc1.devtunnels.ms")
EXTERNAL_API_TIMEOUT = 120  # seconds — video processing can be slow


def call_transcribe(audio_path: str) -> dict | None:
    """Send audio to external API for Groq Whisper transcription + niche detection.
    
    Returns: {niche, transcription, summary, supported_niches} or None on failure.
    """
    try:
        import httpx
    except ImportError:
        logger.warning("[EXTERNAL_API] httpx not installed — skipping external transcription")
        return None

    file_path = Path(audio_path)
    if not file_path.exists():
        logger.error(f"[EXTERNAL_API] Audio file not found: {audio_path}")
        return None

    try:
        # Determine MIME type from extension
        ext = file_path.suffix.lower()
        mime_map = {".wav": "audio/wav", ".mp3": "audio/mpeg", ".m4a": "audio/mp4",
                    ".ogg": "audio/ogg", ".flac": "audio/flac"}
        mime = mime_map.get(ext, "audio/mpeg")

        with open(audio_path, "rb") as f:
            files = {"audio": (file_path.name, f, mime)}
            with httpx.Client(timeout=EXTERNAL_API_TIMEOUT, verify=False) as client:
                resp = client.post(f"{EXTERNAL_API_URL}/transcribe_and_summarize", files=files)

        if resp.status_code == 200:
            data = resp.json()
            logger.info(f"[EXTERNAL_API] Transcription OK — niche={data.get('niche')}, "
                       f"transcript_len={len(data.get('transcription', ''))}")
            return data
        else:
            logger.warning(f"[EXTERNAL_API] Transcription failed: {resp.status_code} — {resp.text[:200]}")
            return None

    except Exception as e:
        logger.warning(f"[EXTERNAL_API] Transcription call failed: {e}")
        return None


def call_analyze_video(video_path: str, niche: str = "general") -> dict | None:
    """Send video to external API for 2s-window analysis.
    
    Returns: {status, niche, duration_seconds, overall_score, total_windows,
              drop_zones_count, analysis_windows[], drop_zones[]} or None on failure.
    """
    try:
        import httpx
    except ImportError:
        logger.warning("[EXTERNAL_API] httpx not installed — skipping external video analysis")
        return None

    file_path = Path(video_path)
    if not file_path.exists():
        logger.error(f"[EXTERNAL_API] Video file not found: {video_path}")
        return None

    try:
        ext = file_path.suffix.lower()
        mime_map = {".mp4": "video/mp4", ".avi": "video/x-msvideo", ".mov": "video/quicktime",
                    ".mkv": "video/x-matroska", ".webm": "video/webm", ".flv": "video/x-flv"}
        mime = mime_map.get(ext, "video/mp4")

        with open(video_path, "rb") as f:
            files = {"video": (file_path.name, f, mime)}
            data_fields = {"niche": niche}
            with httpx.Client(timeout=EXTERNAL_API_TIMEOUT, verify=False) as client:
                resp = client.post(f"{EXTERNAL_API_URL}/analyze_video",
                                   files=files, data=data_fields)

        if resp.status_code == 200:
            result = resp.json()
            windows = result.get("analysis_windows", [])
            drops = result.get("drop_zones", [])
            logger.info(f"[EXTERNAL_API] Video analysis OK — {len(windows)} windows, "
                       f"{len(drops)} drop zones, score={result.get('overall_score')}")
            return result
        else:
            logger.warning(f"[EXTERNAL_API] Video analysis failed: {resp.status_code} — {resp.text[:200]}")
            return None

    except Exception as e:
        logger.warning(f"[EXTERNAL_API] Video analysis call failed: {e}")
        return None
