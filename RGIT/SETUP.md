# Hook Architect — Setup Guide

## Prerequisites
- Python 3.10+
- FFmpeg (included in `backend/` as `ffmpeg.exe` + `ffprobe.exe`)

## Quick Start

```bash
cd RGIT/backend
pip install -r requirements.txt
python main.py
# Open http://localhost:8000
```

No Redis, no Celery, no Docker required. Everything runs from a single process.

---

## Environment Configuration

Edit `backend/.env`:

```env
# Required for LLM features (coaching, script doctor, chat)
GEMINI_API_KEY=your_groq_api_key_here

# Optional: External API for Groq Whisper transcription
EXTERNAL_API_URL=https://your-server-url

# Optional: Multimodal visual AI
MULTIMODAL_LLM_ENABLED=true
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llava:7b
```

Without `GEMINI_API_KEY`, LLM features fall back to rule-based suggestions.

---

## Optional: External API (Enhanced Transcription)

The external API provides Groq Whisper transcription + 2s-window video analysis. It's **optional** — the system works without it.

```bash
cd RGIT/backend/external_api_server
pip install -r requirements.txt
python app.py
# Runs on port 5000
```

---

## Optional: Multimodal LLM (LLaVA via Ollama)

The multimodal coach uses LLaVA to analyze individual video frames for visual engagement feedback. This is **optional** — everything works without it.

### One-Time Setup

1. **Install Ollama**: https://ollama.com/download
   Ollama runs as a background service automatically after install.

2. **Pull the LLaVA model**:
   ```bash
   ollama pull llava:7b
   ```

3. **Verify Ollama is running**:
   ```bash
   curl http://localhost:11434/api/tags
   ```
   You should see `llava` in the list of models.

4. **Enable in `.env`** (already configured by default):
   ```
   MULTIMODAL_LLM_ENABLED=true
   OLLAMA_HOST=http://localhost:11434
   OLLAMA_MODEL=llava:7b
   ```

### What It Does

When enabled, LLaVA analyzes:
- **Hook frames** (t=0,1,2) — visual first impression, weakness, fix
- **Red zone frames** — what visually causes viewer drop-off + specific fix
- Adds "Visual AI" badge and frame-level critiques to the analysis results

If Ollama is not running, the system silently disables multimodal and uses standard analysis.

---

## Optional: ML Engine

The ML engine trains **automatically** from your analysis data. No setup required.

- After **2+ videos**, models start making predictions
- After **5+ videos**, predictions become reliable
- Models are saved to `backend/models/*.pkl` and persist across restarts
- 4 sub-models: Drop Zone Predictor, Niche Classifier, Early Score Predictor, User Weight Learner

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `ffmpeg not found` | Ensure `ffmpeg.exe` and `ffprobe.exe` are in `backend/` |
| `No module named 'librosa'` | Run `pip install -r requirements.txt` |
| LLM features don't work | Check `GEMINI_API_KEY` in `.env` |
| Multimodal disabled at startup | Install Ollama and pull `llava:7b` |
| `Port 8000 already in use` | Change `PORT` in `.env` or kill the existing process |
