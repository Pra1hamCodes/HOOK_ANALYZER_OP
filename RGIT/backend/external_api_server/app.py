"""External Video Analysis API Server — Flask app on port 5000.

Provides two endpoints consumed by Hook Architect's main backend:
  POST /transcribe_and_summarize — Groq Whisper + Llama niche detection
  POST /analyze_video — 2s window analysis with visual_energy, motion_level, drop_risk
"""
from __future__ import annotations

import os
import sys
import json
import math
import tempfile
import logging
from pathlib import Path

import cv2
import numpy as np
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# Load .env from parent backend dir
env_path = Path(__file__).resolve().parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024  # 500 MB

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("external_api")

# ── Groq client setup ────────────────────────────────────
GROQ_API_KEY = os.getenv("GEMINI_API_KEY", "")  # stored as GEMINI_API_KEY in .env
WHISPER_MODEL = "whisper-large-v3-turbo"
LLM_MODEL = "llama-3.3-70b-versatile"

SUPPORTED_NICHES = [
    "emotional", "action", "educational", "vlog",
    "cinematic", "comedy", "music", "medical",
    "motivation", "documentary", "gaming", "fitness",
    "cooking", "tech", "news", "general",
]

# ffmpeg binary — check same location as main backend
BACKEND_DIR = Path(__file__).resolve().parent.parent
_ffmpeg_candidates = [
    BACKEND_DIR / "ffmpeg.exe",
    Path("ffmpeg"),
]
FFMPEG_BIN = str(next((p for p in _ffmpeg_candidates if p.exists()), Path("ffmpeg")))
FFPROBE_BIN = str(next(
    (p for p in [BACKEND_DIR / "ffprobe.exe", Path("ffprobe")] if p.exists()),
    Path("ffprobe"),
))


def _get_groq_client():
    """Lazy-load Groq client."""
    try:
        from groq import Groq
        return Groq(api_key=GROQ_API_KEY)
    except Exception as e:
        logger.error(f"Failed to create Groq client: {e}")
        return None


def _get_video_duration(video_path: str) -> float:
    """Get video duration using ffprobe."""
    import subprocess
    try:
        result = subprocess.run(
            [FFPROBE_BIN, "-v", "error", "-show_entries",
             "format=duration", "-of", "json", video_path],
            capture_output=True, text=True, timeout=30,
        )
        data = json.loads(result.stdout)
        return float(data["format"]["duration"])
    except Exception as e:
        logger.warning(f"ffprobe failed, trying OpenCV: {e}")
        cap = cv2.VideoCapture(video_path)
        if cap.isOpened():
            fps = cap.get(cv2.CAP_PROP_FPS) or 30
            frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
            cap.release()
            return frames / fps
        return 0.0


def _extract_audio_from_video(video_path: str, output_path: str) -> bool:
    """Extract audio track from video using ffmpeg."""
    import subprocess
    try:
        result = subprocess.run(
            [FFMPEG_BIN, "-y", "-i", video_path,
             "-vn", "-acodec", "pcm_s16le", "-ar", "16000",
             "-ac", "1", output_path],
            capture_output=True, text=True, timeout=120,
        )
        return result.returncode == 0 and Path(output_path).exists()
    except Exception as e:
        logger.error(f"Audio extraction failed: {e}")
        return False


# ═══════════════════════════════════════════════════════════
# ENDPOINT 1: TRANSCRIBE AND SUMMARIZE
# ═══════════════════════════════════════════════════════════

@app.route("/transcribe_and_summarize", methods=["POST"])
def transcribe_and_summarize():
    """Transcribe audio via Groq Whisper + detect niche via Llama.
    
    Accepts: multipart form with 'audio' file
    Returns: {niche, transcription, summary, supported_niches}
    """
    if "audio" not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    audio_file = request.files["audio"]
    if not audio_file.filename:
        return jsonify({"error": "Empty filename"}), 400

    client = _get_groq_client()
    if not client:
        return jsonify({"error": "Groq API unavailable — check GEMINI_API_KEY in .env"}), 503

    # Save audio to temp file
    suffix = Path(audio_file.filename).suffix or ".wav"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        audio_file.save(tmp.name)
        tmp_path = tmp.name

    try:
        # ── Step 1: Transcribe with Whisper ──────────────
        logger.info(f"Transcribing audio: {audio_file.filename} ({Path(tmp_path).stat().st_size / 1024:.0f} KB)")

        with open(tmp_path, "rb") as f:
            transcription_response = client.audio.transcriptions.create(
                model=WHISPER_MODEL,
                file=(audio_file.filename, f),
                response_format="text",
                language="en",
            )

        transcript_text = str(transcription_response).strip()
        logger.info(f"Transcription complete: {len(transcript_text)} chars, preview: '{transcript_text[:80]}'")

        if not transcript_text or len(transcript_text) < 5:
            return jsonify({
                "niche": "general",
                "transcription": transcript_text or "",
                "summary": "No meaningful speech detected in the audio.",
                "supported_niches": SUPPORTED_NICHES,
            })

        # ── Step 2: Niche detection + summary via Llama ──
        niche_prompt = f"""Analyze this video transcript and determine:
1. The content NICHE (choose ONE from: {', '.join(SUPPORTED_NICHES)})
2. A brief SUMMARY (2-3 sentences max)

Transcript:
\"\"\"{transcript_text[:2000]}\"\"\"

Reply in EXACTLY this JSON format, nothing else:
{{"niche": "chosen_niche", "summary": "Brief summary of the content"}}"""

        try:
            chat_response = client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": "You are a short-form video content analyst. Respond only with valid JSON."},
                    {"role": "user", "content": niche_prompt},
                ],
                temperature=0.3,
                max_tokens=200,
            )

            llm_text = chat_response.choices[0].message.content.strip()
            # Parse JSON (handle markdown code blocks)
            if "```" in llm_text:
                llm_text = llm_text.split("```json")[-1].split("```")[0].strip()
                if not llm_text:
                    llm_text = chat_response.choices[0].message.content.strip()
                    llm_text = llm_text.split("```")[-2].strip()

            llm_data = json.loads(llm_text)
            niche = llm_data.get("niche", "general").lower()
            summary = llm_data.get("summary", "")

            # Validate niche
            if niche not in SUPPORTED_NICHES:
                niche = "general"

            logger.info(f"Niche detected: {niche}, summary: {summary[:60]}")

        except Exception as llm_err:
            logger.warning(f"LLM niche detection failed: {llm_err}")
            niche = "general"
            summary = f"Video contains speech: {transcript_text[:150]}..."

        return jsonify({
            "niche": niche,
            "transcription": transcript_text,
            "summary": summary,
            "supported_niches": SUPPORTED_NICHES,
        })

    except Exception as e:
        logger.error(f"Transcription pipeline failed: {e}")
        return jsonify({"error": str(e)}), 500

    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════
# ENDPOINT 2: ANALYZE VIDEO
# ═══════════════════════════════════════════════════════════

@app.route("/analyze_video", methods=["POST"])
def analyze_video():
    """Analyze a video in 2-second windows for visual energy, motion, and drop risk.
    
    Accepts: multipart form with 'video' file + optional 'niche' field
    Returns: {status, niche, duration_seconds, overall_score, total_windows,
              drop_zones_count, analysis_windows[], drop_zones[]}
    """
    if "video" not in request.files:
        return jsonify({"error": "No video file provided"}), 400

    video_file = request.files["video"]
    niche = request.form.get("niche", "general")

    if not video_file.filename:
        return jsonify({"error": "Empty filename"}), 400

    # Save video to temp file
    suffix = Path(video_file.filename).suffix or ".mp4"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        video_file.save(tmp.name)
        tmp_path = tmp.name

    try:
        logger.info(f"Analyzing video: {video_file.filename}, niche={niche}")

        # Get duration
        duration = _get_video_duration(tmp_path)
        if duration <= 0:
            return jsonify({"error": "Could not determine video duration"}), 422

        logger.info(f"Video duration: {duration:.1f}s")

        # ── Analyze in 2-second windows ──────────────────
        cap = cv2.VideoCapture(tmp_path)
        if not cap.isOpened():
            return jsonify({"error": "Could not open video file"}), 422

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        window_size = 2.0  # seconds
        frames_per_window = int(fps * window_size)

        analysis_windows = []
        window_idx = 0
        prev_window_gray = None

        while True:
            window_start = window_idx * window_size
            if window_start >= duration:
                break

            window_end = min(window_start + window_size, duration)
            start_frame = int(window_start * fps)
            end_frame = min(int(window_end * fps), total_frames)

            if start_frame >= total_frames:
                break

            # Read frames in this window
            cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
            window_frames = []
            window_grays = []

            for _ in range(end_frame - start_frame):
                ret, frame = cap.read()
                if not ret:
                    break
                window_frames.append(frame)
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                window_grays.append(gray)

            if len(window_frames) < 2:
                window_idx += 1
                continue

            # ── Compute motion (frame-to-frame differences) ──
            motion_scores = []
            for i in range(1, len(window_grays)):
                diff = cv2.absdiff(window_grays[i], window_grays[i - 1])
                motion = np.mean(diff)
                motion_scores.append(motion)

            avg_motion = np.mean(motion_scores) if motion_scores else 0.0

            # ── Compute inter-window motion (scene transitions) ──
            scene_change = False
            if prev_window_gray is not None and len(window_grays) > 0:
                cross_diff = cv2.absdiff(window_grays[0], prev_window_gray)
                cross_motion = np.mean(cross_diff)
                if cross_motion > 30:  # significant scene change
                    scene_change = True

            prev_window_gray = window_grays[-1] if window_grays else prev_window_gray

            # ── Compute brightness/contrast (visual complexity) ──
            brightnesses = [np.mean(g) for g in window_grays]
            avg_brightness = np.mean(brightnesses)
            brightness_variance = np.var(brightnesses) if len(brightnesses) > 1 else 0

            # ── Compute edge density (visual complexity) ──
            edge_scores = []
            for g in window_grays[::max(1, len(window_grays) // 3)]:  # sample 3 frames
                edges = cv2.Canny(g, 50, 150)
                edge_density = np.mean(edges) / 255.0 * 100
                edge_scores.append(edge_density)
            avg_edge_density = np.mean(edge_scores) if edge_scores else 0

            # ── Compute color variance (visual richness) ──
            color_variances = []
            for f in window_frames[::max(1, len(window_frames) // 3)]:
                hsv = cv2.cvtColor(f, cv2.COLOR_BGR2HSV)
                color_var = np.std(hsv[:, :, 0])  # hue variance
                color_variances.append(color_var)
            avg_color_var = np.mean(color_variances) if color_variances else 0

            # ── Compute visual_energy (1-10 scale) ───────
            # Combines motion, edge density, brightness variance, color variance
            motion_component = min(10, (avg_motion / 15.0) * 10)  # 0-15+ range → 1-10
            edge_component = min(10, (avg_edge_density / 20.0) * 10)  # 0-20+ → 1-10
            brightness_var_component = min(10, (brightness_variance / 200.0) * 10)
            color_component = min(10, (avg_color_var / 40.0) * 10)
            scene_bonus = 2.0 if scene_change else 0.0

            visual_energy_raw = (
                motion_component * 0.35 +
                edge_component * 0.25 +
                brightness_var_component * 0.15 +
                color_component * 0.15 +
                scene_bonus * 0.10
            )
            visual_energy = round(max(1.0, min(10.0, visual_energy_raw + 1)), 1)

            # ── Determine motion_level label ─────────────
            if avg_motion > 20:
                motion_level = "high"
            elif avg_motion > 8:
                motion_level = "medium"
            elif avg_motion > 3:
                motion_level = "low"
            else:
                motion_level = "static"

            # ── Determine drop_risk ──────────────────────
            # Drop risk = low visual energy + low motion + low brightness variance
            drop_risk = False
            if visual_energy <= 3.5 and motion_level in ("static", "low"):
                drop_risk = True
            elif visual_energy <= 2.5:
                drop_risk = True
            # Middle sections are more vulnerable to drops
            relative_pos = window_start / max(duration, 1)
            if 0.3 < relative_pos < 0.8 and visual_energy <= 4.0 and motion_level == "low":
                drop_risk = True

            window_data = {
                "window_index": window_idx,
                "start": round(window_start, 1),
                "end": round(window_end, 1),
                "visual_energy": visual_energy,
                "motion_level": motion_level,
                "avg_motion": round(float(avg_motion), 2),
                "avg_brightness": round(float(avg_brightness), 1),
                "brightness_variance": round(float(brightness_variance), 1),
                "edge_density": round(float(avg_edge_density), 1),
                "color_variance": round(float(avg_color_var), 1),
                "scene_change": scene_change,
                "drop_risk": drop_risk,
                "frames_analyzed": len(window_frames),
            }
            analysis_windows.append(window_data)
            window_idx += 1

        cap.release()

        # ── Identify drop zones (consecutive drop_risk windows) ──
        drop_zones = []
        zone_start = None
        for w in analysis_windows:
            if w["drop_risk"]:
                if zone_start is None:
                    zone_start = w["start"]
                zone_end = w["end"]
            else:
                if zone_start is not None:
                    drop_zones.append({
                        "start": zone_start,
                        "end": zone_end,
                        "duration": round(zone_end - zone_start, 1),
                        "severity": "high" if (zone_end - zone_start) > 4 else "medium",
                    })
                    zone_start = None
        # Close trailing zone
        if zone_start is not None:
            drop_zones.append({
                "start": zone_start,
                "end": zone_end,
                "duration": round(zone_end - zone_start, 1),
                "severity": "high" if (zone_end - zone_start) > 4 else "medium",
            })

        # ── Compute overall score (0-100) ────────────────
        if analysis_windows:
            avg_energy = sum(w["visual_energy"] for w in analysis_windows) / len(analysis_windows)
            drop_ratio = sum(1 for w in analysis_windows if w["drop_risk"]) / len(analysis_windows)

            # Energy contribution (scaled 1-10 → 0-60)
            energy_score = ((avg_energy - 1) / 9) * 60

            # Drop penalty (0 drops = full 40 bonus, all drops = 0)
            drop_penalty = (1 - drop_ratio) * 40

            overall_score = round(min(100, max(0, energy_score + drop_penalty)), 1)
        else:
            overall_score = 0

        result = {
            "status": "success",
            "niche": niche,
            "duration_seconds": round(duration, 1),
            "overall_score": overall_score,
            "total_windows": len(analysis_windows),
            "drop_zones_count": len(drop_zones),
            "analysis_windows": analysis_windows,
            "drop_zones": drop_zones,
        }

        logger.info(f"Analysis complete: {len(analysis_windows)} windows, "
                    f"{len(drop_zones)} drop zones, score={overall_score}")

        return jsonify(result)

    except Exception as e:
        logger.error(f"Video analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════
# HEALTH & INFO
# ═══════════════════════════════════════════════════════════

@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "service": "Hook Architect — External Video Analysis API",
        "version": "1.0.0",
        "endpoints": [
            {"path": "/transcribe_and_summarize", "method": "POST",
             "description": "Groq Whisper transcription + Llama niche detection"},
            {"path": "/analyze_video", "method": "POST",
             "description": "2s window video analysis with visual_energy, motion, drop_risk"},
        ],
        "supported_niches": SUPPORTED_NICHES,
        "groq_api_configured": bool(GROQ_API_KEY),
    })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    port = int(os.getenv("EXTERNAL_API_PORT", "5000"))
    logger.info(f"Starting External Video Analysis API on port {port}")
    logger.info(f"Groq API key configured: {'Yes' if GROQ_API_KEY else 'No'}")
    logger.info(f"FFmpeg: {FFMPEG_BIN}")
    app.run(host="0.0.0.0", port=port, debug=True)
