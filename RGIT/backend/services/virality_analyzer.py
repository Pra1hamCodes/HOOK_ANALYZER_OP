"""Virality Analyzer — Enhanced with trending status, recency scoring, and Audio-Sync Compatibility Index."""
from __future__ import annotations

import json
import math
from datetime import datetime, date
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "trends_db.json"


def _estimate_bpm_from_signals(audio_signals: list[dict]) -> float:
    """Estimate effective BPM from pacing and energy signals."""
    if not audio_signals:
        return 80.0
    avg_pacing = sum(a["pacing"] for a in audio_signals) / len(audio_signals)
    avg_energy = sum(a["energy"] for a in audio_signals) / len(audio_signals)
    # Map pacing (0-100) and energy (0-100) to approximate BPM range (50-180)
    estimated_bpm = 50 + (avg_pacing * 0.8) + (avg_energy * 0.5)
    return min(180, max(50, estimated_bpm))


def _get_recency_multiplier(track: dict) -> float:
    """Calculate a recency multiplier based on trending_status and dates.
    
    Returns a value between 0.5 (stale) and 1.3 (rising/peak).
    """
    status = track.get("trending_status", "peak")
    
    # Date-based freshness check
    peak_str = track.get("peak_date", "")
    if peak_str:
        try:
            peak_date = datetime.strptime(peak_str, "%Y-%m-%d").date()
            today = date.today()
            days_since_peak = (today - peak_date).days
        except (ValueError, TypeError):
            days_since_peak = 0
    else:
        days_since_peak = 0

    if status == "rising":
        return 1.30  # Maximum boost — song is gaining traction
    elif status == "peak":
        if days_since_peak < 90:
            return 1.20  # Still fresh at peak
        else:
            return 1.10  # Been at peak a while but still strong
    elif status == "declining":
        if days_since_peak < 180:
            return 0.85  # Recently started declining
        else:
            return 0.70  # Declining for a while
    elif status == "stale":
        return 0.50  # Outdated, significant penalty
    
    return 1.0


def _score_track(track: dict, estimated_bpm: float, avg_energy: float,
                 avg_pacing: float, dominant_emotion: str, video_nature: str) -> dict:
    """Score a track based on how well it matches the video's audio profile.
    
    Returns a dict with score breakdown for the Audio-Sync Compatibility Index.
    """
    # 1. BPM proximity (0-30 points)
    bpm_diff = abs(track["bpm"] - estimated_bpm)
    bpm_score = max(0, 30 - bpm_diff * 0.5)
    bpm_match_pct = max(0, 100 - bpm_diff * 1.5)  # percentage-based BPM alignment

    # 2. Pacing alignment (0-20 points)
    track_pacing = track["pacing_match"]
    pacing_match_pct = 0
    if avg_pacing > 60 and track_pacing == "fast":
        pacing_score = 20
        pacing_match_pct = 95
    elif 30 <= avg_pacing <= 60 and track_pacing == "medium":
        pacing_score = 20
        pacing_match_pct = 90
    elif avg_pacing < 30 and track_pacing == "slow":
        pacing_score = 20
        pacing_match_pct = 90
    elif abs(avg_pacing - {"fast": 70, "medium": 45, "slow": 15}.get(track_pacing, 45)) < 25:
        pacing_score = 10
        pacing_match_pct = 60
    else:
        pacing_score = 0
        pacing_match_pct = 20

    # 3. Emotion alignment (0-25 points)
    emotion_match_pct = 0
    if dominant_emotion in track.get("mood", []):
        emotion_score = 25
        emotion_match_pct = 95
    elif dominant_emotion in ["neutral", "silent"]:
        emotion_score = 10
        emotion_match_pct = 50
    else:
        emotion_score = 0
        emotion_match_pct = 15

    # 4. Nature/content type alignment (0-25 points)
    if video_nature and video_nature in track.get("trend_type", ""):
        nature_score = 25
    else:
        nature_score = 0

    raw_score = bpm_score + pacing_score + emotion_score + nature_score
    
    # Calculate overall match percentage
    overall_match_pct = round((bpm_match_pct * 0.35 + pacing_match_pct * 0.30 + emotion_match_pct * 0.35), 1)
    
    return {
        "raw_score": raw_score,
        "bpm_alignment_pct": round(bpm_match_pct, 1),
        "pacing_alignment_pct": round(pacing_match_pct, 1),
        "emotion_resonance_pct": round(emotion_match_pct, 1),
        "overall_match_pct": overall_match_pct,
    }


def _build_reasoning(track: dict, estimated_bpm: float, avg_energy: float,
                     avg_pacing: float, score_breakdown: dict) -> str:
    """Build a human-readable reasoning string for a track recommendation."""
    energy_label = 'high' if avg_energy > 60 else ('moderate' if avg_energy > 35 else 'low')
    pacing_label = 'fast' if avg_pacing > 60 else ('medium' if avg_pacing > 30 else 'slow')
    
    parts = []
    parts.append(
        f"Matches your {estimated_bpm:.0f} BPM pacing and {energy_label}-energy tone"
    )
    
    if score_breakdown["bpm_alignment_pct"] > 80:
        parts.append(f"BPM closely aligned ({score_breakdown['bpm_alignment_pct']:.0f}%)")
    
    if score_breakdown["emotion_resonance_pct"] > 70:
        parts.append(f"Strong emotional resonance ({score_breakdown['emotion_resonance_pct']:.0f}%)")
    
    status = track.get("trending_status", "peak")
    if status == "rising":
        parts.append("🔥 Currently rising in popularity")
    elif status == "peak":
        parts.append("📈 At peak viral momentum")
    elif status == "declining":
        parts.append("⚠️ Declining — consider fresher alternatives")
    elif status == "stale":
        parts.append("❌ Outdated — high risk of audience fatigue")
    
    return ". ".join(parts) + "."


def analyze_virality(
    audio_signals: list[dict],
    dominant_emotion: str,
    video_nature: str
) -> dict:
    """Enhanced virality analysis with trending status, recency scoring,
    and Audio-Sync Compatibility Index returning top 3 tracks."""

    # 1. Calculate actual audio metrics
    avg_pacing = sum(a["pacing"] for a in audio_signals) / max(len(audio_signals), 1)
    avg_energy = sum(a["energy"] for a in audio_signals) / max(len(audio_signals), 1)
    avg_pitch = sum(a["pitch_variation"] for a in audio_signals) / max(len(audio_signals), 1)
    estimated_bpm = _estimate_bpm_from_signals(audio_signals)

    logger.info(f"[VIRALITY] Inputs: nature={video_nature}, emotion={dominant_emotion}, "
                f"pacing={avg_pacing:.1f}, energy={avg_energy:.1f}, pitch={avg_pitch:.1f}, est_bpm={estimated_bpm:.0f}")

    # 2. Load Trends DB
    try:
        with open(DB_PATH, "r", encoding="utf-8") as f:
            trends = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load trends DB: {e}")
        trends = []

    if not trends:
        return {
            "sound_score": 50.0, "recommended_track": None,
            "trend_type_rec": "Trending Music",
            "reasoning": "Database unavailable.",
            "song_meaning": "No music database available.",
            "top_recommendations": [],
            "audio_profile": {},
        }

    # 3. Score every track with recency multiplier
    scored = []
    for track in trends:
        score_breakdown = _score_track(track, estimated_bpm, avg_energy, avg_pacing, dominant_emotion, video_nature)
        recency_mult = _get_recency_multiplier(track)
        
        # Apply recency to final score
        adjusted_score = score_breakdown["raw_score"] * recency_mult
        
        scored.append({
            "track": track,
            "adjusted_score": adjusted_score,
            "raw_score": score_breakdown["raw_score"],
            "recency_multiplier": recency_mult,
            "breakdown": score_breakdown,
        })
        logger.info(f"  Track '{track['track_name']}' ({track['bpm']}BPM, {track.get('trending_status','?')}) -> "
                    f"raw={score_breakdown['raw_score']:.1f}, recency={recency_mult:.2f}, adj={adjusted_score:.1f}")

    # Sort by adjusted score descending
    scored.sort(key=lambda x: x["adjusted_score"], reverse=True)

    best = scored[0]
    best_match = best["track"]

    # 4. Compute sound_score (viral potential) with recency
    match_quality = best["adjusted_score"] / 100.0
    sound_score = best_match["momentum_score"] * (0.6 + 0.4 * match_quality) * best["recency_multiplier"]
    sound_score = min(100.0, sound_score)

    logger.info(f"[VIRALITY] WINNER: '{best_match['track_name']}' adj_score={best['adjusted_score']:.1f}")

    # 5. Build top 3 recommendations with full Audio-Sync data
    top_recommendations = []
    for entry in scored[:3]:
        t = entry["track"]
        bd = entry["breakdown"]
        reasoning = _build_reasoning(t, estimated_bpm, avg_energy, avg_pacing, bd)
        
        top_recommendations.append({
            "id": t["id"],
            "track_name": t["track_name"],
            "artist": t["artist"],
            "bpm": t["bpm"],
            "trending_status": t.get("trending_status", "unknown"),
            "match_pct": bd["overall_match_pct"],
            "bpm_alignment_pct": bd["bpm_alignment_pct"],
            "pacing_alignment_pct": bd["pacing_alignment_pct"],
            "emotion_resonance_pct": bd["emotion_resonance_pct"],
            "recency_multiplier": entry["recency_multiplier"],
            "reasoning": reasoning,
            "mood": t.get("mood", []),
        })

    # 6. Build main reasoning
    main_reasoning = _build_reasoning(best_match, estimated_bpm, avg_energy, avg_pacing, best["breakdown"])

    song_meaning = (
        f"'{best_match['track_name']}' by {best_match['artist']} is a {best_match['bpm']} BPM "
        f"{best_match['trend_type']} track with mood profile: {', '.join(best_match.get('mood', []))}. "
        f"Selected because its tempo closely matches your video's detected rhythm ({estimated_bpm:.0f} BPM) "
        f"and its energy profile aligns with the {dominant_emotion} emotional arc. "
        f"Trending status: {best_match.get('trending_status', 'unknown').upper()}."
    )

    rec_track = {
        "id": best_match["id"],
        "track_name": best_match["track_name"],
        "artist": best_match["artist"],
        "bpm": best_match["bpm"],
        "trending_status": best_match.get("trending_status", "unknown"),
        "match_pct": best["breakdown"]["overall_match_pct"],
    }

    return {
        "sound_score": round(sound_score, 1),
        "recommended_track": rec_track,
        "trend_type_rec": best_match["trend_type"],
        "reasoning": main_reasoning,
        "song_meaning": song_meaning,
        "top_recommendations": top_recommendations,
        "audio_profile": {
            "estimated_bpm": round(estimated_bpm, 0),
            "avg_energy": round(avg_energy, 1),
            "avg_pacing": round(avg_pacing, 1),
            "avg_pitch": round(avg_pitch, 1),
        },
    }
