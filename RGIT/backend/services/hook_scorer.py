"""Hook Strength Scorer — analyzes the first 3 seconds for immediate impact.

The first 3 seconds determine scroll-or-stay on short-form platforms.
This scorer isolates the opening window and grades it across four axes:
transcript hook, visual energy, audio punch, and face presence.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("hook_architect.hook_scorer")

# Hook keyword patterns that grab attention
HOOK_PHRASES = [
    "stop scrolling", "wait", "did you know", "here's the thing",
    "you won't believe", "watch this", "listen", "the secret",
    "nobody talks about", "i need to tell you", "breaking",
    "don't skip", "this is why", "how to", "what if",
    "the truth about", "warning", "imagine", "let me show you",
    "unpopular opinion", "hot take", "fun fact", "story time",
    "you need to see", "before you", "the real reason",
    "plot twist", "number one", "three things", "here's why",
]

# Question starters (questions = high retention hooks)
QUESTION_STARTERS = [
    "why", "what", "how", "when", "who", "where", "is it",
    "can you", "do you", "have you", "would you", "did you",
]

GRADE_THRESHOLDS = [
    (90, "A+", "🔥 Elite hook — viewers are locked in"),
    (80, "A",  "💎 Excellent hook — very strong opening"),
    (70, "B+", "✅ Good hook — solid first impression"),
    (60, "B",  "👍 Decent hook — room for improvement"),
    (50, "C+", "⚠️ Average hook — may lose some viewers"),
    (40, "C",  "🟡 Weak hook — needs stronger opening"),
    (30, "D",  "🔴 Poor hook — high scroll-away risk"),
    (0,  "F",  "❌ Critical — viewers will scroll past"),
]


def compute_hook_score(
    audio_signals: list[dict],
    visual_signals: list[dict],
    transcript_data: dict | None,
    emotion_data: dict | None,
    external_transcript: dict | None = None,
    external_windows: list[dict] | None = None,
) -> dict:
    """Analyze the first 3 seconds and produce an actionable Hook Score.
    
    Returns:
        {hook_score, grade, grade_description, breakdown:{transcript, visual, audio, face},
         suggestions[], first_words, has_face_opening}
    """
    # ── Transcript Hook Score (0-100) ────────────────────
    transcript_score, first_words, transcript_suggestions = _score_transcript_hook(
        transcript_data, external_transcript
    )

    # ── Visual Energy Score (0-100) ──────────────────────
    visual_score, visual_suggestions = _score_visual_hook(
        visual_signals, external_windows
    )

    # ── Audio Punch Score (0-100) ────────────────────────
    audio_score, audio_suggestions = _score_audio_hook(audio_signals)

    # ── Face Presence Score (0-100) ──────────────────────
    face_score, has_face, face_suggestions = _score_face_presence(
        visual_signals, emotion_data
    )

    # ── Overall Hook Score (weighted composite) ──────────
    # Transcript(30%) + Visual(25%) + Audio(25%) + Face(20%)
    overall = (
        transcript_score * 0.30 +
        visual_score * 0.25 +
        audio_score * 0.25 +
        face_score * 0.20
    )
    overall = round(min(100, max(0, overall)), 1)

    # ── Grade ────────────────────────────────────────────
    grade = "F"
    grade_desc = "❌ Critical"
    for threshold, g, desc in GRADE_THRESHOLDS:
        if overall >= threshold:
            grade = g
            grade_desc = desc
            break

    # ── Compile suggestions (top 3 most impactful) ───────
    all_suggestions = []
    all_suggestions.extend([(s, transcript_score, "transcript") for s in transcript_suggestions])
    all_suggestions.extend([(s, visual_score, "visual") for s in visual_suggestions])
    all_suggestions.extend([(s, audio_score, "audio") for s in audio_suggestions])
    all_suggestions.extend([(s, face_score, "face") for s in face_suggestions])
    # Sort by weakest component first (most impactful improvement)
    all_suggestions.sort(key=lambda x: x[1])
    top_suggestions = [{"text": s[0], "category": s[2]} for s in all_suggestions[:4]]

    return {
        "hook_score": overall,
        "grade": grade,
        "grade_description": grade_desc,
        "breakdown": {
            "transcript": round(transcript_score, 1),
            "visual": round(visual_score, 1),
            "audio": round(audio_score, 1),
            "face": round(face_score, 1),
        },
        "suggestions": top_suggestions,
        "first_words": first_words,
        "has_face_opening": has_face,
    }


def _score_transcript_hook(
    transcript_data: dict | None,
    external_transcript: dict | None,
) -> tuple[float, str, list[str]]:
    """Score the opening transcript for hook effectiveness."""
    suggestions = []
    
    # Get transcription text
    text = ""
    if external_transcript and external_transcript.get("transcription"):
        text = external_transcript["transcription"].strip()
    elif transcript_data and transcript_data.get("transcript"):
        text = transcript_data["transcript"].strip()

    if not text:
        return 20.0, "(no speech detected)", [
            "Start with a powerful spoken hook in the first second — 'Stop scrolling!' or 'You need to see this.'",
            "Even text overlays count — add a bold, curiosity-driven caption.",
        ]

    # Analyze first ~15 words (roughly first 3 seconds of speech)
    words = text.split()
    first_chunk = " ".join(words[:15]).lower()
    first_words = " ".join(words[:10])

    score = 40.0  # Base: has speech = decent start

    # Check for hook phrases
    hook_matches = [phrase for phrase in HOOK_PHRASES if phrase in first_chunk]
    if hook_matches:
        score += 25.0  # Strong hook phrase detected
    else:
        suggestions.append(f"Open with a hook phrase like 'Did you know...', 'Here's the thing about...', or 'Stop scrolling!'")

    # Check for questions (highest retention hooks)
    if "?" in first_chunk or any(first_chunk.startswith(q) for q in QUESTION_STARTERS):
        score += 20.0  # Questions are premium hooks
    else:
        suggestions.append("Questions in the first 3 seconds boost retention — try 'What if you could...?' or 'Why does nobody talk about...?'")

    # Check for numbers/lists (scannable, high-retention)
    if any(c.isdigit() for c in first_chunk):
        score += 10.0

    # Penalize slow starts
    filler_words = {"um", "uh", "so", "like", "okay", "hi", "hello", "hey guys", "what's up"}
    if any(first_chunk.startswith(f) for f in filler_words):
        score -= 15.0
        suggestions.append("Avoid filler words at the start ('um', 'so', 'hey guys') — jump straight into the hook.")

    # Word density: more words in 3s = higher energy delivery
    if len(words) >= 10:
        score += 5.0  # Fast, dense delivery

    return min(100, max(0, score)), first_words, suggestions


def _score_visual_hook(
    visual_signals: list[dict],
    external_windows: list[dict] | None,
) -> tuple[float, list[str]]:
    """Score visual energy in the opening seconds."""
    suggestions = []
    opening = visual_signals[:3] if len(visual_signals) >= 3 else visual_signals

    if not opening:
        return 30.0, ["Ensure your video starts with strong visual motion — don't open on a still frame."]

    # Average motion in first 3 seconds
    avg_motion = sum(v.get("motion_score", 0) for v in opening) / len(opening)
    has_cut = any(v.get("scene_cut", False) for v in opening)

    score = 30.0  # Base

    # Motion scoring
    if avg_motion >= 60:
        score += 35.0
    elif avg_motion >= 40:
        score += 20.0
    elif avg_motion >= 20:
        score += 10.0
    else:
        suggestions.append("The opening is visually static — add quick camera movement, zoom, or a dynamic B-roll shot.")

    # Scene cut bonus
    if has_cut:
        score += 15.0
    else:
        suggestions.append("Add a scene transition in the first 2-3 seconds to create visual variety.")

    # External API visual_energy enrichment
    if external_windows:
        opening_ext = [w for w in external_windows if w.get("start", 0) < 4]
        if opening_ext:
            avg_ext_energy = sum(w.get("visual_energy", 5) for w in opening_ext) / len(opening_ext)
            # Scale 1-10 to bonus points
            ext_bonus = (avg_ext_energy - 5) * 4  # -20 to +20
            score += ext_bonus

    return round(min(100, max(0, score)), 1), suggestions


def _score_audio_hook(audio_signals: list[dict]) -> tuple[float, list[str]]:
    """Score audio punch in the opening seconds."""
    suggestions = []
    opening = audio_signals[:3] if len(audio_signals) >= 3 else audio_signals

    if not opening:
        return 25.0, ["Add audio to your opening — background music or an immediate voiceover."]

    avg_energy = sum(a.get("energy", 0) for a in opening) / len(opening)
    avg_pacing = sum(a.get("pacing", 0) for a in opening) / len(opening)
    has_silence = any(a.get("silence_flag", True) for a in opening)

    score = 30.0

    # Energy scoring
    if avg_energy >= 55:
        score += 30.0
    elif avg_energy >= 35:
        score += 15.0
    else:
        suggestions.append("Boost opening audio energy — start with energetic music, a sound effect, or a punchy voiceover.")

    # Pacing
    if avg_pacing >= 40:
        score += 15.0

    # Silence penalty
    if has_silence:
        if all(a.get("silence_flag", True) for a in opening):
            score -= 20.0
            suggestions.append("Your opening is silent — this is the #1 cause of scroll-away. Add audio immediately.")
        else:
            score -= 5.0

    # Pitch variation (engaging delivery)
    avg_pitch_var = sum(a.get("pitch_variation", 0) for a in opening) / len(opening)
    if avg_pitch_var >= 40:
        score += 10.0

    return round(min(100, max(0, score)), 1), suggestions


def _score_face_presence(
    visual_signals: list[dict],
    emotion_data: dict | None,
) -> tuple[float, bool, list[str]]:
    """Score face presence and emotional expressiveness in the opening."""
    suggestions = []
    opening = visual_signals[:3] if len(visual_signals) >= 3 else visual_signals

    if not opening:
        return 40.0, False, []

    face_count = sum(1 for v in opening if v.get("face_present", False))
    has_face = face_count > 0
    face_ratio = face_count / len(opening)

    score = 30.0

    if face_ratio >= 0.8:
        score += 40.0  # Face anchoring from the start
    elif face_ratio >= 0.5:
        score += 25.0
    elif has_face:
        score += 15.0
    else:
        suggestions.append("Show your face in the first second — face anchoring increases retention by 35% on short-form.")

    # Emotional expressiveness in opening
    if emotion_data and emotion_data.get("emotion_timeline"):
        opening_emotions = emotion_data["emotion_timeline"][:3]
        expressive_emotions = {"excited", "happy", "surprise", "angry"}
        has_expression = any(
            e.get("facial_emotion", "neutral") in expressive_emotions or
            e.get("vocal_emotion", "neutral") in expressive_emotions
            for e in opening_emotions
        )
        if has_expression:
            score += 20.0
        else:
            suggestions.append("Show immediate emotion in your opening — surprise, excitement, or urgency grabs attention.")

    return round(min(100, max(0, score)), 1), has_face, suggestions
