import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
PROCESSED_DIR = BASE_DIR / "processed"
FRAMES_DIR = PROCESSED_DIR / "frames"
AUDIO_DIR = PROCESSED_DIR / "audio"
DATA_DIR = BASE_DIR / "data"
DATABASE_PATH = DATA_DIR / "hook_architect.db"

# Create directories
for d in [UPLOAD_DIR, PROCESSED_DIR, FRAMES_DIR, AUDIO_DIR, DATA_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Server
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

# Processing
MAX_VIDEO_DURATION = 120  # seconds
ANALYSIS_FPS = 5  # frames per second for visual analysis
AUDIO_CHUNK_DURATION = 1.0  # seconds per analysis window

# Scoring weights (Cross-Modal Fusion) — global defaults (used when no profile is active)
AUDIO_WEIGHT = 0.35  
VISUAL_WEIGHT = 0.25  
OBJECT_RICHNESS_WEIGHT = 0.10
TRANSCRIPT_WEIGHT = 0.30
SONG_WEIGHT = 0.30
TEMPORAL_WEIGHT = 0.20  
ENGAGEMENT_WEIGHT = 0.15

# Zone thresholds
GREEN_THRESHOLD = 75
YELLOW_THRESHOLD = 45

# Gemini API (Feature 7 — Script Doctor)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# External Video Analysis API (Phase 3)
EXTERNAL_API_URL = os.getenv("EXTERNAL_API_URL", "https://4hfvh1dh-5000.inc1.devtunnels.ms")
