"""ML Engine — Unified ML layer with 4 sub-models.

Sub-models:
  1. DropZonePredictor   — RandomForest per-second zone classification
  2. NicheClassifier     — SVC niche auto-detection
  3. EarlyScorePredictor — XGBRegressor score estimate from first 10s
  4. UserWeightLearner   — Ridge regression per-user weight suggestion

All models gracefully return None when model files are missing or insufficient data.
"""
from __future__ import annotations

import json
import logging
import os
import pickle
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger("hook_architect.ml_engine")

# ── Paths ────────────────────────────────────────────────
MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

DROP_MODEL_PATH = MODELS_DIR / "drop_predictor.pkl"
DROP_META_PATH = MODELS_DIR / "drop_predictor_meta.json"

NICHE_MODEL_PATH = MODELS_DIR / "niche_classifier.pkl"
NICHE_META_PATH = MODELS_DIR / "niche_classifier_meta.json"

EARLY_MODEL_PATH = MODELS_DIR / "early_score_predictor.pkl"
EARLY_META_PATH = MODELS_DIR / "early_score_predictor_meta.json"

USER_WEIGHTS_DIR = MODELS_DIR  # user_weights_{user_id}.pkl

# ── Zone mapping ─────────────────────────────────────────
ZONE_TO_INT = {"green": 0, "yellow": 1, "red": 2}
INT_TO_ZONE = {0: "green", 1: "yellow", 2: "red"}


# ═══════════════════════════════════════════════════════════
# HELPER — safe meta read / write
# ═══════════════════════════════════════════════════════════

def _read_meta(path: Path) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"sample_count": 0}


def _write_meta(path: Path, meta: dict):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(meta, f)


def _save_model(model: Any, path: Path):
    with open(path, "wb") as f:
        pickle.dump(model, f)


def _load_model(path: Path) -> Any | None:
    if not path.exists():
        return None
    try:
        with open(path, "rb") as f:
            return pickle.load(f)
    except Exception as e:
        logger.warning(f"[ML] Failed to load model {path.name}: {e}")
        return None


# ═══════════════════════════════════════════════════════════
# SUB-MODEL 1: Drop Zone Predictor
# ═══════════════════════════════════════════════════════════

class DropZonePredictor:
    """RandomForest per-second zone classifier."""

    MIN_SAMPLES = 20  # minimum videos before model activates

    def _build_features(
        self,
        audio_signals: list[dict],
        visual_signals: list[dict],
        duration: float,
    ) -> np.ndarray:
        """Build feature matrix from audio + visual signals."""
        n = max(len(audio_signals), len(visual_signals))
        dur = max(duration, 1.0)
        rows = []
        for i in range(n):
            a = audio_signals[i] if i < len(audio_signals) else {
                "energy": 0, "pitch_variation": 0, "pacing": 0,
                "silence_flag": True, "audio_score": 0,
            }
            v = visual_signals[i] if i < len(visual_signals) else {
                "motion_score": 0, "scene_cut": False,
                "face_present": False, "visual_score": 0,
            }
            rows.append([
                a.get("energy", 0),
                a.get("pitch_variation", 0),
                a.get("pacing", 0),
                1 if a.get("silence_flag", False) else 0,
                v.get("motion_score", 0),
                1 if v.get("scene_cut", False) else 0,
                1 if v.get("face_present", False) else 0,
                a.get("audio_score", 0),
                v.get("visual_score", 0),
                i / dur,  # timestamp_normalized
            ])
        return np.array(rows, dtype=np.float64)

    def predict(
        self,
        audio_signals: list[dict],
        visual_signals: list[dict],
        duration: float,
    ) -> list[str] | None:
        """Predict per-second zones. Returns None if model missing."""
        model = _load_model(DROP_MODEL_PATH)
        if model is None:
            return None
        meta = _read_meta(DROP_META_PATH)
        if meta.get("sample_count", 0) < self.MIN_SAMPLES:
            return None
        try:
            X = self._build_features(audio_signals, visual_signals, duration)
            preds = model.predict(X)
            return [INT_TO_ZONE.get(int(p), "yellow") for p in preds]
        except Exception as e:
            logger.warning(f"[ML] DropZonePredictor.predict failed: {e}")
            return None

    def train(
        self,
        audio_signals: list[dict],
        visual_signals: list[dict],
        timeline: list[dict],
        duration: float,
    ):
        """Incrementally collect training samples and retrain."""
        try:
            from sklearn.ensemble import RandomForestClassifier

            X = self._build_features(audio_signals, visual_signals, duration)
            y = np.array([
                ZONE_TO_INT.get(t.get("zone", "yellow"), 1)
                for t in timeline[:len(X)]
            ])
            if len(X) != len(y):
                min_len = min(len(X), len(y))
                X, y = X[:min_len], y[:min_len]

            # Load existing training data
            cache_path = MODELS_DIR / "drop_predictor_cache.pkl"
            if cache_path.exists():
                with open(cache_path, "rb") as f:
                    cache = pickle.load(f)
                X_all = np.vstack([cache["X"], X])
                y_all = np.concatenate([cache["y"], y])
            else:
                X_all, y_all = X, y

            # Save updated cache
            with open(cache_path, "wb") as f:
                pickle.dump({"X": X_all, "y": y_all}, f)

            meta = _read_meta(DROP_META_PATH)
            meta["sample_count"] = meta.get("sample_count", 0) + 1
            _write_meta(DROP_META_PATH, meta)

            if meta["sample_count"] >= self.MIN_SAMPLES:
                clf = RandomForestClassifier(n_estimators=100, random_state=42)
                clf.fit(X_all, y_all)
                _save_model(clf, DROP_MODEL_PATH)
                logger.info(f"[ML] DropZonePredictor trained — {len(X_all)} samples, {meta['sample_count']} videos")
        except Exception as e:
            logger.warning(f"[ML] DropZonePredictor.train failed: {e}")


# ═══════════════════════════════════════════════════════════
# SUB-MODEL 2: Niche Classifier
# ═══════════════════════════════════════════════════════════

class NicheClassifier:
    """SVC niche auto-detector."""

    MIN_SAMPLES = 30
    VALID_NICHES = ["action", "educational", "emotional", "vlog", "cinematic", "comedy", "music"]

    def _build_features(
        self,
        audio_signals: list[dict],
        visual_signals: list[dict],
        transcript_data: dict | None,
    ) -> np.ndarray:
        """Build single-row feature vector for a video."""
        n_a = max(len(audio_signals), 1)
        n_v = max(len(visual_signals), 1)

        avg_energy = sum(a.get("energy", 0) for a in audio_signals) / n_a
        avg_pitch = sum(a.get("pitch_variation", 0) for a in audio_signals) / n_a
        avg_pacing = sum(a.get("pacing", 0) for a in audio_signals) / n_a
        avg_motion = sum(v.get("motion_score", 0) for v in visual_signals) / n_v
        avg_face = sum(1 for v in visual_signals if v.get("face_present", False)) / n_v
        silence_ratio = sum(1 for a in audio_signals if a.get("silence_flag", False)) / n_a
        avg_scene_cut = sum(1 for v in visual_signals if v.get("scene_cut", False)) / n_v

        word_count = 0
        duration = max(len(audio_signals), 1)
        if transcript_data and transcript_data.get("transcript"):
            word_count = len(transcript_data["transcript"].split())
        wps = word_count / duration

        return np.array([[
            avg_energy, avg_pitch, avg_pacing, avg_motion,
            avg_face, silence_ratio, avg_scene_cut, wps,
        ]], dtype=np.float64)

    def predict_niche(
        self,
        audio_signals: list[dict],
        visual_signals: list[dict],
        transcript_data: dict | None,
    ) -> dict | None:
        """Predict niche with confidence. Returns None if model missing or low confidence."""
        model = _load_model(NICHE_MODEL_PATH)
        if model is None:
            return None
        meta = _read_meta(NICHE_META_PATH)
        if meta.get("sample_count", 0) < self.MIN_SAMPLES:
            return None
        try:
            X = self._build_features(audio_signals, visual_signals, transcript_data)
            proba = model.predict_proba(X)[0]
            max_idx = int(np.argmax(proba))
            confidence = float(proba[max_idx])
            niche = model.classes_[max_idx]
            if confidence < 0.55:
                return None
            return {"niche": str(niche), "confidence": round(confidence, 3)}
        except Exception as e:
            logger.warning(f"[ML] NicheClassifier.predict_niche failed: {e}")
            return None

    def train(
        self,
        audio_signals: list[dict],
        visual_signals: list[dict],
        transcript_data: dict | None,
        niche_label: str,
    ):
        """Add training sample and retrain when enough data."""
        if niche_label not in self.VALID_NICHES:
            return
        try:
            from sklearn.svm import SVC

            X = self._build_features(audio_signals, visual_signals, transcript_data)

            cache_path = MODELS_DIR / "niche_classifier_cache.pkl"
            if cache_path.exists():
                with open(cache_path, "rb") as f:
                    cache = pickle.load(f)
                X_all = np.vstack([cache["X"], X])
                y_all = cache["y"] + [niche_label]
            else:
                X_all = X
                y_all = [niche_label]

            with open(cache_path, "wb") as f:
                pickle.dump({"X": X_all, "y": y_all}, f)

            meta = _read_meta(NICHE_META_PATH)
            meta["sample_count"] = meta.get("sample_count", 0) + 1
            _write_meta(NICHE_META_PATH, meta)

            if meta["sample_count"] >= self.MIN_SAMPLES and len(set(y_all)) >= 2:
                clf = SVC(kernel="rbf", probability=True)
                clf.fit(X_all, y_all)
                _save_model(clf, NICHE_MODEL_PATH)
                logger.info(f"[ML] NicheClassifier trained — {len(X_all)} samples, {meta['sample_count']} videos")
        except Exception as e:
            logger.warning(f"[ML] NicheClassifier.train failed: {e}")


# ═══════════════════════════════════════════════════════════
# SUB-MODEL 3: Early Score Predictor
# ═══════════════════════════════════════════════════════════

class EarlyScorePredictor:
    """XGBRegressor — predicts overall score from first 10s of audio+visual."""

    MIN_SAMPLES = 15

    def _build_features(
        self,
        audio_first10: list[dict],
        visual_first10: list[dict],
        hook_score: float | None = None,
    ) -> np.ndarray:
        """Build feature vector from first 10 seconds."""
        n_a = max(len(audio_first10), 1)
        n_v = max(len(visual_first10), 1)

        avg_energy = sum(a.get("energy", 0) for a in audio_first10) / n_a
        avg_pitch = sum(a.get("pitch_variation", 0) for a in audio_first10) / n_a
        avg_motion = sum(v.get("motion_score", 0) for v in visual_first10) / n_v
        face_ratio = sum(1 for v in visual_first10 if v.get("face_present", False)) / n_v
        silence_ratio = sum(1 for a in audio_first10 if a.get("silence_flag", False)) / n_a
        avg_pacing = sum(a.get("pacing", 0) for a in audio_first10) / n_a
        hs = hook_score if hook_score is not None else 50.0

        return np.array([[
            avg_energy, avg_pitch, avg_motion, face_ratio,
            silence_ratio, avg_pacing, hs,
        ]], dtype=np.float64)

    def predict_early(
        self,
        audio_first10: list[dict],
        visual_first10: list[dict],
        hook_score: float | None = None,
    ) -> float | None:
        """Predict overall score from first 10s. Returns None if model missing."""
        model = _load_model(EARLY_MODEL_PATH)
        if model is None:
            return None
        meta = _read_meta(EARLY_META_PATH)
        if meta.get("sample_count", 0) < self.MIN_SAMPLES:
            return None
        try:
            X = self._build_features(audio_first10, visual_first10, hook_score)
            pred = float(model.predict(X)[0])
            return max(0.0, min(100.0, pred))
        except Exception as e:
            logger.warning(f"[ML] EarlyScorePredictor.predict_early failed: {e}")
            return None

    def train(
        self,
        audio_signals: list[dict],
        visual_signals: list[dict],
        overall_score: float,
        hook_score: float | None = None,
    ):
        """Add training sample and retrain."""
        try:
            from xgboost import XGBRegressor

            X = self._build_features(
                audio_signals[:10], visual_signals[:10], hook_score
            )
            y = np.array([overall_score])

            cache_path = MODELS_DIR / "early_score_cache.pkl"
            if cache_path.exists():
                with open(cache_path, "rb") as f:
                    cache = pickle.load(f)
                X_all = np.vstack([cache["X"], X])
                y_all = np.concatenate([cache["y"], y])
            else:
                X_all, y_all = X, y

            with open(cache_path, "wb") as f:
                pickle.dump({"X": X_all, "y": y_all}, f)

            meta = _read_meta(EARLY_META_PATH)
            meta["sample_count"] = meta.get("sample_count", 0) + 1
            _write_meta(EARLY_META_PATH, meta)

            if meta["sample_count"] >= self.MIN_SAMPLES:
                reg = XGBRegressor(
                    n_estimators=200, max_depth=4,
                    learning_rate=0.05, random_state=42,
                )
                reg.fit(X_all, y_all)
                _save_model(reg, EARLY_MODEL_PATH)
                logger.info(f"[ML] EarlyScorePredictor trained — {len(X_all)} samples, {meta['sample_count']} videos")
        except Exception as e:
            logger.warning(f"[ML] EarlyScorePredictor.train failed: {e}")


# ═══════════════════════════════════════════════════════════
# SUB-MODEL 4: User-Personalized Weight Learner
# ═══════════════════════════════════════════════════════════

class UserWeightLearner:
    """Ridge regression per-user — suggests fusion weights."""

    MIN_VIDEOS = 5
    WEIGHT_KEYS = ["audio_weight", "visual_weight", "transcript_weight",
                   "song_weight", "temporal_weight", "engagement_weight"]

    def _user_model_path(self, user_id: str) -> Path:
        safe_id = user_id.replace("/", "_").replace("\\", "_")
        return MODELS_DIR / f"user_weights_{safe_id}.pkl"

    def _build_features(
        self,
        audio_avg: float,
        visual_avg: float,
        transcript_score: float,
        emotion_alignment: float,
        green_pct: float,
        yellow_pct: float,
        red_pct: float,
        video_count: int,
    ) -> np.ndarray:
        return np.array([[
            audio_avg, visual_avg, transcript_score, emotion_alignment,
            green_pct, yellow_pct, red_pct, video_count,
        ]], dtype=np.float64)

    def predict_weights(
        self,
        user_id: str,
        audio_avg: float,
        visual_avg: float,
        transcript_score: float,
        emotion_alignment: float,
        green_pct: float,
        yellow_pct: float,
        red_pct: float,
        video_count: int,
    ) -> dict | None:
        """Predict suggested fusion weights for user. Returns None if insufficient data."""
        if video_count < self.MIN_VIDEOS:
            return None
        model = _load_model(self._user_model_path(user_id))
        if model is None:
            return None
        try:
            X = self._build_features(
                audio_avg, visual_avg, transcript_score,
                emotion_alignment, green_pct, yellow_pct,
                red_pct, video_count,
            )
            pred = model.predict(X)[0]
            # pred is the predicted overall_score, derive weights from feature importances
            # Use the model coefficients to derive relative weight suggestions
            coefs = np.abs(model.coef_)
            # Map first 6 coefficients to weight keys (audio, visual, transcript, emotion→engagement, ...)
            weight_coefs = coefs[:6] if len(coefs) >= 6 else np.ones(6)
            total = weight_coefs.sum()
            if total == 0:
                return None
            normalized = weight_coefs / total
            weights = {}
            for i, key in enumerate(self.WEIGHT_KEYS):
                weights[key] = round(float(normalized[i]), 4)
            return weights
        except Exception as e:
            logger.warning(f"[ML] UserWeightLearner.predict_weights failed: {e}")
            return None

    def train_incremental(
        self,
        user_id: str,
        audio_avg: float,
        visual_avg: float,
        transcript_score: float,
        emotion_alignment: float,
        green_pct: float,
        yellow_pct: float,
        red_pct: float,
        video_count: int,
        overall_score: float,
    ):
        """Add sample and retrain user model."""
        try:
            from sklearn.linear_model import Ridge

            X = self._build_features(
                audio_avg, visual_avg, transcript_score,
                emotion_alignment, green_pct, yellow_pct,
                red_pct, video_count,
            )
            y = np.array([overall_score])

            cache_path = MODELS_DIR / f"user_weights_{user_id}_cache.pkl"
            if cache_path.exists():
                with open(cache_path, "rb") as f:
                    cache = pickle.load(f)
                X_all = np.vstack([cache["X"], X])
                y_all = np.concatenate([cache["y"], y])
            else:
                X_all, y_all = X, y

            with open(cache_path, "wb") as f:
                pickle.dump({"X": X_all, "y": y_all}, f)

            if len(y_all) >= self.MIN_VIDEOS:
                reg = Ridge(alpha=1.0)
                reg.fit(X_all, y_all)
                _save_model(reg, self._user_model_path(user_id))
                logger.info(f"[ML] UserWeightLearner trained for user {user_id} — {len(X_all)} samples")
        except Exception as e:
            logger.warning(f"[ML] UserWeightLearner.train_incremental failed: {e}")


# ═══════════════════════════════════════════════════════════
# GLOBAL TRAINING TRIGGER
# ═══════════════════════════════════════════════════════════

def train_all_models():
    """Train all models on existing data caches.
    
    Called at startup and after each analysis.
    Works on cached data files — does not need DB connection.
    """
    logger.info("[ML] train_all_models() — checking cached training data...")

    # Drop predictor
    try:
        cache_path = MODELS_DIR / "drop_predictor_cache.pkl"
        meta = _read_meta(DROP_META_PATH)
        if cache_path.exists() and meta.get("sample_count", 0) >= DropZonePredictor.MIN_SAMPLES:
            from sklearn.ensemble import RandomForestClassifier
            with open(cache_path, "rb") as f:
                cache = pickle.load(f)
            clf = RandomForestClassifier(n_estimators=100, random_state=42)
            clf.fit(cache["X"], cache["y"])
            _save_model(clf, DROP_MODEL_PATH)
            logger.info(f"[ML] DropZonePredictor retrained — {len(cache['X'])} samples")
    except Exception as e:
        logger.warning(f"[ML] DropZonePredictor retrain failed: {e}")

    # Niche classifier
    try:
        cache_path = MODELS_DIR / "niche_classifier_cache.pkl"
        meta = _read_meta(NICHE_META_PATH)
        if cache_path.exists() and meta.get("sample_count", 0) >= NicheClassifier.MIN_SAMPLES:
            from sklearn.svm import SVC
            with open(cache_path, "rb") as f:
                cache = pickle.load(f)
            if len(set(cache["y"])) >= 2:
                clf = SVC(kernel="rbf", probability=True)
                clf.fit(cache["X"], cache["y"])
                _save_model(clf, NICHE_MODEL_PATH)
                logger.info(f"[ML] NicheClassifier retrained — {len(cache['X'])} samples")
    except Exception as e:
        logger.warning(f"[ML] NicheClassifier retrain failed: {e}")

    # Early score predictor
    try:
        cache_path = MODELS_DIR / "early_score_cache.pkl"
        meta = _read_meta(EARLY_META_PATH)
        if cache_path.exists() and meta.get("sample_count", 0) >= EarlyScorePredictor.MIN_SAMPLES:
            from xgboost import XGBRegressor
            with open(cache_path, "rb") as f:
                cache = pickle.load(f)
            reg = XGBRegressor(
                n_estimators=200, max_depth=4,
                learning_rate=0.05, random_state=42,
            )
            reg.fit(cache["X"], cache["y"])
            _save_model(reg, EARLY_MODEL_PATH)
            logger.info(f"[ML] EarlyScorePredictor retrained — {len(cache['X'])} samples")
    except Exception as e:
        logger.warning(f"[ML] EarlyScorePredictor retrain failed: {e}")

    logger.info("[ML] train_all_models() complete.")
