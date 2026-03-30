"""Emotion Arc Mapping — maps the emotional journey of a video as a timeline.

Combines per-second facial/vocal emotion data with audio energy signals and
optional external API visual_energy windows to produce a continuous emotional
intensity curve with labeled phases and transition detection.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("hook_architect.emotion_arc")

# ── Emotion → Arousal score mapping ──────────────────────
EMOTION_AROUSAL = {
    "excited": 92, "surprise": 80, "happy": 78, "angry": 72,
    "fear": 65, "disgust": 55, "neutral": 50, "unknown": 50,
    "anxious/hesitant": 40, "sad": 30, "sad/bored": 25, "silent": 20,
}

# Phase labels
PHASE_HOOK = "hook"
PHASE_BUILD = "build"
PHASE_PEAK = "peak"
PHASE_VALLEY = "valley"
PHASE_RECOVERY = "recovery"
PHASE_OUTRO = "outro"


def _emotion_to_arousal(emotion_name: str) -> float:
    """Convert emotion label to 0-100 arousal value."""
    return EMOTION_AROUSAL.get(emotion_name.lower(), 50)


def _smooth(values: list[float], window: int = 3) -> list[float]:
    """Simple moving average smoothing."""
    if len(values) <= window:
        return values
    smoothed = []
    half = window // 2
    for i in range(len(values)):
        start = max(0, i - half)
        end = min(len(values), i + half + 1)
        smoothed.append(sum(values[start:end]) / (end - start))
    return smoothed


def compute_emotion_arc(
    emotion_data: dict | None,
    audio_signals: list[dict],
    visual_signals: list[dict],
    duration: float,
    external_windows: list[dict] | None = None,
) -> dict:
    """Compute the full emotion arc for a video.
    
    Args:
        emotion_data: From emotion_analyzer — contains emotion_timeline with
                      per-second {timestamp, vocal_emotion, facial_emotion}
        audio_signals: Per-second audio analysis with energy, pacing, etc.
        visual_signals: Per-second visual analysis with motion_score, face_present
        duration: Video duration in seconds
        external_windows: Optional 2s windows from external API with visual_energy (1-10)
    
    Returns:
        dict with arc_points[], phases[], transitions[], arc_summary, dominant_arc_shape
    """
    total_seconds = max(1, int(duration))
    emotion_timeline = emotion_data.get("emotion_timeline", []) if emotion_data else []

    # ── Build per-second external energy lookup ──────────
    external_energy_map = {}
    if external_windows:
        for w in external_windows:
            start = w.get("start", 0)
            end = w.get("end", start + 2)
            # visual_energy is 1-10 from external API → scale to 0-100
            ve = w.get("visual_energy", 5)
            scaled = min(100, max(0, (ve - 1) * (100 / 9)))
            for t in range(int(start), min(int(end), total_seconds)):
                external_energy_map[t] = scaled

    # ── Compute raw emotional intensity per second ───────
    raw_intensities = []
    for t in range(total_seconds):
        # Face arousal
        face_arousal = 50.0
        vocal_arousal = 50.0
        if t < len(emotion_timeline):
            et = emotion_timeline[t]
            face_arousal = _emotion_to_arousal(et.get("facial_emotion", "neutral"))
            vocal_arousal = _emotion_to_arousal(et.get("vocal_emotion", "neutral"))

        # Audio energy (0-100 already)
        audio_energy = 50.0
        if t < len(audio_signals):
            audio_energy = audio_signals[t].get("energy", 50)

        # Visual motion (0-100 already)
        motion = 50.0
        if t < len(visual_signals):
            motion = visual_signals[t].get("motion_score", 50)

        # External visual energy (0-100 scaled)
        ext_energy = external_energy_map.get(t, None)

        # Weighted composite
        if ext_energy is not None:
            # With external data: face(25%) + voice(20%) + audio(20%) + motion(15%) + external(20%)
            intensity = (
                face_arousal * 0.25 +
                vocal_arousal * 0.20 +
                audio_energy * 0.20 +
                motion * 0.15 +
                ext_energy * 0.20
            )
        else:
            # Without external: face(30%) + voice(25%) + audio(25%) + motion(20%)
            intensity = (
                face_arousal * 0.30 +
                vocal_arousal * 0.25 +
                audio_energy * 0.25 +
                motion * 0.20
            )

        raw_intensities.append(round(intensity, 1))

    # ── Smooth the curve ─────────────────────────────────
    smoothed = _smooth(raw_intensities, window=3)

    # ── Build arc points ─────────────────────────────────
    arc_points = []
    for t in range(total_seconds):
        emotion_label = "neutral"
        if t < len(emotion_timeline):
            et = emotion_timeline[t]
            face_e = et.get("facial_emotion", "unknown")
            vocal_e = et.get("vocal_emotion", "silent")
            # Use whichever is more intense
            if _emotion_to_arousal(face_e) != 50:
                emotion_label = face_e
            elif vocal_e != "silent":
                emotion_label = vocal_e

        arc_points.append({
            "t": t,
            "intensity": round(smoothed[t], 1),
            "raw_intensity": raw_intensities[t],
            "emotion": emotion_label,
            "arousal": _emotion_to_arousal(emotion_label),
        })

    # ── Detect phases ────────────────────────────────────
    phases = _detect_phases(arc_points, total_seconds)

    # ── Detect transitions ───────────────────────────────
    transitions = _detect_transitions(arc_points)

    # ── Determine dominant arc shape ─────────────────────
    arc_shape = _classify_arc_shape(arc_points)

    # ── Build summary ────────────────────────────────────
    avg_intensity = sum(p["intensity"] for p in arc_points) / len(arc_points)
    peak_t = max(arc_points, key=lambda p: p["intensity"])
    valley_t = min(arc_points, key=lambda p: p["intensity"])

    arc_summary = (
        f"Emotion arc follows a '{arc_shape}' pattern. "
        f"Average emotional intensity: {avg_intensity:.0f}/100. "
        f"Peak at {_fmt(peak_t['t'])} ({peak_t['intensity']:.0f}/100, {peak_t['emotion']}). "
        f"Lowest at {_fmt(valley_t['t'])} ({valley_t['intensity']:.0f}/100, {valley_t['emotion']}). "
        f"{len(transitions)} emotional transitions detected."
    )

    return {
        "arc_points": arc_points,
        "phases": phases,
        "transitions": transitions,
        "arc_shape": arc_shape,
        "arc_summary": arc_summary,
        "avg_intensity": round(avg_intensity, 1),
        "peak": {"t": peak_t["t"], "intensity": peak_t["intensity"], "emotion": peak_t["emotion"]},
        "valley": {"t": valley_t["t"], "intensity": valley_t["intensity"], "emotion": valley_t["emotion"]},
    }


def _detect_phases(arc_points: list[dict], total_seconds: int) -> list[dict]:
    """Label arc segments into narrative phases."""
    phases = []
    if total_seconds <= 0:
        return phases

    # Hook: first 3 seconds
    hook_end = min(3, total_seconds)
    hook_avg = sum(p["intensity"] for p in arc_points[:hook_end]) / hook_end
    phases.append({
        "phase": PHASE_HOOK, "start": 0, "end": hook_end,
        "avg_intensity": round(hook_avg, 1),
        "label": f"Hook ({hook_avg:.0f}/100)"
    })

    if total_seconds <= 3:
        return phases

    # Analyze remaining for build/peak/valley/recovery/outro
    remaining = arc_points[hook_end:]
    if not remaining:
        return phases

    # Find the global peak and valley in the remaining content
    peak_idx = max(range(len(remaining)), key=lambda i: remaining[i]["intensity"])
    valley_idx = min(range(len(remaining)), key=lambda i: remaining[i]["intensity"])

    # Build: from hook_end to peak (or first major rise)
    if peak_idx > 0:
        build_end = hook_end + peak_idx
        build_avg = sum(p["intensity"] for p in remaining[:peak_idx]) / peak_idx
        phases.append({
            "phase": PHASE_BUILD, "start": hook_end, "end": build_end,
            "avg_intensity": round(build_avg, 1),
            "label": f"Build-up ({build_avg:.0f}/100)"
        })

    # Peak: around the peak point (±1s)
    peak_start = hook_end + max(0, peak_idx - 1)
    peak_end = hook_end + min(len(remaining), peak_idx + 2)
    peak_avg = remaining[peak_idx]["intensity"]
    phases.append({
        "phase": PHASE_PEAK, "start": peak_start, "end": peak_end,
        "avg_intensity": round(peak_avg, 1),
        "label": f"Peak ({peak_avg:.0f}/100)"
    })

    # Valley: if it comes after peak
    if valley_idx > peak_idx:
        valley_start = hook_end + peak_idx + 2
        valley_end = hook_end + min(len(remaining), valley_idx + 2)
        valley_avg = remaining[valley_idx]["intensity"]
        phases.append({
            "phase": PHASE_VALLEY, "start": valley_start, "end": valley_end,
            "avg_intensity": round(valley_avg, 1),
            "label": f"Valley ({valley_avg:.0f}/100)"
        })

        # Recovery: anything after valley that rises
        if valley_idx + 2 < len(remaining):
            recovery_slice = remaining[valley_idx + 2:]
            if recovery_slice:
                rec_avg = sum(p["intensity"] for p in recovery_slice) / len(recovery_slice)
                if rec_avg > valley_avg + 5:
                    phases.append({
                        "phase": PHASE_RECOVERY,
                        "start": hook_end + valley_idx + 2,
                        "end": total_seconds,
                        "avg_intensity": round(rec_avg, 1),
                        "label": f"Recovery ({rec_avg:.0f}/100)"
                    })

    # Outro: last 2 seconds
    if total_seconds > 5:
        outro_start = max(hook_end, total_seconds - 2)
        outro_slice = arc_points[outro_start:]
        outro_avg = sum(p["intensity"] for p in outro_slice) / len(outro_slice) if outro_slice else 0
        phases.append({
            "phase": PHASE_OUTRO, "start": outro_start, "end": total_seconds,
            "avg_intensity": round(outro_avg, 1),
            "label": f"Outro ({outro_avg:.0f}/100)"
        })

    return phases


def _detect_transitions(arc_points: list[dict], threshold: float = 15.0) -> list[dict]:
    """Detect significant emotional transitions (shifts > threshold in intensity)."""
    transitions = []
    for i in range(1, len(arc_points)):
        delta = arc_points[i]["intensity"] - arc_points[i - 1]["intensity"]
        if abs(delta) >= threshold:
            direction = "rise" if delta > 0 else "drop"
            from_emo = arc_points[i - 1]["emotion"]
            to_emo = arc_points[i]["emotion"]

            if direction == "drop":
                desc = f"Engagement drops: {from_emo} → {to_emo} (−{abs(delta):.0f} pts)"
                trans_type = "drop_point"
            else:
                desc = f"Re-engagement: {from_emo} → {to_emo} (+{delta:.0f} pts)"
                trans_type = "recovery_point"

            transitions.append({
                "t": arc_points[i]["t"],
                "type": trans_type,
                "delta": round(delta, 1),
                "from_emotion": from_emo,
                "to_emotion": to_emo,
                "description": desc,
            })

    return transitions


def _classify_arc_shape(arc_points: list[dict]) -> str:
    """Classify the overall arc shape from the intensity curve."""
    if len(arc_points) < 4:
        return "flat"

    n = len(arc_points)
    first_quarter = sum(p["intensity"] for p in arc_points[:n // 4]) / (n // 4)
    mid = sum(p["intensity"] for p in arc_points[n // 4: 3 * n // 4]) / max(1, 3 * n // 4 - n // 4)
    last_quarter = sum(p["intensity"] for p in arc_points[3 * n // 4:]) / max(1, n - 3 * n // 4)

    if mid > first_quarter + 8 and mid > last_quarter + 8:
        return "mountain"  # peaks in middle
    elif first_quarter > mid + 8:
        return "declining"  # starts strong, fades
    elif last_quarter > mid + 8:
        return "rising"  # builds to end
    elif first_quarter > mid + 5 and last_quarter > mid + 5:
        return "U-shape"  # strong start, dip, strong finish
    elif abs(first_quarter - mid) < 8 and abs(mid - last_quarter) < 8:
        return "steady"  # consistent intensity
    else:
        return "wave"  # oscillating


def _fmt(seconds: float) -> str:
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m}:{s:02d}"
