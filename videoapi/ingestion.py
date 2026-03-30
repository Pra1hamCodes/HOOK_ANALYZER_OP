import ffmpeg
import tempfile
import os
import re
from pathlib import Path

MAX_DURATION = 90  # seconds
SCENE_THRESHOLD = 0.4  # 0–1, higher = fewer cuts detected
BURST_WINDOW = 0.5  # seconds before/after each cut for the 5fps burst


# ─── helpers ──────────────────────────────────────────────────────────────────

def get_duration(input_path: str) -> float:
    """Read video duration using ffprobe."""
    probe = ffmpeg.probe(input_path)
    video_stream = next(
        (s for s in probe['streams'] if s['codec_type'] == 'video'), None
    )
    if video_stream is None:
        raise ValueError('No video stream found in file')
    return float(probe['format']['duration'])


def detect_cut_timestamps(input_path: str) -> list[float]:
    """
    Run scene detection via ffmpeg showinfo filter.
    Returns a list of timestamps (in seconds) where cuts occur.
    """
    out, err = (
        ffmpeg
        .input(input_path)
        .video
        .filter('select', f'gt(scene,{SCENE_THRESHOLD})')
        .filter('showinfo')
        .output('pipe:', format='null', vsync='vfr')
        .run(capture_stdout=True, capture_stderr=True, quiet=True)
    )

    # showinfo writes to stderr: parse "pts_time:<timestamp>"
    timestamps = []
    for match in re.finditer(r'pts_time:([\d.]+)', err.decode('utf-8', errors='ignore')):
        timestamps.append(float(match.group(1)))

    return timestamps


# ─── extraction steps ─────────────────────────────────────────────────────────

def extract_audio(input_path: str, output_dir: str) -> str:
    """
    Extract WAV audio at 16kHz mono.
    Returns the path to the output .wav file.
    """
    out_path = os.path.join(output_dir, 'audio.wav')

    (
        ffmpeg
        .input(input_path)
        .audio
        .output(
            out_path,
            ar=16000,   # 16kHz sample rate
            ac=1,        # mono
            format='wav'
        )
        .overwrite_output()
        .run(quiet=True)
    )

    return out_path


def extract_frames_1fps(input_path: str, output_dir: str) -> list[str]:
    """
    Extract one frame per second across the full video.
    Returns a list of saved frame paths.
    """
    frames_dir = os.path.join(output_dir, 'frames_1fps')
    os.makedirs(frames_dir, exist_ok=True)

    out_pattern = os.path.join(frames_dir, 'frame_%04d.jpg')

    (
        ffmpeg
        .input(input_path)
        .video
        .filter('fps', fps=1)
        .output(out_pattern, qscale_v=2)
        .overwrite_output()
        .run(quiet=True)
    )

    return sorted(Path(frames_dir).glob('*.jpg'))


def extract_burst_around_cut(
    input_path: str,
    output_dir: str,
    timestamp: float,
    duration: float
) -> list[str]:
    """
    Extract frames at 5fps for a short window around a detected cut.
    Clamps start/end to valid video range.
    """
    start = max(0.0, timestamp - BURST_WINDOW)
    end   = min(duration, timestamp + BURST_WINDOW)
    window = end - start

    if window <= 0:
        return []

    burst_dir = os.path.join(output_dir, f'burst_{timestamp:.2f}')
    os.makedirs(burst_dir, exist_ok=True)

    out_pattern = os.path.join(burst_dir, 'frame_%02d.jpg')

    (
        ffmpeg
        .input(input_path, ss=start, t=window)
        .video
        .filter('fps', fps=5)
        .output(out_pattern, qscale_v=2)
        .overwrite_output()
        .run(quiet=True)
    )

    return sorted(Path(burst_dir).glob('*.jpg'))


# ─── main entry point ─────────────────────────────────────────────────────────

def ingest_video(input_path: str) -> dict:
    """
    Full ingestion pipeline:
      1. Validate duration
      2. Extract WAV 16kHz mono
      3. Extract frames at 1fps
      4. Detect scene cuts → 5fps burst around each cut

    Returns a summary dict with all output paths.
    """
    # Step 1 — duration gate
    duration = get_duration(input_path)
    if duration > MAX_DURATION:
        raise ValueError(f'Video is {duration:.1f}s — maximum allowed is {MAX_DURATION}s')

    output_dir = tempfile.mkdtemp(prefix='ingest_')

    # Step 2 — audio
    audio_path = extract_audio(input_path, output_dir)

    # Step 3 — 1fps baseline frames
    baseline_frames = extract_frames_1fps(input_path, output_dir)

    # Step 4 — scene detection + burst frames
    cut_timestamps = detect_cut_timestamps(input_path)

    burst_frames = {}
    for ts in cut_timestamps:
        frames = extract_burst_around_cut(input_path, output_dir, ts, duration)
        burst_frames[f'{ts:.2f}s'] = [str(f) for f in frames]

    return {
        'output_dir':      output_dir,
        'duration_s':      round(duration, 2),
        'audio':           audio_path,
        'baseline_frames': [str(f) for f in baseline_frames],
        'cuts_detected':   len(cut_timestamps),
        'cut_timestamps':  [round(t, 2) for t in cut_timestamps],
        'burst_frames':    burst_frames,
    }