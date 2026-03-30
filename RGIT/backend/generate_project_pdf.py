"""Generate a comprehensive PDF documenting the entire Hook Architect project."""
import os
import sys

HTML_CONTENT = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Hook Architect — Complete Project Documentation</title>
<style>
    @page { size: A4; margin: 2cm 1.8cm; }
    body { font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; color: #1a1a2e; line-height: 1.7; font-size: 11pt; }
    h1 { color: #8b5cf6; font-size: 26pt; margin-bottom: 4px; border-bottom: 3px solid #8b5cf6; padding-bottom: 10px; }
    h2 { color: #0f172a; font-size: 17pt; margin-top: 30px; padding-bottom: 6px; border-bottom: 2px solid #e2e8f0; page-break-after: avoid; }
    h3 { color: #334155; font-size: 13pt; margin-top: 18px; page-break-after: avoid; }
    h4 { color: #475569; font-size: 11pt; margin-top: 14px; }
    hr { border: none; border-top: 1px solid #e2e8f0; margin: 20px 0; }
    table { width: 100%; border-collapse: collapse; margin: 10px 0; font-size: 10pt; }
    th { background: #f1f5f9; color: #334155; text-align: left; padding: 8px 10px; border: 1px solid #e2e8f0; font-weight: 600; }
    td { padding: 6px 10px; border: 1px solid #e2e8f0; vertical-align: top; }
    tr:nth-child(even) { background: #fafafa; }
    code { background: #f1f5f9; padding: 1px 5px; border-radius: 3px; font-size: 9.5pt; color: #8b5cf6; }
    .badge { display: inline-block; padding: 2px 10px; border-radius: 12px; font-size: 9pt; font-weight: 600; margin: 2px; }
    .section-box { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px 18px; margin: 12px 0; }
    .flow-step { background: linear-gradient(135deg, #f0f4ff, #f8f0ff); border-left: 4px solid #8b5cf6; padding: 10px 14px; margin: 6px 0; border-radius: 0 6px 6px 0; }
    .subtitle { color: #64748b; font-size: 11pt; margin-top: 0; }
    ul { padding-left: 18px; }
    li { margin: 3px 0; }
    .toc a { text-decoration: none; color: #8b5cf6; }
    .toc li { margin: 5px 0; }
    .page-break { page-break-before: always; }
</style>
</head>
<body>

<!-- ═══════ COVER PAGE ═══════ -->
<div style="text-align:center; padding: 80px 0 40px;">
    <div style="font-size: 60pt;">🎬</div>
    <h1 style="border:none; font-size: 32pt; margin-top:10px;">Hook Architect</h1>
    <p style="font-size: 14pt; color: #64748b; margin-top: 0;">AI-Powered Real-Time Video Retention Analysis Engine</p>
    <p style="font-size: 11pt; color: #94a3b8;">Complete Project Documentation &bull; v4.0.0</p>
    <p style="font-size: 10pt; color: #94a3b8; margin-top: 40px;">Generated: March 2026</p>
</div>
<hr>

<!-- ═══════ TABLE OF CONTENTS ═══════ -->
<h2>📋 Table of Contents</h2>
<div class="toc">
<ol>
    <li><a href="#overview">Project Overview</a></li>
    <li><a href="#architecture">System Architecture</a></li>
    <li><a href="#project-structure">Project Structure</a></li>
    <li><a href="#tech-stack">Technology Stack</a></li>
    <li><a href="#pipeline">Analysis Pipeline (12-Step)</a></li>
    <li><a href="#services">Service Modules (19 files)</a></li>
    <li><a href="#ml-engine">ML Predictive Engine</a></li>
    <li><a href="#multimodal">Multimodal Visual AI (LLaVA)</a></li>
    <li><a href="#api-routes">API Routes &amp; Endpoints</a></li>
    <li><a href="#database">Database Schema</a></li>
    <li><a href="#persona">Persona Engine &amp; Presets</a></li>
    <li><a href="#scoring">Scoring &amp; Fusion Formula</a></li>
    <li><a href="#running">How to Run</a></li>
</ol>
</div>

<!-- ═══════ 1. PROJECT OVERVIEW ═══════ -->
<div class="page-break"></div>
<h2 id="overview">1. 🎯 Project Overview</h2>
<div class="section-box">
<p><strong>Hook Architect</strong> is a real-time, AI-powered short-form video analysis engine designed for content creators. It analyzes uploaded videos across <strong>7+ signal dimensions</strong> — audio energy, visual motion, transcript intelligence, emotion tracking, virality scoring, ML prediction, and multimodal visual diagnostics — to produce an actionable retention report.</p>
<p>The system runs as a <strong>single FastAPI process</strong> with no external infrastructure required (no Redis, no Celery, no Docker). Everything is in-memory with SQLite persistence for user profiles and history.</p>
</div>

<h3>Core Capabilities</h3>
<ul>
    <li><strong>Multi-Modal Video Analysis</strong> — Audio, Visual, Transcript, Emotion, Virality analyzed independently then fused</li>
    <li><strong>Per-Second Attention Scoring</strong> — Every second gets a 0-100 attention score with zone classification (Green/Yellow/Red)</li>
    <li><strong>ML Predictive Layer</strong> — 4 scikit-learn sub-models that train incrementally from your own data</li>
    <li><strong>Multimodal Visual AI</strong> — LLaVA via Ollama for frame-level visual diagnostics (optional)</li>
    <li><strong>Hook Strength Scorer</strong> — First 3 seconds graded across 4 axes (transcript, visual, audio, face)</li>
    <li><strong>Retention Curve Prediction</strong> — YouTube-style viewer retention graph simulation</li>
    <li><strong>Emotion Arc Mapping</strong> — Continuous emotional journey tracking with phase detection</li>
    <li><strong>Viral Music Matching</strong> — Audio-Sync Compatibility Index with trending song database</li>
    <li><strong>AI Script Doctor</strong> — LLM-powered content rewriting for low-engagement zones</li>
    <li><strong>Adaptive Feedback Loop</strong> — EMA-based weight adjustment that learns from each upload</li>
    <li><strong>Reference Induction</strong> — Upload reference videos to create your quality baseline</li>
    <li><strong>Evolution Ledger</strong> — Track how your scoring weights evolve over time</li>
    <li><strong>PDF Report Generation</strong> — Full HTML/PDF analysis reports</li>
    <li><strong>Interactive AI Chat</strong> — Ask questions about your analysis report via Groq LLM</li>
</ul>

<!-- ═══════ 2. SYSTEM ARCHITECTURE ═══════ -->
<div class="page-break"></div>
<h2 id="architecture">2. 🏗️ System Architecture</h2>

<h3>High-Level Architecture</h3>
<div class="section-box">
<pre style="font-size:9pt; line-height:1.5;">
┌──────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (SPA)                               │
│  index.html + app.js + style.css                                     │
│  Upload → WebSocket Progress → Interactive Dashboard                 │
│  Charts · Heatmap · Zone Cards · ML Badge · Visual AI · AI Chat      │
└──────────────────────────┬───────────────────────────────────────────┘
                           │ HTTP + WebSocket
┌──────────────────────────▼───────────────────────────────────────────┐
│                  FASTAPI BACKEND — main.py (port 8000)               │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │              ANALYSIS PIPELINE (12-step, threaded)               │ │
│  │                                                                   │ │
│  │  video_processor → audio_analyzer → visual_analyzer              │ │
│  │  → transcript_analyzer → emotion_analyzer → external_api        │ │
│  │  → virality_analyzer → semantic_summarizer → fusion_engine      │ │
│  │  → ML Engine → hook_scorer → emotion_arc → retention_curve      │ │
│  │  → Multimodal Coach (LLaVA) → adaptive_engine                   │ │
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
</pre>
</div>

<!-- ═══════ 3. PROJECT STRUCTURE ═══════ -->
<div class="page-break"></div>
<h2 id="project-structure">3. 📁 Project Structure</h2>

<table>
<tr><th>Path</th><th>Purpose</th></tr>
<tr><td colspan="2" style="background:#e8e4f0;font-weight:600;">backend/ — Main Backend Application</td></tr>
<tr><td><code>main.py</code></td><td>FastAPI application — all 20+ API routes, 12-step analysis pipeline, WebSocket handler (1800 lines)</td></tr>
<tr><td><code>.env</code></td><td>Environment variables (API keys, Ollama config)</td></tr>
<tr><td><code>requirements.txt</code></td><td>Python dependencies (21 packages)</td></tr>
<tr><td colspan="2" style="background:#f0f4ff;font-weight:600;">core/ — Configuration & Data Layer</td></tr>
<tr><td><code>core/config.py</code></td><td>Paths, scoring weights, thresholds, API keys</td></tr>
<tr><td><code>core/database.py</code></td><td>SQLite layer — 6 tables, full CRUD, shared reports</td></tr>
<tr><td><code>core/persona_presets.py</code></td><td>7 niche-specific weight presets</td></tr>
<tr><td colspan="2" style="background:#f0f4ff;font-weight:600;">services/ — 19 Analysis Engine Modules</td></tr>
<tr><td><code>video_processor.py</code></td><td>FFmpeg wrappers: extract audio, frames, metadata</td></tr>
<tr><td><code>audio_analyzer.py</code></td><td>Librosa: RMS energy, pitch (pyin), pacing, silence</td></tr>
<tr><td><code>visual_analyzer.py</code></td><td>OpenCV: optical flow, Haar cascade, histogram scene cuts</td></tr>
<tr><td><code>transcript_analyzer.py</code></td><td>SpeechRecognition ASR + TextBlob NLP</td></tr>
<tr><td><code>emotion_analyzer.py</code></td><td>DeepFace facial + acoustic vocal emotion</td></tr>
<tr><td><code>virality_analyzer.py</code></td><td>BPM estimation, trend DB matching, Audio-Sync Index</td></tr>
<tr><td><code>semantic_summarizer.py</code></td><td>Dual-track summarization + Vibe Check</td></tr>
<tr><td><code>fusion_engine.py</code></td><td>Cross-modal attention fusion → zones (with ML blending)</td></tr>
<tr><td><code>hook_scorer.py</code></td><td>First 3s grading: transcript, visual, audio, face axes</td></tr>
<tr><td><code>emotion_arc.py</code></td><td>Emotional journey: phases, transitions, arc shape</td></tr>
<tr><td><code>retention_curve.py</code></td><td>YouTube-style retention simulation</td></tr>
<tr><td><code>ml_engine.py</code></td><td>4 ML sub-models (scikit-learn): prediction + training</td></tr>
<tr><td><code>multimodal_coach.py</code></td><td>LLaVA hook critique + red zone diagnosis</td></tr>
<tr><td><code>drop_fixer.py</code></td><td>Groq LLM script rewriting for red zones</td></tr>
<tr><td><code>llm_coach.py</code></td><td>Per-zone coaching, goal keywords, interactive chat</td></tr>
<tr><td><code>adaptive_engine.py</code></td><td>EMA weight evolution from video history</td></tr>
<tr><td><code>report_generator.py</code></td><td>HTML/PDF report generation</td></tr>
<tr><td><code>external_api.py</code></td><td>HTTP client for optional external API</td></tr>
<tr><td colspan="2" style="background:#f0f4ff;font-weight:600;">models/ — Data Schemas</td></tr>
<tr><td><code>models/schemas.py</code></td><td>Pydantic models: AudioSignal, VisualSignal, Zone, AnalysisResult, etc.</td></tr>
<tr><td colspan="2" style="background:#e8e4f0;font-weight:600;">frontend/ — Web UI</td></tr>
<tr><td><code>index.html</code></td><td>Single-page application</td></tr>
<tr><td><code>static/style.css</code></td><td>Dark glassmorphism design system</td></tr>
<tr><td><code>static/app.js</code></td><td>Full client application with ML/Visual AI components</td></tr>
</table>

<!-- ═══════ 4. TECHNOLOGY STACK ═══════ -->
<h2 id="tech-stack">4. 🛠️ Technology Stack</h2>
<table>
<tr><th>Layer</th><th>Technology</th><th>Purpose</th></tr>
<tr><td>Web Framework</td><td>FastAPI + Uvicorn</td><td>Async HTTP server, WebSocket, static serving</td></tr>
<tr><td>Audio Analysis</td><td>Librosa 0.10.2</td><td>RMS energy, pitch tracking, onset detection</td></tr>
<tr><td>Visual Analysis</td><td>OpenCV 4.9+</td><td>Optical flow, face detection, histograms</td></tr>
<tr><td>Object Detection</td><td>Ultralytics YOLOv8</td><td>Object richness scoring</td></tr>
<tr><td>Face Emotion</td><td>DeepFace</td><td>Facial emotion recognition</td></tr>
<tr><td>Speech-to-Text</td><td>SpeechRecognition + Groq Whisper</td><td>Local STT + cloud Whisper</td></tr>
<tr><td>NLP</td><td>TextBlob</td><td>Sentiment, subjectivity, noun phrases</td></tr>
<tr><td>ML Prediction</td><td>scikit-learn + XGBoost</td><td>4 predictive sub-models</td></tr>
<tr><td>Multimodal AI</td><td>LLaVA via Ollama</td><td>Frame-level visual diagnostics</td></tr>
<tr><td>LLM Coaching</td><td>Groq (Llama 3.3 70B)</td><td>Script rewriting, coaching, chat</td></tr>
<tr><td>Video Processing</td><td>FFmpeg / FFprobe</td><td>Audio/frame extraction, metadata</td></tr>
<tr><td>Database</td><td>SQLite (WAL mode)</td><td>Profiles, history, weight snapshots</td></tr>
<tr><td>PDF Generation</td><td>xhtml2pdf</td><td>HTML to PDF report conversion</td></tr>
</table>

<!-- ═══════ 5. ANALYSIS PIPELINE ═══════ -->
<div class="page-break"></div>
<h2 id="pipeline">5. 🔄 Analysis Pipeline (12-Step)</h2>
<p>When a video is uploaded, <code>run_analysis_pipeline()</code> in <code>main.py</code> executes in a background thread:</p>

<div class="flow-step"><strong>Step 1 (5%)</strong> — <code>get_video_info()</code> → Read video metadata (duration, resolution, FPS)</div>
<div class="flow-step"><strong>Step 2 (10%)</strong> — <code>extract_audio()</code> → FFmpeg extracts mono 22050Hz WAV</div>
<div class="flow-step"><strong>Step 3 (20%)</strong> — <code>extract_frames()</code> → FFmpeg extracts JPEG frames at 5 FPS</div>
<div class="flow-step"><strong>Step 4 (30-50%)</strong> — <code>analyze_audio()</code> → Per-second: energy, pitch, pacing, silence</div>
<div class="flow-step" style="border-left-color: #06b6d4;"><strong>ML (50%)</strong> — <code>EarlyScorePredictor</code> → Audio-only early score estimate</div>
<div class="flow-step"><strong>Step 5 (55-75%)</strong> — <code>analyze_visual()</code> → Per-second: motion, scene cuts, face detection</div>
<div class="flow-step" style="border-left-color: #06b6d4;"><strong>ML (75%)</strong> — <code>EarlyScorePredictor</code> → Audio+visual early score estimate</div>
<div class="flow-step"><strong>Step 5.5 (76%)</strong> — <code>analyze_transcript()</code> → ASR transcription + NLP sentiment</div>
<div class="flow-step"><strong>Step 5.8 (78%)</strong> — <code>analyze_emotions()</code> → DeepFace facial + acoustic vocal emotions</div>
<div class="flow-step"><strong>Step 5.85 (79%)</strong> — External API enrichment (optional) + <code>NicheClassifier</code> override</div>
<div class="flow-step"><strong>Step 5.9 (80%)</strong> — <code>analyze_virality()</code> → Trending audio matching</div>
<div class="flow-step"><strong>Step 5.10 (82%)</strong> — <code>semantic_summarizer()</code> → Dual-track Vibe Check</div>
<div class="flow-step"><strong>Step 6 (85%)</strong> — <code>fuse_signals()</code> → Weighted fusion → zones + <code>DropZonePredictor</code> blending</div>
<div class="flow-step"><strong>Step 6.1-6.3 (88-92%)</strong> — Emotion Arc → Hook Score → Retention Curve</div>
<div class="flow-step" style="border-left-color: #06b6d4;"><strong>Step 6.4 (93%)</strong> — <code>Multimodal Coach</code> → LLaVA hook critique + red zone diagnosis (optional)</div>
<div class="flow-step"><strong>Step 8 (95%)</strong> — <code>adaptive_engine</code> → EMA weight nudging + ML training</div>
<div class="flow-step"><strong>Step 9 (100%)</strong> — Store results → broadcast "complete" via WebSocket</div>

<!-- ═══════ 6. SERVICE MODULES ═══════ -->
<div class="page-break"></div>
<h2 id="services">6. ⚙️ Service Modules</h2>

<table>
<tr><th>Module</th><th>Input</th><th>Output</th></tr>
<tr><td><code>video_processor.py</code></td><td>Video file path</td><td>Metadata, WAV audio, JPEG frames</td></tr>
<tr><td><code>audio_analyzer.py</code></td><td>WAV audio + duration</td><td>Per-second: energy, pitch, pacing, silence, audio_score</td></tr>
<tr><td><code>visual_analyzer.py</code></td><td>Frames dir + duration</td><td>Per-second: motion, scene_cut, face, visual_score</td></tr>
<tr><td><code>transcript_analyzer.py</code></td><td>Audio path</td><td>Transcript, sentiment, keywords, transcription_score</td></tr>
<tr><td><code>emotion_analyzer.py</code></td><td>Frames, audio signals</td><td>Facial/vocal emotions, alignment_score, timeline</td></tr>
<tr><td><code>virality_analyzer.py</code></td><td>Audio signals, emotion</td><td>Sound score, recommended tracks, Audio-Sync Index</td></tr>
<tr><td><code>semantic_summarizer.py</code></td><td>Transcript, signals</td><td>Narrative/visual style, vibe check, reference comparison</td></tr>
<tr><td><code>fusion_engine.py</code></td><td>All signals + weights</td><td>Per-second attention scores + zones (timeline, zones)</td></tr>
<tr><td><code>ml_engine.py</code></td><td>Signal features</td><td>ML zone predictions, niche, early scores, weight suggestions</td></tr>
<tr><td><code>multimodal_coach.py</code></td><td>Video frames, zones</td><td>Hook critique, red zone visual diagnoses</td></tr>
<tr><td><code>hook_scorer.py</code></td><td>First 3s signals</td><td>Hook score (0-100), grade (A+ to F), 4-axis breakdown</td></tr>
<tr><td><code>emotion_arc.py</code></td><td>Emotion timeline</td><td>Arc points, phases, transitions, arc shape</td></tr>
<tr><td><code>retention_curve.py</code></td><td>Timeline, hook score</td><td>Retention curve, avg retention, watch-through rate</td></tr>
<tr><td><code>drop_fixer.py</code></td><td>Red zones, transcript</td><td>Rewritten script, hook alternatives, visual recs</td></tr>
<tr><td><code>llm_coach.py</code></td><td>Zones, signals</td><td>Per-zone coaching, goal keywords, chat responses</td></tr>
<tr><td><code>adaptive_engine.py</code></td><td>Analysis metrics</td><td>Updated weights, weight snapshot</td></tr>
<tr><td><code>report_generator.py</code></td><td>Full analysis result</td><td>HTML report (for PDF), plain-text (for LLM)</td></tr>
<tr><td><code>external_api.py</code></td><td>Audio/video files</td><td>Groq Whisper transcript, 2s-window analysis</td></tr>
</table>

<!-- ═══════ 7. ML ENGINE ═══════ -->
<h2 id="ml-engine">7. 🧠 ML Predictive Engine</h2>
<div class="section-box">
<p><code>services/ml_engine.py</code> — 4 sub-models using scikit-learn. All models train incrementally from your own data and fail gracefully if no training data exists yet.</p>
</div>

<table>
<tr><th>Model</th><th>Type</th><th>Purpose</th></tr>
<tr><td><strong>DropZonePredictor</strong></td><td>RandomForestClassifier</td><td>Predicts green/yellow/red zones from per-second signals</td></tr>
<tr><td><strong>NicheClassifier</strong></td><td>RandomForestClassifier</td><td>Auto-detects content niche from audio/visual features</td></tr>
<tr><td><strong>EarlyScorePredictor</strong></td><td>GradientBoostingRegressor</td><td>Predicts final score from partial signals at 50% and 75% pipeline</td></tr>
<tr><td><strong>UserWeightLearner</strong></td><td>Linear regression + heuristics</td><td>Suggests personalized fusion weights</td></tr>
</table>

<p><strong>Training</strong>: Models are NOT pre-trained. They train incrementally after each video analysis. After 2+ videos, predictions become active. Until then, <code>None</code> is returned and the pipeline uses rule-based logic.</p>

<!-- ═══════ 8. MULTIMODAL ═══════ -->
<h2 id="multimodal">8. 👁 Multimodal Visual AI (LLaVA)</h2>
<div class="section-box">
<p><code>services/multimodal_coach.py</code> — Optional frame-level visual diagnostics via Ollama + LLaVA 7B.</p>
<ul>
    <li><strong>Hook Critique</strong>: Analyzes frames at t=0, t=1, t=2 for first impression, weakness, and fix</li>
    <li><strong>Red Zone Diagnosis</strong>: Analyzes the middle frame of each red zone for visual causes + fixes</li>
    <li>Runs concurrently using <code>asyncio.gather()</code> with 20s timeout</li>
    <li>If Ollama is not running, silently disabled — zero impact on pipeline</li>
</ul>
</div>

<!-- ═══════ 9. API ROUTES ═══════ -->
<div class="page-break"></div>
<h2 id="api-routes">9. 🌐 API Routes</h2>

<table>
<tr><th>Method</th><th>Route</th><th>Description</th></tr>
<tr><td>POST</td><td><code>/api/analyze</code></td><td>Upload video → start analysis → return job_id</td></tr>
<tr><td>GET</td><td><code>/api/results/{job_id}</code></td><td>Get full analysis results (includes ML + multimodal data)</td></tr>
<tr><td>GET</td><td><code>/api/jobs/{job_id}</code></td><td>Poll job status</td></tr>
<tr><td>WS</td><td><code>/ws/{job_id}</code></td><td>WebSocket for real-time progress updates</td></tr>
<tr><td>POST</td><td><code>/api/fix-drops/{job_id}</code></td><td>AI Script Doctor for drop zones</td></tr>
<tr><td>GET</td><td><code>/api/presets</code></td><td>List 7 persona presets</td></tr>
<tr><td>POST</td><td><code>/api/profiles</code></td><td>Create user profile with niche</td></tr>
<tr><td>GET</td><td><code>/api/profiles</code></td><td>List all profiles</td></tr>
<tr><td>GET</td><td><code>/api/profiles/{id}/ledger</code></td><td>Evolution Ledger (weight deltas)</td></tr>
<tr><td>POST</td><td><code>/api/profiles/{id}/references</code></td><td>Upload reference video for baseline</td></tr>
<tr><td>POST</td><td><code>/api/report/{job_id}</code></td><td>Generate downloadable PDF</td></tr>
<tr><td>POST</td><td><code>/api/chat</code></td><td>Interactive AI chat about analysis</td></tr>
<tr><td>POST</td><td><code>/api/goals/process</code></td><td>Extract goal keywords via LLM</td></tr>
<tr><td>POST</td><td><code>/api/youtube/download</code></td><td>Download + analyze YouTube video</td></tr>
<tr><td>POST</td><td><code>/api/share/{job_id}</code></td><td>Create shareable report link</td></tr>
</table>

<!-- ═══════ 10. DATABASE ═══════ -->
<h2 id="database">10. 🗄️ Database Schema</h2>
<p>SQLite database at <code>data/hook_architect.db</code> with WAL mode.</p>
<table>
<tr><th>Table</th><th>Purpose</th><th>Key Columns</th></tr>
<tr><td><code>user_profiles</code></td><td>User accounts</td><td>username, niche, 10 weight columns, thresholds, rewards</td></tr>
<tr><td><code>video_history</code></td><td>Past analyses</td><td>user_id, filename, overall_score, signal averages, zone distribution</td></tr>
<tr><td><code>weight_snapshots</code></td><td>Weight audit trail</td><td>user_id, trigger, weights JSON</td></tr>
<tr><td><code>reference_videos</code></td><td>Reference uploads</td><td>user_id, averaged metrics, dominant emotion/style</td></tr>
<tr><td><code>reference_baselines</code></td><td>Aggregated baselines</td><td>user_id (unique), video_count, all averaged metrics</td></tr>
<tr><td><code>shared_reports</code></td><td>Shareable links</td><td>token, job_id, created_at</td></tr>
</table>

<!-- ═══════ 11. PERSONA ENGINE ═══════ -->
<h2 id="persona">11. 🎭 Persona Presets</h2>
<table>
<tr><th>Niche</th><th>Audio</th><th>Visual</th><th>Transcript</th><th>Song</th><th>Slow Reward</th><th>Energy Reward</th></tr>
<tr><td>🎭 Emotional</td><td>0.40</td><td>0.20</td><td>0.35</td><td>0.25</td><td>+15</td><td>0</td></tr>
<tr><td>🔥 Action</td><td>0.25</td><td>0.45</td><td>0.15</td><td>0.35</td><td>0</td><td>+20</td></tr>
<tr><td>📚 Educational</td><td>0.35</td><td>0.20</td><td>0.45</td><td>0.15</td><td>+5</td><td>0</td></tr>
<tr><td>📹 Vlog</td><td>0.30</td><td>0.35</td><td>0.30</td><td>0.30</td><td>0</td><td>0</td></tr>
<tr><td>🎬 Cinematic</td><td>0.30</td><td>0.45</td><td>0.15</td><td>0.35</td><td>+10</td><td>0</td></tr>
<tr><td>😂 Comedy</td><td>0.40</td><td>0.25</td><td>0.40</td><td>0.20</td><td>0</td><td>0</td></tr>
<tr><td>🎵 Music</td><td>0.45</td><td>0.30</td><td>0.05</td><td>0.45</td><td>0</td><td>+15</td></tr>
</table>

<!-- ═══════ 12. SCORING ═══════ -->
<h2 id="scoring">12. 📊 Scoring &amp; Fusion Formula</h2>
<div class="section-box">
<p><strong>Per-second attention:</strong></p>
<p><code>raw = (α×audio + β×visual + γ×transcript + δ×song + ε×temporal + ζ×engagement) / sum(weights)</code></p>
<p><code>attention = 100 / (1 + e^(-0.05×(raw−50)))</code> ← sigmoid normalization to 0–100</p>
<p><strong>Zone classification:</strong> Green (≥75) | Yellow (≥45) | Red (&lt;45)</p>
<p><strong>ML blending:</strong> When DropZonePredictor is active, majority vote between rule-based and ML-predicted zones per second.</p>
</div>

<!-- ═══════ 13. HOW TO RUN ═══════ -->
<h2 id="running">13. 🚀 How to Run</h2>
<div class="section-box">
<h4>Prerequisites</h4>
<ul>
    <li>Python 3.10+</li>
    <li>FFmpeg binaries in <code>backend/</code> directory (ffmpeg.exe, ffprobe.exe)</li>
    <li>Groq API key in <code>.env</code> (for LLM features)</li>
</ul>
<h4>Start the Server</h4>
<pre style="background:#1e1e2e; color:#cdd6f4; padding:14px; border-radius:8px; font-size:9.5pt;">
cd RGIT/backend
pip install -r requirements.txt
python main.py

<span style="color:#a6e3a1"># Open browser → http://localhost:8000</span>
</pre>
<p style="color:#64748b">No Redis, no Celery, no Docker required.</p>

<h4>Optional: External API (port 5000)</h4>
<pre style="background:#1e1e2e; color:#cdd6f4; padding:14px; border-radius:8px; font-size:9.5pt;">
cd RGIT/backend/external_api_server
pip install -r requirements.txt
python app.py
</pre>

<h4>Optional: Multimodal AI (LLaVA)</h4>
<pre style="background:#1e1e2e; color:#cdd6f4; padding:14px; border-radius:8px; font-size:9.5pt;">
<span style="color:#a6e3a1"># Install Ollama → https://ollama.com/download</span>
ollama pull llava:7b
<span style="color:#a6e3a1"># The system will auto-detect LLaVA on startup</span>
</pre>
</div>

<hr>
<p style="text-align:center; color:#94a3b8; font-size:9pt; margin-top:40px;">
    Hook Architect v4.0.0 — AI-Powered Video Retention Analysis Engine<br>
    Documentation generated automatically • March 2026
</p>

</body>
</html>"""

def main():
    output_pdf = os.path.join(os.path.dirname(__file__), "..", "Hook_Architect_Documentation.pdf")
    output_pdf = os.path.abspath(output_pdf)

    try:
        from xhtml2pdf import pisa

        with open(output_pdf, "wb") as f:
            status = pisa.CreatePDF(HTML_CONTENT, dest=f)

        if status.err:
            print(f"PDF generation had {status.err} errors, but file was created.")
        else:
            print(f"PDF generated successfully: {output_pdf}")

    except ImportError:
        # Fallback: save as HTML
        output_html = output_pdf.replace(".pdf", ".html")
        with open(output_html, "w", encoding="utf-8") as f:
            f.write(HTML_CONTENT)
        print(f"xhtml2pdf not available. HTML saved: {output_html}")
        print("Open the HTML file in a browser and use Print > Save as PDF")

if __name__ == "__main__":
    main()
