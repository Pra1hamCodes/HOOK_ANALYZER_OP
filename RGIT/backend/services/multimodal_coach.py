"""Multimodal Coach — LLaVA integration via Ollama for visual frame analysis.

Functions:
  1. analyze_frame_context   — single frame visual diagnosis
  2. critique_hook_frames    — first 3 frames hook critique
  3. diagnose_red_zone       — red zone visual cause + fix

All functions are async, return None gracefully on failure, and respect
the MULTIMODAL_LLM_ENABLED environment variable.
"""
from __future__ import annotations

import asyncio
import base64
import logging
import os
from pathlib import Path

logger = logging.getLogger("hook_architect.multimodal_coach")

ENABLED = os.getenv("MULTIMODAL_LLM_ENABLED", "false").lower() == "true"
MODEL = os.getenv("OLLAMA_MODEL", "llava:7b")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
CALL_TIMEOUT = 15.0  # per-call timeout
TOTAL_BUDGET = 20.0  # total gather timeout


def _check_enabled() -> bool:
    """Re-check env at call time (can be toggled at startup)."""
    return os.getenv("MULTIMODAL_LLM_ENABLED", "false").lower() == "true"


def _encode_image(frame_path: str) -> str | None:
    """Base64 encode an image file."""
    try:
        with open(frame_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception as e:
        logger.warning(f"[MULTIMODAL] Failed to encode image {frame_path}: {e}")
        return None


def _find_frame(frames_dir: str, second: int) -> str | None:
    """Find the frame file for a given second."""
    d = Path(frames_dir)
    # Try common naming patterns
    for pattern in [f"frame_{second:04d}.jpg", f"frame_{second:05d}.jpg",
                    f"frame_{second:03d}.jpg", f"frame_{second}.jpg"]:
        candidate = d / pattern
        if candidate.exists():
            return str(candidate)
    # Fallback: glob and pick closest
    frames = sorted(d.glob("frame_*.jpg"))
    if second < len(frames):
        return str(frames[second])
    if frames:
        return str(frames[-1])
    return None


async def _ollama_chat(prompt: str, images: list[str] | None = None) -> str | None:
    """Call Ollama LLaVA with timeout. Returns response text or None."""
    if not _check_enabled():
        return None
    try:
        import ollama as ollama_client

        message = {"role": "user", "content": prompt}
        if images:
            message["images"] = images

        # Run in executor since ollama client is synchronous
        loop = asyncio.get_event_loop()

        def _call():
            client = ollama_client.Client(host=OLLAMA_HOST)
            response = client.chat(model=MODEL, messages=[message])
            return response["message"]["content"]

        result = await asyncio.wait_for(
            loop.run_in_executor(None, _call),
            timeout=CALL_TIMEOUT,
        )
        return result
    except asyncio.TimeoutError:
        logger.warning(f"[MULTIMODAL] Ollama call timed out after {CALL_TIMEOUT}s")
        return None
    except ImportError:
        logger.warning("[MULTIMODAL] ollama package not installed")
        return None
    except Exception as e:
        logger.warning(f"[MULTIMODAL] Ollama call failed: {e}")
        return None


# ═══════════════════════════════════════════════════════════
# FUNCTION 1: Analyze Frame Context
# ═══════════════════════════════════════════════════════════

async def analyze_frame_context(
    frame_path: str,
    timestamp: float,
    audio_score: float,
    zone: str,
) -> dict | None:
    """Send a single frame to LLaVA for visual engagement analysis."""
    if not _check_enabled():
        return None

    img_b64 = _encode_image(frame_path)
    if not img_b64:
        return None

    prompt = (
        f"You are a short-form video retention expert. This frame is from second {timestamp:.1f} "
        f"of a video. The audio engagement score at this moment is {audio_score:.0f}/100. "
        f"The zone is {zone} (green=engaging, yellow=moderate, red=dropping off).\n\n"
        "In 2-3 sentences max, describe:\n"
        "1. What visual elements are present and how engaging they appear\n"
        "2. One specific visual improvement for this exact frame\n\n"
        "Be direct and specific. No preamble."
    )

    text = await _ollama_chat(prompt, images=[img_b64])
    if not text:
        return None

    # Parse into structured output
    lines = text.strip().split("\n")
    description = lines[0] if lines else text
    fix = lines[-1] if len(lines) > 1 else ""

    return {
        "timestamp": timestamp,
        "visual_description": description.strip(),
        "visual_fix": fix.strip(),
    }


# ═══════════════════════════════════════════════════════════
# FUNCTION 2: Critique Hook Frames
# ═══════════════════════════════════════════════════════════

async def critique_hook_frames(
    frames_dir: str,
    hook_score: float,
    hook_grade: str,
    transcript_first3s: str,
) -> dict | None:
    """Analyze first 3 frames (t=0,1,2) for hook quality."""
    if not _check_enabled():
        return None

    images = []
    for t in range(3):
        fp = _find_frame(frames_dir, t)
        if fp:
            img = _encode_image(fp)
            if img:
                images.append(img)

    if not images:
        return None

    prompt = (
        f"You are analyzing the hook (first 3 seconds) of a short-form video.\n"
        f"Hook score: {hook_score:.0f}/100. Grade: {hook_grade}.\n"
        f"What was said: '{transcript_first3s}'\n\n"
        "These are frames from second 0, 1, and 2.\n\n"
        "Answer these 3 questions briefly:\n"
        "1. What is the viewer's first visual impression?\n"
        "2. What is the single biggest visual weakness in these 3 frames?\n"
        "3. What ONE visual change would most improve the hook?\n\n"
        "Be specific about what you actually see. Max 4 sentences total."
    )

    text = await _ollama_chat(prompt, images=images)
    if not text:
        return None

    # Parse response
    lines = [l.strip() for l in text.strip().split("\n") if l.strip()]
    impression = lines[0] if len(lines) > 0 else text
    weakness = lines[1] if len(lines) > 1 else ""
    fix = lines[2] if len(lines) > 2 else ""

    return {
        "hook_visual_impression": impression,
        "hook_visual_weakness": weakness,
        "hook_visual_fix": fix,
        "grade": hook_grade,
    }


# ═══════════════════════════════════════════════════════════
# FUNCTION 3: Diagnose Red Zone
# ═══════════════════════════════════════════════════════════

async def diagnose_red_zone(
    zone_start: int,
    zone_end: int,
    frames_dir: str,
    zone_flags: list,
    transcript_segment: str,
) -> dict | None:
    """Analyze 2 frames from a red zone for drop-off diagnosis."""
    if not _check_enabled():
        return None

    # Pick 2 evenly spaced frames within the zone
    span = max(zone_end - zone_start, 1)
    t1 = zone_start + span // 3
    t2 = zone_start + (2 * span) // 3

    images = []
    for t in [t1, t2]:
        fp = _find_frame(frames_dir, t)
        if fp:
            img = _encode_image(fp)
            if img:
                images.append(img)

    if not images:
        return None

    flags_str = ", ".join(str(f) for f in zone_flags) if zone_flags else "none"
    transcript_clip = (transcript_segment or "")[:200]

    prompt = (
        f"A short-form video is losing viewers between second {zone_start} and {zone_end}.\n"
        f"Audio/transcript issues detected: {flags_str}.\n"
        f"Transcript in this segment: '{transcript_clip}'\n\n"
        "Look at these frames from this time window.\n\n"
        "In 3 sentences max:\n"
        "1. What do you visually see that could cause viewer drop-off?\n"
        "2. Give one specific visual fix (cut, overlay, zoom, text, B-roll suggestion)\n\n"
        "Be concrete — reference what you actually see in the frames."
    )

    text = await _ollama_chat(prompt, images=images)
    if not text:
        return None

    lines = [l.strip() for l in text.strip().split("\n") if l.strip()]
    cause = lines[0] if len(lines) > 0 else text
    fix = lines[-1] if len(lines) > 1 else ""

    return {
        "visual_cause": cause,
        "visual_fix": fix,
        "zone_start": zone_start,
        "zone_end": zone_end,
    }


# ═══════════════════════════════════════════════════════════
# UTILITY: Extract transcript segment by time range
# ═══════════════════════════════════════════════════════════

def extract_transcript_segment(
    transcript: str,
    start: float,
    end: float,
    total_duration: float | None = None,
) -> str:
    """Approximate transcript segment for a time range."""
    if not transcript:
        return ""
    words = transcript.split()
    if not words:
        return ""
    if total_duration and total_duration > 0:
        wps = len(words) / total_duration
        start_word = int(start * wps)
        end_word = int(end * wps)
        return " ".join(words[start_word:end_word])
    return transcript[:200]
