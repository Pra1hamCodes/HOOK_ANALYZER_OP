"""Retention Curve Predictor — simulates a YouTube-style viewer retention graph.

Uses per-second attention scores, hook quality, and external drop_risk data
to model how many viewers would remain at each point in the video.

Supports platform-specific decay profiles: tiktok, reels, youtube_shorts, generic.
"""
from __future__ import annotations

import math
import logging

logger = logging.getLogger("hook_architect.retention_curve")

# ── Configuration ────────────────────────────────────────
INITIAL_VIEWERS = 100.0

# Base decay per second (even a perfect video loses some viewers naturally)
BASE_DECAY_RATE = 0.003  # 0.3% per second natural attrition

# First 3 seconds have amplified decay (short-form "thumb stop" test)
HOOK_WINDOW = 3

# Attention thresholds that accelerate viewer loss
ATTENTION_SEVERE_DROP = 35   # Below this = severe viewer loss
ATTENTION_MODERATE_DROP = 55  # Below this = moderate viewer loss
ATTENTION_GOOD = 75          # Above this = minimal extra loss

# ── Platform-specific decay profiles ─────────────────────
PLATFORM_PROFILES = {
    "tiktok": {
        "name": "TikTok",
        "description": "Aggressive early drop, stabilizes by 10s",
        "hook_window": 3,
        "hook_decay_multiplier": 5.0,      # Very punishing first 3s
        "initial_drop_multiplier": 1.5,    # 1.5x the normal initial drop
        "low_hook_penalty_per_sec": 0.03,  # -3% per second if hook_score < 70
        "low_hook_threshold": 70,
        "stabilization_target": 60.0,      # Stabilizes at ~60% by second 10
        "stabilization_second": 10,
        "late_decay_multiplier": 0.6,      # Slower decay after stabilization
        "midpoint_retention_bonus": 0.0,
        "late_acceleration_start": None,   # No late acceleration
    },
    "reels": {
        "name": "Instagram Reels",
        "description": "Moderate drop, viewers expect 15-30s content",
        "hook_window": 3,
        "hook_decay_multiplier": 3.5,
        "initial_drop_multiplier": 1.2,
        "low_hook_penalty_per_sec": 0.02,
        "low_hook_threshold": 65,
        "stabilization_target": 65.0,
        "stabilization_second": 8,
        "late_decay_multiplier": 0.8,
        "midpoint_retention_bonus": 0.0,
        "late_acceleration_start": 20,     # Decay accelerates after 20s
    },
    "youtube_shorts": {
        "name": "YouTube Shorts",
        "description": "Slowest decay, 60s tolerance, retains well if hook is strong",
        "hook_window": 3,
        "hook_decay_multiplier": 2.5,      # More forgiving hook window
        "initial_drop_multiplier": 0.8,    # Gentler initial drop
        "low_hook_penalty_per_sec": 0.015,
        "low_hook_threshold": 60,
        "stabilization_target": 70.0,      # Higher stabilization
        "stabilization_second": 8,
        "late_decay_multiplier": 0.5,      # Very slow late decay
        "midpoint_retention_bonus": 10.0,  # Retains 70% through midpoint if hook > 60
        "late_acceleration_start": None,
    },
    "generic": {
        "name": "Generic",
        "description": "Standard decay model (platform-agnostic)",
        "hook_window": 3,
        "hook_decay_multiplier": 4.0,
        "initial_drop_multiplier": 1.0,
        "low_hook_penalty_per_sec": 0.0,
        "low_hook_threshold": 0,
        "stabilization_target": 0,
        "stabilization_second": 0,
        "late_decay_multiplier": 1.0,
        "midpoint_retention_bonus": 0.0,
        "late_acceleration_start": None,
    },
}

SUPPORTED_PLATFORMS = list(PLATFORM_PROFILES.keys())


def predict_retention_curve(
    timeline: list[dict],
    hook_score_data: dict | None = None,
    external_windows: list[dict] | None = None,
    duration: float = 0,
    platform: str = "generic",
) -> dict:
    """Predict a viewer retention curve from analysis data.
    
    Args:
        timeline: Per-second timeline from fusion engine with 'attention' scores
        hook_score_data: Optional hook score data for calibrating opening decay
        external_windows: Optional 2s windows from external API with drop_risk flags
        duration: Video duration in seconds
        platform: Target platform (tiktok, reels, youtube_shorts, generic)
    
    Returns:
        {curve_points[], predicted_avg_retention, predicted_watch_through_rate,
         key_moments[], retention_grade, sections_analysis, platform, platform_name}
    """
    total_seconds = max(1, len(timeline))
    if duration > 0:
        total_seconds = max(total_seconds, int(duration))

    # ── Resolve platform profile ─────────────────────────
    profile = PLATFORM_PROFILES.get(platform, PLATFORM_PROFILES["generic"])
    is_platform_specific = platform != "generic"

    # ── Build external drop_risk lookup ──────────────────
    external_drop_map = {}
    ext_energy_map = {}
    if external_windows:
        for w in external_windows:
            start = int(w.get("start", 0))
            end = int(w.get("end", start + 2))
            is_drop = w.get("drop_risk", False)
            ve = w.get("visual_energy", 5)
            for t in range(start, min(end, total_seconds)):
                external_drop_map[t] = is_drop
                ext_energy_map[t] = ve

    # ── Get hook quality modifier ────────────────────────
    hook_quality = 0.5  # neutral default
    hook_score_raw = 50
    if hook_score_data:
        hook_score_raw = hook_score_data.get("hook_score", 50)
        hook_quality = hook_score_raw / 100.0

    # ── Simulate retention curve ─────────────────────────
    curve_points = []
    viewers = INITIAL_VIEWERS
    key_moments = []

    for t in range(total_seconds):
        # Record current state
        curve_points.append({
            "t": t,
            "retention_pct": round(viewers, 2),
            "viewers_remaining": round(viewers, 2),
        })

        if t >= total_seconds - 1:
            break

        # ── Calculate decay for this second ──────────────
        attention = 50.0
        if t < len(timeline):
            attention = timeline[t].get("attention", 50)

        decay = BASE_DECAY_RATE

        # Hook window: first N seconds have amplified decay based on hook quality
        hook_win = profile["hook_window"]
        if t < hook_win:
            hook_modifier = 1.0 + (1.0 - hook_quality) * profile["hook_decay_multiplier"]
            decay *= hook_modifier

            # Very first second has the steepest natural drop
            if t == 0:
                initial_drop = (1.0 - hook_quality) * 0.08 * profile["initial_drop_multiplier"]
                viewers -= viewers * initial_drop

            # Platform-specific: extra penalty if hook is weak
            if is_platform_specific and hook_score_raw < profile["low_hook_threshold"]:
                decay += profile["low_hook_penalty_per_sec"]

        # ── Platform-specific: stabilization behavior ────
        if is_platform_specific and profile["stabilization_second"] > 0:
            stab_sec = profile["stabilization_second"]
            if t >= stab_sec:
                # After stabilization: use reduced decay
                decay *= profile["late_decay_multiplier"]

        # ── Platform-specific: late acceleration (reels) ─
        if is_platform_specific and profile.get("late_acceleration_start"):
            if t >= profile["late_acceleration_start"]:
                # Decay accelerates in the later part of the video
                late_factor = 1.0 + (t - profile["late_acceleration_start"]) * 0.05
                decay *= min(late_factor, 3.0)

        # ── Platform-specific: midpoint retention bonus (youtube_shorts) ──
        if is_platform_specific and profile["midpoint_retention_bonus"] > 0:
            midpoint = total_seconds // 2
            if t >= midpoint - 2 and t <= midpoint + 2 and hook_score_raw >= profile["low_hook_threshold"]:
                # Reduce decay near midpoint for strong-hooked videos
                decay *= 0.3

        # Attention-based decay
        if attention < ATTENTION_SEVERE_DROP:
            severity = (ATTENTION_SEVERE_DROP - attention) / ATTENTION_SEVERE_DROP
            decay += 0.04 * severity
        elif attention < ATTENTION_MODERATE_DROP:
            severity = (ATTENTION_MODERATE_DROP - attention) / (ATTENTION_MODERATE_DROP - ATTENTION_SEVERE_DROP)
            decay += 0.015 * severity
        elif attention >= ATTENTION_GOOD:
            decay *= 0.5

        # External drop_risk amplifier
        if external_drop_map.get(t, False):
            decay *= 1.8
            ext_e = ext_energy_map.get(t, 5)
            if ext_e < 3:
                decay *= 1.3

        # Apply decay
        viewers = max(0, viewers * (1 - decay))

        # ── Detect key moments ───────────────────────────
        if t > 0:
            prev_viewers = curve_points[-1]["viewers_remaining"] if curve_points else 100
            drop_pct = prev_viewers - viewers
            if drop_pct > 3.0:
                key_moments.append({
                    "t": t,
                    "event": "sharp_drop",
                    "description": f"Sharp viewer drop at {_fmt(t)}: lost {drop_pct:.1f}% viewers",
                    "retention_at": round(viewers, 1),
                })
            elif t > 0 and len(curve_points) >= 2:
                if len(curve_points) >= 3:
                    prev_drop = curve_points[-2]["viewers_remaining"] - curve_points[-1]["viewers_remaining"]
                    curr_drop = curve_points[-1]["viewers_remaining"] - viewers
                    if prev_drop > 2 and curr_drop < 0.5:
                        key_moments.append({
                            "t": t,
                            "event": "stabilization",
                            "description": f"Viewer retention stabilizes at {_fmt(t)} ({viewers:.0f}%)",
                            "retention_at": round(viewers, 1),
                        })

    # ── Mark the hook moment ─────────────────────────────
    if len(curve_points) > 3:
        hook_retention = curve_points[3]["retention_pct"]
        quality_label = "strong" if hook_retention > 85 else "average" if hook_retention > 70 else "weak"
        key_moments.insert(0, {
            "t": 3,
            "event": "hook_test",
            "description": f"After 3s hook window: {hook_retention:.0f}% viewers remain ({quality_label})",
            "retention_at": round(hook_retention, 1),
        })

    # ── Compute summary metrics ──────────────────────────
    avg_retention = sum(p["retention_pct"] for p in curve_points) / len(curve_points)
    watch_through = curve_points[-1]["retention_pct"] if curve_points else 0

    # ── Grade ────────────────────────────────────────────
    if avg_retention >= 75:
        grade = "Exceptional"
    elif avg_retention >= 60:
        grade = "Good"
    elif avg_retention >= 45:
        grade = "Average"
    elif avg_retention >= 30:
        grade = "Below Average"
    else:
        grade = "Critical"

    # ── Sections analysis (thirds) ───────────────────────
    third = max(1, len(curve_points) // 3)
    first_third = curve_points[:third]
    mid_third = curve_points[third:2 * third]
    last_third = curve_points[2 * third:]

    sections = {
        "opening": {
            "start_retention": first_third[0]["retention_pct"] if first_third else 100,
            "end_retention": first_third[-1]["retention_pct"] if first_third else 100,
            "drop": round((first_third[0]["retention_pct"] - first_third[-1]["retention_pct"]) if first_third else 0, 1),
        },
        "middle": {
            "start_retention": round(mid_third[0]["retention_pct"], 1) if mid_third else 0,
            "end_retention": round(mid_third[-1]["retention_pct"], 1) if mid_third else 0,
            "drop": round((mid_third[0]["retention_pct"] - mid_third[-1]["retention_pct"]) if mid_third else 0, 1),
        },
        "closing": {
            "start_retention": round(last_third[0]["retention_pct"], 1) if last_third else 0,
            "end_retention": round(last_third[-1]["retention_pct"], 1) if last_third else 0,
            "drop": round((last_third[0]["retention_pct"] - last_third[-1]["retention_pct"]) if last_third else 0, 1),
        },
    }

    return {
        "curve_points": curve_points,
        "predicted_avg_retention": round(avg_retention, 1),
        "predicted_watch_through_rate": round(watch_through, 1),
        "key_moments": key_moments,
        "retention_grade": grade,
        "sections_analysis": sections,
        "total_seconds": total_seconds,
        "platform": platform,
        "platform_name": profile["name"],
        "platform_description": profile["description"],
    }


def _fmt(seconds: float) -> str:
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m}:{s:02d}"
