"""Persona presets — niche-specific weight dictionaries for the scoring engine.

Each preset is a real-world tuned weight configuration. The weights control how
the fusion engine scores videos, making the system subjective to the creator's niche.

Special rewards:
  - slow_pacing_reward: added to engagement_bonus when slow_pacing flag is present
    (turns a "fault" into a "strength" for cinematic/emotional content)
  - high_energy_reward: added to engagement_bonus when energy > 60
    (amplifies high-energy content for action/music creators)
"""
from __future__ import annotations


# ═══════════════════════════════════════════════════════════
# NICHE PRESET DEFINITIONS
# ═══════════════════════════════════════════════════════════

PERSONA_PRESETS: dict[str, dict] = {
    "emotional": {
        "label": "Emotional / Storytelling",
        "icon": "🎭",
        "description": "Optimized for emotional narratives — slow pacing is rewarded, vocal expressiveness matters most.",
        "audio_weight": 0.40,
        "visual_weight": 0.20,
        "transcript_weight": 0.35,
        "song_weight": 0.25,
        "temporal_weight": 0.10,
        "engagement_weight": 0.10,
        "green_threshold": 70.0,
        "yellow_threshold": 40.0,
        "slow_pacing_reward": 15.0,
        "high_energy_reward": 0.0,
    },
    "action": {
        "label": "Action / High-Energy",
        "icon": "🔥",
        "description": "Fast cuts, high motion, and intense audio are king. Static moments are penalized.",
        "audio_weight": 0.25,
        "visual_weight": 0.45,
        "transcript_weight": 0.15,
        "song_weight": 0.35,
        "temporal_weight": 0.25,
        "engagement_weight": 0.25,
        "green_threshold": 75.0,
        "yellow_threshold": 45.0,
        "slow_pacing_reward": 0.0,
        "high_energy_reward": 20.0,
    },
    "educational": {
        "label": "Educational / Tutorial",
        "icon": "📚",
        "description": "Clarity and speech density matter. Face presence and steady pacing are valued.",
        "audio_weight": 0.35,
        "visual_weight": 0.20,
        "transcript_weight": 0.45,
        "song_weight": 0.15,
        "temporal_weight": 0.15,
        "engagement_weight": 0.10,
        "green_threshold": 70.0,
        "yellow_threshold": 40.0,
        "slow_pacing_reward": 5.0,
        "high_energy_reward": 0.0,
    },
    "vlog": {
        "label": "Vlog / Lifestyle",
        "icon": "📹",
        "description": "Balanced scoring — face presence, scene variety, and natural pacing all contribute.",
        "audio_weight": 0.30,
        "visual_weight": 0.35,
        "transcript_weight": 0.30,
        "song_weight": 0.30,
        "temporal_weight": 0.20,
        "engagement_weight": 0.20,
        "green_threshold": 75.0,
        "yellow_threshold": 45.0,
        "slow_pacing_reward": 0.0,
        "high_energy_reward": 0.0,
    },
    "cinematic": {
        "label": "Cinematic / Film",
        "icon": "🎬",
        "description": "Visual composition leads. Slow, deliberate pacing is rewarded. Music integration matters.",
        "audio_weight": 0.30,
        "visual_weight": 0.45,
        "transcript_weight": 0.15,
        "song_weight": 0.35,
        "temporal_weight": 0.20,
        "engagement_weight": 0.15,
        "green_threshold": 70.0,
        "yellow_threshold": 40.0,
        "slow_pacing_reward": 10.0,
        "high_energy_reward": 0.0,
    },
    "comedy": {
        "label": "Comedy / Entertainment",
        "icon": "😂",
        "description": "Transcript impact and vocal energy drive scores. Timing and pacing are key.",
        "audio_weight": 0.40,
        "visual_weight": 0.25,
        "transcript_weight": 0.40,
        "song_weight": 0.20,
        "temporal_weight": 0.15,
        "engagement_weight": 0.20,
        "green_threshold": 75.0,
        "yellow_threshold": 45.0,
        "slow_pacing_reward": 0.0,
        "high_energy_reward": 0.0,
    },
    "music": {
        "label": "Music / Performance",
        "icon": "🎵",
        "description": "Audio energy and viral sound matching dominate. Transcript is nearly irrelevant.",
        "audio_weight": 0.45,
        "visual_weight": 0.30,
        "transcript_weight": 0.05,
        "song_weight": 0.45,
        "temporal_weight": 0.15,
        "engagement_weight": 0.15,
        "green_threshold": 75.0,
        "yellow_threshold": 45.0,
        "slow_pacing_reward": 0.0,
        "high_energy_reward": 15.0,
    },
}

# ═══════════════════════════════════════════════════════════
# DEFAULT (fallback when no profile is active)
# ═══════════════════════════════════════════════════════════

DEFAULT_WEIGHTS: dict = {
    "audio_weight": 0.35,
    "visual_weight": 0.30,
    "transcript_weight": 0.30,
    "song_weight": 0.30,
    "temporal_weight": 0.20,
    "engagement_weight": 0.15,
    "green_threshold": 75.0,
    "yellow_threshold": 45.0,
    "slow_pacing_reward": 0.0,
    "high_energy_reward": 0.0,
}


def get_preset(niche: str) -> dict:
    """Return weights for a niche. Falls back to DEFAULT_WEIGHTS if unknown."""
    preset = PERSONA_PRESETS.get(niche, None)
    if preset is None:
        return dict(DEFAULT_WEIGHTS)
    # Return only the weight keys (strip label/icon/description)
    return {k: v for k, v in preset.items() if k not in ("label", "icon", "description")}


def list_available_presets() -> list[dict]:
    """Return metadata for all persona presets (for the onboarding UI)."""
    return [
        {
            "niche": key,
            "label": val["label"],
            "icon": val["icon"],
            "description": val["description"],
        }
        for key, val in PERSONA_PRESETS.items()
    ]
