"""LLM Coach — Groq-powered per-zone AI coaching for video creators."""
from __future__ import annotations

import logging
import json
from typing import Any

from core.config import GEMINI_API_KEY

logger = logging.getLogger("hook_architect.llm_coach")


async def generate_zone_insights(
    zones: list[dict],
    timeline: list[dict],
    transcript_data: dict | None,
    emotion_data: dict | None,
    virality_data: dict | None,
    hook_score_data: dict | None,
    retention_data: dict | None,
    niche: str = "general",
) -> list[dict]:
    """Generate AI coaching insights for each zone using Gemini Flash.

    Returns a list of insight dicts, one per zone, with:
    - zone_index, start, end
    - overall_advice (1-2 sentence summary)
    - signal_diagnosis (which signals are weak and why)
    - fix_actions (3 concrete actions ranked by impact)
    - hook_alternatives (if zone is in first 3s)
    """
    if not GEMINI_API_KEY:
        logger.warning("[LLM_COACH] No API key — using rule-based fallback")
        return _rule_based_insights(zones, timeline, transcript_data, emotion_data)

    try:
        from groq import Groq
        client = Groq(api_key=GEMINI_API_KEY)
    except ImportError:
        logger.error("[LLM_COACH] groq package not installed")
        return _rule_based_insights(zones, timeline, transcript_data, emotion_data)
    except Exception as e:
        logger.error(f"[LLM_COACH] Groq init failed: {e}")
        return _rule_based_insights(zones, timeline, transcript_data, emotion_data)

    insights = []

    for i, zone in enumerate(zones):
        start, end = zone["start"], zone["end"]
        zone_type = zone.get("zone", "yellow")
        avg_att = zone.get("avg_attention", 50)

        # Gather zone-specific timeline data
        zone_points = [p for p in timeline if start <= p["t"] < end]
        avg_audio = _avg(zone_points, "audio_score")
        avg_visual = _avg(zone_points, "visual_score")
        avg_transcript = _avg(zone_points, "transcript_score")

        faults = set()
        strengths = set()
        for p in zone_points:
            for f in p.get("faults", []):
                faults.add(f.get("label", str(f)) if isinstance(f, dict) else str(f))
            for s in p.get("strengths", []):
                strengths.add(s.get("label", str(s)) if isinstance(s, dict) else str(s))

        # Context from other analyzers
        hook_info = ""
        if hook_score_data and start < 3:
            hook_info = f"Hook score: {hook_score_data.get('hook_score', 0)}/100 ({hook_score_data.get('grade', '?')}). "
            hook_info += f"Weakest axis: {_weakest_hook_axis(hook_score_data)}."

        retention_info = ""
        if retention_data and retention_data.get("curve_points"):
            zone_retention = [p for p in retention_data["curve_points"] if start <= p["t"] < end]
            if zone_retention:
                ret_start = zone_retention[0]["retention_pct"]
                ret_end = zone_retention[-1]["retention_pct"]
                retention_info = f"Retention drops from {ret_start:.0f}% to {ret_end:.0f}% in this zone."

        emotion_info = ""
        if emotion_data:
            emotion_info = f"Dominant emotion: {emotion_data.get('dominant_facial_emotion', 'neutral')}. Alignment: {emotion_data.get('alignment_score', 50):.0f}/100."

        transcript_text = ""
        if transcript_data and transcript_data.get("transcript"):
            transcript_text = transcript_data["transcript"][:300]

        prompt = f"""You are a world-class short-form video retention coach. Analyze this video zone and provide actionable coaching.

ZONE CONTEXT:
- Zone: {_format_time(start)} → {_format_time(end)} ({zone_type.upper()} zone)
- Creator niche: {niche}
- Average attention: {avg_att:.0f}/100
- Audio score: {avg_audio:.0f}/100 | Visual score: {avg_visual:.0f}/100 | Transcript score: {avg_transcript:.0f}/100
- Detected issues: {', '.join(faults) if faults else 'none'}
- Detected strengths: {', '.join(strengths) if strengths else 'none'}
{f'- {hook_info}' if hook_info else ''}
{f'- {retention_info}' if retention_info else ''}
{f'- {emotion_info}' if emotion_info else ''}
{f'- Transcript excerpt: "{transcript_text}"' if transcript_text else '- No speech in this zone'}

Respond in EXACTLY this JSON format (no markdown, no code fences):
{{"overall_advice": "1-2 sentence diagnosis and top recommendation",
"signal_diagnosis": {{"weakest": "audio|visual|transcript", "explanation": "why this signal is dragging the zone down"}},
"fix_actions": [
  {{"action": "specific action text", "impact": "high|medium|low", "category": "audio|visual|script|pacing"}},
  {{"action": "second action", "impact": "high|medium|low", "category": "audio|visual|script|pacing"}},
  {{"action": "third action", "impact": "medium|low", "category": "audio|visual|script|pacing"}}
]}}"""

        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=500,
            )
            text = response.choices[0].message.content.strip()
            # Strip markdown code fences if present
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                if text.endswith("```"):
                    text = text[:-3]
                text = text.strip()

            parsed = json.loads(text)
            insights.append({
                "zone_index": i,
                "start": start,
                "end": end,
                "zone_type": zone_type,
                "avg_attention": avg_att,
                "overall_advice": parsed.get("overall_advice", ""),
                "signal_diagnosis": parsed.get("signal_diagnosis", {}),
                "fix_actions": parsed.get("fix_actions", []),
                "signals": {
                    "audio": round(avg_audio, 1),
                    "visual": round(avg_visual, 1),
                    "transcript": round(avg_transcript, 1),
                },
                "faults": list(faults),
                "strengths": list(strengths),
                "source": "gemini",
            })
        except Exception as e:
            logger.error(f"[LLM_COACH] Groq call failed for zone {i}: {e}")
            insights.append(_rule_based_single(i, zone, zone_points, faults, strengths,
                                                avg_audio, avg_visual, avg_transcript))

    return insights


def _rule_based_insights(
    zones: list[dict],
    timeline: list[dict],
    transcript_data: dict | None,
    emotion_data: dict | None,
) -> list[dict]:
    """Rule-based fallback when Gemini is unavailable."""
    insights = []
    for i, zone in enumerate(zones):
        start, end = zone["start"], zone["end"]
        zone_points = [p for p in timeline if start <= p["t"] < end]

        faults = set()
        strengths = set()
        for p in zone_points:
            for f in p.get("faults", []):
                faults.add(f.get("label", str(f)) if isinstance(f, dict) else str(f))
            for s in p.get("strengths", []):
                strengths.add(s.get("label", str(s)) if isinstance(s, dict) else str(s))

        avg_audio = _avg(zone_points, "audio_score")
        avg_visual = _avg(zone_points, "visual_score")
        avg_transcript = _avg(zone_points, "transcript_score")

        insights.append(_rule_based_single(i, zone, zone_points, faults, strengths,
                                            avg_audio, avg_visual, avg_transcript))
    return insights


def _rule_based_single(i, zone, zone_points, faults, strengths,
                        avg_audio, avg_visual, avg_transcript):
    """Generate a single rule-based insight."""
    zone_type = zone.get("zone", "yellow")
    avg_att = zone.get("avg_attention", 50)
    faults_lower = [f.lower() for f in faults]

    # Determine weakest signal
    signals = {"audio": avg_audio, "visual": avg_visual, "transcript": avg_transcript}
    weakest = min(signals, key=signals.get)

    # Generate advice based on weakest signal and faults
    advice_map = {
        "audio": "Your audio is the weakest signal here. Add vocal energy variation, background music, or sound effects to maintain engagement.",
        "visual": "Visual engagement is dropping. Add jump cuts, B-roll, or on-screen text to keep viewers watching.",
        "transcript": "The script needs work. Add a pattern interrupt — a question, surprising fact, or direct address to the viewer.",
    }

    actions = []
    if "silence" in " ".join(faults_lower) or "low energy" in " ".join(faults_lower):
        actions.append({"action": "Add background music or voiceover to fill dead air", "impact": "high", "category": "audio"})
    if "static" in " ".join(faults_lower) or "no face" in " ".join(faults_lower):
        actions.append({"action": "Insert B-roll footage or switch camera angle", "impact": "high", "category": "visual"})
    if "monotone" in " ".join(faults_lower):
        actions.append({"action": "Re-record with vocal emphasis on key words", "impact": "high", "category": "audio"})
    if "slow" in " ".join(faults_lower):
        actions.append({"action": "Speed up to 1.2x or add rapid-fire cuts", "impact": "medium", "category": "pacing"})

    # Ensure we have 3 actions
    default_actions = [
        {"action": "Add text overlay highlighting the key message", "impact": "medium", "category": "visual"},
        {"action": "Insert a hook phrase: 'Here's why this matters...'", "impact": "medium", "category": "script"},
        {"action": "Add zoom-in effect on the speaker's face", "impact": "low", "category": "visual"},
    ]
    while len(actions) < 3:
        for da in default_actions:
            if da not in actions and len(actions) < 3:
                actions.append(da)

    return {
        "zone_index": i,
        "start": zone["start"],
        "end": zone["end"],
        "zone_type": zone_type,
        "avg_attention": avg_att,
        "overall_advice": advice_map.get(weakest, "This zone needs improvement across multiple signals."),
        "signal_diagnosis": {"weakest": weakest, "explanation": f"{weakest.title()} averages {signals[weakest]:.0f}/100 — well below the engagement threshold."},
        "fix_actions": actions[:3],
        "signals": {
            "audio": round(avg_audio, 1),
            "visual": round(avg_visual, 1),
            "transcript": round(avg_transcript, 1),
        },
        "faults": list(faults),
        "strengths": list(strengths),
        "source": "rule_based",
    }


def _avg(points: list[dict], key: str) -> float:
    vals = [p.get(key, 0) for p in points]
    return sum(vals) / max(len(vals), 1)


def _weakest_hook_axis(hook_data: dict) -> str:
    bd = hook_data.get("breakdown", {})
    if not bd:
        return "unknown"
    return min(bd, key=bd.get)


def _format_time(seconds: float) -> str:
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m}:{s:02d}"


# ═══════════════════════════════════════════════════════════
# GOAL KEYWORD EXTRACTION
# ═══════════════════════════════════════════════════════════

async def extract_goal_keywords(goal_text: str) -> dict:
    """Use Gemini to extract evaluation keywords and criteria from the user's goal description.

    Returns dict with:
    - keywords: list of evaluation keywords
    - category: video category/type
    - evaluation_criteria: list of what to look for
    - summary: one-line summary of the goal
    """
    if not goal_text or not goal_text.strip():
        return {"keywords": [], "category": "general", "evaluation_criteria": [], "summary": ""}

    # Rule-based fallback keywords
    fallback = _rule_based_keywords(goal_text)

    if not GEMINI_API_KEY:
        logger.warning("[LLM_COACH] No API key — using rule-based keyword extraction")
        return fallback

    try:
        from groq import Groq
        client = Groq(api_key=GEMINI_API_KEY)
    except Exception as e:
        logger.error(f"[LLM_COACH] Groq init failed for keywords: {e}")
        return fallback

    prompt = f"""You are a video content strategist. The user describes the kind of video they want to create. Extract evaluation keywords, category, and criteria.

USER GOAL: "{goal_text}"

Respond in EXACTLY this JSON format (no markdown, no code fences):
{{"keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"],
"category": "one word category like travel, cooking, tech, fitness, education, comedy, etc",
"evaluation_criteria": ["what to look for 1", "what to look for 2", "what to look for 3"],
"summary": "one-line summary of what the user wants"}}"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=300,
        )
        text = response.choices[0].message.content.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
        parsed = json.loads(text)
        return {
            "keywords": parsed.get("keywords", [])[:10],
            "category": parsed.get("category", "general"),
            "evaluation_criteria": parsed.get("evaluation_criteria", [])[:5],
            "summary": parsed.get("summary", ""),
        }
    except Exception as e:
        logger.error(f"[LLM_COACH] Groq keyword extraction failed: {e}")
        return fallback


def _rule_based_keywords(goal_text: str) -> dict:
    """Simple keyword extraction fallback."""
    import re
    words = re.findall(r'\b[a-zA-Z]{3,}\b', goal_text.lower())
    stopwords = {"the", "and", "for", "that", "with", "this", "from", "your", "have",
                 "are", "was", "were", "been", "being", "will", "would", "could",
                 "should", "can", "may", "might", "shall", "must", "need", "want",
                 "like", "make", "video", "kind", "type", "sort", "aiming", "looking"}
    keywords = [w for w in words if w not in stopwords]
    # Deduplicate preserving order
    seen = set()
    unique = []
    for k in keywords:
        if k not in seen:
            seen.add(k)
            unique.append(k)
    return {
        "keywords": unique[:8],
        "category": "general",
        "evaluation_criteria": ["content relevance", "visual quality", "audience engagement"],
        "summary": goal_text[:100],
    }


# ═══════════════════════════════════════════════════════════
# CHAT WITH REPORT (Interactive Q&A)
# ═══════════════════════════════════════════════════════════

async def chat_with_report(report_text: str, message: str, history: list[dict] | None = None) -> str:
    """Use Gemini to answer user questions about their video analysis report.

    Args:
        report_text: Full text report from generate_report_text()
        message: User's question
        history: Previous chat messages [{"role": "user"|"assistant", "content": "..."}]

    Returns:
        AI response string
    """
    if not GEMINI_API_KEY:
        return ("I'm currently unavailable (no API key configured). "
                "Please check your GEMINI_API_KEY in the .env file.")

    try:
        from groq import Groq
        client = Groq(api_key=GEMINI_API_KEY)
    except ImportError:
        return "The groq package is not installed. Run: pip install groq"
    except Exception as e:
        return f"Failed to initialize AI: {e}"

    # Build conversation context
    history_text = ""
    if history:
        for msg in history[-10:]:  # Keep last 10 messages for context
            role = "User" if msg.get("role") == "user" else "Assistant"
            history_text += f"\n{role}: {msg.get('content', '')}"

    prompt = f"""You are Hook Architect AI — a world-class video retention coach and analyst.
You have access to the complete analysis report of the user's video below.
Answer the user's questions with specific, actionable insights based on the report data.
Be concise but thorough. Use emoji sparingly for visual appeal.
Reference specific scores, timestamps, and data points from the report.

═══ ANALYSIS REPORT ═══
{report_text}
═══ END REPORT ═══
{f'''
═══ CONVERSATION HISTORY ═══{history_text}
═══ END HISTORY ═══''' if history_text else ''}

User: {message}

Respond naturally as a helpful video coach. Keep responses focused and actionable."""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=800,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"[LLM_COACH] Chat failed: {e}")
        return f"Sorry, I encountered an error: {e}. Please try again."
