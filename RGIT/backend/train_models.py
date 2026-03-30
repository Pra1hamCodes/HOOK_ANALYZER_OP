"""
train_models.py — Synthetic dataset generator + ML model trainer for Hook Architect.

Generates realistic video-analysis signal data across 7 niches and trains all 4 ML
sub-models so they activate immediately at server startup.

Usage:
    cd backend
    python train_models.py
"""
from __future__ import annotations

import json
import logging
import pickle
import random
import sys
from pathlib import Path

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("train_models")

# ── Paths (mirror ml_engine.py) ─────────────────────────────
MODELS_DIR = Path(__file__).resolve().parent / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

SEED = 42
random.seed(SEED)
np.random.seed(SEED)

# ═══════════════════════════════════════════════════════════
# NICHE SIGNAL PROFILES
# ═══════════════════════════════════════════════════════════
# Each niche defines (mean, std) for continuous signals, and probability for flags.

NICHE_PROFILES = {
    "action": {
        "energy":          (75, 12),
        "pitch_variation": (65, 12),
        "pacing":          (70, 12),
        "motion_score":    (78, 12),
        "face_prob":       0.30,
        "scene_cut_prob":  0.50,
        "silence_prob":    0.05,
        "words_per_sec":   (1.8, 0.6),
        "overall_bias":    72,
    },
    "educational": {
        "energy":          (47, 10),
        "pitch_variation": (42, 10),
        "pacing":          (42, 10),
        "motion_score":    (28, 10),
        "face_prob":       0.80,
        "scene_cut_prob":  0.15,
        "silence_prob":    0.10,
        "words_per_sec":   (3.0, 0.8),
        "overall_bias":    65,
    },
    "emotional": {
        "energy":          (38, 10),
        "pitch_variation": (55, 12),
        "pacing":          (28, 10),
        "motion_score":    (22, 10),
        "face_prob":       0.75,
        "scene_cut_prob":  0.20,
        "silence_prob":    0.15,
        "words_per_sec":   (2.2, 0.7),
        "overall_bias":    58,
    },
    "vlog": {
        "energy":          (52, 10),
        "pitch_variation": (48, 10),
        "pacing":          (48, 10),
        "motion_score":    (40, 12),
        "face_prob":       0.85,
        "scene_cut_prob":  0.30,
        "silence_prob":    0.08,
        "words_per_sec":   (2.8, 0.7),
        "overall_bias":    63,
    },
    "cinematic": {
        "energy":          (28, 10),
        "pitch_variation": (28, 10),
        "pacing":          (20, 8),
        "motion_score":    (65, 12),
        "face_prob":       0.25,
        "scene_cut_prob":  0.45,
        "silence_prob":    0.20,
        "words_per_sec":   (1.0, 0.5),
        "overall_bias":    60,
    },
    "comedy": {
        "energy":          (70, 12),
        "pitch_variation": (70, 12),
        "pacing":          (65, 12),
        "motion_score":    (45, 12),
        "face_prob":       0.75,
        "scene_cut_prob":  0.40,
        "silence_prob":    0.06,
        "words_per_sec":   (3.2, 0.8),
        "overall_bias":    68,
    },
    "music": {
        "energy":          (65, 12),
        "pitch_variation": (42, 10),
        "pacing":          (60, 12),
        "motion_score":    (50, 12),
        "face_prob":       0.50,
        "scene_cut_prob":  0.35,
        "silence_prob":    0.05,
        "words_per_sec":   (2.0, 0.8),
        "overall_bias":    66,
    },
}

NICHES = list(NICHE_PROFILES.keys())
VIDEOS_PER_NICHE = 35  # 35 * 7 = 245 total videos
VIDEO_DURATION_RANGE = (8, 45)  # seconds


# ═══════════════════════════════════════════════════════════
# SYNTHETIC DATA GENERATORS
# ═══════════════════════════════════════════════════════════

def _clamp(val: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, val))


def _sample(mean: float, std: float) -> float:
    return _clamp(np.random.normal(mean, std))


def generate_per_second_signals(
    niche: str, duration: int
) -> tuple[list[dict], list[dict]]:
    """Generate per-second audio + visual signal dicts for a synthetic video."""
    p = NICHE_PROFILES[niche]
    audio_signals = []
    visual_signals = []

    for t in range(duration):
        # ── Audio ─────────────────────────────────────────
        energy = _sample(*p["energy"])
        pitch  = _sample(*p["pitch_variation"])
        pacing = _sample(*p["pacing"])
        silence = random.random() < p["silence_prob"]

        # Audio score: weighted combo
        audio_score = _clamp(
            0.35 * energy + 0.25 * pitch + 0.25 * pacing
            + (0 if silence else 15)
        )

        audio_signals.append({
            "timestamp": float(t),
            "energy": round(energy, 2),
            "pitch_variation": round(pitch, 2),
            "pacing": round(pacing, 2),
            "silence_flag": silence,
            "audio_score": round(audio_score, 2),
        })

        # ── Visual ────────────────────────────────────────
        motion   = _sample(*p["motion_score"])
        face     = random.random() < p["face_prob"]
        cut      = random.random() < p["scene_cut_prob"]

        visual_score = _clamp(
            0.40 * motion
            + (30 if face else 0)
            + (15 if cut else 0)
        )

        visual_signals.append({
            "timestamp": float(t),
            "motion_score": round(motion, 2),
            "face_present": face,
            "scene_cut": cut,
            "visual_score": round(visual_score, 2),
            "detected_objects": [],
            "object_richness_score": round(_clamp(motion * 0.6 + random.gauss(10, 5)), 2),
        })

    return audio_signals, visual_signals


def compute_zone_label(audio: dict, visual: dict) -> str:
    """Derive zone label from signal quality."""
    a = audio["audio_score"]
    v = visual["visual_score"]
    if a > 60 and v > 55:
        return "green"
    if a < 35 or v < 30:
        return "red"
    return "yellow"


def generate_transcript_data(niche: str, duration: int) -> dict:
    """Generate synthetic transcript metadata."""
    p = NICHE_PROFILES[niche]
    wps_mean, wps_std = p["words_per_sec"]
    wps = max(0.5, np.random.normal(wps_mean, wps_std))
    word_count = int(wps * duration)
    # Subjectivity varies by niche
    if niche in ("educational", "cinematic"):
        subjectivity = round(_clamp(np.random.normal(0.25, 0.10), 0, 1), 2)
    elif niche in ("emotional", "vlog"):
        subjectivity = round(_clamp(np.random.normal(0.55, 0.12), 0, 1), 2)
    else:
        subjectivity = round(_clamp(np.random.normal(0.40, 0.12), 0, 1), 2)

    return {
        "transcript": " ".join(["word"] * word_count),
        "word_count": word_count,
        "sentiment_polarity": round(np.random.normal(0.1, 0.3), 2),
        "subjectivity": subjectivity,
        "transcription_score": round(_clamp(np.random.normal(55, 15)), 2),
    }


def compute_overall_score(audio_signals: list[dict], visual_signals: list[dict], bias: float) -> float:
    """Compute a synthetic overall score from signals + niche bias."""
    n = max(len(audio_signals), 1)
    avg_audio = sum(a["audio_score"] for a in audio_signals) / n
    avg_visual = sum(v["visual_score"] for v in visual_signals) / max(len(visual_signals), 1)
    raw = 0.45 * avg_audio + 0.35 * avg_visual + 0.20 * bias
    noise = np.random.normal(0, 3)
    return round(_clamp(raw + noise), 1)


# ═══════════════════════════════════════════════════════════
# TRAINING LOGIC
# ═══════════════════════════════════════════════════════════

def train_drop_zone_predictor(all_data: list[dict]):
    """Train DropZonePredictor (RandomForest) on per-second features → zone labels."""
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import accuracy_score, classification_report

    ZONE_TO_INT = {"green": 0, "yellow": 1, "red": 2}

    X_rows, y_rows = [], []
    for video in all_data:
        audio_sigs = video["audio_signals"]
        visual_sigs = video["visual_signals"]
        duration = video["duration"]
        n = min(len(audio_sigs), len(visual_sigs))
        for i in range(n):
            a = audio_sigs[i]
            v = visual_sigs[i]
            zone = compute_zone_label(a, v)
            X_rows.append([
                a["energy"], a["pitch_variation"], a["pacing"],
                1 if a["silence_flag"] else 0,
                v["motion_score"],
                1 if v["scene_cut"] else 0,
                1 if v["face_present"] else 0,
                a["audio_score"], v["visual_score"],
                i / max(duration, 1),  # timestamp_normalized
            ])
            y_rows.append(ZONE_TO_INT[zone])

    X = np.array(X_rows, dtype=np.float64)
    y = np.array(y_rows)

    log.info(f"\n{'='*60}")
    log.info("MODEL 1: DropZonePredictor (RandomForest)")
    log.info(f"{'='*60}")
    log.info(f"  Samples: {len(X)}")
    log.info(f"  Class distribution: green={sum(y==0)}, yellow={sum(y==1)}, red={sum(y==2)}")

    clf = RandomForestClassifier(n_estimators=100, random_state=SEED)
    clf.fit(X, y)

    preds = clf.predict(X)
    acc = accuracy_score(y, preds)
    log.info(f"  Training accuracy: {acc:.4f}")
    log.info(f"  Feature importances: {[round(x,3) for x in clf.feature_importances_]}")

    # Save model
    model_path = MODELS_DIR / "drop_predictor.pkl"
    with open(model_path, "wb") as f:
        pickle.dump(clf, f)

    # Save cache for incremental training
    cache_path = MODELS_DIR / "drop_predictor_cache.pkl"
    with open(cache_path, "wb") as f:
        pickle.dump({"X": X, "y": y}, f)

    # Save meta
    meta = {"sample_count": len(all_data)}
    with open(MODELS_DIR / "drop_predictor_meta.json", "w") as f:
        json.dump(meta, f)

    log.info(f"  ✅ Saved: {model_path.name}, cache, meta")
    return clf


def train_niche_classifier(all_data: list[dict]):
    """Train NicheClassifier (SVC) on per-video features → niche labels."""
    from sklearn.svm import SVC
    from sklearn.metrics import accuracy_score, classification_report
    from sklearn.preprocessing import StandardScaler

    X_rows, y_rows = [], []
    for video in all_data:
        audio_sigs = video["audio_signals"]
        visual_sigs = video["visual_signals"]
        transcript = video["transcript_data"]
        n_a = max(len(audio_sigs), 1)
        n_v = max(len(visual_sigs), 1)

        avg_energy  = sum(a["energy"] for a in audio_sigs) / n_a
        avg_pitch   = sum(a["pitch_variation"] for a in audio_sigs) / n_a
        avg_pacing  = sum(a["pacing"] for a in audio_sigs) / n_a
        avg_motion  = sum(v["motion_score"] for v in visual_sigs) / n_v
        avg_face    = sum(1 for v in visual_sigs if v["face_present"]) / n_v
        silence_rat = sum(1 for a in audio_sigs if a["silence_flag"]) / n_a
        avg_cut     = sum(1 for v in visual_sigs if v["scene_cut"]) / n_v
        wps = transcript.get("word_count", 0) / max(len(audio_sigs), 1)

        X_rows.append([
            avg_energy, avg_pitch, avg_pacing, avg_motion,
            avg_face, silence_rat, avg_cut, wps,
        ])
        y_rows.append(video["niche"])

    X = np.array(X_rows, dtype=np.float64)

    # Normalize for SVM
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    log.info(f"\n{'='*60}")
    log.info("MODEL 2: NicheClassifier (SVC)")
    log.info(f"{'='*60}")
    log.info(f"  Samples: {len(X)}")
    from collections import Counter
    dist = Counter(y_rows)
    log.info(f"  Class distribution: {dict(dist)}")

    clf = SVC(kernel="rbf", probability=True, random_state=SEED)
    clf.fit(X_scaled, y_rows)

    preds = clf.predict(X_scaled)
    acc = accuracy_score(y_rows, preds)
    log.info(f"  Training accuracy: {acc:.4f}")

    # Save model — Note: the existing ml_engine does NOT use a scaler,
    # so we need to train on raw features to match the predict() code.
    clf_raw = SVC(kernel="rbf", probability=True, random_state=SEED)
    clf_raw.fit(X, y_rows)
    raw_acc = accuracy_score(y_rows, clf_raw.predict(X))
    log.info(f"  Training accuracy (raw, for deployment): {raw_acc:.4f}")

    model_path = MODELS_DIR / "niche_classifier.pkl"
    with open(model_path, "wb") as f:
        pickle.dump(clf_raw, f)

    # Cache
    cache_path = MODELS_DIR / "niche_classifier_cache.pkl"
    with open(cache_path, "wb") as f:
        pickle.dump({"X": X, "y": y_rows}, f)

    # Meta
    meta = {"sample_count": len(all_data)}
    with open(MODELS_DIR / "niche_classifier_meta.json", "w") as f:
        json.dump(meta, f)

    log.info(f"  ✅ Saved: {model_path.name}, cache, meta")
    return clf_raw


def train_early_score_predictor(all_data: list[dict]):
    """Train EarlyScorePredictor (XGBRegressor) on first-10s → overall score."""
    from xgboost import XGBRegressor
    from sklearn.metrics import r2_score, mean_absolute_error

    X_rows, y_rows = [], []
    for video in all_data:
        audio_first10 = video["audio_signals"][:10]
        visual_first10 = video["visual_signals"][:10]
        overall = video["overall_score"]
        hook_score = video.get("hook_score", 50.0)

        n_a = max(len(audio_first10), 1)
        n_v = max(len(visual_first10), 1)

        avg_energy  = sum(a["energy"] for a in audio_first10) / n_a
        avg_pitch   = sum(a["pitch_variation"] for a in audio_first10) / n_a
        avg_motion  = sum(v["motion_score"] for v in visual_first10) / n_v
        face_ratio  = sum(1 for v in visual_first10 if v["face_present"]) / n_v
        silence_rat = sum(1 for a in audio_first10 if a["silence_flag"]) / n_a
        avg_pacing  = sum(a["pacing"] for a in audio_first10) / n_a

        X_rows.append([
            avg_energy, avg_pitch, avg_motion, face_ratio,
            silence_rat, avg_pacing, hook_score,
        ])
        y_rows.append(overall)

    X = np.array(X_rows, dtype=np.float64)
    y = np.array(y_rows)

    log.info(f"\n{'='*60}")
    log.info("MODEL 3: EarlyScorePredictor (XGBRegressor)")
    log.info(f"{'='*60}")
    log.info(f"  Samples: {len(X)}")
    log.info(f"  Target range: [{y.min():.1f}, {y.max():.1f}], mean={y.mean():.1f}")

    reg = XGBRegressor(
        n_estimators=200, max_depth=4,
        learning_rate=0.05, random_state=SEED,
    )
    reg.fit(X, y)

    preds = reg.predict(X)
    r2 = r2_score(y, preds)
    mae = mean_absolute_error(y, preds)
    log.info(f"  Training R²: {r2:.4f}")
    log.info(f"  Training MAE: {mae:.2f}")

    model_path = MODELS_DIR / "early_score_predictor.pkl"
    with open(model_path, "wb") as f:
        pickle.dump(reg, f)

    cache_path = MODELS_DIR / "early_score_cache.pkl"
    with open(cache_path, "wb") as f:
        pickle.dump({"X": X, "y": y}, f)

    meta = {"sample_count": len(all_data)}
    with open(MODELS_DIR / "early_score_predictor_meta.json", "w") as f:
        json.dump(meta, f)

    log.info(f"  ✅ Saved: {model_path.name}, cache, meta")
    return reg


def train_user_weight_learner(all_data: list[dict]):
    """Train UserWeightLearner (Ridge) for a demo user on aggregated metrics."""
    from sklearn.linear_model import Ridge
    from sklearn.metrics import r2_score

    ZONE_TO_INT = {"green": 0, "yellow": 1, "red": 2}

    X_rows, y_rows = [], []
    for i, video in enumerate(all_data):
        audio_sigs = video["audio_signals"]
        visual_sigs = video["visual_signals"]
        n_a = max(len(audio_sigs), 1)
        n_v = max(len(visual_sigs), 1)

        audio_avg = sum(a["audio_score"] for a in audio_sigs) / n_a
        visual_avg = sum(v["visual_score"] for v in visual_sigs) / n_v
        transcript_score = video["transcript_data"].get("transcription_score", 50)
        emotion_alignment = round(_clamp(np.random.normal(55, 12)), 2)

        # Zone distribution
        zones = {"green": 0, "yellow": 0, "red": 0}
        n = min(len(audio_sigs), len(visual_sigs))
        for j in range(n):
            z = compute_zone_label(audio_sigs[j], visual_sigs[j])
            zones[z] += 1
        total = max(n, 1)

        X_rows.append([
            audio_avg, visual_avg, transcript_score, emotion_alignment,
            zones["green"] / total, zones["yellow"] / total,
            zones["red"] / total, i + 1,  # video_count
        ])
        y_rows.append(video["overall_score"])

    X = np.array(X_rows, dtype=np.float64)
    y = np.array(y_rows)

    log.info(f"\n{'='*60}")
    log.info("MODEL 4: UserWeightLearner (Ridge) — demo_user")
    log.info(f"{'='*60}")
    log.info(f"  Samples: {len(X)}")

    reg = Ridge(alpha=1.0)
    reg.fit(X, y)

    preds = reg.predict(X)
    r2 = r2_score(y, preds)
    log.info(f"  Training R²: {r2:.4f}")
    log.info(f"  Coefficients: {[round(c,4) for c in reg.coef_]}")

    model_path = MODELS_DIR / "user_weights_demo_user.pkl"
    with open(model_path, "wb") as f:
        pickle.dump(reg, f)

    cache_path = MODELS_DIR / "user_weights_demo_user_cache.pkl"
    with open(cache_path, "wb") as f:
        pickle.dump({"X": X, "y": y}, f)

    log.info(f"  ✅ Saved: {model_path.name}, cache")
    return reg


# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════

def main():
    log.info("╔══════════════════════════════════════════════════════╗")
    log.info("║  Hook Architect — ML Model Training Pipeline        ║")
    log.info("╚══════════════════════════════════════════════════════╝")
    log.info(f"\nGenerating synthetic data: {VIDEOS_PER_NICHE} videos × {len(NICHES)} niches "
             f"= {VIDEOS_PER_NICHE * len(NICHES)} total videos")
    log.info(f"Models directory: {MODELS_DIR}\n")

    # ── Step 1: Generate synthetic dataset ────────────────
    all_data = []
    for niche in NICHES:
        p = NICHE_PROFILES[niche]
        for _ in range(VIDEOS_PER_NICHE):
            duration = random.randint(*VIDEO_DURATION_RANGE)
            audio_signals, visual_signals = generate_per_second_signals(niche, duration)
            transcript_data = generate_transcript_data(niche, duration)
            overall = compute_overall_score(audio_signals, visual_signals, p["overall_bias"])

            # Compute a synthetic hook score from first 3 seconds
            if len(audio_signals) >= 3:
                first3_audio_avg = sum(a["audio_score"] for a in audio_signals[:3]) / 3
                first3_visual_avg = sum(v["visual_score"] for v in visual_signals[:3]) / 3
                hook_score = round(_clamp(0.5 * first3_audio_avg + 0.5 * first3_visual_avg + np.random.normal(0, 5)), 1)
            else:
                hook_score = 50.0

            all_data.append({
                "niche": niche,
                "duration": duration,
                "audio_signals": audio_signals,
                "visual_signals": visual_signals,
                "transcript_data": transcript_data,
                "overall_score": overall,
                "hook_score": hook_score,
            })

    log.info(f"✅ Generated {len(all_data)} synthetic videos\n")

    # ── Step 2: Train all models ──────────────────────────
    train_drop_zone_predictor(all_data)
    train_niche_classifier(all_data)
    train_early_score_predictor(all_data)
    train_user_weight_learner(all_data)

    # ── Summary ───────────────────────────────────────────
    log.info(f"\n{'='*60}")
    log.info("TRAINING COMPLETE")
    log.info(f"{'='*60}")

    model_files = list(MODELS_DIR.glob("*.pkl")) + list(MODELS_DIR.glob("*.json"))
    log.info(f"\nFiles in {MODELS_DIR}:")
    for f in sorted(model_files):
        size_kb = f.stat().st_size / 1024
        log.info(f"  {f.name:40s} {size_kb:8.1f} KB")

    log.info("\n✅ All 4 models trained and saved. They will activate on next server startup.")


if __name__ == "__main__":
    main()
