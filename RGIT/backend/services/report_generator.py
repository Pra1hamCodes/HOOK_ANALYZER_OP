"""PDF Report Generator — Generates comprehensive analysis reports."""
from __future__ import annotations

import io
import json
import logging
from typing import Any

logger = logging.getLogger("hook_architect.report_generator")


def generate_report_html(result: dict) -> str:
    """Generate a full HTML report from analysis results.
    
    Returns HTML string that can be converted to PDF or served directly.
    """
    video_meta = result.get("video_meta", {})
    raw_summary = result.get("summary", {})
    # summary can be a string or dict — normalize to dict
    if isinstance(raw_summary, str):
        summary = {"text": raw_summary, "overall_score": result.get("overall_score", 0)}
    else:
        summary = raw_summary or {}
    if "overall_score" not in summary:
        summary["overall_score"] = result.get("overall_score", 0)
    zones = result.get("zones", [])
    timeline = result.get("timeline", [])
    hook_score = result.get("hook_score", {})
    emotion_arc = result.get("emotion_arc", {})
    retention_curve = result.get("retention_curve", {})
    transcript_data = result.get("transcript_data", {})
    virality_data = result.get("virality_data", {})
    emotion_data = result.get("emotion_data", {})
    persona = result.get("persona", {})

    # Zone summary
    red_zones = [z for z in zones if z.get("zone") == "red"]
    yellow_zones = [z for z in zones if z.get("zone") == "yellow"]
    green_zones = [z for z in zones if z.get("zone") == "green"]

    zones_html = ""
    for z in zones:
        color = "#ef4444" if z["zone"] == "red" else "#f59e0b" if z["zone"] == "yellow" else "#22c55e"
        flags = ", ".join(z.get("flags", []))
        zones_html += f"""
        <div style="border-left:4px solid {color};padding:12px 16px;margin:8px 0;background:rgba(0,0,0,0.03);border-radius:6px;">
            <strong>{_ft(z['start'])} → {_ft(z['end'])}</strong> — {z['zone'].upper()} zone
            <span style="float:right;font-weight:700;color:{color}">{z.get('avg_attention',0):.0f}/100</span>
            {f'<br><small style="color:#666">{flags}</small>' if flags else ''}
        </div>"""

    # Hook score section
    hs = hook_score
    hook_html = ""
    if hs:
        bd = hs.get("breakdown", {})
        hook_html = f"""
        <div style="text-align:center;margin:20px 0;">
            <div style="font-size:48px;font-weight:800;color:#8b5cf6">{hs.get('hook_score',0):.0f}<small>/100</small></div>
            <div style="font-size:16px;color:#666">Grade: {hs.get('grade','?')}</div>
        </div>
        <table style="width:100%;border-collapse:collapse;margin:10px 0;">
            <tr><th style="text-align:left;padding:6px;border-bottom:1px solid #ddd">Signal</th><th style="text-align:right;padding:6px;border-bottom:1px solid #ddd">Score</th></tr>
            <tr><td style="padding:6px">📝 Transcript Hook</td><td style="text-align:right;padding:6px;font-weight:600">{bd.get('transcript',0):.0f}</td></tr>
            <tr><td style="padding:6px">👁 Visual Energy</td><td style="text-align:right;padding:6px;font-weight:600">{bd.get('visual',0):.0f}</td></tr>
            <tr><td style="padding:6px">🔊 Audio Punch</td><td style="text-align:right;padding:6px;font-weight:600">{bd.get('audio',0):.0f}</td></tr>
            <tr><td style="padding:6px">👤 Face Presence</td><td style="text-align:right;padding:6px;font-weight:600">{bd.get('face',0):.0f}</td></tr>
        </table>"""
        if hs.get("suggestions"):
            hook_html += "<h4>💡 Improvement Suggestions</h4><ul>"
            for s in hs["suggestions"]:
                hook_html += f"<li><strong>[{s.get('category','')}]</strong> {s.get('text','')}</li>"
            hook_html += "</ul>"

    # Emotion arc
    arc_html = ""
    if emotion_arc:
        arc_html = f"""
        <p><strong>Arc Shape:</strong> {emotion_arc.get('arc_shape','—')}</p>
        <p>{emotion_arc.get('arc_summary','')}</p>"""
        if emotion_arc.get("transitions"):
            arc_html += "<h4>⚡ Emotional Transitions</h4><ul>"
            for tr in emotion_arc["transitions"]:
                icon = "🔴" if tr.get("type") == "drop_point" else "🟢"
                arc_html += f"<li>{icon} <strong>{_ft(tr['t'])}</strong> — {tr.get('description','')}</li>"
            arc_html += "</ul>"

    # Retention
    ret_html = ""
    if retention_curve:
        ret_html = f"""
        <div style="display:flex;gap:30px;margin:16px 0;">
            <div><div style="font-size:12px;color:#666">Avg Retention</div><div style="font-size:28px;font-weight:700">{retention_curve.get('predicted_avg_retention',0)}%</div></div>
            <div><div style="font-size:12px;color:#666">Watch-Through</div><div style="font-size:28px;font-weight:700">{retention_curve.get('predicted_watch_through_rate',0)}%</div></div>
            <div><div style="font-size:12px;color:#666">Grade</div><div style="font-size:28px;font-weight:700">{retention_curve.get('retention_grade','—')}</div></div>
        </div>"""
        if retention_curve.get("key_moments"):
            ret_html += "<h4>📌 Key Moments</h4><ul>"
            for m in retention_curve["key_moments"]:
                ret_html += f"<li><strong>{_ft(m['t'])}</strong> — {m.get('description','')}</li>"
            ret_html += "</ul>"

    # Transcript
    ts_html = ""
    if transcript_data:
        ts_html = f"""
        <p><strong>Score:</strong> {transcript_data.get('transcription_score',0):.0f}/100</p>
        <p><strong>Keywords:</strong> {', '.join(transcript_data.get('keywords',[]))}</p>
        <blockquote style="border-left:3px solid #8b5cf6;padding:8px 16px;margin:12px 0;background:rgba(139,92,246,0.05);color:#333;font-style:italic;">
            {transcript_data.get('transcript','(no transcript)')[:500]}
        </blockquote>"""

    # Emotion
    em_html = ""
    if emotion_data:
        em_html = f"""
        <p><strong>Facial:</strong> {emotion_data.get('dominant_facial_emotion','—')} | <strong>Vocal:</strong> {emotion_data.get('dominant_vocal_emotion','—')}</p>
        <p><strong>Alignment Score:</strong> {emotion_data.get('alignment_score',0):.0f}/100</p>"""

    # Virality
    vir_html = ""
    if virality_data:
        track = virality_data.get("recommended_track", {})
        vir_html = f"""
        <p><strong>Sound Score:</strong> {virality_data.get('sound_score',0):.0f}/100</p>
        {f'<p><strong>Recommended Track:</strong> {track.get("track_name","—")} by {track.get("artist","—")}</p>' if track else ''}
        <p><strong>Reasoning:</strong> {virality_data.get('song_meaning','') or virality_data.get('reasoning','—')}</p>"""

    # Goal keywords
    goal_keywords = result.get("goal_keywords", [])
    goal_html = ""
    if goal_keywords:
        goal_html = f"""
        <h3>🎯 Video Goals & Keywords</h3>
        <p><strong>Goal:</strong> {result.get('goal_text', '—')}</p>
        <p><strong>Evaluation Keywords:</strong> {', '.join(goal_keywords)}</p>
        <p><strong>Goal Alignment Score:</strong> {result.get('goal_alignment_score', '—')}/100</p>
        <p>{result.get('goal_evaluation_summary', '')}</p>
        <hr>"""

    overall_score = summary.get("overall_score", 0)
    score_color = "#22c55e" if overall_score >= 70 else "#f59e0b" if overall_score >= 45 else "#ef4444"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Hook Architect Analysis Report</title>
<style>
    body {{ font-family: 'Segoe UI', system-ui, sans-serif; max-width: 800px; margin: 0 auto; padding: 40px 30px; color: #1a1a2e; line-height: 1.6; }}
    h1 {{ color: #8b5cf6; font-size: 28px; margin-bottom: 4px; }}
    h2 {{ color: #0f172a; font-size: 20px; margin-top: 32px; padding-bottom: 8px; border-bottom: 2px solid #e2e8f0; }}
    h3 {{ color: #334155; font-size: 16px; margin-top: 20px; }}
    h4 {{ color: #475569; font-size: 14px; margin-top: 16px; }}
    hr {{ border: none; border-top: 1px solid #e2e8f0; margin: 24px 0; }}
    table {{ font-size: 14px; }}
    ul {{ padding-left: 20px; }}
    li {{ margin: 4px 0; }}
    .meta {{ color: #64748b; font-size: 13px; }}
    .badge {{ display: inline-block; padding: 2px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; }}
    @media print {{ body {{ padding: 20px; }} }}
</style>
</head>
<body>
    <h1>🎬 Hook Architect — Analysis Report</h1>
    <p class="meta">Generated for: {video_meta.get('filename','—')} | Duration: {video_meta.get('duration',0):.1f}s |
    {f'Persona: {persona.get("niche","general")}' if persona else 'No persona'}</p>
    <hr>

    {goal_html}

    <h2>📊 Overall Score</h2>
    <div style="text-align:center;margin:20px 0;">
        <div style="font-size:64px;font-weight:800;color:{score_color}">{overall_score}</div>
        <div style="font-size:14px;color:#666">/100 Hook Viability Score</div>
    </div>
    <p>{summary.get('text','')}</p>
    <div style="margin:12px 0;">
        <span class="badge" style="background:rgba(34,197,94,0.1);color:#22c55e">🟢 {len(green_zones)} Green</span>
        <span class="badge" style="background:rgba(245,158,11,0.1);color:#f59e0b">🟡 {len(yellow_zones)} Yellow</span>
        <span class="badge" style="background:rgba(239,68,68,0.1);color:#ef4444">🔴 {len(red_zones)} Red</span>
    </div>
    <hr>

    <h2>🎣 Hook Strength</h2>
    {hook_html or '<p>No hook score data.</p>'}
    <hr>

    <h2>📈 Emotion Arc</h2>
    {arc_html or '<p>No emotion arc data.</p>'}
    <hr>

    <h2>📉 Retention Curve</h2>
    {ret_html or '<p>No retention data.</p>'}
    <hr>

    <h2>⚠️ Zone Analysis</h2>
    {zones_html or '<p>No zones detected.</p>'}
    <hr>

    <h2>🗣️ Transcript Analysis</h2>
    {ts_html or '<p>No transcript data.</p>'}
    <hr>

    <h2>🎭 Emotion Analysis</h2>
    {em_html or '<p>No emotion data.</p>'}
    <hr>

    <h2>🎵 Virality & Audio</h2>
    {vir_html or '<p>No virality data.</p>'}
    <hr>
    
    <p class="meta" style="text-align:center;margin-top:40px;">Generated by Hook Architect • AI-Powered Video Retention Engine</p>
</body>
</html>"""
    return html


def generate_report_text(result: dict) -> str:
    """Generate a plain-text summary of the analysis for LLM context."""
    raw_summary = result.get("summary", {})
    if isinstance(raw_summary, str):
        summary = {"text": raw_summary, "overall_score": result.get("overall_score", 0)}
    else:
        summary = raw_summary or {}
    if "overall_score" not in summary:
        summary["overall_score"] = result.get("overall_score", 0)
    zones = result.get("zones", [])
    hook_score = result.get("hook_score", {})
    emotion_arc = result.get("emotion_arc", {})
    retention_curve = result.get("retention_curve", {})
    transcript_data = result.get("transcript_data", {})
    emotion_data = result.get("emotion_data", {})
    virality_data = result.get("virality_data", {})
    video_meta = result.get("video_meta", {})

    lines = [
        f"VIDEO ANALYSIS REPORT",
        f"File: {video_meta.get('filename','—')} | Duration: {video_meta.get('duration',0):.1f}s",
        f"Overall Score: {summary.get('overall_score', 0)}/100",
        f"Summary: {summary.get('text', '')}",
        "",
    ]
    
    # Goal info
    if result.get("goal_keywords"):
        lines.append(f"Goal: {result.get('goal_text', '')}")
        lines.append(f"Goal Keywords: {', '.join(result['goal_keywords'])}")
        lines.append(f"Goal Alignment: {result.get('goal_alignment_score', '?')}/100")
        lines.append(f"Goal Eval: {result.get('goal_evaluation_summary', '')}")
        lines.append("")

    # Hook
    if hook_score:
        lines.append(f"HOOK SCORE: {hook_score.get('hook_score',0):.0f}/100 (Grade: {hook_score.get('grade','?')})")
        bd = hook_score.get("breakdown", {})
        lines.append(f"  Transcript: {bd.get('transcript',0):.0f} | Visual: {bd.get('visual',0):.0f} | Audio: {bd.get('audio',0):.0f} | Face: {bd.get('face',0):.0f}")
        if hook_score.get("suggestions"):
            for s in hook_score["suggestions"]:
                lines.append(f"  → [{s.get('category','')}] {s.get('text','')}")
        lines.append("")

    # Emotions
    if emotion_data:
        lines.append(f"EMOTION: Facial={emotion_data.get('dominant_facial_emotion','—')} Vocal={emotion_data.get('dominant_vocal_emotion','—')} Alignment={emotion_data.get('alignment_score',0):.0f}/100")
        lines.append("")

    # Emotion Arc
    if emotion_arc:
        lines.append(f"EMOTION ARC: Shape={emotion_arc.get('arc_shape','—')}")
        lines.append(f"  {emotion_arc.get('arc_summary','')}")
        for tr in emotion_arc.get("transitions", []):
            lines.append(f"  {'↓ DROP' if tr.get('type')=='drop_point' else '↑ RECOVERY'} at {_ft(tr['t'])}: {tr.get('description','')}")
        lines.append("")

    # Retention
    if retention_curve:
        lines.append(f"RETENTION: Avg={retention_curve.get('predicted_avg_retention',0)}% Watch-Through={retention_curve.get('predicted_watch_through_rate',0)}% Grade={retention_curve.get('retention_grade','—')}")
        for m in retention_curve.get("key_moments", []):
            lines.append(f"  {m.get('event','')} at {_ft(m['t'])}: {m.get('description','')}")
        lines.append("")

    # Zones
    lines.append(f"ZONES: {len([z for z in zones if z['zone']=='green'])} green, {len([z for z in zones if z['zone']=='yellow'])} yellow, {len([z for z in zones if z['zone']=='red'])} red")
    for z in zones:
        flags = ", ".join(z.get("flags", []))
        lines.append(f"  [{z['zone'].upper()}] {_ft(z['start'])}→{_ft(z['end'])} score={z.get('avg_attention',0):.0f} {flags}")
    lines.append("")

    # Transcript
    if transcript_data:
        lines.append(f"TRANSCRIPT (score {transcript_data.get('transcription_score',0):.0f}/100):")
        lines.append(f"  Keywords: {', '.join(transcript_data.get('keywords',[]))}")
        lines.append(f"  \"{transcript_data.get('transcript','')[:400]}\"")
        lines.append("")

    # Virality
    if virality_data:
        track = virality_data.get("recommended_track", {})
        lines.append(f"VIRALITY: Sound Score={virality_data.get('sound_score',0):.0f}/100")
        if track:
            lines.append(f"  Recommended: {track.get('track_name','—')} by {track.get('artist','—')}")
        lines.append("")

    return "\n".join(lines)


def _ft(seconds: float) -> str:
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m}:{s:02d}"
