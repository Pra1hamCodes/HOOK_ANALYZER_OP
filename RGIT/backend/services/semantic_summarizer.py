"""Semantic Summarizer — Dual-track summarization, reference overlap check, and Narrative Blueprint."""
from __future__ import annotations


def generate_semantic_summary(
    transcript_data: dict | None,
    visual_signals: list[dict],
    duration: float,
    reference_baseline: dict | None = None
) -> dict:
    """
    1. Extracts transcript narrative (Narrative Track).
    2. Builds visual narrative using motion, faces, and cuts (Visual Track).
    3. Calculates Semantic Overlap ("Vibe Check") — internal consistency.
    4. If reference_baseline exists, calculates Reference Overlap (Semantic Consistency Check).
    """
    # 1. Transcript (Narrative) Track
    if transcript_data and transcript_data.get("transcript"):
        narrative_track = transcript_data.get("narrative_summary", "A neutral overview of topics.")
        sentiment = transcript_data.get("sentiment_polarity", 0.0)
        subjectivity = transcript_data.get("subjectivity", 0.0)
    else:
        narrative_track = "No speech detected (Instrumental/Silent or ASR failed)."
        sentiment = 0.0
        subjectivity = 0.0

    narrative_style = "educational" if subjectivity < 0.4 else "vlog/storytelling"

    # 2. Visual Track
    total_seconds = max(len(visual_signals), 1)

    avg_motion = sum(v["motion_score"] for v in visual_signals) / total_seconds
    face_percentage = sum(1 for v in visual_signals if v["face_present"]) / total_seconds
    cut_count = sum(1 for v in visual_signals if v["scene_cut"])
    
    # Visual cut frequency (cuts per 5 seconds)
    visual_cut_frequency = (cut_count / max(duration, 1)) * 5.0

    # Classify visual vibe
    if face_percentage > 0.7 and avg_motion < 30:
        visual_style = "educational"
        visual_description = "A static 'talking-head' style focusing closely on the speaker."
    elif avg_motion > 50 and cut_count > duration / 5.0:
        visual_style = "vlog/storytelling"
        visual_description = "High-energy layout with frequent cuts and dynamic motion."
    elif avg_motion < 20 and face_percentage < 0.3:
        visual_style = "b-roll/ambient"
        visual_description = "Static non-face aesthetic/b-roll footage."
    else:
        visual_style = "mixed"
        visual_description = "A balanced mix of motion, faces, and transitions."

    visual_track = f"{visual_description} (Style: {visual_style.capitalize()})"

    # 3. Internal Semantic Overlap Check ("Vibe Check")
    overlap_score = 50.0
    drift_flag = False

    if narrative_style == visual_style:
        overlap_score = 90.0
        drift_flag = False
        vibe_message = f"Strong alignment! Both what is said and what is shown fit a {narrative_style} format."
    else:
        if visual_style == "mixed":
            overlap_score = 70.0
            drift_flag = False
            vibe_message = "Acceptable alignment. The visual layout supports the narrative adequately."
        else:
            overlap_score = 30.0
            drift_flag = True
            vibe_message = f"Semantic Drift detected! You are speaking in an {narrative_style} tone, but visually portraying a {visual_style} style."

    # 4. Reference Baseline Overlap (Semantic Consistency Check — Feature 4)
    reference_overlap_score = None
    reference_drift = False
    reference_comparison_message = ""

    if reference_baseline:
        ref_narrative = reference_baseline.get("dominant_narrative_style", "mixed")
        ref_visual = reference_baseline.get("dominant_visual_style", "mixed")
        ref_blueprint = reference_baseline.get("narrative_blueprint", "")

        # Compare current styles against reference
        style_matches = 0
        total_comparisons = 2

        if _styles_compatible(narrative_style, ref_narrative):
            style_matches += 1
        if _styles_compatible(visual_style, ref_visual):
            style_matches += 1

        reference_overlap_score = round((style_matches / total_comparisons) * 100.0, 1)

        # Compare motion/energy quantitatively
        ref_motion = reference_baseline.get("avg_motion", 50.0)
        motion_diff = abs(avg_motion - ref_motion)
        motion_penalty = min(30, motion_diff * 0.5)
        reference_overlap_score = max(0, reference_overlap_score - motion_penalty)

        if reference_overlap_score >= 70:
            reference_drift = False
            reference_comparison_message = (
                f"✅ Strong consistency with your reference baseline! "
                f"Your video matches the '{ref_narrative}' narrative and '{ref_visual}' visual style "
                f"you established. Vibe Match: {reference_overlap_score:.0f}%."
            )
        elif reference_overlap_score >= 40:
            reference_drift = False
            reference_comparison_message = (
                f"⚠️ Partial consistency with your reference baseline. "
                f"Reference: {ref_narrative}/{ref_visual}. Current: {narrative_style}/{visual_style}. "
                f"Vibe Match: {reference_overlap_score:.0f}%. Consider aligning more closely to your target style."
            )
        else:
            reference_drift = True
            reference_comparison_message = (
                f"❌ Style drift from your reference baseline! "
                f"Reference style: {ref_narrative}/{ref_visual}. Your current video: {narrative_style}/{visual_style}. "
                f"Vibe Match: {reference_overlap_score:.0f}%. You may have deviated from the original concept."
            )

        if ref_blueprint:
            reference_comparison_message += f"\n📋 Reference Blueprint: {ref_blueprint}"

    return {
        "transcript_narrative": narrative_track,
        "visual_narrative": visual_track,
        "narrative_style": narrative_style,
        "visual_style": visual_style,
        "visual_cut_frequency": round(visual_cut_frequency, 2),
        "avg_motion": round(avg_motion, 1),
        "face_percentage": round(face_percentage * 100, 1),
        "semantic_overlap_score": round(overlap_score, 1),
        "semantic_drift_detected": drift_flag,
        "vibe_check_message": vibe_message,
        # Reference comparison (Feature 4)
        "reference_overlap_score": reference_overlap_score,
        "reference_drift_detected": reference_drift,
        "reference_comparison_message": reference_comparison_message,
    }


def generate_narrative_blueprint(
    reference_videos_data: list[dict],
    avg_baseline: dict
) -> str:
    """Generate a Narrative Blueprint from reference video analysis data.
    
    The blueprint describes:
    - The "What": Core topic/concept
    - The "How": Delivery style, energy levels, visual pacing
    """
    if not reference_videos_data:
        return "No reference videos provided."

    # Aggregate characteristics
    natures = [r.get("video_nature", "general") for r in reference_videos_data]
    nature_counts = {}
    for n in natures:
        nature_counts[n] = nature_counts.get(n, 0) + 1
    dominant_nature = max(nature_counts, key=nature_counts.get) if nature_counts else "general"

    emotions = [r.get("dominant_emotion", "neutral") for r in reference_videos_data]
    emotion_counts = {}
    for e in emotions:
        emotion_counts[e] = emotion_counts.get(e, 0) + 1
    dominant_emotion = max(emotion_counts, key=emotion_counts.get) if emotion_counts else "neutral"

    avg_energy = avg_baseline.get("avg_energy", 50)
    avg_pacing = avg_baseline.get("avg_pacing", 50)
    avg_motion = avg_baseline.get("avg_motion", 50)
    avg_bpm = avg_baseline.get("avg_bpm", 80)

    # Energy level description
    if avg_energy > 60:
        energy_desc = "high-energy, vibrant"
    elif avg_energy > 35:
        energy_desc = "moderate, balanced"
    else:
        energy_desc = "calm, measured"

    # Pacing description
    if avg_pacing > 60:
        pacing_desc = "fast-paced with rapid transitions"
    elif avg_pacing > 30:
        pacing_desc = "steady with periodic transitions"
    else:
        pacing_desc = "slow and deliberate"

    # Visual style description
    if avg_motion > 50:
        visual_desc = "dynamic visuals with frequent movement"
    elif avg_motion > 25:
        visual_desc = "balanced visual composition"
    else:
        visual_desc = "static, focused framing"

    narrative_style = avg_baseline.get("dominant_narrative_style", "mixed")
    visual_style = avg_baseline.get("dominant_visual_style", "mixed")

    blueprint = (
        f"THE WHAT: {dominant_nature.capitalize()} content with a {dominant_emotion} emotional core. "
        f"THE HOW: {energy_desc} delivery ({avg_energy:.0f}/100 energy) at ~{avg_bpm:.0f} BPM effective pace. "
        f"Visual approach is {visual_desc} ({avg_motion:.0f}/100 motion density), {pacing_desc}. "
        f"Narrative mode: {narrative_style}. Visual mode: {visual_style}. "
        f"This baseline represents {len(reference_videos_data)} reference video(s)."
    )

    return blueprint


def _styles_compatible(style_a: str, style_b: str) -> bool:
    """Check if two style labels are compatible."""
    if style_a == style_b:
        return True
    if "mixed" in (style_a, style_b):
        return True
    # Partial compatibility
    compat_groups = [
        {"educational", "b-roll/ambient"},
        {"vlog/storytelling", "mixed"},
    ]
    for group in compat_groups:
        if style_a in group and style_b in group:
            return True
    return False
