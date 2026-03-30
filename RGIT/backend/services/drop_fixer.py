"""Generative Drop-Fixer & Script Doctor — LLM-powered content rewriting for low-engagement zones (Groq)."""
from __future__ import annotations

import logging
from typing import Any

from core.config import GEMINI_API_KEY

logger = logging.getLogger("hook_architect.drop_fixer")


def identify_drop_zones(
    timeline: list[dict],
    zones: list[dict],
    transcript_data: dict | None,
    threshold: float = 45.0,
) -> list[dict]:
    """Identify precise drop zones where attention falls below threshold.
    
    Returns a list of drop-zone dicts with start/end timestamps,
    relevant transcript segments, and visual metadata.
    """
    drop_zones = []

    for zone in zones:
        if zone.get("zone") != "red":
            continue

        start = zone["start"]
        end = zone["end"]
        avg_attention = zone.get("avg_attention", 0)

        # Get timeline points in this zone
        zone_points = [p for p in timeline if start <= p["t"] < end]

        # Extract the flags/faults from these points
        faults = set()
        for p in zone_points:
            for f in p.get("faults", []):
                if isinstance(f, dict):
                    faults.add(f.get("label", f.get("key", "")))
                else:
                    faults.add(str(f))

        # Extract transcript for this time range
        transcript_segment = ""
        if transcript_data and transcript_data.get("transcript"):
            # We have the full transcript — provide it for the zone
            full_transcript = transcript_data["transcript"]
            # Approximate: split transcript by proportion of duration
            transcript_segment = full_transcript  # Full transcript as context

        drop_zones.append({
            "start": start,
            "end": end,
            "duration": end - start,
            "avg_attention": avg_attention,
            "faults": list(faults),
            "transcript_segment": transcript_segment,
        })

    return drop_zones


def generate_quick_fix(
    timeline_points: list[dict],
    start: float,
    end: float,
    video_nature: str = "general",
) -> dict:
    """Generate deterministic rule-based quick fixes for a drop zone.

    Always works — no LLM dependency. Returns a dict with a list of
    specific, actionable suggestions based on detected signal patterns.
    """
    points = [p for p in timeline_points if start <= p.get("t", p.get("timestamp", 0)) < end]
    if not points:
        return {"suggestions": ["Add visual variety and vocal energy to this section."], "severity": "medium"}

    suggestions = []
    severity = "medium"

    # ── Check for silence ──────────────────────────────────
    silence_count = sum(1 for p in points if p.get("silence_flag", False))
    if silence_count > 0 and silence_count / len(points) > 0.3:
        suggestions.append("Add background music or voiceover. Current silence kills retention.")
        severity = "high"

    # ── Check for low motion ───────────────────────────────
    avg_motion = sum(p.get("motion_score", p.get("visual_score", 50)) for p in points) / len(points)
    if avg_motion < 20:
        suggestions.append("Cut to a new angle or add B-roll. Static shots lose viewers fast.")
        severity = "high"

    # ── Check for missing face in talking-head niches ──────
    face_niches = {"vlog", "educational", "comedy", "emotional"}
    face_count = sum(1 for p in points if p.get("face_present", False))
    if video_nature.lower() in face_niches and face_count / max(len(points), 1) < 0.3:
        suggestions.append(
            "Show your face. Face presence increases attention score by up to 40 points."
        )

    # ── Check for monotone delivery ────────────────────────
    avg_pitch = sum(p.get("pitch_variation", 50) for p in points) / len(points)
    if avg_pitch < 15:
        suggestions.append("Vary your vocal delivery. Monotone speech drops engagement by 30%.")

    # ── Check for consecutive seconds without scene cuts ───
    consecutive_no_cut = 0
    max_no_cut = 0
    for p in points:
        if not p.get("scene_cut", False):
            consecutive_no_cut += 1
            max_no_cut = max(max_no_cut, consecutive_no_cut)
        else:
            consecutive_no_cut = 0
    if max_no_cut > 5:
        suggestions.append(
            f"Add a scene transition here. Viewers expect visual change every 3-5 seconds "
            f"(you have {max_no_cut}s without a cut)."
        )

    if not suggestions:
        suggestions.append("Increase pacing: add text overlays, sound effects, or a direct question to re-engage viewers.")

    return {"suggestions": suggestions, "severity": severity}


async def generate_fix_suggestions(
    drop_zones: list[dict],
    transcript_data: dict | None,
    audio_profile: dict | None,
    reference_baseline: dict | None,
    video_nature: str = "general",
    timeline: list[dict] | None = None,
    multimodal_diagnoses: list[dict] | None = None,
) -> list[dict]:
    """For each drop zone, generate AI-powered fix suggestions using Gemini.

    Returns a list of suggestion dicts with:
    - timestamp range
    - current_script (what's there now)
    - ai_suggestion (rewritten script)
    - format_recommendation (visual change)
    - reasoning
    - quick_fix (always present — deterministic rule-based suggestions)
    - frame_analysis (multimodal visual diagnosis, if available)
    """
    # Always generate quick_fix for every zone (works offline)
    tl = timeline or []

    # Build multimodal lookup by zone start time
    mm_lookup: dict[float, dict] = {}
    if multimodal_diagnoses:
        for diag in multimodal_diagnoses:
            if diag and isinstance(diag, dict):
                mm_lookup[float(diag.get("zone_start", -1))] = diag

    if not GEMINI_API_KEY:
        logger.warning("[DROP_FIXER] No API key configured — using rule-based fallback")
        results = _rule_based_suggestions(drop_zones, transcript_data, audio_profile)
        for r, dz in zip(results, drop_zones):
            r["quick_fix"] = generate_quick_fix(tl, dz["start"], dz["end"], video_nature)
        return results

    try:
        from groq import Groq
        client = Groq(api_key=GEMINI_API_KEY)
    except ImportError:
        logger.error("[DROP_FIXER] groq package not installed")
        results = _rule_based_suggestions(drop_zones, transcript_data, audio_profile)
        for r, dz in zip(results, drop_zones):
            r["quick_fix"] = generate_quick_fix(tl, dz["start"], dz["end"], video_nature)
        return results
    except Exception as e:
        logger.error(f"[DROP_FIXER] Groq init failed: {e}")
        results = _rule_based_suggestions(drop_zones, transcript_data, audio_profile)
        for r, dz in zip(results, drop_zones):
            r["quick_fix"] = generate_quick_fix(tl, dz["start"], dz["end"], video_nature)
        return results

    suggestions = []

    for dz in drop_zones:
        # Always compute quick_fix deterministically
        quick_fix = generate_quick_fix(tl, dz["start"], dz["end"], video_nature)

        # Build context prompt
        bpm_info = ""
        if audio_profile:
            bpm_info = f"The video's audio runs at approximately {audio_profile.get('estimated_bpm', 80):.0f} BPM with {audio_profile.get('avg_energy', 50):.0f}/100 energy."

        ref_info = ""
        if reference_baseline:
            ref_info = f"The user's reference baseline style is: {reference_baseline.get('narrative_blueprint', 'N/A')}"

        faults_str = ", ".join(dz["faults"]) if dz["faults"] else "general low engagement"

        prompt = f"""You are a viral short-form video retention expert. Analyze this low-engagement section and provide fixes.

CONTEXT:
- Video type: {video_nature}
- Time range: {_format_time(dz['start'])} — {_format_time(dz['end'])} ({dz['duration']:.0f} seconds)
- Average attention score: {dz['avg_attention']:.0f}/100 (CRITICAL — below 45 is a viewer drop-off point)
- Detected issues: {faults_str}
{f'- Current transcript: "{dz["transcript_segment"]}"' if dz['transcript_segment'] else '- No speech detected in this section'}
{bpm_info}
{ref_info}

Provide your response in EXACTLY this format (no markdown, no extra text):
REWRITTEN_SCRIPT: [A punchy, retention-optimized rewrite of what should be said in these ~{dz['duration']:.0f} seconds. If there's no speech, write a voiceover hook.]
VISUAL_FORMAT: [Specific technical suggestion: e.g., "Quick zoom-in on face + text overlay" or "Switch to B-roll montage with 0.5s cuts"]
REASONING: [1-2 sentences explaining why these changes would fix viewer drop-off]
HOOK_ALT_1: [Alternative opening hook phrase — punchy, curiosity-driven]
HOOK_ALT_2: [A different hook approach — emotional, surprising, or confrontational]
HOOK_ALT_3: [Bold/unconventional hook — pattern interrupt style]
PACING: [Recommended speed adjustment e.g., 'Speed up 1.2x' or 'Maintain current pace' or 'Slow to 0.8x for emphasis']"""

        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=600,
            )
            text = response.choices[0].message.content.strip()

            # Parse response
            rewritten = _extract_field(text, "REWRITTEN_SCRIPT")
            visual = _extract_field(text, "VISUAL_FORMAT")
            reasoning = _extract_field(text, "REASONING")
            hook1 = _extract_field(text, "HOOK_ALT_1")
            hook2 = _extract_field(text, "HOOK_ALT_2")
            hook3 = _extract_field(text, "HOOK_ALT_3")
            pacing = _extract_field(text, "PACING")

            hook_alternatives = [h for h in [hook1, hook2, hook3] if h]

            # Multimodal visual diagnosis prepend
            mm_diag = mm_lookup.get(float(dz["start"]))
            base_suggestion = rewritten or "Add a strong hook: 'Here's the part nobody talks about...'"
            if mm_diag:
                visual_prefix = (
                    f"[Frame analysis: {mm_diag.get('visual_cause', '')}] "
                    f"[Visual fix: {mm_diag.get('visual_fix', '')}] "
                )
                ai_suggestion_final = visual_prefix + base_suggestion
            else:
                ai_suggestion_final = base_suggestion

            suggestions.append({
                "start": dz["start"],
                "end": dz["end"],
                "start_formatted": _format_time(dz["start"]),
                "end_formatted": _format_time(dz["end"]),
                "avg_attention": dz["avg_attention"],
                "current_script": dz["transcript_segment"] or "(No speech — silent section)",
                "ai_suggestion": ai_suggestion_final,
                "format_recommendation": visual or "Increase visual variety: add B-roll or text overlay",
                "reasoning": reasoning or f"This {dz['duration']:.0f}s section scores {dz['avg_attention']:.0f}/100 due to {faults_str}.",
                "hook_alternatives": hook_alternatives,
                "pacing_recommendation": pacing or "Maintain current pace",
                "faults": dz["faults"],
                "quick_fix": quick_fix,
                "frame_analysis": mm_diag,
                "source": "gemini",
            })

        except Exception as e:
            logger.error(f"[DROP_FIXER] Groq call failed for zone {dz['start']}-{dz['end']}: {e}")
            # Fallback to rule-based for this zone
            fb = _rule_based_single(dz, transcript_data, audio_profile)
            fb["quick_fix"] = quick_fix
            # Still attach multimodal diagnosis if available
            mm_diag = mm_lookup.get(float(dz["start"]))
            if mm_diag:
                fb["ai_suggestion"] = (
                    f"[Frame analysis: {mm_diag.get('visual_cause', '')}] "
                    f"[Visual fix: {mm_diag.get('visual_fix', '')}] "
                    + fb.get("ai_suggestion", "")
                )
                fb["frame_analysis"] = mm_diag
            suggestions.append(fb)

    return suggestions


def _rule_based_suggestions(
    drop_zones: list[dict],
    transcript_data: dict | None,
    audio_profile: dict | None,
) -> list[dict]:
    """Rule-based fallback when Gemini is unavailable."""
    return [_rule_based_single(dz, transcript_data, audio_profile) for dz in drop_zones]


def _rule_based_single(
    dz: dict,
    transcript_data: dict | None,
    audio_profile: dict | None,
) -> dict:
    """Generate a single rule-based suggestion."""
    faults = dz.get("faults", [])
    faults_lower = [f.lower() for f in faults]

    # Generate contextual suggestion based on detected faults
    if any("silence" in f for f in faults_lower):
        ai_text = "Break the silence with a direct question or surprising fact. 'Did you know that...?' or 'Wait — watch what happens next.'"
        format_rec = "Add background music and text overlays during silent sections. Consider a quick zoom-in to create visual interest."
    elif any("monotone" in f for f in faults_lower):
        ai_text = "Inject vocal energy variation. Start with a whisper, then crescendo: 'And THIS... is where it gets interesting.'"
        format_rec = "Add jump cuts every 2-3 seconds to compensate for flat vocal energy. Overlay dynamic text to emphasize key words."
    elif any("static" in f or "no face" in f for f in faults_lower):
        ai_text = "Anchor the viewer with a direct-to-camera moment. 'Look — I need to show you something.'"
        format_rec = "Switch to face-cam or add quick B-roll cuts. Static visuals without a face lose viewers in 3 seconds."
    elif any("slow" in f or "pacing" in f for f in faults_lower):
        ai_text = "Speed up the information delivery. Cut filler words. 'Three things you need to know — first...'"
        format_rec = f"Increase cut frequency to match your audio BPM ({audio_profile.get('estimated_bpm', 80):.0f} BPM). Add visual transitions every 1-2 seconds."
    else:
        ai_text = "Stop scrolling! Here's the one thing nobody tells you about this..."
        format_rec = "Quick-cut montage with text overlays + background music beat drop."

    bpm_note = ""
    if audio_profile:
        bpm_note = f" Target {audio_profile.get('estimated_bpm', 80):.0f} BPM visual rhythm."

    hook_alternatives = [
        "Wait — this changes everything...",
        "Nobody talks about this, but...",
        "Here's what most people miss:",
    ]

    return {
        "start": dz["start"],
        "end": dz["end"],
        "start_formatted": _format_time(dz["start"]),
        "end_formatted": _format_time(dz["end"]),
        "avg_attention": dz["avg_attention"],
        "current_script": dz.get("transcript_segment", "") or "(No speech — silent section)",
        "ai_suggestion": ai_text,
        "format_recommendation": format_rec + bpm_note,
        "reasoning": f"This {dz['duration']:.0f}s section scores {dz['avg_attention']:.0f}/100. Issues: {', '.join(dz['faults']) or 'general low engagement'}.",
        "hook_alternatives": hook_alternatives,
        "pacing_recommendation": "Speed up to 1.2x" if any("slow" in f for f in faults_lower) else "Maintain current pace",
        "faults": dz["faults"],
        "source": "rule_based",
    }


def _extract_field(text: str, field_name: str) -> str:
    """Extract a field value from structured LLM response."""
    import re
    pattern = rf'{field_name}:\s*(.+?)(?:\n[A-Z_]+:|$)'
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""


def _format_time(seconds: float) -> str:
    """Format seconds to MM:SS."""
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m}:{s:02d}"
