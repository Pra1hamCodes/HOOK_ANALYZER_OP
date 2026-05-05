# 🎬 Hook Architect — AI-Powered Video Retention Intelligence Platform

> **Upload a video. Get a complete retention intelligence report.**
> Per-second attention heatmaps · ML drop-zone predictions · emotion arcs · hook grading · AI coaching · PDF expor
---

## 📖 Table of Contents

- [What Is Hook Architect?](#what-is-hook-architect)
- [Key Features](#key-features)
- [Architecture Overview](#architecture-overview)
- [Project Structure](#project-structure)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [Environment Configuration](#environment-configuration)
- [Optional Features](#optional-features)
- [ML Engine](#ml-engine)
- [API Reference](#api-reference)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

---

## What Is Hook Architect?

Hook Architect is a full-stack AI platform built for short-form content creators (TikTok, Reels, YouTube Shorts) who want to understand *why* viewers drop off and *how* to fix their hooks.

The core problem it solves: **most creators have no idea where in their video they lose people, or why.** Hook Architect gives you second-by-second retention intelligence powered by a combination of audio analysis, computer vision, emotion detection, and large language models — all running locally with no cloud infrastructure required.

**Workflow:**
1. Upload a short-form video
2. The backend pipeline extracts audio, analyses speech pace, detects emotions, scores visual energy, and identifies drop zones
3. An LLM coach (Groq Llama 3.3 70B) synthesises the signals into actionable feedback
4. A report is generated with attention heatmaps, hook grades, and a fix roadmap

---

## Key Features

### 🔥 Retention Heatmaps
Per-second attention scores rendered as a colour-coded timeline. Pinpoints exactly when viewer interest spikes or collapses, not just an average retention curve.

### 🎯 Hook Grading
The first 3 seconds of your video are graded (A–F) based on visual energy, speech clarity, pacing, and emotional intensity. Identifies whether your hook fails visually, verbally, or structurally.

### 📉 Drop Zone Predictor (ML)
A scikit-learn model trained on your own historical uploads identifies high-risk drop zones before viewers even watch. Once you have 2+ analysed videos, predictions begin; at 5+ videos they become reliable. The model updates continuously from your data.

### 😮 Emotion Arc Analysis
Uses DeepFace to detect emotional state (happy, surprised, neutral, fear, disgust, etc.) frame-by-frame across the video. Maps the creator's emotional arc and correlates emotional flatness with drop-off points.

### 🧠 AI Coaching (Groq LLM)
A Groq-powered Llama 3.3 70B model acts as a retention coach. It synthesises all analysis signals and produces:
- A plain-English diagnosis of why the hook underperforms
- A "Script Doctor" rewrite suggestion
- An interactive chat interface for follow-up questions

### 👁️ Visual Frame Analysis (Optional — LLaVA)
When Ollama + LLaVA 7B is enabled, individual video frames are analysed by a multimodal LLM. Hook frames (t=0,1,2s) and red-zone frames receive specific visual critiques: what the viewer sees, what weakens engagement, and exactly how to fix it.

### 📝 Transcript & Script Doctor
Groq Whisper (via optional external API) or local transcription extracts the full spoken transcript. The Script Doctor feature rewrites weak opening lines with stronger hooks based on the analysis.

### 📄 PDF Report Export
All findings — heatmaps, grades, emotion arcs, coaching notes, and fix suggestions — are compiled into a downloadable PDF report.

### 💾 Persistent History (SQLite)
All analyses are stored in a local SQLite database (WAL mode for concurrent reads). Revisit any past video, track improvement over time, and let the ML engine learn from your upload history.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                     Frontend (SPA)                       │
│         Vanilla HTML / CSS / JS — Dark Glassmorphism     │
│    Upload · Heatmap UI · Emotion Charts · Chat · PDF     │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP (REST)
┌──────────────────────▼──────────────────────────────────┐
│                  FastAPI Backend                          │
│                   (main.py / Python)                     │
│  ┌────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │ Audio      │  │ Vision       │  │ LLM Coach       │  │
│  │ Pipeline   │  │ Pipeline     │  │ (Groq / LLaVA)  │  │
│  │ (librosa)  │  │ (OpenCV,     │  │                 │  │
│  │            │  │  DeepFace,   │  │                 │  │
│  │            │  │  YOLOv8)     │  │                 │  │
│  └────────────┘  └──────────────┘  └─────────────────┘  │
│  ┌────────────────────────────────────────────────────┐  │
│  │               ML Engine (scikit-learn)             │  │
│  │  Drop Zone · Niche Classifier · Score Predictor    │  │
│  └────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────┐  │
│  │              SQLite Database (WAL mode)            │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
          │ Optional                    │ Optional
┌─────────▼─────────┐        ┌──────────▼──────────┐
│  External API      │        │  Ollama (local)      │
│  (Groq Whisper     │        │  LLaVA 7B            │
│   transcription)   │        │  Visual Frame AI     │
└───────────────────┘        └──────────────────────┘
```

The system runs entirely from a **single Python process** — no Redis, no Celery, no Docker, no external infrastructure required. The only mandatory external dependency is a Groq API key for LLM coaching features (falls back to rule-based suggestions without it).

---

## Project Structure

```
HOOK_ANALYZER/
│
├── RGIT/                          # Primary application (main build)
│   ├── backend/
│   │   ├── main.py                # FastAPI app entry point
│   │   ├── requirements.txt       # Python dependencies
│   │   ├── .env                   # Environment configuration
│   │   ├── ffmpeg.exe             # Bundled FFmpeg binary (Windows)
│   │   ├── ffprobe.exe            # Bundled FFprobe binary (Windows)
│   │   ├── models/                # Persisted ML model files (*.pkl)
│   │   ├── external_api_server/   # Optional Groq Whisper transcription server
│   │   │   ├── app.py             # Runs on port 5000
│   │   │   └── requirements.txt
│   │   └── ...                    # Analysis pipeline modules
│   ├── frontend/                  # Vanilla JS SPA
│   │   ├── index.html
│   │   ├── style.css              # Dark glassmorphism design
│   │   └── script.js              # UI logic, chart rendering, API calls
│   ├── README.md                  # Full technical documentation
│   └── SETUP.md                   # Setup guide (this repo references it)
│
├── video-pipeline/                # Standalone video processing module / prototype
├── videoapi/                      # Standalone API module / prototype
│
├── testlocal.py                   # Local integration testing script
├── .gitignore
└── README.md                      # Root README (this file's source)
```

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Backend Framework** | FastAPI (Python) | REST API, async request handling, WebSocket support |
| **Audio Analysis** | librosa | Pace detection, energy extraction, spectral features |
| **Video Processing** | OpenCV, FFmpeg | Frame extraction, visual energy scoring, scene detection |
| **Emotion Detection** | DeepFace | Per-frame facial emotion classification |
| **Object Detection** | YOLOv8 | Visual content detection for engagement signals |
| **LLM Coaching** | Groq (Llama 3.3 70B) | Retention coaching, script doctor, chat interface |
| **Transcription** | Groq Whisper (optional) | Speech-to-text for transcript and script analysis |
| **Multimodal AI** | LLaVA 7B via Ollama (optional) | Frame-level visual critique |
| **ML Engine** | scikit-learn | Drop zone prediction, niche classification, score prediction |
| **Database** | SQLite (WAL mode) | Analysis history, ML training data, persistence |
| **Frontend** | Vanilla HTML / CSS / JS | Dark glassmorphism SPA — zero framework dependencies |
| **PDF Export** | Python PDF library | Report generation |

**Language breakdown:** Python 46.7% · JavaScript 26.1% · CSS 16.5% · HTML 10.7%

---

## Getting Started

### Prerequisites

- Python 3.10 or higher
- FFmpeg — pre-bundled as `ffmpeg.exe` / `ffprobe.exe` in `RGIT/backend/` (Windows). Linux/macOS users should install via package manager.
- A [Groq API key](https://console.groq.com) for LLM features (optional but recommended)

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/Pra1hamCodes/HOOK_ANALYZER.git
cd HOOK_ANALYZER

# 2. Navigate to the backend
cd RGIT/backend

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Start the server
python main.py

# 5. Open in your browser
# http://localhost:8000
```

That's it. No Docker, no Redis, no Celery. Everything runs in a single process.

### Linux / macOS — FFmpeg

```bash
# macOS (Homebrew)
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg
```

---

## Environment Configuration

Create or edit `RGIT/backend/.env`:

```env
# ── Required for LLM features ──────────────────────────────
# Groq API key (powers Llama 3.3 70B coaching + Whisper transcription)
GEMINI_API_KEY=your_groq_api_key_here

# ── Optional: External transcription server ─────────────────
EXTERNAL_API_URL=https://your-server-url

# ── Optional: Multimodal visual AI (LLaVA via Ollama) ───────
MULTIMODAL_LLM_ENABLED=true
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llava:7b

# ── Optional: Port configuration ────────────────────────────
PORT=8000
```

**Without `GEMINI_API_KEY`:** All LLM-powered features (coaching, script doctor, chat) automatically fall back to rule-based analysis. The platform is still fully functional — heatmaps, emotion arcs, drop zone predictions, and hook grading all work without an API key.

---

## Optional Features

### Enhanced Transcription (Groq Whisper via External API)

The external API server provides Groq Whisper transcription with 2-second window video analysis for higher-quality speech-to-text.

```bash
cd RGIT/backend/external_api_server
pip install -r requirements.txt
python app.py
# Runs on port 5000
```

Then set `EXTERNAL_API_URL=http://localhost:5000` in your `.env`.

This is **optional** — the system works without it using local transcription.

### Multimodal Visual AI (LLaVA via Ollama)

LLaVA analyses individual video frames to provide visual engagement critiques. When enabled, it examines:

- **Hook frames** (t = 0s, 1s, 2s) — first visual impression, identified weaknesses, suggested fixes
- **Red zone frames** — what the viewer sees at drop-off moments and exactly why it causes disengagement

Adds a "Visual AI" badge to the analysis dashboard with frame-level critique cards.

**Setup:**

```bash
# 1. Install Ollama
# https://ollama.com/download

# 2. Pull the LLaVA model (~4GB)
ollama pull llava:7b

# 3. Verify Ollama is running
curl http://localhost:11434/api/tags

# 4. Enable in .env (already set by default)
MULTIMODAL_LLM_ENABLED=true
```

If Ollama is not running, the system silently disables multimodal and proceeds with standard analysis — no errors, no crashes.

---

## ML Engine

The ML engine is **self-training** and requires zero manual configuration. It trains automatically from your own analysis data.

### Four Sub-Models

| Model | Purpose | Activates After |
|---|---|---|
| **Drop Zone Predictor** | Predicts which seconds are high drop-off risk before viewers watch | 2+ videos |
| **Niche Classifier** | Identifies the content niche/category based on audio-visual features | 2+ videos |
| **Early Score Predictor** | Estimates retention score from the first 3 seconds alone | 5+ videos |
| **User Weight Learner** | Personalises predictions based on your individual upload patterns | 5+ videos |

### How It Works

- Models are trained incrementally each time you analyse a new video
- Trained models are saved to `RGIT/backend/models/*.pkl` and persist across server restarts
- Predictions improve with each upload — the more you use it, the smarter it gets
- At 5+ analysed videos, predictions become statistically reliable

---

## API Reference

The FastAPI backend auto-generates interactive API docs. With the server running, visit:

- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

### Key Endpoints (Overview)

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/upload` | Upload a video for analysis |
| `GET` | `/analysis/{id}` | Retrieve a completed analysis result |
| `GET` | `/history` | List all past analyses |
| `POST` | `/chat` | Send a follow-up question to the AI coach |
| `GET` | `/report/{id}/pdf` | Download the PDF report for an analysis |
| `GET` | `/health` | Server health check |

> Full endpoint documentation with request/response schemas is available at `/docs` when the server is running.

---

## Troubleshooting

| Issue | Fix |
|---|---|
| `ffmpeg not found` | On Windows, ensure `ffmpeg.exe` and `ffprobe.exe` are in `RGIT/backend/`. On Linux/macOS, install via `apt` or `brew`. |
| `No module named 'librosa'` | Run `pip install -r requirements.txt` from `RGIT/backend/` |
| LLM features not working | Check that `GEMINI_API_KEY` is correctly set in `RGIT/backend/.env` |
| Multimodal analysis disabled at startup | Install Ollama and run `ollama pull llava:7b`, then verify with `curl http://localhost:11434/api/tags` |
| `Port 8000 already in use` | Set `PORT=8001` (or any free port) in `.env`, or kill the existing process with `lsof -ti:8000 \| xargs kill` |
| DeepFace slow on first run | DeepFace downloads model weights on first use (~500MB). This is a one-time download. |
| ML predictions not appearing | You need at least 2 analysed videos before the ML engine starts producing predictions |

---

## Contributing

Contributions are welcome! This is an ambitious solo project and there are many directions to take it.

```bash
# 1. Fork the repository on GitHub

# 2. Clone your fork
git clone https://github.com/YOUR_USERNAME/HOOK_ANALYZER.git

# 3. Create a feature branch
git checkout -b feature/your-feature-name

# 4. Make your changes and commit
git commit -m "feat: add your feature description"

# 5. Push and open a Pull Request
git push origin feature/your-feature-name
```

### Ideas for Contributions

- **Platform adapters** — pull videos directly from TikTok/YouTube URLs instead of manual upload
- **Batch analysis** — analyse multiple videos and compare them side by side
- **Benchmark datasets** — train the ML engine on public retention data rather than only personal uploads
- **Windows installer** — package the app as a standalone `.exe` with bundled Python
- **Dark/light theme toggle** — the current UI is dark glassmorphism only
- **Export formats** — JSON export of raw analysis data for use in other tools

---

## License

No license file is currently included in this repository. All rights are retained by the author. If you intend to use, fork, or distribute this project, please reach out to the repository owner.

---

## 👤 Author

**Pra1hamCodes**
GitHub: [@Pra1hamCodes](https://github.com/Pra1hamCodes)
Live Demo: [hookanalyzer-six.vercel.app](https://hookanalyzer-six.vercel.app)

---

> *Built with FastAPI, Groq, DeepFace, YOLOv8, librosa, scikit-learn, and Vanilla JS — no cloud infrastructure, no Docker, just Python and a browser.*
