"""Cross-Modal Attention Engine — fuses audio + visual signals into attention scores.

Supports persona-aware scoring via optional user_weights parameter.
Flags are now typed as Strengths or Faults based on the user's niche rewards.
Includes object_richness signal from YOLOv8 and per-second confidence scoring.
"""
from __future__ import annotations

import math
from models.schemas import TimelinePoint, RiskZone, Zone
from core.config import (
    AUDIO_WEIGHT,
    VISUAL_WEIGHT,
    OBJECT_RICHNESS_WEIGHT,
    TRANSCRIPT_WEIGHT,
    SONG_WEIGHT,
    TEMPORAL_WEIGHT,
    ENGAGEMENT_WEIGHT,
    GREEN_THRESHOLD,
    YELLOW_THRESHOLD,
)


def _sigmoid(x: float) -> float:
    """Sigmoid normalization to 0-100 range."""
    clamped = max(-500, min(500, -0.05 * (x - 50)))
    return 100.0 / (1.0 + math.exp(clamped))


def _classify_zone(score: float, green_threshold: float = 75.0, yellow_threshold: float = 45.0) -> Zone:
    if score >= green_threshold:
        return Zone.GREEN
    elif score >= yellow_threshold:
        return Zone.YELLOW
    return Zone.RED


def _build_typed_flags(audio: dict, visual: dict, niche_rewards: dict | None = None) -> list[dict]:
    """Generate typed flags — each flag is either a 'strength' or a 'fault'.
    
    Niche rewards can flip certain faults into strengths:
      - slow_pacing_reward > 0: slow_pacing becomes a strength
      - high_energy_reward > 0: high_energy gets an extra strength flag
    """
    rewards = niche_rewards or {}
    slow_reward = rewards.get("slow_pacing_reward", 0.0)
    energy_reward = rewards.get("high_energy_reward", 0.0)
    
    flags = []

    # ── Audio flags ──────────────────────────────────────
    if audio["energy"] < 25:
        flags.append({"type": "fault", "key": "low_energy", "label": "Low vocal energy"})
    elif audio["energy"] > 60:
        flags.append({"type": "strength", "key": "high_energy", "label": "Strong vocal energy"})
        if energy_reward > 0:
            flags.append({"type": "strength", "key": "energy_bonus", "label": "High energy rewarded for your niche"})

    if audio["pitch_variation"] < 20:
        flags.append({"type": "fault", "key": "monotone", "label": "Monotone delivery"})
    elif audio["pitch_variation"] > 50:
        flags.append({"type": "strength", "key": "expressive", "label": "Expressive vocal range"})

    if audio["silence_flag"]:
        flags.append({"type": "fault", "key": "silence", "label": "Silence detected"})

    if audio["pacing"] < 20:
        if slow_reward > 0:
            flags.append({"type": "strength", "key": "slow_pacing", "label": "Deliberate pacing (rewarded for your niche)"})
        else:
            flags.append({"type": "fault", "key": "slow_pacing", "label": "Slow pacing"})
    elif audio["pacing"] > 60:
        flags.append({"type": "strength", "key": "fast_pacing", "label": "Dynamic pacing"})

    # ── Visual flags ─────────────────────────────────────
    if visual["motion_score"] < 20:
        flags.append({"type": "fault", "key": "static", "label": "Low visual motion"})
    elif visual["motion_score"] > 50:
        flags.append({"type": "strength", "key": "high_motion", "label": "High visual motion"})

    if not visual["face_present"]:
        flags.append({"type": "fault", "key": "no_face", "label": "No face detected"})
    else:
        flags.append({"type": "strength", "key": "face_anchor", "label": "Face anchoring viewer"})

    if visual["scene_cut"]:
        flags.append({"type": "strength", "key": "scene_cut", "label": "Scene cut keeps attention"})
    else:
        flags.append({"type": "fault", "key": "no_cut", "label": "No scene transition"})

    # ── Object richness flag ─────────────────────────────
    obj_richness = visual.get("object_richness_score", 0)
    if obj_richness >= 80:
        flags.append({"type": "strength", "key": "rich_scene", "label": "Rich visual scene (many objects)"})
    elif obj_richness <= 20:
        flags.append({"type": "fault", "key": "sparse_scene", "label": "Sparse visual scene"})

    return flags


def _legacy_flag_keys(typed_flags: list[dict]) -> list[str]:
    """Extract just the fault keys for backward compatibility with zone aggregation."""
    return [f["key"] for f in typed_flags if f["type"] == "fault"]


def compute_confidence(
    audio_signals: list[dict],
    visual_signals: list[dict],
    transcript_data: dict | None,
    duration: float,
) -> tuple[float, list[str]]:
    """Compute overall analysis confidence score (0-100) with reasons.
    
    Rules:
    - Base 100
    - No face detected for >80% of seconds: -20
    - Transcript word count < 10: -25
    - Video duration < 5s: -30
    - Silence >50% of seconds: -20
    - Floor at 10
    """
    confidence = 100.0
    reasons = []
    
    # Face data availability
    if visual_signals:
        face_count = sum(1 for v in visual_signals if v.get("face_present", False))
        face_pct = face_count / len(visual_signals)
        if face_pct < 0.2:
            confidence -= 20
            reasons.append("No face detected in most frames")
    
    # Transcript length
    if transcript_data:
        text = transcript_data.get("transcript", "")
        word_count = len(text.split()) if text else 0
        if word_count < 10:
            confidence -= 25
            reasons.append("Very short or no speech detected")
    else:
        confidence -= 25
        reasons.append("No transcript available")
    
    # Video duration
    if duration < 5:
        confidence -= 30
        reasons.append("Video too short for reliable analysis")
    
    # Silence check
    if audio_signals:
        silence_count = sum(1 for a in audio_signals if a.get("silence_flag", False))
        silence_pct = silence_count / len(audio_signals)
        if silence_pct > 0.5:
            confidence -= 20
            reasons.append("Mostly silent audio track")
    
    confidence = max(10, confidence)
    return round(confidence, 1), reasons


def compute_per_second_confidence(
    audio: dict,
    visual: dict,
    has_transcript: bool,
) -> float:
    """Compute per-second confidence (0-100)."""
    conf = 100.0
    if not visual.get("face_present", False):
        conf -= 15
    if audio.get("silence_flag", False):
        conf -= 15
    if not has_transcript:
        conf -= 20
    return max(10, conf)


def fuse_signals(
    audio_signals: list[dict],
    visual_signals: list[dict],
    transcript_score: float = 0.0,
    song_score: float = 0.0,
    emotional_alignment: float = 50.0,
    user_weights: dict | None = None,
    ml_predicted_zones: list[str] | None = None,
) -> tuple[list[dict], list[dict]]:
    """
    Combine audio and visual signals into unified attention scores.
    
    If user_weights is provided, uses persona-specific weights instead of global defaults.
    user_weights keys: audio_weight, visual_weight, transcript_weight, song_weight,
                       temporal_weight, engagement_weight, green_threshold, yellow_threshold,
                       slow_pacing_reward, high_energy_reward
    
    Returns:
        (timeline_points, risk_zones) — both as lists of dicts.
    """
    # ── Resolve weights ──────────────────────────────────
    if user_weights:
        w_audio = user_weights.get("audio_weight", AUDIO_WEIGHT)
        w_visual = user_weights.get("visual_weight", VISUAL_WEIGHT)
        w_obj_richness = user_weights.get("object_richness_weight", OBJECT_RICHNESS_WEIGHT)
        w_transcript = user_weights.get("transcript_weight", TRANSCRIPT_WEIGHT)
        w_song = user_weights.get("song_weight", SONG_WEIGHT)
        w_temporal = user_weights.get("temporal_weight", TEMPORAL_WEIGHT)
        w_engagement = user_weights.get("engagement_weight", ENGAGEMENT_WEIGHT)
        green_thr = user_weights.get("green_threshold", GREEN_THRESHOLD)
        yellow_thr = user_weights.get("yellow_threshold", YELLOW_THRESHOLD)
        niche_rewards = {
            "slow_pacing_reward": user_weights.get("slow_pacing_reward", 0.0),
            "high_energy_reward": user_weights.get("high_energy_reward", 0.0),
        }
    else:
        w_audio = AUDIO_WEIGHT
        w_visual = VISUAL_WEIGHT
        w_obj_richness = OBJECT_RICHNESS_WEIGHT
        w_transcript = TRANSCRIPT_WEIGHT
        w_song = SONG_WEIGHT
        w_temporal = TEMPORAL_WEIGHT
        w_engagement = ENGAGEMENT_WEIGHT
        green_thr = GREEN_THRESHOLD
        yellow_thr = YELLOW_THRESHOLD
        niche_rewards = {"slow_pacing_reward": 0.0, "high_energy_reward": 0.0}

    n = max(len(audio_signals), len(visual_signals))
    timeline: list[dict] = []

    has_transcript = transcript_score > 5

    for i in range(n):
        if i < len(audio_signals):
            audio = audio_signals[i]
        else:
            audio = {
                "timestamp": float(i), "energy": 0.0, 
                "pitch_variation": 0.0, "pacing": 0.0, 
                "silence_flag": True, "audio_score": 0.0
            }
            
        if i < len(visual_signals):
            visual = visual_signals[i]
        else:
            visual = {
                "timestamp": float(i), "motion_score": 0.0, 
                "face_present": False, "scene_cut": False, "visual_score": 0.0,
                "detected_objects": [], "object_richness_score": 0.0,
            }

        # ── Object richness score ────────────────────────
        obj_richness = visual.get("object_richness_score", 0.0)

        # ── Temporal context penalty ─────────────────────
        lookback = min(3, max(1, n // 3))
        if i >= lookback:
            recent_audio = [audio_signals[j]["audio_score"] if j < len(audio_signals) else 0.0 for j in range(i - lookback, i)]
            recent_visual = [visual_signals[j]["visual_score"] if j < len(visual_signals) else 0.0 for j in range(i - lookback, i)]
            avg_recent = (sum(recent_audio) + sum(recent_visual)) / (2 * lookback)
            threshold = 30 if n < 10 else 40
            temporal_penalty = max(0, threshold - avg_recent)  
            temporal_context = 100.0 - temporal_penalty * 2.5  
        else:
            temporal_context = 50.0

        # ── Engagement bonus (persona-aware) ─────────────
        engagement_bonus = 0.0
        if visual["face_present"]:
            engagement_bonus += 40.0
        if visual["scene_cut"]:
            engagement_bonus += 30.0
        if not audio["silence_flag"] and audio["energy"] > 50:
            engagement_bonus += 30.0
        
        # Apply niche-specific rewards
        slow_reward = niche_rewards.get("slow_pacing_reward", 0.0)
        energy_reward = niche_rewards.get("high_energy_reward", 0.0)
        
        if slow_reward > 0 and audio["pacing"] < 30:
            engagement_bonus += slow_reward
        if energy_reward > 0 and audio["energy"] > 60:
            engagement_bonus += energy_reward
            
        engagement_bonus = min(100.0, engagement_bonus)

        # ── Emotional Alignment Penalty ──────────────────
        alignment_bonus = (emotional_alignment - 50.0) * 0.4

        # ── Weighted fusion (now includes object_richness) ──
        total_structural_weights = w_audio + w_visual + w_obj_richness + w_transcript + w_song + w_temporal + w_engagement
        raw_score = (
            (w_audio * audio["audio_score"]
            + w_visual * visual["visual_score"]
            + w_obj_richness * obj_richness
            + w_transcript * transcript_score
            + w_song * song_score
            + w_temporal * temporal_context
            + w_engagement * engagement_bonus) / total_structural_weights
        ) + alignment_bonus

        attention = round(_sigmoid(raw_score), 1)
        rule_zone = _classify_zone(attention, green_thr, yellow_thr)

        # ── ML zone blending (majority-vote: 2 voters) ────
        if ml_predicted_zones is not None and i < len(ml_predicted_zones):
            ml_zone_str = ml_predicted_zones[i]
            if ml_zone_str == rule_zone.value:
                # Both agree — use agreed zone
                zone = rule_zone
            else:
                # Disagree — rule-based wins
                zone = rule_zone
        else:
            zone = rule_zone

        # Build typed flags (persona-aware)
        typed_flags = _build_typed_flags(audio, visual, niche_rewards)

        # Per-second confidence
        sec_confidence = compute_per_second_confidence(audio, visual, has_transcript)

        timeline.append({
            "t": audio["timestamp"],
            "audio_score": audio["audio_score"],
            "visual_score": visual["visual_score"],
            "object_richness_score": obj_richness,
            "detected_objects": visual.get("detected_objects", []),
            "transcript_score": transcript_score,
            "song_score": song_score,
            "attention": attention,
            "zone": zone.value,
            "flags": typed_flags if zone != Zone.GREEN else [],
            "strengths": [f for f in typed_flags if f["type"] == "strength"],
            "faults": [f for f in typed_flags if f["type"] == "fault"],
            "confidence": sec_confidence,
            "ml_zone": ml_predicted_zones[i] if ml_predicted_zones and i < len(ml_predicted_zones) else None,
        })

    # ── Aggregate risk zones ─────────────────────────────
    zones = _aggregate_zones(timeline)

    return timeline, zones


def _aggregate_zones(timeline: list[dict]) -> list[dict]:
    """Group consecutive non-green seconds into risk zones."""
    zones: list[dict] = []
    current_zone = None

    for point in timeline:
        zone_val = point["zone"]

        if zone_val != "green":
            if current_zone is None:
                current_zone = {
                    "start": point["t"],
                    "end": point["t"] + 1,
                    "zone": zone_val,
                    "attention_sum": point["attention"],
                    "count": 1,
                    "flags": set(_legacy_flag_keys(point.get("flags", []))),
                }
            else:
                if zone_val == "red":
                    current_zone["zone"] = "red"
                current_zone["end"] = point["t"] + 1
                current_zone["attention_sum"] += point["attention"]
                current_zone["count"] += 1
                current_zone["flags"].update(_legacy_flag_keys(point.get("flags", [])))
        else:
            if current_zone is not None:
                zones.append({
                    "start": current_zone["start"],
                    "end": current_zone["end"],
                    "zone": current_zone["zone"],
                    "avg_attention": round(
                        current_zone["attention_sum"] / current_zone["count"], 1
                    ),
                    "flags": sorted(current_zone["flags"]),
                    "recommendations": [],
                })
                current_zone = None

    if current_zone is not None:
        zones.append({
            "start": current_zone["start"],
            "end": current_zone["end"],
            "zone": current_zone["zone"],
            "avg_attention": round(
                current_zone["attention_sum"] / current_zone["count"], 1
            ),
            "flags": sorted(current_zone["flags"]),
            "recommendations": [],
        })

    return zones


def compute_overall_score(timeline: list[dict]) -> float:
    """Compute a single 0-100 score for the entire video."""
    if not timeline:
        return 0.0
    return round(sum(p["attention"] for p in timeline) / len(timeline), 1)


def generate_summary(
    overall_score: float,
    zones: list[dict],
    duration: float,
    timeline: list[dict] | None = None,
    niche: str | None = None,
) -> str:
    """Generate a natural-language summary of the analysis from real computed data."""
    red_zones = [z for z in zones if z["zone"] == "red"]
    yellow_zones = [z for z in zones if z["zone"] == "yellow"]

    parts = []
    
    if niche:
        parts.append(f"Scored as **{niche.capitalize()}** creator.")
    
    parts.append(f"Overall hook score: {overall_score}/100.")

    if not red_zones and not yellow_zones:
        parts.append("Excellent! No significant drop-off risks detected. Your video maintains strong engagement throughout.")
    else:
        if red_zones:
            red_desc = ", ".join(
                f"{z['start']:.0f}s–{z['end']:.0f}s" for z in red_zones
            )
            parts.append(f"🔴 {len(red_zones)} critical drop-off zone(s) at: {red_desc}.")
        if yellow_zones:
            yellow_desc = ", ".join(
                f"{z['start']:.0f}s–{z['end']:.0f}s" for z in yellow_zones
            )
            parts.append(f"🟡 {len(yellow_zones)} at-risk zone(s) at: {yellow_desc}.")

    if timeline and len(timeline) > 0:
        green_seconds = sum(1 for p in timeline if p["zone"] == "green")
        total_seconds = len(timeline)
        green_pct = round((green_seconds / total_seconds) * 100, 1)
        parts.append(f"{green_pct}% of the video ({green_seconds}s/{total_seconds}s) is in the safe retention zone.")
    
    parts.append(f"Video duration: {duration:.1f}s.")

    return " ".join(parts)
