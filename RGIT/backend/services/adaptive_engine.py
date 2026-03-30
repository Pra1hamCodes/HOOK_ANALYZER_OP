"""Adaptive Feedback Loop — EMA-based weight adjustment after each video analysis.

After every video upload, this engine:
1. Records the analysis metrics to video_history (with niche qualification + weights snapshot)
2. Compares against the user's running averages
3. Nudges weights toward consistently strong/weak signals using EMA
4. Saves a snapshot of the updated weights for audit trail
"""
from __future__ import annotations

import logging
from core.database import (
    get_profile,
    get_video_history,
    record_video,
    update_profile_weights,
    increment_video_count,
    extract_weights_from_profile,
)
from core.persona_presets import PERSONA_PRESETS

logger = logging.getLogger("hook_architect.adaptive")

# EMA smoothing factor — lower = slower learning (more stable)
EMA_ALPHA = 0.15

# Bounds: no weight can drop below MIN or exceed MAX
WEIGHT_MIN = 0.05
WEIGHT_MAX = 0.60

# Minimum videos before adaptation kicks in (avoids overreacting to first upload)
MIN_VIDEOS_FOR_ADAPTATION = 2

# Threshold bounds
THRESHOLD_MIN = 30.0
THRESHOLD_MAX = 90.0


def _determine_niche_qualification(video_nature: str, dominant_emotion: str, 
                                     overall_score: float) -> str:
    """Determine which niche category this video qualifies for based on its content."""
    nature_to_niche = {
        "educational": "educational",
        "documentary": "educational",
        "medical": "educational",
        "motivation": "action",
        "hype": "action",
        "cinematic": "cinematic",
    }
    
    base_niche = nature_to_niche.get(video_nature, "vlog")
    
    # Emotional override
    emotional_emotions = {"sad", "sad/bored", "anxious/hesitant"}
    if dominant_emotion in emotional_emotions:
        base_niche = "emotional"
    elif dominant_emotion in {"excited", "angry"}:
        if base_niche not in {"action", "music"}:
            base_niche = "action"
    
    # Find the label from presets
    preset = PERSONA_PRESETS.get(base_niche, {})
    label = preset.get("label", base_niche.capitalize())
    
    return f"{label}"


def record_and_adapt(
    user_id: str,
    filename: str,
    duration: float,
    overall_score: float,
    audio_signals: list[dict],
    visual_signals: list[dict],
    transcript_score: float,
    emotion_alignment: float,
    dominant_emotion: str,
    video_nature: str,
    timeline: list[dict],
    semantic_data: dict | None = None,
    user_weights: dict | None = None,
) -> dict:
    """
    Record a completed analysis and adapt the user's weights.
    
    Returns a dict with:
      - recorded: bool
      - adapted: bool
      - weight_changes: dict of field -> (old, new) for any changed weights
      - niche_qualification: str — what niche this video qualified for
    """
    # ── 1. Compute averages from the analysis ─────────────
    audio_avg = _safe_avg([s["audio_score"] for s in audio_signals]) if audio_signals else 0.0
    visual_avg = _safe_avg([s["visual_score"] for s in visual_signals]) if visual_signals else 0.0

    # Zone distribution
    zone_dist = {"green": 0, "yellow": 0, "red": 0}
    for t in timeline:
        z = t.get("zone", "red")
        zone_dist[z] = zone_dist.get(z, 0) + 1

    # Niche qualification
    niche_qualification = _determine_niche_qualification(video_nature, dominant_emotion, overall_score)

    # ── 2. Record the video with enriched metadata ────────
    record_video(user_id, {
        "filename": filename,
        "duration": duration,
        "overall_score": overall_score,
        "audio_avg": audio_avg,
        "visual_avg": visual_avg,
        "transcript_score": transcript_score,
        "emotion_alignment": emotion_alignment,
        "dominant_emotion": dominant_emotion,
        "video_nature": video_nature,
        "zone_distribution": zone_dist,
        "niche_qualification": niche_qualification,
        "weights_snapshot": user_weights or {},
        "semantic_summary": semantic_data or {},
    })
    increment_video_count(user_id)

    # ── 3. Check if we should adapt ──────────────────────
    profile = get_profile(user_id)
    if not profile:
        return {"recorded": True, "adapted": False, "weight_changes": {}, 
                "niche_qualification": niche_qualification}

    if profile["video_count"] < MIN_VIDEOS_FOR_ADAPTATION:
        logger.info(f"[ADAPTIVE] User {user_id}: {profile['video_count']} videos — skipping adaptation (min={MIN_VIDEOS_FOR_ADAPTATION})")
        return {"recorded": True, "adapted": False, "weight_changes": {},
                "niche_qualification": niche_qualification}

    # ── 4. Compute running averages from history ─────────
    history = get_video_history(user_id, limit=20)  # last 20 videos
    if len(history) < MIN_VIDEOS_FOR_ADAPTATION:
        return {"recorded": True, "adapted": False, "weight_changes": {},
                "niche_qualification": niche_qualification}

    hist_audio_avg = _safe_avg([h["audio_avg"] for h in history])
    hist_visual_avg = _safe_avg([h["visual_avg"] for h in history])
    hist_transcript_avg = _safe_avg([h["transcript_score"] for h in history])
    hist_emotion_avg = _safe_avg([h["emotion_alignment"] for h in history])
    hist_score_avg = _safe_avg([h["overall_score"] for h in history])

    # ── 5. EMA weight nudging ────────────────────────────
    current_weights = extract_weights_from_profile(profile)
    new_weights = dict(current_weights)
    changes = {}

    # Signal strength: how much each signal contributes to high-scoring videos
    signal_map = {
        "audio_weight": hist_audio_avg,
        "visual_weight": hist_visual_avg,
        "transcript_weight": hist_transcript_avg,
    }

    for weight_key, signal_avg in signal_map.items():
        old_val = current_weights[weight_key]
        signal_strength = (signal_avg - 50.0) / 100.0
        nudge = EMA_ALPHA * signal_strength * 0.1
        new_val = _clamp(old_val + nudge, WEIGHT_MIN, WEIGHT_MAX)
        new_val = round(new_val, 4)

        if abs(new_val - old_val) > 0.0001:
            new_weights[weight_key] = new_val
            changes[weight_key] = {"old": round(old_val, 4), "new": new_val}

    # Emotion alignment affects engagement weight
    if hist_emotion_avg > 60:
        nudge = EMA_ALPHA * 0.02
    elif hist_emotion_avg < 40:
        nudge = -EMA_ALPHA * 0.02
    else:
        nudge = 0.0

    if nudge != 0.0:
        old_eng = current_weights["engagement_weight"]
        new_eng = _clamp(old_eng + nudge, WEIGHT_MIN, WEIGHT_MAX)
        new_eng = round(new_eng, 4)
        if abs(new_eng - old_eng) > 0.0001:
            new_weights["engagement_weight"] = new_eng
            changes["engagement_weight"] = {"old": round(old_eng, 4), "new": new_eng}

    # Threshold adaptation
    if hist_score_avg > 70 and profile["video_count"] >= 5:
        old_green = current_weights["green_threshold"]
        new_green = _clamp(old_green + EMA_ALPHA * 1.0, THRESHOLD_MIN, THRESHOLD_MAX)
        new_green = round(new_green, 1)
        if abs(new_green - old_green) > 0.05:
            new_weights["green_threshold"] = new_green
            changes["green_threshold"] = {"old": old_green, "new": new_green}

    # ── 6. Apply if anything changed ─────────────────────
    if changes:
        update_profile_weights(user_id, new_weights, trigger="auto_adapt")
        logger.info(f"[ADAPTIVE] User {user_id}: adapted weights — {changes}")
    else:
        logger.info(f"[ADAPTIVE] User {user_id}: no weight changes needed")

    return {
        "recorded": True,
        "adapted": bool(changes),
        "weight_changes": changes,
        "niche_qualification": niche_qualification,
    }


def _safe_avg(values: list[float]) -> float:
    """Average that doesn't crash on empty lists."""
    if not values:
        return 0.0
    return sum(values) / len(values)


def _clamp(value: float, lo: float, hi: float) -> float:
    """Clamp a value between lo and hi."""
    return max(lo, min(hi, value))
