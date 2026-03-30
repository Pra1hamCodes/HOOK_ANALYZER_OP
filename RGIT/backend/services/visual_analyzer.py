"""Visual Activity Analyzer — OpenCV optical flow, scene cuts, face detection + YOLOv8 object detection."""
from __future__ import annotations

import cv2
import numpy as np
from pathlib import Path
import logging

from core.config import ANALYSIS_FPS

logger = logging.getLogger("hook_architect.visual_analyzer")

# ── Lazy-load YOLOv8 model (singleton) ─────────────────────
_yolo_model = None

def _get_yolo_model():
    """Lazy-load YOLOv8 nano model once."""
    global _yolo_model
    if _yolo_model is None:
        try:
            from ultralytics import YOLO
            _yolo_model = YOLO("yolov8n.pt")
            logger.info("[VISUAL] YOLOv8n model loaded successfully")
        except Exception as e:
            logger.warning(f"[VISUAL] YOLOv8 unavailable: {e}")
            _yolo_model = False  # Mark as failed so we don't retry
    return _yolo_model if _yolo_model is not False else None


def _run_yolo_on_frame(model, frame) -> list[dict]:
    """Run YOLOv8 inference on a single frame. Returns list of {class, confidence}."""
    try:
        results = model(frame, verbose=False, conf=0.3)
        detections = []
        if results and len(results) > 0:
            for box in results[0].boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                cls_name = model.names.get(cls_id, f"class_{cls_id}")
                detections.append({"class": cls_name, "confidence": round(conf, 3)})
        return detections
    except Exception as e:
        logger.debug(f"[VISUAL] YOLO inference failed on frame: {e}")
        return []


def analyze_visual(frames_dir: str, duration: float) -> list[dict]:
    """
    Analyze extracted frames for motion, scene cuts, face presence, and object detection.

    Returns a list of per-second VisualSignal-compatible dicts.
    Now includes detected_objects and object_richness_score via YOLOv8.
    """
    frames_path = Path(frames_dir)
    frame_files = sorted(frames_path.glob("frame_*.jpg"))

    if not frame_files:
        return []

    total_seconds = int(duration)
    frames_per_second = ANALYSIS_FPS

    # Load Haar cascade for face detection (fast, no GPU needed)
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )

    # Lazy-load YOLOv8 model
    yolo_model = _get_yolo_model()

    signals: list[dict] = []
    
    prev_gray = None
    prev_hist = None

    for t in range(total_seconds):
        start_idx = t * frames_per_second
        end_idx = min(start_idx + frames_per_second, len(frame_files))

        if start_idx >= len(frame_files):
            # No frames for this second — fill with zeros
            signals.append({
                "timestamp": float(t),
                "motion_score": 0.0,
                "scene_cut": False,
                "face_present": False,
                "visual_score": 0.0,
                "detected_objects": [],
                "object_richness_score": 0.0,
            })
            continue

        chunk_frames = frame_files[start_idx:end_idx]
        motion_scores = []
        scene_cut_detected = False
        face_detected = False
        all_detections = []  # Accumulate YOLO detections for this second

        for frame_idx, frame_file in enumerate(chunk_frames):
            frame = cv2.imread(str(frame_file))
            if frame is None:
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            small = cv2.resize(gray, (320, 240))  # downscale for speed

            # ── Optical Flow (motion) ────────────────────
            if prev_gray is not None:
                flow = cv2.calcOpticalFlowFarneback(
                    prev_gray, small,
                    None,
                    pyr_scale=0.5,
                    levels=3,
                    winsize=15,
                    iterations=3,
                    poly_n=5,
                    poly_sigma=1.2,
                    flags=0,
                )
                magnitude, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
                avg_motion = float(np.mean(magnitude))
                motion_scores.append(avg_motion)

            # ── Scene Cut Detection (histogram diff) ─────
            hist = cv2.calcHist([small], [0], None, [64], [0, 256])
            hist = cv2.normalize(hist, hist).flatten()
            if prev_hist is not None:
                correlation = cv2.compareHist(hist, prev_hist, cv2.HISTCMP_CORREL)
                if correlation < 0.4:  # big visual change = scene cut
                    scene_cut_detected = True

            # ── Face Detection ───────────────────────────
            faces = face_cascade.detectMultiScale(
                small, scaleFactor=1.1, minNeighbors=4, minSize=(30, 30)
            )
            if len(faces) > 0:
                face_detected = True

            # ── YOLOv8 Object Detection (every 5th frame for performance) ──
            global_frame_idx = start_idx + frame_idx
            if yolo_model and global_frame_idx % 5 == 0:
                detections = _run_yolo_on_frame(yolo_model, frame)
                all_detections.extend(detections)

            prev_gray = small
            prev_hist = hist

        # ── Compute scores ───────────────────────────────
        if motion_scores:
            avg_motion = float(np.mean(motion_scores))
            # Normalize: typical motion range 0-10 pixels → 0-100
            motion_normalized = min(100.0, (avg_motion / 8.0) * 100)
        else:
            motion_normalized = 0.0

        # Composite visual score
        visual_score = (
            0.45 * motion_normalized
            + 0.20 * (100.0 if scene_cut_detected else 0.0)
            + 0.35 * (100.0 if face_detected else 20.0)  # face is a strong anchor
        )

        # ── Deduplicate and compute object richness ──────
        # Keep highest confidence per class
        class_best: dict[str, float] = {}
        for det in all_detections:
            cls = det["class"]
            conf = det["confidence"]
            if cls not in class_best or conf > class_best[cls]:
                class_best[cls] = conf

        detected_objects = [
            {"class": cls, "confidence": round(conf, 3)}
            for cls, conf in sorted(class_best.items(), key=lambda x: -x[1])
        ]

        # Object richness: unique classes / 5 * 100, capped at 100
        unique_count = len(class_best)
        object_richness_score = min(100.0, (unique_count / 5.0) * 100.0)

        signals.append({
            "timestamp": float(t),
            "motion_score": round(motion_normalized, 1),
            "scene_cut": scene_cut_detected,
            "face_present": face_detected,
            "visual_score": round(visual_score, 1),
            "detected_objects": detected_objects,
            "object_richness_score": round(object_richness_score, 1),
        })

    return signals
