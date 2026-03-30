"""Emotion AI Analyzer \u2014 Face (DeepFace) and Voice (Acoustic) emotion fusion."""
from __future__ import annotations

import os
import cv2
import numpy as np
from pathlib import Path
import logging

# We import deepface locally to handle gracefully if missing or crashing
try:
    from deepface import DeepFace
    HAS_DEEPFACE = True
except ImportError:
    HAS_DEEPFACE = False

from core.config import ANALYSIS_FPS
from models.schemas import AudioSignal

logger = logging.getLogger(__name__)

# Map acoustic features to basic emotional quadrants
# (energy, pitch_var) -> emotion
def infer_vocal_emotion(energy: float, pitch_var: float) -> str:
    """Heuristic mapping of vocal acoustics to emotion."""
    if energy > 60 and pitch_var > 60:
        return "excited"
    elif energy > 50 and pitch_var < 40:
        return "angry"
    elif energy < 30 and pitch_var < 30:
        return "sad/bored"
    elif energy < 40 and pitch_var > 40:
        return "anxious/hesitant"
    return "neutral"


def _analyze_face_emotion(frame_path: str) -> str:
    """Runs DeepFace on a single frame. Returns dominant emotion or 'neutral'."""
    if not HAS_DEEPFACE:
        return "unknown"
    
    try:
        # enforce_detection=False so it doesn't crash if no face is found
        results = DeepFace.analyze(
            img_path=frame_path,
            actions=["emotion"],
            enforce_detection=False,
            silent=True
        )
        if isinstance(results, list) and len(results) > 0:
            return results[0].get("dominant_emotion", "neutral")
        elif isinstance(results, dict):
            return results.get("dominant_emotion", "neutral")
    except Exception as e:
        logger.warning(f"DeepFace analysis failed for {frame_path}: {e}")
    
    return "unknown"


def analyze_emotions(
    frames_dir: str, 
    audio_signals: list[dict], 
    narrative_sentiment: float, 
    duration: float
) -> dict:
    """
    1. Analyzes facial expressions every N frames.
    2. Infers vocal emotion per second from audio signals.
    3. Calculates an overall Emotional Alignment Score against the text sentiment.
    """
    frames_path = Path(frames_dir)
    frame_files = sorted(frames_path.glob("frame_*.jpg"))
    total_seconds = int(duration)
    
    timeline = []
    
    # We'll sample 1 frame per second to speed up DeepFace
    frames_per_second = ANALYSIS_FPS
    
    face_emotions_tally = {}
    vocal_emotions_tally = {}
    
    for t in range(total_seconds):
        # Vocal
        if t < len(audio_signals):
            a_sig = audio_signals[t]
            v_emo = infer_vocal_emotion(a_sig["energy"], a_sig["pitch_variation"])
            if a_sig["silence_flag"]:
                v_emo = "silent"
        else:
            v_emo = "silent"
            
        vocal_emotions_tally[v_emo] = vocal_emotions_tally.get(v_emo, 0) + 1
        
        # Facial
        start_idx = t * frames_per_second
        f_emo = "unknown"
        if start_idx < len(frame_files):
            # Pick the middle frame of this second
            mid_idx = min(start_idx + frames_per_second // 2, len(frame_files) - 1)
            frame_file = str(frame_files[mid_idx])
            f_emo = _analyze_face_emotion(frame_file)
        
        if f_emo != "unknown":
            face_emotions_tally[f_emo] = face_emotions_tally.get(f_emo, 0) + 1
            
        timeline.append({
            "timestamp": float(t),
            "vocal_emotion": v_emo,
            "facial_emotion": f_emo
        })

    # Find dominant emotions
    dom_vocal = max(vocal_emotions_tally, key=vocal_emotions_tally.get) if vocal_emotions_tally else "neutral"
    
    dom_face = "neutral"
    if face_emotions_tally:
        dom_face = max(face_emotions_tally, key=face_emotions_tally.get)

    # Calculate Emotional Alignment Score
    # Does the face/voice match the text sentiment?
    # Text sentiment: -1.0 to 1.0
    
    # Vibe mapping
    positive_emotions = {"happy", "surprise", "excited"}
    negative_emotions = {"angry", "sad", "disgust", "fear", "sad/bored", "anxious/hesitant"}
    
    alignment_score = 50.0 # base neutral
    
    if narrative_sentiment > 0.2:
        # text is positive
        if dom_face in positive_emotions or dom_vocal in positive_emotions:
            alignment_score = 90.0
        elif dom_face in negative_emotions or dom_vocal in negative_emotions:
            alignment_score = 30.0 # mismatch
    elif narrative_sentiment < -0.2:
        # text is negative
        if dom_face in negative_emotions or dom_vocal in negative_emotions:
            alignment_score = 90.0
        elif dom_face in positive_emotions or dom_vocal in positive_emotions:
            alignment_score = 30.0 # mismatch
    else:
        # text is neutral
        if dom_face in {"neutral", "unknown"} and dom_vocal in {"neutral", "silent"}:
            alignment_score = 80.0
        else:
            alignment_score = 60.0

    harmony_state = "harmonious" if alignment_score > 60 else "dissonant"
    visual_meaning = (
        f"The video's visual output reflects a '{dom_face}' state, while the acoustic vocal tone projects as '{dom_vocal}'. "
        f"When overlaid against the semantic transcript sentiment, this visual/audio blend creates a {harmony_state} atmosphere "
        f"for the viewer, achieving an emotional synchronization score of {alignment_score} / 100."
    )

    return {
        "dominant_facial_emotion": dom_face,
        "dominant_vocal_emotion": dom_vocal,
        "alignment_score": round(alignment_score, 1),
        "emotion_timeline": timeline,
        "visual_meaning": visual_meaning
    }
