"""Hook Architect — FastAPI Application (Standalone mode — no Redis/Celery required).

Phase 1 Complete: All features including Reference Induction, Evolution Ledger,
Audio-Sync Index, Script Doctor, Dynamic Virality.
"""
from __future__ import annotations

import uuid
import json
import asyncio
import threading
import shutil
import time
import subprocess
import logging
from pathlib import Path
from typing import Any
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from core.config import CORS_ORIGINS, UPLOAD_DIR, MAX_VIDEO_DURATION
from core.database import (
    init_db,
    create_profile,
    get_profile,
    get_profile_by_username,
    list_profiles,
    delete_profile,
    update_profile_weights,
    extract_weights_from_profile,
    get_video_history,
    get_weight_history,
    get_ledger_history,
    save_reference_video,
    update_reference_baseline,
    get_reference_baseline,
    get_reference_videos,
    delete_reference_data,
    create_shared_report,
    get_shared_report,
)
from core.persona_presets import get_preset, list_available_presets, DEFAULT_WEIGHTS
from services.video_processor import get_video_info, extract_audio, extract_frames, _ffmpeg_bin
from services.audio_analyzer import analyze_audio
from services.visual_analyzer import analyze_visual
from services.transcript_analyzer import analyze_transcript
from services.emotion_analyzer import analyze_emotions
from services.virality_analyzer import analyze_virality
from services.semantic_summarizer import generate_semantic_summary, generate_narrative_blueprint
from services.fusion_engine import fuse_signals, compute_overall_score, generate_summary, compute_confidence
from services.adaptive_engine import record_and_adapt
from services.drop_fixer import identify_drop_zones, generate_fix_suggestions
from services.external_api import call_transcribe, call_analyze_video
from services.emotion_arc import compute_emotion_arc
from services.hook_scorer import compute_hook_score
from services.retention_curve import predict_retention_curve
from services.llm_coach import generate_zone_insights, extract_goal_keywords, chat_with_report
from services.report_generator import generate_report_html, generate_report_text
from services.ml_engine import (
    DropZonePredictor, NicheClassifier, EarlyScorePredictor,
    UserWeightLearner, train_all_models,
)
from services.multimodal_coach import (
    critique_hook_frames, diagnose_red_zone, extract_transcript_segment,
)

# Path to frontend
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("hook_architect")

# ── In-memory job storage (replaces Redis for standalone mode) ──
job_store: dict[str, dict[str, Any]] = {}
result_store: dict[str, dict[str, Any]] = {}
ws_subscribers: dict[str, list[asyncio.Queue]] = {}
job_timestamps: dict[str, float] = {}

MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB
JOB_TTL = 3600  # 1 hour

async def memory_cleanup_task():
    """Background task to remove old jobs from memory."""
    while True:
        try:
            now = time.time()
            expired_jobs = [j for j, t in job_timestamps.items() if (now - t) > JOB_TTL]
            for j in expired_jobs:
                res = result_store.pop(j, None)
                if res and "video_meta" in res:
                    fpath = UPLOAD_DIR / res["video_meta"]["filename"]
                    if fpath.exists():
                        fpath.unlink(missing_ok=True)
                    opath = UPLOAD_DIR / f"edited_{j}.mp4"
                    if opath.exists():
                        opath.unlink(missing_ok=True)
                job_store.pop(j, None)
                job_timestamps.pop(j, None)
                if j in ws_subscribers:
                    del ws_subscribers[j]
        except Exception:
            pass
        await asyncio.sleep(600)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: init database and cleanup task
    init_db()
    task = asyncio.create_task(memory_cleanup_task())

    # ── ML: train all models on existing cached data ──────
    try:
        train_all_models()
    except Exception as ml_startup_err:
        logger.warning(f"[ML] train_all_models() at startup failed: {ml_startup_err}")

    # ── Ollama / LLaVA health check ───────────────────────
    try:
        import httpx as _httpx
        import os as _os
        r = _httpx.get("http://localhost:11434/api/tags", timeout=3)
        if "llava" not in r.text:
            logger.warning("[MULTIMODAL] LLaVA model not found. Run: ollama pull llava:7b")
            _os.environ["MULTIMODAL_LLM_ENABLED"] = "false"
        else:
            logger.info("[MULTIMODAL] Ollama + LLaVA ready.")
    except Exception:
        logger.warning("[MULTIMODAL] Ollama not running — multimodal LLM disabled.")
        import os as _os
        _os.environ["MULTIMODAL_LLM_ENABLED"] = "false"

    yield
    task.cancel()

app = FastAPI(
    title="Hook Architect",
    description="Real-time short-form video analysis engine with personalized scoring",
    version="3.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════════
# PYDANTIC REQUEST MODELS
# ═══════════════════════════════════════════════════════════

class CreateProfileRequest(BaseModel):
    username: str
    niche: str = "vlog"

class UpdateWeightsRequest(BaseModel):
    audio_weight: float | None = None
    visual_weight: float | None = None
    transcript_weight: float | None = None
    song_weight: float | None = None
    temporal_weight: float | None = None
    engagement_weight: float | None = None
    green_threshold: float | None = None
    yellow_threshold: float | None = None
    slow_pacing_reward: float | None = None
    high_energy_reward: float | None = None

class GoalProcessRequest(BaseModel):
    goal_text: str

class YouTubeDownloadRequest(BaseModel):
    url: str

class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []
    job_id: str = ""

class CompareRequest(BaseModel):
    job_id_a: str
    job_id_b: str


# ═══════════════════════════════════════════════════════════
# PROGRESS BROADCASTING
# ═══════════════════════════════════════════════════════════

def update_progress(job_id: str, status: str, progress: float, message: str = ""):
    """Update job status in memory and notify WebSocket subscribers."""
    payload = {
        "job_id": job_id,
        "status": status,
        "progress": progress,
        "message": message,
    }
    job_timestamps[job_id] = time.time()
    job_store[job_id] = payload

    if job_id in ws_subscribers:
        for queue in ws_subscribers[job_id]:
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                pass


# ═══════════════════════════════════════════════════════════
# ANALYSIS PIPELINE (runs in background thread)
# ═══════════════════════════════════════════════════════════

def run_analysis_pipeline(job_id: str, filename: str, user_id: str | None = None, goal_text: str = "", platform: str = "generic"):
    """Full video analysis pipeline — runs in a background thread.
    
    If user_id is provided, uses their persona weights for scoring
    and records the result for adaptive feedback.
    If goal_text is provided, evaluates video against goal keywords.
    platform: one of 'tiktok', 'reels', 'youtube_shorts', 'generic'
    """
    video_path = UPLOAD_DIR / filename

    # Resolve user weights
    user_weights = None
    niche = None
    profile = None
    reference_baseline = None
    if user_id:
        profile = get_profile(user_id)
        if profile:
            user_weights = extract_weights_from_profile(profile)
            niche = profile["niche"]
            logger.info(f"[PIPELINE] Persona-aware scoring: niche={niche}, weights={user_weights}")
            # Feature 4: Load reference baseline
            reference_baseline = get_reference_baseline(user_id)
            if reference_baseline:
                logger.info(f"[PIPELINE] Reference baseline loaded: {reference_baseline.get('video_count', 0)} reference videos")

    try:
        # Step 1: Video info
        update_progress(job_id, "extracting", 5, "Reading video metadata...")
        info = get_video_info(video_path)
        duration = info["duration"]

        if duration <= 0:
            raise ValueError(f"Invalid video duration: {duration}s")

        # Step 2: Extract audio
        update_progress(job_id, "extracting", 10, "Extracting audio track...")
        audio_path = extract_audio(video_path, job_id)

        # Step 3: Extract frames
        update_progress(job_id, "extracting", 20, "Extracting video frames...")
        frames_dir = extract_frames(video_path, job_id)

        # Step 4: Audio analysis
        update_progress(job_id, "analyzing_audio", 30, "Analyzing vocal energy & pitch...")
        audio_signals = analyze_audio(str(audio_path), duration)
        update_progress(job_id, "analyzing_audio", 50,
                       f"Audio analysis complete — {len(audio_signals)} seconds analyzed.")

        # ── ML: Early score estimate (audio-only) ────────
        early_score_estimates = []
        try:
            early_pred_audio = EarlyScorePredictor().predict_early(audio_signals[:10], [])
            if early_pred_audio is not None:
                early_score_estimates.append({"stage": "audio", "value": round(early_pred_audio, 1)})
                update_progress(job_id, "analyzing_audio", 50,
                                f"Audio done — early score estimate: {early_pred_audio:.0f}/100")
        except Exception as esp_err:
            logger.warning(f"[ML] EarlyScorePredictor (audio stage) failed: {esp_err}")

        # Step 5: Visual analysis
        update_progress(job_id, "analyzing_visual", 55, "Analyzing motion & scene cuts...")
        visual_signals = analyze_visual(str(frames_dir), duration)
        update_progress(job_id, "analyzing_visual", 75,
                       f"Visual analysis complete — {len(visual_signals)} seconds analyzed.")

        # ── ML: Early score estimate (audio + visual) ─────
        try:
            early_pred_av = EarlyScorePredictor().predict_early(audio_signals[:10], visual_signals[:10])
            if early_pred_av is not None:
                early_score_estimates.append({"stage": "audio+visual", "value": round(early_pred_av, 1)})
                update_progress(job_id, "analyzing_visual", 75,
                                f"Visual done — updated score estimate: {early_pred_av:.0f}/100")
        except Exception as esp_err2:
            logger.warning(f"[ML] EarlyScorePredictor (visual stage) failed: {esp_err2}")

        # Step 5.5: Transcript Intelligence
        update_progress(job_id, "analyzing_transcript", 76, "Running NLP transcript analysis...")
        transcript_data = analyze_transcript(str(audio_path))
        update_progress(job_id, "analyzing_transcript", 77, "Transcript analysis complete.")

        # Step 5.8: Emotion & Pattern Matching
        update_progress(job_id, "analyzing_emotion", 78, "Running Emotion AI (Face/Voice)...")
        sentiment = transcript_data.get("sentiment_polarity", 0.0) if transcript_data else 0.0
        emotion_data = analyze_emotions(str(frames_dir), audio_signals, sentiment, duration)
        update_progress(job_id, "analyzing_emotion", 79, "Emotion tracking complete.")

        # Step 5.85: ML Niche Override (before external API & persona load)
        ml_niche_detected = None
        try:
            nl_result = NicheClassifier().predict_niche(audio_signals, visual_signals, transcript_data)
            if nl_result and nl_result.get("confidence", 0) >= 0.55:
                old_niche = niche or "(none)"
                niche = nl_result["niche"]
                ml_niche_detected = nl_result
                logger.info(
                    f"[ML] Niche override: {niche} (was {old_niche}, "
                    f"confidence: {nl_result['confidence']:.0%})"
                )
                # Re-resolve weights for new ML niche if user has no manual override
                if profile and not user_weights:
                    from core.persona_presets import get_preset
                    user_weights = get_preset(niche)
        except Exception as nc_err:
            logger.warning(f"[ML] NicheClassifier failed: {nc_err}")

        # Step 5.85b: External API Analysis (parallel enrichment)
        update_progress(job_id, "external_api", 79, "Calling external video analysis API...")
        external_video_data = None
        external_transcript_data = None
        external_windows = None
        try:
            external_video_data = call_analyze_video(str(video_path), niche or "general")
            if external_video_data:
                external_windows = external_video_data.get("analysis_windows", [])
                logger.info(f"[PIPELINE] External API: {len(external_windows)} windows, "
                           f"score={external_video_data.get('overall_score')}")
            else:
                logger.info("[PIPELINE] External API: not available, using local-only")
        except Exception as ext_err:
            logger.warning(f"[PIPELINE] External API call failed: {ext_err}")

        try:
            external_transcript_data = call_transcribe(str(audio_path))
            if external_transcript_data:
                logger.info(f"[PIPELINE] External transcript: niche={external_transcript_data.get('niche')}")
        except Exception as ext_t_err:
            logger.warning(f"[PIPELINE] External transcription failed: {ext_t_err}")


        # Step 5.9: Virality & Trend Matching (Enhanced — Features 1 & 6)
        update_progress(job_id, "analyzing_virality", 80, "Cross-referencing Trend Database & Audio-Sync Index...")
        dom_emo = emotion_data.get("dominant_facial_emotion", "neutral") if emotion_data else "neutral"
        if dom_emo == "neutral" and emotion_data:
            dom_emo = emotion_data.get("dominant_vocal_emotion", "neutral")
        if dom_emo == "silent":
            dom_emo = "neutral"
            
        subj = transcript_data.get("subjectivity", 0) if transcript_data else 0
        text_str = transcript_data.get("transcript", "").lower() if transcript_data else ""
        
        # Determine video_nature from transcript keywords
        medical_words = ["patient", "doctor", "alzheimer", "medical", "hospital", "disease", "treatment", "diagnosis", "symptoms", "health", "clinical", "therapy", "brain", "cells"]
        educational_words = ["learn", "tutorial", "explain", "how to", "step by step", "lesson", "guide", "understand"]
        motivation_words = ["grind", "hustle", "success", "mindset", "sigma", "discipline", "focus", "goal"]
        
        if text_str.strip():
            if any(w in text_str for w in medical_words):
                video_nature = "medical"
            elif any(w in text_str for w in motivation_words):
                video_nature = "motivation"
            elif any(w in text_str for w in educational_words) or subj < 0.3:
                video_nature = "educational"
            elif subj < 0.4:
                video_nature = "documentary"
            else:
                video_nature = "hype"
        else:
            avg_energy = sum(a["energy"] for a in audio_signals) / max(len(audio_signals), 1)
            avg_pacing = sum(a["pacing"] for a in audio_signals) / max(len(audio_signals), 1)
            if avg_energy > 55 or avg_pacing > 50:
                video_nature = "hype"
            elif avg_energy > 35:
                video_nature = "motivation"
            else:
                video_nature = "cinematic"
        
        logger.info(f"[PIPELINE] dom_emo='{dom_emo}', video_nature='{video_nature}', subj={subj}, has_transcript={'yes' if text_str.strip() else 'NO'}, transcript_preview='{text_str[:60]}'")
            
        virality_data = analyze_virality(audio_signals, dom_emo, video_nature)
        
        # Step 5.10: Dual-Track Semantic Summarization (Feature 2 enhanced + Feature 4 check)
        update_progress(job_id, "analyzing_semantics", 82, "Performing Vibe Check & Reference Consistency...")
        semantic_data = generate_semantic_summary(
            transcript_data, visual_signals, duration,
            reference_baseline=reference_baseline
        )

        # Step 6: Fusion (persona-aware scoring)
        persona_label = f"Scoring as {niche} creator..." if niche else "Computing attention scores..."
        update_progress(job_id, "fusing", 85, persona_label)
        alignment_val = emotion_data["alignment_score"] if emotion_data else 50.0
        t_score = transcript_data.get("transcription_score", 0.0) if transcript_data else 0.0
        s_score = virality_data.get("sound_score", 0.0) if virality_data else 0.0

        # ── ML: Drop Zone prediction ──────────────────────
        ml_zones_active = False
        ml_predicted_zones = None
        try:
            ml_predicted_zones = DropZonePredictor().predict(audio_signals, visual_signals, duration)
            if ml_predicted_zones is not None:
                ml_zones_active = True
                logger.info(f"[ML] DropZonePredictor: {len(ml_predicted_zones)} zone predictions active")
        except Exception as dzp_err:
            logger.warning(f"[ML] DropZonePredictor failed: {dzp_err}")

        timeline, zones = fuse_signals(
            audio_signals,
            visual_signals,
            transcript_score=t_score,
            song_score=s_score,
            emotional_alignment=alignment_val,
            user_weights=user_weights,
            ml_predicted_zones=ml_predicted_zones,
        )
        overall_score = compute_overall_score(timeline)
        summary = generate_summary(overall_score, zones, duration, timeline=timeline, niche=niche)

        # Load Industry Baselines
        baselines_path = Path(__file__).resolve().parent / "data" / "reference_baselines.json"
        try:
            with open(baselines_path, "r", encoding="utf-8") as bf:
                baselines = json.load(bf)
        except:
            baselines = {}

        # ── Phase 3 Features ─────────────────────────────

        # Step 6.1: Emotion Arc Mapping
        update_progress(job_id, "emotion_arc", 88, "Mapping emotional journey...")
        try:
            emotion_arc_data = compute_emotion_arc(
                emotion_data=emotion_data,
                audio_signals=audio_signals,
                visual_signals=visual_signals,
                duration=duration,
                external_windows=external_windows,
            )
            logger.info(f"[PIPELINE] Emotion Arc: shape={emotion_arc_data.get('arc_shape')}, "
                       f"avg_intensity={emotion_arc_data.get('avg_intensity')}")
        except Exception as arc_err:
            logger.error(f"[PIPELINE] Emotion Arc failed: {arc_err}")
            emotion_arc_data = None

        # Step 6.2: Hook Strength Scorer
        update_progress(job_id, "hook_score", 90, "Scoring your opening hook...")
        try:
            hook_score_data = compute_hook_score(
                audio_signals=audio_signals,
                visual_signals=visual_signals,
                transcript_data=transcript_data,
                emotion_data=emotion_data,
                external_transcript=external_transcript_data,
                external_windows=external_windows,
            )
            logger.info(f"[PIPELINE] Hook Score: {hook_score_data.get('hook_score')}/100 "
                       f"({hook_score_data.get('grade')})")
        except Exception as hook_err:
            logger.error(f"[PIPELINE] Hook Scorer failed: {hook_err}")
            hook_score_data = None

        # Step 6.3: Retention Curve Predictor
        update_progress(job_id, "retention_curve", 92, f"Predicting viewer retention curve ({platform})...")
        try:
            retention_data = predict_retention_curve(
                timeline=timeline,
                hook_score_data=hook_score_data,
                external_windows=external_windows,
                duration=duration,
                platform=platform,
            )
            logger.info(f"[PIPELINE] Retention Curve ({platform}): avg={retention_data.get('predicted_avg_retention')}%, "
                       f"watch-through={retention_data.get('predicted_watch_through_rate')}%")
        except Exception as ret_err:
            logger.error(f"[PIPELINE] Retention Curve failed: {ret_err}")
            retention_data = None

        # Step 6.4: Multimodal Visual Coach (LLaVA via Ollama)
        import os as _os_mm
        multimodal_hook_critique = None
        multimodal_red_zone_diagnoses = []
        multimodal_llm_active = False
        if _os_mm.getenv("MULTIMODAL_LLM_ENABLED", "false").lower() == "true":
            update_progress(job_id, "multimodal", 93, "Analyzing frames with Visual AI (LLaVA)...")
            try:
                frames_dir_str = str(Path("processed") / "frames" / job_id)
                red_zones = [z for z in zones if z.get("zone") == "red"]
                hook_sc = hook_score_data.get("hook_score", 50) if hook_score_data else 50
                hook_gr = hook_score_data.get("grade", "C") if hook_score_data else "C"
                transcript_first3s = (transcript_data.get("transcript", "") if transcript_data else "")[:200]

                mm_tasks_coros = [critique_hook_frames(frames_dir_str, hook_sc, hook_gr, transcript_first3s)]
                for rz in red_zones[:3]:
                    seg_text = extract_transcript_segment(
                        transcript_data.get("transcript", "") if transcript_data else "",
                        rz["start"], rz["end"], duration,
                    )
                    mm_tasks_coros.append(
                        diagnose_red_zone(int(rz["start"]), int(rz["end"]), frames_dir_str,
                                          rz.get("flags", []), seg_text)
                    )

                mm_loop = asyncio.new_event_loop()
                try:
                    mm_results = mm_loop.run_until_complete(
                        asyncio.wait_for(asyncio.gather(*mm_tasks_coros, return_exceptions=True), timeout=20.0)
                    )
                finally:
                    mm_loop.close()

                if mm_results and not isinstance(mm_results[0], Exception):
                    multimodal_hook_critique = mm_results[0]
                multimodal_red_zone_diagnoses = [
                    r for r in mm_results[1:] if r and not isinstance(r, Exception)
                ]
                multimodal_llm_active = (multimodal_hook_critique is not None
                                         or bool(multimodal_red_zone_diagnoses))
                logger.info(f"[MULTIMODAL] hook_critique={'yes' if multimodal_hook_critique else 'no'}, "
                            f"red_zone_diagnoses={len(multimodal_red_zone_diagnoses)}")
            except Exception as mm_err:
                logger.warning(f"[MULTIMODAL] Step 6.4 failed: {mm_err}")

        # Step 6.5: Goal alignment evaluation (if goal_text provided)
        goal_keywords = []
        goal_alignment_score = None
        goal_evaluation_summary = ""
        if goal_text and goal_text.strip():
            update_progress(job_id, "evaluating_goal", 94, "Evaluating video against your goals...")
            try:
                goal_loop = asyncio.new_event_loop()
                goal_data = goal_loop.run_until_complete(extract_goal_keywords(goal_text))
                goal_loop.close()
                goal_keywords = goal_data.get("keywords", [])
                # Simple alignment: check how many keywords appear in transcript
                if transcript_data and transcript_data.get("transcript"):
                    transcript_lower = transcript_data["transcript"].lower()
                    matched = sum(1 for k in goal_keywords if k.lower() in transcript_lower)
                    goal_alignment_score = round((matched / max(len(goal_keywords), 1)) * 100)
                else:
                    goal_alignment_score = 0
                goal_evaluation_summary = goal_data.get("summary", "")
                logger.info(f"[PIPELINE] Goal alignment: {goal_alignment_score}/100, keywords={goal_keywords}")
            except Exception as goal_err:
                logger.error(f"[PIPELINE] Goal evaluation failed: {goal_err}")

        # Step 6.9: Compute analysis confidence
        try:
            analysis_confidence, confidence_reasons = compute_confidence(
                audio_signals, visual_signals, transcript_data, duration
            )
            logger.info(f"[PIPELINE] Confidence: {analysis_confidence}/100, reasons={confidence_reasons}")
        except Exception as conf_err:
            logger.error(f"[PIPELINE] Confidence computation failed: {conf_err}")
            analysis_confidence = 50.0
            confidence_reasons = ["Confidence could not be computed"]

        # Step 6.6: LLM Coach generated Insights
        update_progress(job_id, "llm_coach", 95, "Generating AI coaching insights...")
        try:
            llm_loop = asyncio.new_event_loop()
            llm_insights = llm_loop.run_until_complete(
                generate_zone_insights(
                    zones=zones,
                    timeline=timeline,
                    transcript_data=transcript_data,
                    emotion_data=emotion_data,
                    virality_data=virality_data,
                    hook_score_data=hook_score_data,
                    retention_data=retention_data,
                    niche=niche or "general",
                )
            )
            llm_loop.close()
            logger.info(f"[PIPELINE] Generated {len(llm_insights)} LLM insights")
        except Exception as llm_err:
            logger.error(f"[PIPELINE] LLM Coach failed: {llm_err}")
            llm_insights = []

        # Step 7: Store results
        result = {
            "job_id": job_id,
            "video_meta": {
                "duration": duration,
                "resolution": info["resolution"],
                "fps": info["fps"],
                "filename": filename,
            },
            "timeline": timeline,
            "zones": zones,
            "overall_score": overall_score,
            "summary": summary,
            "transcript_data": transcript_data,
            "emotion_data": emotion_data,
            "virality_data": virality_data,
            "semantic_data": semantic_data,
            "reference_baselines": baselines,
            "reference_baseline": reference_baseline,
            "audio_signals": audio_signals,
            "visual_signals": visual_signals,
            "emotion_arc": emotion_arc_data,
            "hook_score": hook_score_data,
            "retention_curve": retention_data,
            "external_analysis": external_video_data,
            "goal_text": goal_text,
            "goal_keywords": goal_keywords,
            "goal_alignment_score": goal_alignment_score,
            "goal_evaluation_summary": goal_evaluation_summary,
            "analysis_confidence": analysis_confidence,
            "confidence_reasons": confidence_reasons,
            "platform": platform,
            "persona": {
                "user_id": user_id,
                "niche": niche,
                "weights_used": user_weights or DEFAULT_WEIGHTS,
            },
            # ── ML fields ────────────────────────────────────
            "ml_niche_detected": ml_niche_detected,
            "early_score_estimates": early_score_estimates if early_score_estimates else None,
            "ml_zones_active": ml_zones_active,
            # ── Multimodal LLM fields ─────────────────────────
            "multimodal_hook_critique": multimodal_hook_critique,
            "multimodal_red_zone_diagnoses": multimodal_red_zone_diagnoses if multimodal_red_zone_diagnoses else None,
            "multimodal_llm_active": multimodal_llm_active,
            "llm_insights": llm_insights,
        }

        # Step 7.5: Reference vs Main Comparison (only if reference baseline exists)
        comparison_data = None
        if reference_baseline and reference_baseline.get("video_count", 0) > 0:
            try:
                main_avg_energy = sum(a["energy"] for a in audio_signals) / max(len(audio_signals), 1)
                main_avg_pacing = sum(a["pacing"] for a in audio_signals) / max(len(audio_signals), 1)
                main_avg_motion = sum(v["motion_score"] for v in visual_signals) / max(len(visual_signals), 1)
                main_emotion_alignment = alignment_val
                main_sentiment = sentiment
                main_bpm = virality_data.get("audio_profile", {}).get("estimated_bpm", 0) if virality_data else 0
                ref = reference_baseline

                def delta(main_val, ref_val):
                    return round(main_val - ref_val, 1)

                def pct_delta(main_val, ref_val):
                    if ref_val == 0:
                        return 0
                    return round(((main_val - ref_val) / ref_val) * 100, 1)

                metrics = [
                    {"name": "Overall Score", "icon": "🎯", "main": round(overall_score, 1), "ref": round(ref.get("avg_overall_score", 0), 1), "unit": "/100"},
                    {"name": "Energy", "icon": "⚡", "main": round(main_avg_energy, 1), "ref": round(ref.get("avg_energy", 0), 1), "unit": "/100"},
                    {"name": "Pacing", "icon": "🏃", "main": round(main_avg_pacing, 1), "ref": round(ref.get("avg_pacing", 0), 1), "unit": "/100"},
                    {"name": "Motion", "icon": "🎬", "main": round(main_avg_motion, 1), "ref": round(ref.get("avg_motion", 0), 1), "unit": "/100"},
                    {"name": "Emotion Sync", "icon": "💜", "main": round(main_emotion_alignment, 1), "ref": round(ref.get("avg_emotion_alignment", 0), 1), "unit": "/100"},
                    {"name": "BPM", "icon": "🎵", "main": round(main_bpm), "ref": round(ref.get("avg_bpm", 0)), "unit": " bpm"},
                    {"name": "Sentiment", "icon": "😊", "main": round(main_sentiment, 2), "ref": round(ref.get("avg_sentiment", 0), 2), "unit": ""},
                ]
                for m in metrics:
                    m["delta"] = delta(m["main"], m["ref"])
                    m["pct_delta"] = pct_delta(m["main"], m["ref"])

                # Overall comparison verdict
                score_diff = overall_score - ref.get("avg_overall_score", 0)
                if score_diff >= 10:
                    verdict = "🔥 Significantly outperforming your reference standard"
                elif score_diff >= 0:
                    verdict = "✅ Meeting or exceeding your reference baseline"
                elif score_diff >= -10:
                    verdict = "⚠️ Slightly below your reference standard"
                else:
                    verdict = "🔴 Significantly below your reference — review weak signals"

                comparison_data = {
                    "metrics": metrics,
                    "verdict": verdict,
                    "ref_video_count": ref.get("video_count", 0),
                    "ref_narrative_style": ref.get("dominant_narrative_style", "mixed"),
                    "ref_visual_style": ref.get("dominant_visual_style", "mixed"),
                }
                logger.info(f"[PIPELINE] Comparison: score_diff={score_diff:.1f}, verdict={verdict}")
            except Exception as cmp_err:
                logger.error(f"[PIPELINE] Comparison computation failed: {cmp_err}")

        result["comparison"] = comparison_data

        # Step 8: Adaptive Feedback Loop (if user profile exists)
        adaptation_result = None
        if user_id and profile:
            update_progress(job_id, "adapting", 95, "Updating your personalized content standard...")
            try:
                adaptation_result = record_and_adapt(
                    user_id=user_id,
                    filename=filename,
                    duration=duration,
                    overall_score=overall_score,
                    audio_signals=audio_signals,
                    visual_signals=visual_signals,
                    transcript_score=t_score,
                    emotion_alignment=alignment_val,
                    dominant_emotion=dom_emo,
                    video_nature=video_nature,
                    timeline=timeline,
                    semantic_data=semantic_data,
                    user_weights=user_weights,
                )
                logger.info(f"[PIPELINE] Adaptive feedback: {adaptation_result}")
            except Exception as adapt_err:
                logger.error(f"[PIPELINE] Adaptive feedback failed: {adapt_err}")
                adaptation_result = {"recorded": False, "adapted": False, "weight_changes": {}}

            # ── ML: User weight learner incremental training ──
            try:
                zone_dist = {"green": 0, "yellow": 0, "red": 0}
                for tp in timeline:
                    z = tp.get("zone", "red")
                    zone_dist[z] = zone_dist.get(z, 0) + 1
                total_sec = max(len(timeline), 1)
                audio_avg = sum(a.get("audio_score", 0) for a in audio_signals) / max(len(audio_signals), 1)
                visual_avg = sum(v.get("visual_score", 0) for v in visual_signals) / max(len(visual_signals), 1)
                video_count = profile.get("video_count", 1)
                UserWeightLearner().train_incremental(
                    user_id=user_id,
                    audio_avg=audio_avg,
                    visual_avg=visual_avg,
                    transcript_score=t_score,
                    emotion_alignment=alignment_val,
                    green_pct=zone_dist["green"] / total_sec,
                    yellow_pct=zone_dist["yellow"] / total_sec,
                    red_pct=zone_dist["red"] / total_sec,
                    video_count=video_count,
                    overall_score=overall_score,
                )
                logger.info(f"[ML] UserWeightLearner updated for user {user_id}")
            except Exception as uwl_err:
                logger.warning(f"[ML] UserWeightLearner.train_incremental failed: {uwl_err}")

        # ── ML: Retrain all models with new data point ─────
        try:
            train_all_models()
        except Exception as tam_err:
            logger.warning(f"[ML] train_all_models() post-analysis failed: {tam_err}")

        result["adaptation"] = adaptation_result

        result_store[job_id] = result
        update_progress(job_id, "complete", 100, "Analysis complete!")

    except Exception as e:
        update_progress(job_id, "failed", 0, str(e))
    finally:
        try:
            if 'audio_path' in locals() and audio_path and audio_path.exists():
                audio_path.unlink()
            if 'frames_dir' in locals() and frames_dir and frames_dir.exists():
                shutil.rmtree(frames_dir)
        except Exception:
            pass


def run_reference_pipeline(job_id: str, filename: str, user_id: str):
    """Runs the same analysis pipeline on a reference video and stores the baseline."""
    video_path = UPLOAD_DIR / filename

    try:
        update_progress(job_id, "extracting", 5, "Processing reference video...")
        info = get_video_info(video_path)
        duration = info["duration"]

        if duration <= 0:
            raise ValueError(f"Invalid video duration: {duration}s")

        update_progress(job_id, "extracting", 10, "Extracting reference audio...")
        audio_path = extract_audio(video_path, job_id)

        update_progress(job_id, "extracting", 20, "Extracting reference frames...")
        frames_dir = extract_frames(video_path, job_id)

        update_progress(job_id, "analyzing_audio", 30, "Analyzing reference audio...")
        audio_signals = analyze_audio(str(audio_path), duration)

        update_progress(job_id, "analyzing_visual", 50, "Analyzing reference visuals...")
        visual_signals = analyze_visual(str(frames_dir), duration)

        update_progress(job_id, "analyzing_transcript", 65, "Analyzing reference transcript...")
        transcript_data = analyze_transcript(str(audio_path))

        update_progress(job_id, "analyzing_emotion", 75, "Analyzing reference emotions...")
        sentiment = transcript_data.get("sentiment_polarity", 0.0) if transcript_data else 0.0
        emotion_data = analyze_emotions(str(frames_dir), audio_signals, sentiment, duration)

        update_progress(job_id, "analyzing_virality", 80, "Analyzing reference virality...")
        dom_emo = emotion_data.get("dominant_facial_emotion", "neutral") if emotion_data else "neutral"
        if dom_emo in ("neutral", "silent") and emotion_data:
            dom_emo = emotion_data.get("dominant_vocal_emotion", "neutral")
        if dom_emo == "silent":
            dom_emo = "neutral"

        subj = transcript_data.get("subjectivity", 0) if transcript_data else 0
        text_str = transcript_data.get("transcript", "").lower() if transcript_data else ""
        
        medical_words = ["patient", "doctor", "alzheimer", "medical", "hospital"]
        educational_words = ["learn", "tutorial", "explain", "how to"]
        motivation_words = ["grind", "hustle", "success", "mindset", "sigma"]
        
        if text_str.strip():
            if any(w in text_str for w in medical_words):
                video_nature = "medical"
            elif any(w in text_str for w in motivation_words):
                video_nature = "motivation"
            elif any(w in text_str for w in educational_words) or subj < 0.3:
                video_nature = "educational"
            elif subj < 0.4:
                video_nature = "documentary"
            else:
                video_nature = "hype"
        else:
            avg_en = sum(a["energy"] for a in audio_signals) / max(len(audio_signals), 1)
            avg_pa = sum(a["pacing"] for a in audio_signals) / max(len(audio_signals), 1)
            if avg_en > 55 or avg_pa > 50:
                video_nature = "hype"
            elif avg_en > 35:
                video_nature = "motivation"
            else:
                video_nature = "cinematic"

        virality_data = analyze_virality(audio_signals, dom_emo, video_nature)
        semantic_data = generate_semantic_summary(transcript_data, visual_signals, duration)

        # Compute scores
        alignment_val = emotion_data["alignment_score"] if emotion_data else 50.0
        t_score = transcript_data.get("transcription_score", 0.0) if transcript_data else 0.0
        s_score = virality_data.get("sound_score", 0.0) if virality_data else 0.0
        
        timeline, zones = fuse_signals(audio_signals, visual_signals,
                                        transcript_score=t_score, song_score=s_score,
                                        emotional_alignment=alignment_val)
        overall_score = compute_overall_score(timeline)

        # Calculate averages
        avg_energy = sum(a["energy"] for a in audio_signals) / max(len(audio_signals), 1)
        avg_pacing = sum(a["pacing"] for a in audio_signals) / max(len(audio_signals), 1)
        avg_motion = sum(v["motion_score"] for v in visual_signals) / max(len(visual_signals), 1)
        est_bpm = virality_data.get("audio_profile", {}).get("estimated_bpm", 80)

        update_progress(job_id, "storing", 90, "Storing reference baseline...")

        # Save individual reference video
        ref_data = {
            "filename": filename,
            "avg_bpm": est_bpm,
            "avg_energy": avg_energy,
            "avg_pacing": avg_pacing,
            "avg_motion": avg_motion,
            "avg_sentiment": sentiment,
            "avg_emotion_alignment": alignment_val,
            "dominant_emotion": dom_emo,
            "video_nature": video_nature,
            "narrative_style": semantic_data.get("narrative_style", "mixed"),
            "visual_style": semantic_data.get("visual_style", "mixed"),
            "narrative_blueprint": "",
            "overall_score": overall_score,
        }
        save_reference_video(user_id, ref_data)

        # Recalculate aggregated baseline from all reference videos
        all_refs = get_reference_videos(user_id)
        
        agg = {
            "video_count": len(all_refs),
            "avg_bpm": sum(r["avg_bpm"] for r in all_refs) / len(all_refs),
            "avg_energy": sum(r["avg_energy"] for r in all_refs) / len(all_refs),
            "avg_pacing": sum(r["avg_pacing"] for r in all_refs) / len(all_refs),
            "avg_motion": sum(r["avg_motion"] for r in all_refs) / len(all_refs),
            "avg_sentiment": sum(r["avg_sentiment"] for r in all_refs) / len(all_refs),
            "avg_emotion_alignment": sum(r["avg_emotion_alignment"] for r in all_refs) / len(all_refs),
            "avg_overall_score": sum(r["overall_score"] for r in all_refs) / len(all_refs),
        }

        # Determine dominant styles
        narrative_styles = [r["narrative_style"] for r in all_refs]
        visual_styles = [r["visual_style"] for r in all_refs]
        agg["dominant_narrative_style"] = max(set(narrative_styles), key=narrative_styles.count)
        agg["dominant_visual_style"] = max(set(visual_styles), key=visual_styles.count)
        
        # Generate narrative blueprint from all references
        blueprint = generate_narrative_blueprint(
            [{"video_nature": r["video_nature"], "dominant_emotion": r["dominant_emotion"]} for r in all_refs],
            agg
        )
        agg["narrative_blueprint"] = blueprint

        update_reference_baseline(user_id, agg)

        result_store[job_id] = {
            "job_id": job_id,
            "status": "complete",
            "reference_data": ref_data,
            "aggregated_baseline": agg,
            "narrative_blueprint": blueprint,
        }
        update_progress(job_id, "complete", 100, "Reference processed!")

    except Exception as e:
        update_progress(job_id, "failed", 0, str(e))
    finally:
        try:
            if 'audio_path' in locals() and audio_path and audio_path.exists():
                audio_path.unlink()
            if 'frames_dir' in locals() and frames_dir and frames_dir.exists():
                shutil.rmtree(frames_dir)
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════
# PROFILE API ROUTES
# ═══════════════════════════════════════════════════════════

@app.get("/api/presets")
async def get_presets():
    """List all available persona presets for the onboarding UI."""
    return list_available_presets()


@app.post("/api/profiles")
async def create_user_profile(req: CreateProfileRequest):
    """Create a new user profile with niche-specific weights."""
    username = req.username.strip()
    if not username:
        raise HTTPException(400, "Username cannot be empty.")
    if len(username) > 50:
        raise HTTPException(400, "Username too long (max 50 characters).")
    
    # Check uniqueness
    existing = get_profile_by_username(username)
    if existing:
        raise HTTPException(409, f"Username '{username}' already exists.")
    
    # Get preset weights for the niche
    weights = get_preset(req.niche)
    
    try:
        profile = create_profile(username, req.niche, weights)
        return profile
    except Exception as e:
        raise HTTPException(500, f"Failed to create profile: {e}")


@app.get("/api/profiles")
async def get_all_profiles():
    """List all user profiles."""
    return list_profiles()


@app.get("/api/profiles/{profile_id}")
async def get_user_profile(profile_id: str):
    """Get a single user profile with current weights."""
    profile = get_profile(profile_id)
    if not profile:
        raise HTTPException(404, "Profile not found.")
    return profile


@app.get("/api/profiles/{profile_id}/history")
async def get_profile_history(profile_id: str):
    """Get video history and weight evolution for a profile."""
    profile = get_profile(profile_id)
    if not profile:
        raise HTTPException(404, "Profile not found.")
    
    videos = get_video_history(profile_id, limit=50)
    weight_history = get_weight_history(profile_id, limit=20)
    
    return {
        "profile": profile,
        "videos": videos,
        "weight_history": weight_history,
    }


# ═══════════════════════════════════════════════════════════
# EVOLUTION LEDGER (Feature 3)
# ═══════════════════════════════════════════════════════════

@app.get("/api/profiles/{profile_id}/ledger")
async def get_profile_ledger(profile_id: str):
    """Get enriched history for the Evolution Ledger sidebar."""
    profile = get_profile(profile_id)
    if not profile:
        raise HTTPException(404, "Profile not found.")
    
    ledger = get_ledger_history(profile_id, limit=50)
    
    return {
        "profile": profile,
        "ledger": ledger,
        "total_videos": profile.get("video_count", 0),
    }


# ═══════════════════════════════════════════════════════════
# REFERENCE INDUCTION (Feature 4)
# ═══════════════════════════════════════════════════════════

@app.post("/api/profiles/{profile_id}/references")
async def upload_reference_video(
    profile_id: str,
    file: UploadFile = File(...),
):
    """Upload a reference video. Runs it through the full pipeline to build baseline."""
    profile = get_profile(profile_id)
    if not profile:
        raise HTTPException(404, "Profile not found.")

    if not file.filename:
        raise HTTPException(400, "No filename provided.")
    
    allowed = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
    ext = Path(file.filename).suffix.lower()
    if ext not in allowed:
        raise HTTPException(400, f"Unsupported format '{ext}'.")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(413, "File too large.")
    if len(content) == 0:
        raise HTTPException(400, "Empty file.")

    job_id = f"ref_{uuid.uuid4()}"
    safe_name = f"{job_id}{ext}"
    file_path = UPLOAD_DIR / safe_name

    try:
        with open(file_path, "wb") as f:
            f.write(content)
        
        info = get_video_info(file_path)
        if info["duration"] <= 0:
            file_path.unlink(missing_ok=True)
            raise HTTPException(400, "Invalid video.")
        if info["duration"] > MAX_VIDEO_DURATION:
            file_path.unlink(missing_ok=True)
            raise HTTPException(400, f"Video too long ({info['duration']:.0f}s).")
    except HTTPException:
        raise
    except Exception as e:
        file_path.unlink(missing_ok=True)
        raise HTTPException(400, f"Could not read video: {e}")

    update_progress(job_id, "pending", 0, "Processing reference video...")
    thread = threading.Thread(
        target=run_reference_pipeline,
        args=(job_id, safe_name, profile_id),
        daemon=True
    )
    thread.start()

    return {
        "job_id": job_id,
        "message": "Reference video uploaded. Processing started.",
        "ws_url": f"/ws/jobs/{job_id}",
    }


@app.get("/api/profiles/{profile_id}/references")
async def get_profile_references(profile_id: str):
    """Get stored reference baseline and individual reference videos."""
    profile = get_profile(profile_id)
    if not profile:
        raise HTTPException(404, "Profile not found.")
    
    baseline = get_reference_baseline(profile_id)
    refs = get_reference_videos(profile_id)
    
    return {
        "baseline": baseline,
        "reference_videos": refs,
        "has_baseline": baseline is not None,
    }


@app.delete("/api/profiles/{profile_id}/references")
async def clear_references(profile_id: str):
    """Clear all reference videos and baseline."""
    profile = get_profile(profile_id)
    if not profile:
        raise HTTPException(404, "Profile not found.")
    
    delete_reference_data(profile_id)
    return {"cleared": True}


@app.put("/api/profiles/{profile_id}/weights")
async def set_profile_weights(profile_id: str, req: UpdateWeightsRequest):
    """Manually override weights for a profile."""
    profile = get_profile(profile_id)
    if not profile:
        raise HTTPException(404, "Profile not found.")
    
    weights = {k: v for k, v in req.model_dump().items() if v is not None}
    if not weights:
        raise HTTPException(400, "No weights provided.")
    
    updated = update_profile_weights(profile_id, weights, trigger="manual")
    return updated


@app.delete("/api/profiles/{profile_id}")
async def delete_user_profile(profile_id: str):
    """Delete a user profile and all associated data."""
    deleted = delete_profile(profile_id)
    if not deleted:
        raise HTTPException(404, "Profile not found.")
    return {"deleted": True}


# ═══════════════════════════════════════════════════════════
# VIDEO UPLOAD & ANALYSIS
# ═══════════════════════════════════════════════════════════

@app.post("/api/jobs/{job_id}/edit")
async def auto_edit_video(job_id: str):
    """Auto-edit the video by cropping out red zones using FFmpeg."""
    if job_id not in result_store:
        raise HTTPException(404, "Job results not found or expired.")
    
    result = result_store[job_id]
    original_video = UPLOAD_DIR / result["video_meta"]["filename"]
    if not original_video.exists():
        raise HTTPException(404, "Original video was cleaned up and is no longer available for editing.")

    output_path = UPLOAD_DIR / f"edited_{job_id}.mp4"
    if output_path.exists():
        return FileResponse(str(output_path), media_type="video/mp4", filename=f"HookArchitect_Edited.mp4")

    timeline = result.get("timeline", [])
    if not timeline:
        raise HTTPException(400, "Corrupted timeline data.")
        
    keep_segments = []
    start_t = None
    for t in timeline:
        if t["zone"] != "red":
            if start_t is None:
                start_t = t["t"]
        else:
            if start_t is not None:
                keep_segments.append((start_t, t["t"]))
                start_t = None
    if start_t is not None:
        keep_segments.append((start_t, timeline[-1]["t"] + 1.0))

    if not keep_segments:
        raise HTTPException(400, "The entire video is classified as a Risk Zone.")

    if len(keep_segments) == 1 and keep_segments[0][0] == 0 and keep_segments[0][1] >= result["video_meta"]["duration"]:
        return FileResponse(str(original_video), media_type="video/mp4", filename="HookArchitect_Original.mp4")

    has_audio = result["video_meta"].get("has_audio", True)

    filters = []
    concat_labels = ""
    for i, (start, end) in enumerate(keep_segments):
        filters.append(f"[0:v]trim=start={start}:end={end},setpts=PTS-STARTPTS[v{i}];")
        if has_audio:
            filters.append(f"[0:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS[a{i}];")
            concat_labels += f"[v{i}][a{i}]"
        else:
            concat_labels += f"[v{i}]"
    
    if has_audio:
        filters.append(f"{concat_labels}concat=n={len(keep_segments)}:v=1:a=1[outv][outa]")
        maps = ["-map", "[outv]", "-map", "[outa]"]
    else:
        filters.append(f"{concat_labels}concat=n={len(keep_segments)}:v=1:a=0[outv]")
        maps = ["-map", "[outv]"]

    filter_str = "".join(filters)
    cmd = [
        _ffmpeg_bin(), "-y", 
        "-i", str(original_video),
        "-filter_complex", filter_str,
        *maps,
        "-c:v", "libx264", 
    ]
    if has_audio:
        cmd.extend(["-c:a", "aac"])
    cmd.append(str(output_path))
    
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        return FileResponse(str(output_path), media_type="video/mp4", filename=f"HookArchitect_Edited.mp4")
    except subprocess.CalledProcessError as e:
        raise HTTPException(500, f"FFmpeg editing failed: {e.stderr.decode()}")


@app.post("/api/upload")
async def upload_video(
    file: UploadFile = File(...),
    user_id: str = Form(default=""),
    goal_text: str = Form(default=""),
    platform: str = Form(default="generic"),
):
    """Upload a short-form video for analysis. Optionally attach to a user profile."""
    if not file.filename:
        raise HTTPException(400, "No filename provided.")

    allowed = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
    ext = Path(file.filename).suffix.lower()
    if ext not in allowed:
        raise HTTPException(400, f"Unsupported format '{ext}'. Use: {', '.join(sorted(allowed))}")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(413, f"File too large ({len(content) // (1024*1024)} MB). Max 100 MB.")
    if len(content) == 0:
        raise HTTPException(400, "Empty file uploaded.")

    job_id = str(uuid.uuid4())
    safe_name = f"{job_id}{ext}"
    file_path = UPLOAD_DIR / safe_name

    try:
        with open(file_path, "wb") as f:
            f.write(content)

        info = get_video_info(file_path)
        if info["duration"] <= 0:
            file_path.unlink(missing_ok=True)
            raise HTTPException(400, "Could not determine video duration. File may be corrupt.")
        if info["duration"] > MAX_VIDEO_DURATION:
            file_path.unlink(missing_ok=True)
            raise HTTPException(400, f"Video too long ({info['duration']:.0f}s). Max {MAX_VIDEO_DURATION}s.")
    except HTTPException:
        raise
    except Exception as e:
        file_path.unlink(missing_ok=True)
        raise HTTPException(400, f"Could not read video: {e}")

    # Validate user_id if provided
    resolved_user_id = user_id.strip() if user_id else None
    if resolved_user_id:
        profile = get_profile(resolved_user_id)
        if not profile:
            resolved_user_id = None  # Fall back to generic scoring

    # Resolve platform
    valid_platforms = {"tiktok", "reels", "youtube_shorts", "generic"}
    resolved_platform = platform.strip().lower() if platform else "generic"
    if resolved_platform not in valid_platforms:
        resolved_platform = "generic"

    # Start analysis in background thread
    resolved_goal = goal_text.strip() if goal_text else ""
    update_progress(job_id, "pending", 0, "Queued for analysis...")
    thread = threading.Thread(
        target=run_analysis_pipeline, 
        args=(job_id, safe_name, resolved_user_id, resolved_goal, resolved_platform), 
        daemon=True
    )
    thread.start()

    return {
        "job_id": job_id,
        "message": "Video uploaded. Analysis started.",
        "ws_url": f"/ws/jobs/{job_id}",
        "user_id": resolved_user_id,
    }


@app.get("/api/jobs/{job_id}/status")
async def get_job_status(job_id: str):
    """Poll job progress."""
    if job_id in job_store:
        return job_store[job_id]
    return {
        "job_id": job_id,
        "status": "pending",
        "progress": 0,
        "message": "Waiting in queue...",
    }


@app.get("/api/results/{job_id}")
async def get_results(job_id: str):
    """Fetch complete analysis results."""
    if job_id in result_store:
        return result_store[job_id]

    if job_id in job_store:
        status = job_store[job_id]
        if status.get("status") == "failed":
            raise HTTPException(400, f"Analysis failed: {status.get('message')}")
        raise HTTPException(202, "Analysis still in progress.")

    raise HTTPException(404, "Job not found.")


@app.post("/api/results/{job_id}/share")
async def share_results(job_id: str):
    """Create a 72-hour shareable snapshot URL for a completed analysis."""
    if job_id not in result_store:
        raise HTTPException(404, "Results not found.")

    result = result_store[job_id]
    share_id = str(uuid.uuid4())
    user_id = result.get("persona", {}).get("user_id", "") or ""
    snapshot_json = json.dumps(result)
    create_shared_report(
        share_id=share_id,
        job_id=job_id,
        user_id=user_id,
        result_json=snapshot_json,
        ttl_hours=72,
    )
    return {"share_url": f"/share/{share_id}", "share_id": share_id}


@app.get("/api/share/{share_id}")
async def get_shared_result_data(share_id: str):
    """Return shared snapshot data if unexpired."""
    row = get_shared_report(share_id)
    if not row:
        raise HTTPException(404, "Shared report not found or expired.")

    now = time.time()
    expires_in_hours = max(0, int((row["expires_at"] - now) // 3600))
    return {
        "share_id": share_id,
        "job_id": row["job_id"],
        "created_at": row["created_at"],
        "expires_at": row["expires_at"],
        "expires_in_hours": expires_in_hours,
        "result": row.get("result_snapshot", {}),
    }


@app.get("/share/{share_id}")
async def serve_shared_page(share_id: str):
    """Serve frontend page for a shared report URL (read-only render handled in frontend)."""
    row = get_shared_report(share_id)
    if not row:
        raise HTTPException(404, "Shared report not found or expired.")
    return FileResponse(str(FRONTEND_DIR / "index.html"))


@app.post("/api/compare")
async def compare_results(req: CompareRequest):
    """Compare two completed analyses side-by-side."""
    if req.job_id_a not in result_store:
        raise HTTPException(404, f"Results not found for job_id_a: {req.job_id_a}")
    if req.job_id_b not in result_store:
        raise HTTPException(404, f"Results not found for job_id_b: {req.job_id_b}")

    a = result_store[req.job_id_a]
    b = result_store[req.job_id_b]

    a_timeline = a.get("timeline", [])
    b_timeline = b.get("timeline", [])
    max_len = max(len(a_timeline), len(b_timeline))
    attention_delta = []
    for i in range(max_len):
        a_val = a_timeline[i].get("attention", 0.0) if i < len(a_timeline) else 0.0
        b_val = b_timeline[i].get("attention", 0.0) if i < len(b_timeline) else 0.0
        attention_delta.append(round(b_val - a_val, 2))

    def zone_distribution(result_obj: dict) -> dict:
        tl = result_obj.get("timeline", [])
        if not tl:
            return {"green_pct": 0.0, "yellow_pct": 0.0, "red_pct": 0.0}
        total = len(tl)
        green = sum(1 for p in tl if p.get("zone") == "green")
        yellow = sum(1 for p in tl if p.get("zone") == "yellow")
        red = sum(1 for p in tl if p.get("zone") == "red")
        return {
            "green_pct": round((green / total) * 100, 2),
            "yellow_pct": round((yellow / total) * 100, 2),
            "red_pct": round((red / total) * 100, 2),
        }

    curve_a = (a.get("retention_curve") or {}).get("curve_points", [])
    curve_b = (b.get("retention_curve") or {}).get("curve_points", [])
    max_curve = max(len(curve_a), len(curve_b))
    retention_overlay = []
    for i in range(max_curve):
        a_pt = curve_a[i] if i < len(curve_a) else {"t": i, "retention_pct": 0.0}
        b_pt = curve_b[i] if i < len(curve_b) else {"t": i, "retention_pct": 0.0}
        retention_overlay.append({
            "t": a_pt.get("t", b_pt.get("t", i)),
            "a": a_pt.get("retention_pct", 0.0),
            "b": b_pt.get("retention_pct", 0.0),
        })

    overall_delta = round(b.get("overall_score", 0.0) - a.get("overall_score", 0.0), 2)
    hook_a = (a.get("hook_score") or {}).get("hook_score", 0.0)
    hook_b = (b.get("hook_score") or {}).get("hook_score", 0.0)
    hook_delta = round(hook_b - hook_a, 2)

    if overall_delta > 0:
        winner = "b"
    elif overall_delta < 0:
        winner = "a"
    else:
        winner = "tie"

    return {
        "job_id_a": req.job_id_a,
        "job_id_b": req.job_id_b,
        "diff": {
            "overall_score_delta": overall_delta,
            "hook_score_delta": hook_delta,
            "attention_delta": attention_delta,
            "zone_distribution": {
                "a": zone_distribution(a),
                "b": zone_distribution(b),
            },
            "retention_curve_overlay": retention_overlay,
            "winner": winner,
        },
    }

@app.post("/api/chat")
async def chat_interaction(req: ChatRequest):
    """Interact with the LLM Coach regarding a specific video analysis."""
    if req.job_id not in result_store:
        raise HTTPException(404, "Results not found. The job might have expired, or ID is invalid.")
        
    result = result_store[req.job_id]
    report_text = generate_report_text(result)
    
    reply = await chat_with_report(report_text, req.message, history=req.history)
    return {"reply": reply}

@app.get("/api/results/{job_id}/timeline")
async def get_timeline(job_id: str):
    """Fetch just the timeline data."""
    if job_id in result_store:
        result = result_store[job_id]
        return {
            "job_id": job_id,
            "timeline": result.get("timeline", []),
            "zones": result.get("zones", []),
            "overall_score": result.get("overall_score", 0),
        }
    raise HTTPException(404, "Results not found.")


# ═══════════════════════════════════════════════════════════
# SCRIPT DOCTOR — DROP FIXER (Feature 7)
# ═══════════════════════════════════════════════════════════

@app.post("/api/jobs/{job_id}/fix-drops")
async def fix_drops(job_id: str):
    """Identify drop zones and generate AI-powered fix suggestions."""
    if job_id not in result_store:
        raise HTTPException(404, "Job results not found or expired.")
    
    result = result_store[job_id]
    timeline = result.get("timeline", [])
    zones = result.get("zones", [])
    transcript_data = result.get("transcript_data")
    audio_profile = result.get("virality_data", {}).get("audio_profile")
    reference_baseline = result.get("reference_baseline")
    
    # Determine video nature from stored data
    video_nature = "general"
    if result.get("adaptation") and result["adaptation"].get("niche_qualification"):
        video_nature = result["adaptation"]["niche_qualification"]
    
    # Identify drop zones
    drop_zones = identify_drop_zones(timeline, zones, transcript_data)
    
    if not drop_zones:
        return {
            "job_id": job_id,
            "suggestions": [],
            "message": "No critical drop zones detected — your video maintains good engagement!",
        }
    
    # Generate AI fix suggestions (with multimodal visual diagnoses if available)
    multimodal_diagnoses = result.get("multimodal_red_zone_diagnoses") or []
    suggestions = await generate_fix_suggestions(
        drop_zones, transcript_data, audio_profile, reference_baseline, video_nature,
        timeline=timeline,
        multimodal_diagnoses=multimodal_diagnoses,
    )
    
    return {
        "job_id": job_id,
        "suggestions": suggestions,
        "drop_zones_count": len(drop_zones),
        "message": f"Found {len(drop_zones)} critical drop zone(s). AI suggestions generated.",
    }



# ═══════════════════════════════════════════════════════════
# LLM-POWERED ZONE INSIGHTS (Phase 2)
# ═══════════════════════════════════════════════════════════

@app.post("/api/jobs/{job_id}/ai-insights")
async def get_ai_insights(job_id: str):
    """Generate AI coaching insights for each zone using Gemini."""
    if job_id not in result_store:
        raise HTTPException(404, "Job results not found or expired.")
    
    result = result_store[job_id]
    zones = result.get("zones", [])
    timeline = result.get("timeline", [])
    niche = result.get("persona", {}).get("niche", "general")
    
    insights = await generate_zone_insights(
        zones=zones,
        timeline=timeline,
        transcript_data=result.get("transcript_data"),
        emotion_data=result.get("emotion_data"),
        virality_data=result.get("virality_data"),
        hook_score_data=result.get("hook_score"),
        retention_data=result.get("retention_curve"),
        niche=niche,
    )
    
    return {
        "job_id": job_id,
        "insights": insights,
        "total_zones": len(zones),
    }


# ═══════════════════════════════════════════════════════════
# ONE-CLICK HOOK APPLY — FFmpeg Preview (Phase 4)
# ═══════════════════════════════════════════════════════════

class HookApplyRequest(BaseModel):
    start: float
    end: float
    overlay_text: str = ""
    speed: float = 1.0

@app.post("/api/jobs/{job_id}/apply-hook")
async def apply_hook(job_id: str, req: HookApplyRequest):
    """Generate an FFmpeg preview clip with text overlay and speed adjustment."""
    if job_id not in result_store:
        raise HTTPException(404, "Job results not found or expired.")
    
    result = result_store[job_id]
    original_video = UPLOAD_DIR / result["video_meta"]["filename"]
    if not original_video.exists():
        raise HTTPException(404, "Original video no longer available.")
    
    preview_path = UPLOAD_DIR / f"preview_{job_id}_{int(req.start)}_{int(req.end)}.mp4"
    
    # Build FFmpeg command with text overlay + speed
    speed = max(0.5, min(2.0, req.speed))
    duration = req.end - req.start
    
    # Build filter complex
    filters = []
    filters.append(f"setpts={1/speed}*PTS")
    
    if req.overlay_text:
        # Escape special characters for FFmpeg drawtext
        safe_text = req.overlay_text.replace("'", "").replace('"', '').replace(':', '\\:')[:120]
        filters.append(
            f"drawtext=text='{safe_text}'"
            f":fontsize=28:fontcolor=white:borderw=3:bordercolor=black"
            f":x=(w-text_w)/2:y=h-th-40"
            f":enable='between(t,0,{duration/speed})'"
        )
    
    vf = ",".join(filters)
    
    cmd = [
        _ffmpeg_bin(), "-y",
        "-ss", str(req.start),
        "-t", str(duration),
        "-i", str(original_video),
        "-vf", vf,
        "-af", f"atempo={speed}" if speed != 1.0 else "anull",
        "-c:v", "libx264",
        "-c:a", "aac",
        "-preset", "ultrafast",
        str(preview_path),
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=30)
        return FileResponse(
            str(preview_path),
            media_type="video/mp4",
            filename=f"HookArchitect_Preview_{int(req.start)}s.mp4"
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(500, "Preview generation timed out.")
    except subprocess.CalledProcessError as e:
        raise HTTPException(500, f"FFmpeg preview failed: {e.stderr.decode()[:200]}")


# ═══════════════════════════════════════════════════════════
# GOAL KEYWORD PROCESSING
# ═══════════════════════════════════════════════════════════

@app.post("/api/goals/process")
async def process_goal(req: GoalProcessRequest):
    """Extract evaluation keywords from the user's goal description."""
    if not req.goal_text or not req.goal_text.strip():
        raise HTTPException(400, "Goal text cannot be empty.")
    
    result = await extract_goal_keywords(req.goal_text.strip())
    return {
        "goal_text": req.goal_text.strip(),
        **result,
    }


# ═══════════════════════════════════════════════════════════
# YOUTUBE REFERENCE DOWNLOAD
# ═══════════════════════════════════════════════════════════

@app.post("/api/profiles/{profile_id}/references/youtube")
async def upload_reference_from_youtube(profile_id: str, req: YouTubeDownloadRequest):
    """Download a YouTube video and use it as a reference."""
    profile = get_profile(profile_id)
    if not profile:
        raise HTTPException(404, "Profile not found.")
    
    url = req.url.strip()
    if not url:
        raise HTTPException(400, "URL cannot be empty.")
    
    # Basic YouTube URL validation
    if not any(domain in url for domain in ["youtube.com", "youtu.be", "youtube-nocookie.com"]):
        raise HTTPException(400, "Please provide a valid YouTube URL.")
    
    job_id = f"ytref_{uuid.uuid4()}"
    update_progress(job_id, "downloading", 5, "Downloading YouTube video...")
    
    def download_and_process():
        try:
            import yt_dlp
            safe_name = f"{job_id}.mp4"
            output_path = UPLOAD_DIR / safe_name
            
            ydl_opts = {
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4/best',
                'outtmpl': str(output_path),
                'max_filesize': MAX_FILE_SIZE,
                'socket_timeout': 30,
                'quiet': True,
                'no_warnings': True,
                'merge_output_format': 'mp4',
            }
            
            update_progress(job_id, "downloading", 10, "Fetching video from YouTube...")
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(url, download=True)
                
            if not output_path.exists():
                # yt-dlp may have appended extension
                for candidate in UPLOAD_DIR.glob(f"{job_id}.*"):
                    if candidate.suffix in ('.mp4', '.mkv', '.webm'):
                        output_path = candidate
                        safe_name = candidate.name
                        break
            
            if not output_path.exists():
                update_progress(job_id, "failed", 0, "Download failed — video file not found.")
                return
            
            # Check duration
            try:
                info = get_video_info(output_path)
                if info["duration"] <= 0:
                    output_path.unlink(missing_ok=True)
                    update_progress(job_id, "failed", 0, "Invalid video.")
                    return
                if info["duration"] > MAX_VIDEO_DURATION:
                    output_path.unlink(missing_ok=True)
                    update_progress(job_id, "failed", 0, f"Video too long ({info['duration']:.0f}s). Max {MAX_VIDEO_DURATION}s.")
                    return
            except Exception as ve:
                output_path.unlink(missing_ok=True)
                update_progress(job_id, "failed", 0, f"Could not read video: {ve}")
                return
            
            update_progress(job_id, "processing", 15, "YouTube video downloaded. Starting reference analysis...")
            run_reference_pipeline(job_id, safe_name, profile_id)
            
        except Exception as e:
            update_progress(job_id, "failed", 0, f"YouTube download failed: {str(e)[:200]}")
    
    thread = threading.Thread(target=download_and_process, daemon=True)
    thread.start()
    
    return {
        "job_id": job_id,
        "message": "YouTube download started. Processing as reference.",
        "ws_url": f"/ws/jobs/{job_id}",
    }


# ═══════════════════════════════════════════════════════════
# PDF REPORT DOWNLOAD
# ═══════════════════════════════════════════════════════════

@app.get("/api/jobs/{job_id}/report-pdf")
async def download_report_pdf(job_id: str):
    """Generate and download a PDF analysis report."""
    if job_id not in result_store:
        raise HTTPException(404, "Job results not found or expired.")
    
    result = result_store[job_id]
    
    # Generate HTML report
    html_content = generate_report_html(result)
    
    # Convert HTML to PDF
    from io import BytesIO
    try:
        from xhtml2pdf import pisa
        pdf_buffer = BytesIO()
        pisa_status = pisa.CreatePDF(html_content, dest=pdf_buffer)
        
        if pisa_status.err:
            raise HTTPException(500, "PDF generation failed.")
        
        pdf_buffer.seek(0)
        pdf_path = UPLOAD_DIR / f"report_{job_id}.pdf"
        with open(pdf_path, "wb") as f:
            f.write(pdf_buffer.read())
        
        return FileResponse(
            str(pdf_path),
            media_type="application/pdf",
            filename=f"HookArchitect_Report_{job_id[:8]}.pdf",
        )
    except ImportError:
        raise HTTPException(500, "xhtml2pdf not installed. Run: pip install xhtml2pdf")
    except Exception as e:
        raise HTTPException(500, f"PDF generation failed: {e}")


# ═══════════════════════════════════════════════════════════
# INTERACTIVE CHAT ASSISTANT
# ═══════════════════════════════════════════════════════════

@app.post("/api/jobs/{job_id}/chat")
async def chat_about_analysis(job_id: str, req: ChatRequest):
    """Chat with AI about the analysis results."""
    if job_id not in result_store:
        raise HTTPException(404, "Job results not found or expired.")
    
    if not req.message or not req.message.strip():
        raise HTTPException(400, "Message cannot be empty.")
    
    result = result_store[job_id]
    report_text = generate_report_text(result)
    
    response = await chat_with_report(
        report_text=report_text,
        message=req.message.strip(),
        history=req.history,
    )
    
    return {
        "job_id": job_id,
        "response": response,
    }


# ═══════════════════════════════════════════════════════════
# WEBSOCKET (in-memory pub/sub)
# ═══════════════════════════════════════════════════════════

@app.websocket("/ws/jobs/{job_id}")
async def job_progress_ws(websocket: WebSocket, job_id: str):
    """Stream job progress updates to the client."""
    await websocket.accept()

    queue: asyncio.Queue = asyncio.Queue(maxsize=50)
    if job_id not in ws_subscribers:
        ws_subscribers[job_id] = []
    ws_subscribers[job_id].append(queue)

    try:
        while True:
            try:
                data = await asyncio.wait_for(queue.get(), timeout=1.0)
                await websocket.send_json(data)
                if data.get("status") in ("complete", "failed"):
                    break
            except asyncio.TimeoutError:
                if job_id in job_store:
                    status = job_store[job_id]
                    if status.get("status") in ("complete", "failed"):
                        await websocket.send_json(status)
                        break
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        if job_id in ws_subscribers:
            try:
                ws_subscribers[job_id].remove(queue)
            except ValueError:
                pass
            if not ws_subscribers[job_id]:
                del ws_subscribers[job_id]


# ═══════════════════════════════════════════════════════════
# HEALTH & FRONTEND SERVING
# ═══════════════════════════════════════════════════════════

@app.get("/health")
async def health():
    return {"status": "ok"}


# ── New UI Routes ─────────────────────────────────────────

@app.get("/")
async def serve_landing():
    """Serve the new landing page."""
    return FileResponse(str(FRONTEND_DIR / "landing.html"))


@app.get("/login")
async def serve_login():
    """Serve the login page."""
    return FileResponse(str(FRONTEND_DIR / "login.html"))


@app.get("/signup")
async def serve_signup():
    """Serve the signup page."""
    return FileResponse(str(FRONTEND_DIR / "signup.html"))


@app.get("/dashboard")
async def serve_dashboard():
    """Serve the dashboard page."""
    return FileResponse(str(FRONTEND_DIR / "dashboard.html"))


@app.get("/dashboard/analysis/{job_id}")
async def serve_analysis(job_id: str):
    """Serve the analysis results page."""
    return FileResponse(str(FRONTEND_DIR / "analysis.html"))


@app.get("/dashboard/history")
async def serve_history():
    """Serve the dashboard (history view)."""
    return FileResponse(str(FRONTEND_DIR / "dashboard.html"))


@app.get("/dashboard/profile")
async def serve_profile():
    """Serve the dedicated profile page."""
    return FileResponse(str(FRONTEND_DIR / "profile.html"))


# ── Legacy UI (preserved) ────────────────────────────────

@app.get("/old")
async def serve_old_index():
    """Serve the old single-page frontend (preserved for compatibility)."""
    return FileResponse(str(FRONTEND_DIR / "index.html"))


# Static mounts (AFTER all explicit routes)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR / "static")), name="static")
