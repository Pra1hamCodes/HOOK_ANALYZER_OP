# 🎬 Hook Architect — AI-Powered Video Retention Intelligence Platform

> **Upload a short-form video → Receive a complete retention analysis** with per-second attention heatmaps, emotion arcs, hook grading, ML-powered predictions, optional visual AI diagnostics, predictive retention curves, AI coaching, trending audio matching, and one-click PDF reports — all personalized to your creator niche.

![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.99-green?logo=fastapi)
![OpenCV](https://img.shields.io/badge/OpenCV-4.9%2B-blue?logo=opencv)
![scikit-learn](https://img.shields.io/badge/scikit--learn-1.4%2B-orange?logo=scikit-learn)
![LLaVA](https://img.shields.io/badge/LLaVA-Multimodal-purple)

---

## 📑 Table of Contents

- [Overview](#-overview)
- [Architecture](#-architecture)
- [Analysis Pipeline](#-analysis-pipeline--step-by-step)
- [Full Feature Breakdown](#-full-feature-breakdown)
- [ML Predictive Engine](#-ml-predictive-engine)
- [Multimodal Visual AI](#-multimodal-visual-ai-llava)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Getting Started](#-getting-started)
- [Configuration](#%EF%B8%8F-configuration)
- [API Reference](#-api-reference)
- [Database Schema](#-database-schema)
- [Scoring & Fusion Formula](#-scoring--fusion-formula)
- [Persona Presets](#-persona-presets--niche-system)

---

## 🎯 Overview

Hook Architect is a full-stack video retention analysis platform designed for short-form content creators (TikTok, YouTube Shorts, Reels). It processes uploaded videos through a **multi-modal AI pipeline** to identify **exactly** where viewers would drop off, why, and how to fix it.

### What It Does

1. **Uploads** a video (up to 120 seconds, or a YouTube URL)
2. **Extracts** audio (WAV) and frames (JPEG @ 5fps) using FFmpeg
3. **Analyzes** audio signals (energy, pitch, pacing, silence) via librosa
4. **Analyzes** visual signals (motion, scene cuts, face detection) via OpenCV + YOLOv8
5. **Runs** speech-to-text transcription + NLP sentiment analysis
6. **Detects** facial and vocal emotions via DeepFace + acoustic heuristics
7. **Enriches** via external API (Groq Whisper + 2s window analysis) — optional, graceful fallback
8. **Matches** trending audio from a local database (Audio-Sync Index)
9. **Summarizes** content with dual-track narrative vs visual Vibe Check
10. **Fuses** all signals into a weighted attention score per second (cross-modal fusion engine)
11. **Predicts** ML-powered drop zones (RandomForest), niche classification, and early score estimates
12. **Diagnoses** visual weaknesses via LLaVA multimodal AI (optional, via Ollama)
13. **Generates** Hook Strength Score (A+ to F), Emotion Arc, Retention Curve
14. **Coaches** with per-zone AI insights, script rewrites, and fix suggestions
15. **Adapts** scoring weights via EMA-based learning from your video history
16. **Serves** everything via an interactive single-page dashboard with heatmap timeline, charts, and PDF export

### Key Differentiators

- **Zero external dependencies at runtime** — no Redis, no Celery, no Docker required
- **Standalone `main.py`** — one file runs the entire backend (FastAPI + WebSocket + in-memory job store)
- **Graceful degradation everywhere** — ML models, LLaVA, Groq API, external API all fail silently
- **Incremental ML training** — models get smarter as you analyze more videos
- **Niche-aware scoring** — 7 persona presets customize weights for your content type

---

## 🏗 Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (SPA)                               │
│  index.html + app.js + style.css                                     │
│  Upload → Progress (WebSocket) → Interactive Dashboard               │
│  Charts · Heatmap · Zone Cards · AI Chat · ML Badge · Visual AI      │
└──────────────────────────┬───────────────────────────────────────────┘
                           │ HTTP + WebSocket
┌──────────────────────────▼───────────────────────────────────────────┐
│                  FASTAPI BACKEND — main.py (port 8000)               │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │              ANALYSIS PIPELINE (12-step, threaded)               │ │
│  │                                                                   │ │
│  │  FFmpeg ──► Audio + Frames                                       │ │
│  │    ↓            ↓                                                 │ │
│  │  audio_      visual_     transcript_   emotion_   virality_      │ │
│  │  analyzer    analyzer    analyzer      analyzer   analyzer       │ │
│  │    ↓            ↓            ↓             ↓           ↓          │ │
│  │  ┌──────────────────────────────────────────────────────────┐    │ │
│  │  │  ML Engine (scikit-learn)                                │    │ │
│  │  │  EarlyScorePredictor · NicheClassifier                  │    │ │
│  │  │  DropZonePredictor · UserWeightLearner                  │    │ │
│  │  └──────────────────────────────────────────────────────────┘    │ │
│  │    ↓                                                             │ │
│  │  fusion_engine ──► zones + attention scores                      │ │
│  │    ↓                                                             │ │
│  │  hook_scorer · emotion_arc · retention_curve                     │ │
│  │    ↓                                                             │ │
│  │  ┌──────────────────────────────────────────────────────────┐    │ │
│  │  │  Multimodal Coach (LLaVA via Ollama) — optional          │    │ │
│  │  │  critique_hook_frames · diagnose_red_zone               │    │ │
│  │  └──────────────────────────────────────────────────────────┘    │ │
│  │    ↓                                                             │ │
│  │  adaptive_engine ──► weight evolution                            │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  ┌───────────┐ │
│  │ SQLite DB    │  │ In-Memory    │  │ WebSocket  │  │ Groq LLM  │ │
│  │ (profiles,   │  │ Job Store    │  │ Progress   │  │ (coaching  │ │
│  │  history)    │  │ (results)    │  │ Broadcast  │  │  + chat)   │ │
│  └──────────────┘  └──────────────┘  └────────────┘  └───────────┘ │
└──────────────────────────┬───────────────────────────────────────────┘
                           │ HTTP (httpx, optional)
┌──────────────────────────▼───────────────────────────────────────────┐
│         EXTERNAL VIDEO API — Flask (port 5000) — OPTIONAL            │
│  POST /transcribe_and_summarize (Groq Whisper + Llama niche)         │
│  POST /analyze_video (OpenCV 2s-window visual energy analysis)       │
└──────────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
Video Upload
    │
    ▼
FFmpeg ──► Audio (WAV 22050Hz mono) ──► librosa ──► Audio Signals
    │                                                    │
    ├──► Frames (JPEG @ 5fps) ──► OpenCV/YOLO ──► Visual Signals
    │                                                │
    │    Audio ──► SpeechRecognition ──► Transcript + NLP
    │    Frames ──► DeepFace ──► Facial Emotions
    │    Audio Signals ──► Acoustic Heuristics ──► Vocal Emotions
    │                                                    │
    │    ┌── ML Engine ──────────────────────┐           │
    │    │ EarlyScorePredictor (audio-only)  │           │
    │    │ EarlyScorePredictor (audio+visual)│           │
    │    │ NicheClassifier                   │           │
    │    │ DropZonePredictor                 │           │
    │    └───────────────────────────────────┘           │
    ▼                                                    ▼
External API ──► Groq Whisper + Window Analysis    Fusion Engine
    (optional)                                          │
                                         ┌──────────────┤
                                         ▼              ▼
                                   Hook Scorer    Emotion Arc
                                   (first 3s)   (intensity map)
                                         │              │
                                         ▼              ▼
                    ┌── Multimodal Coach (LLaVA) ──┐  Retention Curve
                    │ critique_hook_frames          │  (viewer sim)
                    │ diagnose_red_zone             │
                    └──────────────────────────────┘
                                         │
                                         ▼
                              Adaptive Engine (EMA)
                                         │
                                         ▼
                              Dashboard + PDF Report
```

---

## 🔄 Analysis Pipeline — Step by Step

| Step | % | Module | What Happens |
|------|---|--------|-------------|
| 1 | 5% | `video_processor` | FFprobe reads metadata (duration, resolution, FPS) |
| 2 | 10% | `video_processor` | FFmpeg extracts mono 22050Hz WAV audio |
| 3 | 20% | `video_processor` | FFmpeg extracts JPEG frames at 5fps |
| 4 | 30–50% | `audio_analyzer` | Per-second: energy, pitch variation, pacing, silence |
| — | 50% | `ml_engine` | **ML: Early score prediction (audio-only)** |
| 5 | 55–75% | `visual_analyzer` | Per-second: motion score, scene cuts, face detection |
| — | 75% | `ml_engine` | **ML: Early score prediction (audio+visual)** |
| 5.5 | 76% | `transcript_analyzer` | ASR transcription + NLP sentiment analysis |
| 5.8 | 78% | `emotion_analyzer` | DeepFace facial + acoustic vocal emotion tracking |
| 5.85 | 79% | `external_api` | Groq Whisper + 2s-window enrichment (optional) |
| — | 79% | `ml_engine` | **ML: Niche classification override** |
| 5.9 | 80% | `virality_analyzer` | Trending audio matching + Audio-Sync Index |
| 5.10 | 82% | `semantic_summarizer` | Dual-track Vibe Check + reference comparison |
| 6 | 85% | `fusion_engine` | Weighted fusion → attention timeline + zones |
| — | 85% | `ml_engine` | **ML: Drop zone prediction → zone blending** |
| 6.1 | 88% | `emotion_arc` | Emotional journey: phases, transitions, arc shape |
| 6.2 | 90% | `hook_scorer` | First 3s graded on 4 axes (A+ to F) |
| 6.3 | 92% | `retention_curve` | YouTube-style viewer retention simulation |
| 6.4 | 93% | `multimodal_coach` | **LLaVA: Hook frame critique + red zone diagnosis** (optional) |
| 6.5 | 93% | goal evaluation | Goal alignment scoring (if goal text provided) |
| 7.5 | 94% | reference comparison | Reference vs Main video comparison |
| 8 | 95% | `adaptive_engine` | EMA weight nudging + ML incremental training |
| 9 | 100% | result broadcast | Store results → WebSocket "complete" |

---

## ✨ Full Feature Breakdown

### 1. 🎧 Audio Analysis (`audio_analyzer.py`)

| Signal | Method | Range | Formula |
|--------|--------|-------|---------|
| Energy | RMS loudness | 0–100 | Normalized against global max RMS |
| Pitch Variation | pyin F0 (C2–C7) | 0–100 | Std dev of fundamental frequency |
| Pacing | Onset strength | 0–100 | Average onset strength per second |
| Silence Flag | RMS < 15% mean | bool | True when energy drops below threshold |
| Audio Score | Weighted composite | 0–100 | `0.40×energy + 0.30×pitch + 0.20×pacing + 0.10×silence` |

### 2. 👁 Visual Analysis (`visual_analyzer.py`)

| Signal | Method | Range | Details |
|--------|--------|-------|---------|
| Motion Score | Farneback optical flow | 0–100 | Mean pixel displacement, frames downscaled to 320×240 |
| Scene Cut | Histogram correlation | bool | Correlation < 0.4 between consecutive frames |
| Face Present | Haar cascade | bool | `scaleFactor=1.1, minNeighbors=4, minSize=(30,30)` |
| Visual Score | Weighted composite | 0–100 | `0.45×motion + 0.20×scene_cut + 0.35×face` |

### 3. 🗣 Transcript Analysis (`transcript_analyzer.py`)

- **ASR**: Google SpeechRecognition (free, local) or Groq Whisper (via external API)
- **NLP**: TextBlob sentiment polarity, subjectivity, noun phrase extraction
- **Score**: Word density × engagement multiplier (`1.0 + |polarity|×0.3 + subjectivity×0.2`)

### 4. 🎭 Emotion Analysis (`emotion_analyzer.py`)

- **Facial**: DeepFace recognition (happy, sad, angry, surprise, fear, disgust, neutral)
- **Vocal**: Acoustic heuristics mapping (energy, pitch) → emotion quadrants
- **Alignment**: Cross-references text sentiment with face/voice emotions (0–100)

### 5. ⚡ Cross-Modal Fusion Engine (`fusion_engine.py`)

The core scoring engine. Per-second:
```
raw = (α×audio + β×visual + γ×transcript + δ×song + ε×temporal + ζ×engagement) / sum(weights)
attention = sigmoid(raw) → 0–100
zone = Green (≥75) | Yellow (≥45) | Red (<45)
```

With ML zone blending: majority vote between rule-based and ML-predicted zones per second.

### 6. 🎣 Hook Strength Scorer (`hook_scorer.py`)

Grades first 3 seconds across 4 axes:
| Axis | Weight | What |
|------|--------|------|
| Transcript Hook | 30% | Hook phrases, questions, numbers, filler penalty |
| Visual Energy | 25% | Motion + scene cuts in opening frames |
| Audio Punch | 25% | Energy, pacing, silence penalty |
| Face Presence | 20% | Face anchoring + emotional expressiveness |

Grades: A+ (≥90) through F (<30)

### 7. 📈 Emotion Arc (`emotion_arc.py`)

Maps emotional intensity over time → phases (Hook, Build, Peak, Valley, Recovery, Outro) → arc shape (Mountain, Declining, Rising, U-shape, Steady, Wave)

### 8. 📉 Retention Curve (`retention_curve.py`)

YouTube-style viewer retention simulation. Starts at 100% viewers, applies per-second decay based on attention scores, hook quality, and external drop risk flags. Outputs: avg retention, watch-through rate, retention grade, sections analysis.

### 9. 🎵 Virality & Audio Matching (`virality_analyzer.py`)

Matches videos against `trends_db.json` using BPM proximity (35%), pacing alignment (30%), and emotion resonance (35%). Includes recency multiplier (Rising: 1.3×, Peak: 1.2×, Declining: 0.85×, Stale: 0.5×).

### 10. 🧠 Semantic Summarizer (`semantic_summarizer.py`)

Dual-track: narrative style (educational vs storytelling) vs visual style (talking-head vs dynamic). Detects **semantic drift** when content doesn't match visuals.

### 11. ✏️ Script Doctor (`drop_fixer.py`)

LLM-powered rewriting for red zones: rewritten script, visual format rec, 3 hook alternatives, pacing rec. Falls back to rule-based suggestions without API key.

### 12. 🤖 LLM Coach (`llm_coach.py`)

Per-zone AI coaching (Groq Llama 3.3 70B), goal keyword extraction, interactive report chat.

### 13. 🔄 Adaptive Feedback Loop (`adaptive_engine.py`)

EMA-based weight evolution (α=0.15). After 2+ videos, nudges scoring weights based on signal averages. Weight bounds: 0.05–0.60.

### 14. 📄 Report Generator (`report_generator.py`)

HTML reports (convertible to PDF via xhtml2pdf) + plain-text for LLM context.

### 15. 👤 Persona Presets (`persona_presets.py`)

| Niche | Audio | Visual | Transcript | Slow Reward | Energy Reward |
|-------|-------|--------|------------|-------------|---------------|
| 🎭 Emotional | 0.40 | 0.20 | 0.35 | +15 | 0 |
| 🔥 Action | 0.25 | 0.45 | 0.15 | 0 | +20 |
| 📚 Educational | 0.35 | 0.20 | 0.45 | +5 | 0 |
| 📹 Vlog | 0.30 | 0.35 | 0.30 | 0 | 0 |
| 🎬 Cinematic | 0.30 | 0.45 | 0.15 | +10 | 0 |
| 😂 Comedy | 0.40 | 0.25 | 0.40 | 0 | 0 |
| 🎵 Music | 0.45 | 0.30 | 0.05 | 0 | +15 |

---

## 🧠 ML Predictive Engine

`services/ml_engine.py` — 4 sub-models using scikit-learn, all with graceful fallback.

| Model | Type | Purpose |
|-------|------|---------|
| **EarlyScorePredictor** | GradientBoostingRegressor | Predicts final score from partial signals (50% and 75% pipeline) |
| **NicheClassifier** | RandomForestClassifier | Auto-detects content niche from audio/visual features |
| **DropZonePredictor** | RandomForestClassifier | Predicts green/yellow/red zones from per-second signals |
| **UserWeightLearner** | Linear regression + heuristics | Suggests personalized fusion weights from video history |

### How Training Works

- **Not pre-trained** — models learn incrementally from your own analysis data
- After each video analysis, training data is cached to `models/*.pkl`
- `train_all_models()` runs on startup and after each analysis
- After **2+ videos**, models start making predictions
- Until then, all predictions return `None` and the pipeline uses rule-based logic

---

## 👁 Multimodal Visual AI (LLaVA)

`services/multimodal_coach.py` — optional frame-level visual diagnostics via Ollama + LLaVA.

### What It Does

| Feature | Frames Analyzed | Output |
|---------|----------------|--------|
| **Hook Critique** | t=0, t=1, t=2 | First impression, visual weakness, specific fix |
| **Red Zone Diagnosis** | Middle frame of each red zone | What causes visual drop-off + fix suggestion |

### Setup

Requires [Ollama](https://ollama.com/) running locally with `llava:7b` model pulled. See [SETUP.md](SETUP.md) for details.

If Ollama is not running, the system silently disables multimodal and uses standard analysis.

---

## 🛠 Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Web Framework | FastAPI + Uvicorn | Async HTTP, WebSocket, static serving |
| Audio Analysis | librosa 0.10.2 | RMS, F0 pitch, onset detection |
| Visual Analysis | OpenCV 4.9+ | Optical flow, Haar cascades, histograms |
| Object Detection | Ultralytics YOLOv8 | Object richness scoring |
| Face Emotion | DeepFace | Facial emotion recognition |
| Speech-to-Text | SpeechRecognition + Groq Whisper | Local Google STT + cloud Whisper |
| NLP | TextBlob | Sentiment, subjectivity, noun phrases |
| ML Engine | scikit-learn + XGBoost | 4 predictive sub-models |
| Multimodal AI | LLaVA via Ollama | Frame-level visual diagnostics |
| LLM Coaching | Groq (Llama 3.3 70B) | Script rewriting, coaching, chat |
| Video Processing | FFmpeg / FFprobe | Audio/frame extraction, metadata |
| Database | SQLite (WAL mode) | Profiles, history, weight snapshots |
| PDF Export | xhtml2pdf | HTML → PDF report generation |
| HTTP Client | httpx | External API calls |
| Video Download | yt-dlp | YouTube/TikTok URL support |

### Frontend
- **Vanilla HTML/CSS/JS** — zero-dependency SPA
- **CSS Custom Properties** — dark glassmorphism design system
- **WebSocket API** — real-time progress streaming
- **Canvas/Charts** — interactive heatmap and signal visualization

---

## 📁 Project Structure

```
RGIT/
├── backend/
│   ├── main.py                          # FastAPI app — ALL routes + pipeline (1800 lines)
│   ├── .env                             # Environment variables (API keys)
│   ├── requirements.txt                 # Python dependencies
│   ├── ffmpeg.exe / ffprobe.exe         # Bundled FFmpeg binaries
│   ├── yolov8n.pt                       # YOLOv8 nano model
│   │
│   ├── core/
│   │   ├── config.py                    # Paths, weights, thresholds
│   │   ├── database.py                  # SQLite CRUD — profiles, history, references
│   │   └── persona_presets.py           # 7 niche-specific weight presets
│   │
│   ├── services/                        # 19 analysis modules
│   │   ├── video_processor.py           # FFmpeg wrappers
│   │   ├── audio_analyzer.py            # librosa audio signals
│   │   ├── visual_analyzer.py           # OpenCV visual signals
│   │   ├── transcript_analyzer.py       # ASR + NLP
│   │   ├── emotion_analyzer.py          # DeepFace + acoustic emotions
│   │   ├── virality_analyzer.py         # Audio-Sync Index + trend matching
│   │   ├── semantic_summarizer.py       # Dual-track Vibe Check
│   │   ├── fusion_engine.py             # Cross-modal attention scoring
│   │   ├── hook_scorer.py               # First 3s grading (A+ to F)
│   │   ├── emotion_arc.py               # Emotional journey mapping
│   │   ├── retention_curve.py           # Viewer retention simulation
│   │   ├── ml_engine.py                 # 4 ML sub-models (scikit-learn)
│   │   ├── multimodal_coach.py          # LLaVA visual diagnostics
│   │   ├── drop_fixer.py               # Script Doctor (LLM rewriting)
│   │   ├── llm_coach.py                # AI coaching + chat
│   │   ├── adaptive_engine.py           # EMA weight evolution
│   │   ├── report_generator.py          # HTML/PDF report generation
│   │   └── external_api.py             # Remote API client (Groq Whisper)
│   │
│   ├── models/
│   │   └── schemas.py                   # Pydantic models
│   │
│   ├── external_api_server/             # Optional Flask server (port 5000)
│   │   └── app.py                       # Groq Whisper + OpenCV window analysis
│   │
│   ├── data/
│   │   ├── hook_architect.db            # SQLite database
│   │   ├── trends_db.json               # Trending audio tracks
│   │   └── reference_baselines.json     # Reference baseline data
│   │
│   ├── uploads/                         # Uploaded videos (auto-cleaned after 1hr)
│   └── processed/                       # Extracted frames + audio (temporary)
│
├── frontend/
│   ├── index.html                       # Single-page application
│   └── static/
│       ├── style.css                    # Dark glassmorphism design system
│       └── app.js                       # Full client application
│
├── README.md                            # This file
└── SETUP.md                             # Quick start + optional setup guide
```

---

## 🚀 Getting Started

### Prerequisites
- **Python 3.10+**
- **FFmpeg** (bundled as `ffmpeg.exe` / `ffprobe.exe` in `backend/`)

### Quick Start

```bash
# 1. Install dependencies
cd RGIT/backend
pip install -r requirements.txt

# 2. Configure environment (edit .env with your API key)
#    GEMINI_API_KEY=your_groq_api_key_here

# 3. Start the server
python main.py

# 4. Open browser → http://localhost:8000
```

That's it. No Redis, no Celery, no Docker required.

### Optional: Enhanced Transcription (External API)

```bash
# In a separate terminal:
cd RGIT/backend/external_api_server
pip install -r requirements.txt
python app.py
# Runs on port 5000 — provides Groq Whisper transcription
```

### Optional: Visual AI (LLaVA via Ollama)

See [SETUP.md](SETUP.md) for Ollama installation and LLaVA model setup.

---

## ⚙️ Configuration

### Environment Variables (`.env`)

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `GEMINI_API_KEY` | For LLM features | `""` | Groq API key for coaching, script doctor, chat |
| `EXTERNAL_API_URL` | No | `https://...devtunnels.ms` | Remote analysis API endpoint |
| `MULTIMODAL_LLM_ENABLED` | No | `true` | Enable/disable LLaVA integration |
| `OLLAMA_HOST` | No | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | No | `llava:7b` | Multimodal model name |
| `HOST` | No | `0.0.0.0` | Server bind address |
| `PORT` | No | `8000` | Server port |

### Scoring Weights (`core/config.py`)

| Weight | Default | Description |
|--------|---------|-------------|
| `AUDIO_WEIGHT` | 0.35 | Voice/music importance |
| `VISUAL_WEIGHT` | 0.25 | Visual activity importance |
| `OBJECT_RICHNESS_WEIGHT` | 0.10 | Object detection (YOLOv8) |
| `TRANSCRIPT_WEIGHT` | 0.30 | Speech content importance |
| `SONG_WEIGHT` | 0.30 | Music/audio match importance |
| `TEMPORAL_WEIGHT` | 0.20 | Sustained-lull penalty |
| `ENGAGEMENT_WEIGHT` | 0.15 | Face/cut/energy composite |
| `GREEN_THRESHOLD` | 75 | Score ≥ this = Green zone |
| `YELLOW_THRESHOLD` | 45 | Score ≥ this = Yellow zone |

---

## 🔌 API Reference

### Upload & Analysis

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/analyze` | Upload video + start analysis pipeline |
| `GET` | `/api/results/{job_id}` | Get full analysis results |
| `GET` | `/api/jobs/{job_id}` | Poll job status |
| `WS` | `/ws/{job_id}` | Real-time progress WebSocket |
| `POST` | `/api/fix-drops/{job_id}` | AI Script Doctor for drop zones |

### User Profiles

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/profiles` | Create profile with niche |
| `GET` | `/api/profiles` | List all profiles |
| `GET` | `/api/profiles/{id}` | Get single profile |
| `DELETE` | `/api/profiles/{id}` | Delete profile |
| `GET` | `/api/profiles/{id}/history` | Video analysis history |
| `GET` | `/api/profiles/{id}/ledger` | Evolution Ledger (weight deltas) |

### AI & Reports

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/presets` | List 7 persona presets |
| `POST` | `/api/report/{job_id}` | Generate downloadable PDF |
| `POST` | `/api/chat` | Interactive AI chat about analysis |
| `POST` | `/api/goals/process` | Extract goal keywords via LLM |
| `POST` | `/api/youtube/download` | Download + analyze YouTube video |
| `POST` | `/api/share/{job_id}` | Create shareable report link |
| `GET` | `/api/shared/{token}` | View shared report |

### References

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/profiles/{id}/references` | Upload reference video |
| `GET` | `/api/profiles/{id}/references` | Get reference baseline |
| `DELETE` | `/api/profiles/{id}/references` | Delete all reference data |

---

## 🗄 Database Schema

SQLite database at `data/hook_architect.db` (WAL mode):

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `user_profiles` | User accounts | username, niche, 10 weight columns, thresholds, rewards |
| `video_history` | Past analyses | user_id, filename, overall_score, signal averages, zone distribution |
| `weight_snapshots` | Weight audit trail | user_id, trigger (initial/auto_adapt), weights JSON |
| `reference_videos` | Reference uploads | user_id, averaged metrics, dominant emotion/style |
| `reference_baselines` | Aggregated baselines | user_id (unique), video_count, all averaged metrics |
| `shared_reports` | Shareable links | token, job_id, created_at |

---

## 📊 Scoring & Fusion Formula

### Per-Second Attention Score

```
raw = (0.35×audio + 0.30×visual + 0.30×transcript + 0.30×song + 0.20×temporal + 0.15×engagement)
      / (0.35 + 0.30 + 0.30 + 0.30 + 0.20 + 0.15)
      + alignment_bonus

attention = 100 / (1 + e^(-0.05×(raw−50)))    ← sigmoid normalization to 0–100
```

### Engagement Bonus Components

| Condition | Bonus |
|-----------|-------|
| Face present | +40 |
| Scene cut | +30 |
| Active speech + energy > 50 | +30 |
| Slow pacing + niche reward | +slow_pacing_reward |
| High energy + niche reward | +high_energy_reward |

### ML Zone Blending

When the ML DropZonePredictor is active, per-second zones are determined by **majority vote** between:
1. Rule-based zone (from fusion engine)
2. ML-predicted zone (from RandomForest)

---

## 🎭 Persona Presets & Niche System

7 built-in presets customize the entire scoring pipeline:
- **Fusion weights** — which signals matter most for your niche
- **Zone thresholds** — what counts as "good" for your content type
- **Reward bonuses** — niche-specific bonuses (slow pacing for cinematic, high energy for action)
- **Adaptive learning** — weights evolve over time based on your video history (EMA, α=0.15)

---

## 📄 License

Internal project — not licensed for public distribution.
