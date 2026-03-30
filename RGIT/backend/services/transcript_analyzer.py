"""Semantic Transcript Intelligence — local ASR and NLP parsing."""
from __future__ import annotations

import os
import speech_recognition as sr
from textblob import TextBlob
from pathlib import Path


def analyze_transcript(audio_path: str) -> dict:
    """
    1. Runs ASR (Speech-to-Text) using an offline/free engine.
    2. Runs Linguistic Summarization (sentiment, subjective vs objective).
    3. Extracts High-Impact Keywords.
    4. Generates Transcription Score.
    """
    recognizer = sr.Recognizer()
    
    # We must ensure audio is proper wav format for SpeechRecognition
    transcript = ""
    try:
        with sr.AudioFile(audio_path) as source:
            # For large files, we should theoretically chunk, but for short-form video, full record is okay.
            audio_data = recognizer.record(source)
            # Use Google's free public STT (no API key required). 
            # Note: Requires internet. If it fails, fallback to empty.
            transcript = recognizer.recognize_google(audio_data)
    except Exception as e:
        print(f"ASR Warning: {e}")
        transcript = ""

    if not transcript.strip():
        return {
            "transcript": "",
            "sentiment_polarity": 0.0,
            "subjectivity": 0.0,
            "keywords": [],
            "transcription_score": 0.0,
            "narrative_summary": "No speech detected (Instrumental/Silent or ASR failed).",
        }

    # NLP Analysis using TextBlob
    blob = TextBlob(transcript)
    
    # Polarity: -1.0 (Negative) to 1.0 (Positive)
    polarity = float(blob.sentiment.polarity)
    
    # Subjectivity: 0.0 (Objective/Educational) to 1.0 (Subjective/Opinion/Hype)
    subjectivity = float(blob.sentiment.subjectivity)

    # Simple Keyword Harvesting (Noun Phrases)
    # We filter out very short junk phrases
    raw_phrases = blob.noun_phrases
    keywords = list(set([phrase.lower() for phrase in raw_phrases if len(phrase) > 3]))[:10]

    # Transcription Score (Reflects clarity, speech density, and emotional weight)
    # We reward positive momentum and highly objective (educational) OR highly subjective (hype) content.
    # Words per second proxy (assuming short video is ~60s max)
    word_count = len(transcript.split())
    
    # Base score on speech density (too low = boring dropoff, too high = rambling)
    density_score = min(100.0, word_count * 1.5) if word_count < 150 else max(50.0, 100.0 - (word_count - 150) * 0.5)
    
    # Engagement multiplier (highly polarized or highly opinionated content holds attention better than neutral mush)
    engagement_multiplier = 1.0 + (abs(polarity) * 0.3) + (subjectivity * 0.2)
    
    transcription_score = min(100.0, density_score * engagement_multiplier)

    # Automated Linguistic Summarization
    vibe = "neutral"
    if polarity > 0.3:
        vibe = "positive/uplifting"
    elif polarity < -0.3:
        vibe = "critical/negative"
        
    nature = "educational" if subjectivity < 0.4 else "storytelling/hype"
    keywords_str = ', '.join(keywords[:5]) if keywords else 'general topics'
    
    text_meaning = (
        f"The speaker primarily discusses {keywords_str}. "
        f"The underlying tone leans {vibe} with a sentiment polarity of {polarity:.2f}. "
        f"The structure is highly {nature}, tailored for audience engagement through "
        f"{'factual documentary authority' if subjectivity < 0.4 else 'emotional storytelling and hype'}."
    )

    return {
        "transcript": transcript,
        "sentiment_polarity": round(polarity, 2),
        "subjectivity": round(subjectivity, 2),
        "keywords": keywords,
        "transcription_score": round(transcription_score, 1),
        "narrative_summary": text_meaning,
    }
