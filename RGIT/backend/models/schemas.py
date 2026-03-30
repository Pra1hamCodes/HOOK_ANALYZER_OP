"""Pydantic models for API request/response schemas."""
from __future__ import annotations
from enum import Enum
from pydantic import BaseModel, Field


class Zone(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


# ── Audio ───────────────────────────────────────────────
class AudioSignal(BaseModel):
    timestamp: float
    energy: float
    pitch_variation: float
    pacing: float
    silence_flag: bool
    audio_score: float


# ── Visual ──────────────────────────────────────────────
class VisualSignal(BaseModel):
    timestamp: float
    motion_score: float
    scene_cut: bool
    face_present: bool
    visual_score: float


# ── Transcript ──────────────────────────────────────────
class TranscriptData(BaseModel):
    transcript: str
    sentiment_polarity: float
    subjectivity: float
    keywords: list[str]
    transcription_score: float
    narrative_summary: str


# ── Emotion ─────────────────────────────────────────────
class EmotionTimelinePoint(BaseModel):
    timestamp: float
    vocal_emotion: str
    facial_emotion: str


class EmotionData(BaseModel):
    dominant_facial_emotion: str
    dominant_vocal_emotion: str
    alignment_score: float
    emotion_timeline: list[EmotionTimelinePoint]


# ── Virality & Trends ───────────────────────────────────
class RecommendedTrack(BaseModel):
    id: str
    track_name: str
    artist: str
    bpm: int


class ViralityData(BaseModel):
    sound_score: float
    recommended_track: RecommendedTrack | None
    trend_type_rec: str
    reasoning: str


# ── Semantic Summary ────────────────────────────────────
class SemanticSummaryData(BaseModel):
    transcript_narrative: str
    visual_narrative: str
    semantic_overlap_score: float
    semantic_drift_detected: bool
    vibe_check_message: str


# ── Fusion / Timeline ──────────────────────────────────
class TimelinePoint(BaseModel):
    t: float
    audio_score: float
    visual_score: float
    object_richness_score: float = 0.0
    detected_objects: list[dict] = Field(default_factory=list)
    attention: float
    zone: Zone
    flags: list[dict] = Field(default_factory=list)
    strengths: list[dict] = Field(default_factory=list)
    faults: list[dict] = Field(default_factory=list)
    confidence: float = 100.0


class RiskZone(BaseModel):
    start: float
    end: float
    zone: Zone
    avg_attention: float
    flags: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


# ── API responses ──────────────────────────────────────
class VideoMeta(BaseModel):
    duration: float
    resolution: str
    fps: float
    filename: str


class AnalysisResult(BaseModel):
    job_id: str
    video_meta: VideoMeta
    timeline: list[TimelinePoint]
    zones: list[RiskZone]
    overall_score: float
    summary: str
    analysis_confidence: float = 100.0
    confidence_reasons: list[str] = Field(default_factory=list)
    platform: str = "generic"
    transcript_data: TranscriptData | dict | None = None
    emotion_data: EmotionData | dict | None = None
    virality_data: ViralityData | dict | None = None
    semantic_data: SemanticSummaryData | dict | None = None
    reference_baselines: dict | None = None
    # ML fields
    ml_niche_detected: dict | None = None
    early_score_estimates: list | None = None
    ml_zones_active: bool = False
    # Multimodal LLM fields
    multimodal_hook_critique: dict | None = None
    multimodal_red_zone_diagnoses: list | None = None
    multimodal_llm_active: bool = False
