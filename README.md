# 🎬 Hook Architect

AI-Powered Video Retention Intelligence Platform for short-form content creators.

**Upload a video → Get a complete retention analysis** with per-second attention heatmaps, ML-powered predictions, emotion arcs, hook grading, AI coaching, and PDF reports.

## Quick Start

```bash
cd RGIT/backend
pip install -r requirements.txt
python main.py
# Open http://localhost:8000
```

## Documentation

- **[README.md](RGIT/README.md)** — Full project documentation, architecture, API reference
- **[SETUP.md](RGIT/SETUP.md)** — Setup guide with optional features (LLaVA, External API)

## Tech Stack

- **Backend**: FastAPI + Python (librosa, OpenCV, scikit-learn, DeepFace, YOLOv8)
- **Frontend**: Vanilla HTML/CSS/JS (dark glassmorphism SPA)
- **AI**: Groq LLM (Llama 3.3 70B), LLaVA via Ollama (optional)
- **Database**: SQLite (WAL mode)
- **No external infrastructure** — no Redis, no Celery, no Docker required
