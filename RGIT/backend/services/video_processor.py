"""Video processing utilities – FFmpeg wrappers for audio & frame extraction."""
from __future__ import annotations

import json
import subprocess
import shutil
import os
from pathlib import Path

from core.config import AUDIO_DIR, FRAMES_DIR, ANALYSIS_FPS


def _ffmpeg_bin() -> str:
    """Return local ffmpeg binary path."""
    return str(Path(__file__).resolve().parent.parent / "ffmpeg.exe")

def _ffprobe_bin() -> str:
    """Return local ffprobe binary path."""
    return str(Path(__file__).resolve().parent.parent / "ffprobe.exe")


def get_video_info(video_path: str | Path) -> dict:
    """Extract duration, resolution, fps from a video file."""
    cmd = [
        _ffprobe_bin(),
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(video_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)

    video_stream = next(
        (s for s in data.get("streams", []) if s["codec_type"] == "video"), {}
    )

    duration = float(data.get("format", {}).get("duration", 0))
    width = int(video_stream.get("width", 0))
    height = int(video_stream.get("height", 0))

    # Parse fps from r_frame_rate like "30/1"
    fps_str = video_stream.get("r_frame_rate", "30/1")
    parts = fps_str.split("/")
    fps = float(parts[0]) / float(parts[1]) if len(parts) == 2 else 30.0
    has_audio = any(s.get("codec_type") == "audio" for s in data.get("streams", []))

    return {
        "duration": duration,
        "resolution": f"{width}x{height}",
        "fps": fps,
        "has_audio": has_audio,
    }


def extract_audio(video_path: str | Path, job_id: str) -> Path:
    """Extract audio as mono 22050Hz WAV for librosa processing."""
    output_path = AUDIO_DIR / f"{job_id}.wav"
    cmd = [
        _ffmpeg_bin(),
        "-i", str(video_path),
        "-vn",                      # no video
        "-acodec", "pcm_s16le",     # 16-bit PCM
        "-ar", "22050",             # 22.05 kHz (librosa default)
        "-ac", "1",                 # mono
        "-y",                       # overwrite
        str(output_path),
    ]
    try:
        subprocess.run(cmd, capture_output=True, check=True)
    except subprocess.CalledProcessError:
        pass # Allow missing audio streams to return the expected path for librosa to fallback naturally
    return output_path


def extract_frames(video_path: str | Path, job_id: str) -> Path:
    """Extract frames at ANALYSIS_FPS rate as JPEG images."""
    output_dir = FRAMES_DIR / job_id
    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        _ffmpeg_bin(),
        "-i", str(video_path),
        "-vf", f"fps={ANALYSIS_FPS}",
        "-q:v", "2",               # high quality JPEG
        "-y",
        str(output_dir / "frame_%05d.jpg"),
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return output_dir
