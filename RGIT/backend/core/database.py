"""SQLite database layer for Hook Architect — user profiles, video history, weight snapshots, reference baselines."""
from __future__ import annotations

import sqlite3
import json
import uuid
import time
from pathlib import Path
from contextlib import contextmanager
from typing import Any

from core.config import DATABASE_PATH


def _dict_factory(cursor: sqlite3.Cursor, row: tuple) -> dict:
    """Return rows as dicts instead of tuples."""
    return {col[0]: row[i] for i, col in enumerate(cursor.description)}


@contextmanager
def get_db():
    """Context manager for database connections."""
    conn = sqlite3.connect(str(DATABASE_PATH), timeout=10)
    conn.row_factory = _dict_factory
    conn.execute("PRAGMA journal_mode=WAL")  # better concurrency
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Create tables if they don't exist."""
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS user_profiles (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                niche TEXT NOT NULL DEFAULT 'vlog',
                created_at REAL NOT NULL,
                video_count INTEGER NOT NULL DEFAULT 0,
                
                /* Fusion weights */
                audio_weight REAL NOT NULL DEFAULT 0.35,
                visual_weight REAL NOT NULL DEFAULT 0.30,
                transcript_weight REAL NOT NULL DEFAULT 0.30,
                song_weight REAL NOT NULL DEFAULT 0.30,
                temporal_weight REAL NOT NULL DEFAULT 0.20,
                engagement_weight REAL NOT NULL DEFAULT 0.15,
                
                /* Zone thresholds */
                green_threshold REAL NOT NULL DEFAULT 75.0,
                yellow_threshold REAL NOT NULL DEFAULT 45.0,
                
                /* Niche-specific rewards (additive bonuses in engagement calc) */
                slow_pacing_reward REAL NOT NULL DEFAULT 0.0,
                high_energy_reward REAL NOT NULL DEFAULT 0.0
            );

            CREATE TABLE IF NOT EXISTS video_history (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                uploaded_at REAL NOT NULL,
                duration REAL NOT NULL DEFAULT 0.0,
                overall_score REAL NOT NULL DEFAULT 0.0,
                audio_avg REAL NOT NULL DEFAULT 0.0,
                visual_avg REAL NOT NULL DEFAULT 0.0,
                transcript_score REAL NOT NULL DEFAULT 0.0,
                emotion_alignment REAL NOT NULL DEFAULT 0.0,
                dominant_emotion TEXT NOT NULL DEFAULT 'neutral',
                video_nature TEXT NOT NULL DEFAULT 'general',
                zone_distribution TEXT NOT NULL DEFAULT '{}',
                niche_qualification TEXT NOT NULL DEFAULT '',
                weights_snapshot_json TEXT NOT NULL DEFAULT '{}',
                semantic_summary_json TEXT NOT NULL DEFAULT '{}',
                FOREIGN KEY (user_id) REFERENCES user_profiles(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS weight_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                snapshot_at REAL NOT NULL,
                trigger TEXT NOT NULL DEFAULT 'initial',
                weights TEXT NOT NULL DEFAULT '{}',
                FOREIGN KEY (user_id) REFERENCES user_profiles(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS reference_videos (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                uploaded_at REAL NOT NULL,
                filename TEXT NOT NULL DEFAULT '',
                avg_bpm REAL NOT NULL DEFAULT 80.0,
                avg_energy REAL NOT NULL DEFAULT 50.0,
                avg_pacing REAL NOT NULL DEFAULT 50.0,
                avg_motion REAL NOT NULL DEFAULT 50.0,
                avg_sentiment REAL NOT NULL DEFAULT 0.0,
                avg_emotion_alignment REAL NOT NULL DEFAULT 50.0,
                dominant_emotion TEXT NOT NULL DEFAULT 'neutral',
                video_nature TEXT NOT NULL DEFAULT 'general',
                narrative_style TEXT NOT NULL DEFAULT 'mixed',
                visual_style TEXT NOT NULL DEFAULT 'mixed',
                narrative_blueprint TEXT NOT NULL DEFAULT '',
                overall_score REAL NOT NULL DEFAULT 0.0,
                FOREIGN KEY (user_id) REFERENCES user_profiles(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS reference_baselines (
                id TEXT PRIMARY KEY,
                user_id TEXT UNIQUE NOT NULL,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                video_count INTEGER NOT NULL DEFAULT 0,
                avg_bpm REAL NOT NULL DEFAULT 80.0,
                avg_energy REAL NOT NULL DEFAULT 50.0,
                avg_pacing REAL NOT NULL DEFAULT 50.0,
                avg_motion REAL NOT NULL DEFAULT 50.0,
                avg_sentiment REAL NOT NULL DEFAULT 0.0,
                avg_emotion_alignment REAL NOT NULL DEFAULT 50.0,
                avg_overall_score REAL NOT NULL DEFAULT 0.0,
                dominant_narrative_style TEXT NOT NULL DEFAULT 'mixed',
                dominant_visual_style TEXT NOT NULL DEFAULT 'mixed',
                narrative_blueprint TEXT NOT NULL DEFAULT '',
                FOREIGN KEY (user_id) REFERENCES user_profiles(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_video_history_user ON video_history(user_id);
            CREATE INDEX IF NOT EXISTS idx_weight_snapshots_user ON weight_snapshots(user_id);
            CREATE INDEX IF NOT EXISTS idx_reference_videos_user ON reference_videos(user_id);

            CREATE TABLE IF NOT EXISTS shared_reports (
                share_id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL,
                user_id TEXT NOT NULL DEFAULT '',
                created_at REAL NOT NULL,
                expires_at REAL NOT NULL,
                result_snapshot_json TEXT NOT NULL DEFAULT '{}'
            );

            CREATE INDEX IF NOT EXISTS idx_shared_reports_job ON shared_reports(job_id);
        """)

        # Migrate existing video_history table — add new columns if missing
        _migrate_video_history(conn)


def _migrate_video_history(conn: sqlite3.Connection):
    """Add new columns to video_history if they don't exist (safe migration)."""
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(video_history)").fetchall()}
    migrations = {
        "niche_qualification": "ALTER TABLE video_history ADD COLUMN niche_qualification TEXT NOT NULL DEFAULT ''",
        "weights_snapshot_json": "ALTER TABLE video_history ADD COLUMN weights_snapshot_json TEXT NOT NULL DEFAULT '{}'",
        "semantic_summary_json": "ALTER TABLE video_history ADD COLUMN semantic_summary_json TEXT NOT NULL DEFAULT '{}'",
    }
    for col, sql in migrations.items():
        if col not in existing:
            try:
                conn.execute(sql)
            except sqlite3.OperationalError:
                pass


# ═══════════════════════════════════════════════════════════
# USER PROFILE CRUD
# ═══════════════════════════════════════════════════════════

def create_profile(username: str, niche: str, weights: dict) -> dict:
    """Create a new user profile with initial weights from a persona preset."""
    profile_id = str(uuid.uuid4())
    now = time.time()

    with get_db() as conn:
        conn.execute(
            """INSERT INTO user_profiles 
               (id, username, niche, created_at, 
                audio_weight, visual_weight, transcript_weight, song_weight,
                temporal_weight, engagement_weight,
                green_threshold, yellow_threshold,
                slow_pacing_reward, high_energy_reward)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                profile_id, username.strip(), niche, now,
                weights.get("audio_weight", 0.35),
                weights.get("visual_weight", 0.30),
                weights.get("transcript_weight", 0.30),
                weights.get("song_weight", 0.30),
                weights.get("temporal_weight", 0.20),
                weights.get("engagement_weight", 0.15),
                weights.get("green_threshold", 75.0),
                weights.get("yellow_threshold", 45.0),
                weights.get("slow_pacing_reward", 0.0),
                weights.get("high_energy_reward", 0.0),
            ),
        )
        # Save initial weight snapshot
        _save_snapshot(conn, profile_id, "initial", weights)

    return get_profile(profile_id)


def get_profile(profile_id: str) -> dict | None:
    """Fetch a single profile by ID."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM user_profiles WHERE id = ?", (profile_id,)
        ).fetchone()
    return row


def get_profile_by_username(username: str) -> dict | None:
    """Fetch a profile by username."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM user_profiles WHERE username = ?", (username.strip(),)
        ).fetchone()
    return row


def list_profiles() -> list[dict]:
    """Return all profiles, newest first."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM user_profiles ORDER BY created_at DESC"
        ).fetchall()
    return rows


def delete_profile(profile_id: str) -> bool:
    """Delete a profile and cascade to history/snapshots."""
    with get_db() as conn:
        cursor = conn.execute(
            "DELETE FROM user_profiles WHERE id = ?", (profile_id,)
        )
    return cursor.rowcount > 0


def update_profile_weights(profile_id: str, weights: dict, trigger: str = "manual") -> dict | None:
    """Update a profile's weights and save a snapshot."""
    fields = []
    values = []
    allowed = {
        "audio_weight", "visual_weight", "transcript_weight", "song_weight",
        "temporal_weight", "engagement_weight",
        "green_threshold", "yellow_threshold",
        "slow_pacing_reward", "high_energy_reward",
    }
    for key, val in weights.items():
        if key in allowed:
            fields.append(f"{key} = ?")
            values.append(float(val))

    if not fields:
        return get_profile(profile_id)

    values.append(profile_id)

    with get_db() as conn:
        conn.execute(
            f"UPDATE user_profiles SET {', '.join(fields)} WHERE id = ?",
            values,
        )
        _save_snapshot(conn, profile_id, trigger, weights)

    return get_profile(profile_id)


def increment_video_count(profile_id: str):
    """Increment the video_count field by 1."""
    with get_db() as conn:
        conn.execute(
            "UPDATE user_profiles SET video_count = video_count + 1 WHERE id = ?",
            (profile_id,),
        )


def extract_weights_from_profile(profile: dict) -> dict:
    """Pull the weight fields out of a profile row into a clean dict."""
    return {
        "audio_weight": profile["audio_weight"],
        "visual_weight": profile["visual_weight"],
        "transcript_weight": profile["transcript_weight"],
        "song_weight": profile["song_weight"],
        "temporal_weight": profile["temporal_weight"],
        "engagement_weight": profile["engagement_weight"],
        "green_threshold": profile["green_threshold"],
        "yellow_threshold": profile["yellow_threshold"],
        "slow_pacing_reward": profile["slow_pacing_reward"],
        "high_energy_reward": profile["high_energy_reward"],
    }


# ═══════════════════════════════════════════════════════════
# VIDEO HISTORY
# ═══════════════════════════════════════════════════════════

def record_video(user_id: str, data: dict) -> str:
    """Insert a video analysis record. Returns the record ID."""
    record_id = str(uuid.uuid4())
    now = time.time()

    with get_db() as conn:
        conn.execute(
            """INSERT INTO video_history
               (id, user_id, filename, uploaded_at, duration,
                overall_score, audio_avg, visual_avg,
                transcript_score, emotion_alignment,
                dominant_emotion, video_nature, zone_distribution,
                niche_qualification, weights_snapshot_json, semantic_summary_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                record_id, user_id,
                data.get("filename", "unknown"),
                now,
                data.get("duration", 0.0),
                data.get("overall_score", 0.0),
                data.get("audio_avg", 0.0),
                data.get("visual_avg", 0.0),
                data.get("transcript_score", 0.0),
                data.get("emotion_alignment", 0.0),
                data.get("dominant_emotion", "neutral"),
                data.get("video_nature", "general"),
                json.dumps(data.get("zone_distribution", {})),
                data.get("niche_qualification", ""),
                json.dumps(data.get("weights_snapshot", {})),
                json.dumps(data.get("semantic_summary", {})),
            ),
        )
    return record_id


def get_video_history(user_id: str, limit: int = 50) -> list[dict]:
    """Fetch video history for a user, newest first."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM video_history WHERE user_id = ? ORDER BY uploaded_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    # Parse JSON fields
    for row in rows:
        try:
            row["zone_distribution"] = json.loads(row["zone_distribution"])
        except (json.JSONDecodeError, TypeError):
            row["zone_distribution"] = {}
        try:
            row["weights_snapshot"] = json.loads(row.get("weights_snapshot_json", "{}"))
        except (json.JSONDecodeError, TypeError):
            row["weights_snapshot"] = {}
        try:
            row["semantic_summary"] = json.loads(row.get("semantic_summary_json", "{}"))
        except (json.JSONDecodeError, TypeError):
            row["semantic_summary"] = {}
    return rows


def get_ledger_history(user_id: str, limit: int = 50) -> list[dict]:
    """Fetch enriched history with weight deltas for the Evolution Ledger."""
    videos = get_video_history(user_id, limit)
    if not videos:
        return []

    # Calculate weight deltas between consecutive entries (reverse chronological)
    for i, video in enumerate(videos):
        if i < len(videos) - 1:
            prev_weights = videos[i + 1].get("weights_snapshot", {})
            curr_weights = video.get("weights_snapshot", {})
            deltas = {}
            for key in ["audio_weight", "visual_weight", "transcript_weight",
                        "song_weight", "temporal_weight", "engagement_weight"]:
                old_val = prev_weights.get(key, 0)
                new_val = curr_weights.get(key, 0)
                if old_val and new_val and abs(new_val - old_val) > 0.0001:
                    diff = (new_val - old_val) * 100  # as percentage points
                    deltas[key] = round(diff, 2)
            video["weight_deltas"] = deltas
        else:
            video["weight_deltas"] = {}

    return videos


# ═══════════════════════════════════════════════════════════
# WEIGHT SNAPSHOTS
# ═══════════════════════════════════════════════════════════

def _save_snapshot(conn: sqlite3.Connection, user_id: str, trigger: str, weights: dict):
    """Internal: save a weight snapshot (called within an existing transaction)."""
    conn.execute(
        "INSERT INTO weight_snapshots (user_id, snapshot_at, trigger, weights) VALUES (?, ?, ?, ?)",
        (user_id, time.time(), trigger, json.dumps(weights)),
    )


def get_weight_history(user_id: str, limit: int = 20) -> list[dict]:
    """Fetch weight snapshots for a user."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM weight_snapshots WHERE user_id = ? ORDER BY snapshot_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    for row in rows:
        try:
            row["weights"] = json.loads(row["weights"])
        except (json.JSONDecodeError, TypeError):
            row["weights"] = {}
    return rows


# ═══════════════════════════════════════════════════════════
# REFERENCE BASELINES (Feature 4)
# ═══════════════════════════════════════════════════════════

def save_reference_video(user_id: str, data: dict) -> str:
    """Store a single reference video's analysis results."""
    ref_id = str(uuid.uuid4())
    now = time.time()

    with get_db() as conn:
        conn.execute(
            """INSERT INTO reference_videos
               (id, user_id, uploaded_at, filename,
                avg_bpm, avg_energy, avg_pacing, avg_motion,
                avg_sentiment, avg_emotion_alignment,
                dominant_emotion, video_nature,
                narrative_style, visual_style,
                narrative_blueprint, overall_score)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                ref_id, user_id, now,
                data.get("filename", ""),
                data.get("avg_bpm", 80.0),
                data.get("avg_energy", 50.0),
                data.get("avg_pacing", 50.0),
                data.get("avg_motion", 50.0),
                data.get("avg_sentiment", 0.0),
                data.get("avg_emotion_alignment", 50.0),
                data.get("dominant_emotion", "neutral"),
                data.get("video_nature", "general"),
                data.get("narrative_style", "mixed"),
                data.get("visual_style", "mixed"),
                data.get("narrative_blueprint", ""),
                data.get("overall_score", 0.0),
            ),
        )
    return ref_id


def update_reference_baseline(user_id: str, baseline_data: dict):
    """Upsert the aggregated reference baseline for a user."""
    now = time.time()
    baseline_id = str(uuid.uuid4())

    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM reference_baselines WHERE user_id = ?", (user_id,)
        ).fetchone()

        if existing:
            conn.execute(
                """UPDATE reference_baselines SET
                    updated_at = ?, video_count = ?,
                    avg_bpm = ?, avg_energy = ?, avg_pacing = ?, avg_motion = ?,
                    avg_sentiment = ?, avg_emotion_alignment = ?, avg_overall_score = ?,
                    dominant_narrative_style = ?, dominant_visual_style = ?,
                    narrative_blueprint = ?
                   WHERE user_id = ?""",
                (
                    now, baseline_data.get("video_count", 0),
                    baseline_data.get("avg_bpm", 80.0),
                    baseline_data.get("avg_energy", 50.0),
                    baseline_data.get("avg_pacing", 50.0),
                    baseline_data.get("avg_motion", 50.0),
                    baseline_data.get("avg_sentiment", 0.0),
                    baseline_data.get("avg_emotion_alignment", 50.0),
                    baseline_data.get("avg_overall_score", 0.0),
                    baseline_data.get("dominant_narrative_style", "mixed"),
                    baseline_data.get("dominant_visual_style", "mixed"),
                    baseline_data.get("narrative_blueprint", ""),
                    user_id,
                ),
            )
        else:
            conn.execute(
                """INSERT INTO reference_baselines
                   (id, user_id, created_at, updated_at, video_count,
                    avg_bpm, avg_energy, avg_pacing, avg_motion,
                    avg_sentiment, avg_emotion_alignment, avg_overall_score,
                    dominant_narrative_style, dominant_visual_style, narrative_blueprint)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    baseline_id, user_id, now, now,
                    baseline_data.get("video_count", 0),
                    baseline_data.get("avg_bpm", 80.0),
                    baseline_data.get("avg_energy", 50.0),
                    baseline_data.get("avg_pacing", 50.0),
                    baseline_data.get("avg_motion", 50.0),
                    baseline_data.get("avg_sentiment", 0.0),
                    baseline_data.get("avg_emotion_alignment", 50.0),
                    baseline_data.get("avg_overall_score", 0.0),
                    baseline_data.get("dominant_narrative_style", "mixed"),
                    baseline_data.get("dominant_visual_style", "mixed"),
                    baseline_data.get("narrative_blueprint", ""),
                ),
            )


def get_reference_baseline(user_id: str) -> dict | None:
    """Fetch the aggregated reference baseline for a user."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM reference_baselines WHERE user_id = ?", (user_id,)
        ).fetchone()
    return row


def get_reference_videos(user_id: str) -> list[dict]:
    """Fetch individual reference videos for a user."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM reference_videos WHERE user_id = ? ORDER BY uploaded_at DESC",
            (user_id,),
        ).fetchall()
    return rows


def delete_reference_data(user_id: str):
    """Delete all reference videos and baseline for a user."""
    with get_db() as conn:
        conn.execute("DELETE FROM reference_videos WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM reference_baselines WHERE user_id = ?", (user_id,))


# ═══════════════════════════════════════════════════════════
# SHARED REPORTS (Feature 6)
# ═══════════════════════════════════════════════════════════

def create_shared_report(share_id: str, job_id: str, user_id: str, result_json: str, ttl_hours: int = 72) -> dict:
    """Create a shared report entry with an expiration time."""
    now = time.time()
    expires_at = now + (ttl_hours * 3600)

    with get_db() as conn:
        conn.execute(
            """INSERT INTO shared_reports (share_id, job_id, user_id, created_at, expires_at, result_snapshot_json)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (share_id, job_id, user_id, now, expires_at, result_json),
        )
    return {"share_id": share_id, "created_at": now, "expires_at": expires_at}


def get_shared_report(share_id: str) -> dict | None:
    """Fetch a shared report if it exists and hasn't expired."""
    now = time.time()
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM shared_reports WHERE share_id = ? AND expires_at > ?",
            (share_id, now),
        ).fetchone()
    if row:
        try:
            row["result_snapshot"] = json.loads(row.get("result_snapshot_json", "{}"))
        except (json.JSONDecodeError, TypeError):
            row["result_snapshot"] = {}
    return row

