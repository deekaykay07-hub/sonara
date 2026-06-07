#!/usr/bin/env python3
"""
Sonara - Beautiful Speech-to-Text Transcription Web App
Powered by faster-whisper. Easy local & GitHub-first experience.
"""

import os
import uuid
import tempfile
import threading
import time
from pathlib import Path
from typing import Dict, Any, Optional

from fastapi import FastAPI, UploadFile, File, Form, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import uvicorn

from pydub import AudioSegment
from faster_whisper import WhisperModel

# --------------------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------------------
APP_NAME = "Sonara"
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "6574"))
MAX_FILE_SIZE_MB = 350
MAX_FILE_SIZE = MAX_FILE_SIZE_MB * 1024 * 1024

# In-memory job store (simple, ephemeral, perfect for single-user / small deployments)
jobs: Dict[str, Dict[str, Any]] = {}
jobs_lock = threading.Lock()

# Model cache so we don't reload the same size repeatedly
model_cache: Dict[str, WhisperModel] = {}
model_lock = threading.Lock()

# Supported faster-whisper model sizes (user friendly labels)
MODEL_SIZES = {
    "tiny": "Tiny (fastest, ~1GB)",
    "base": "Base (~1.5GB)",
    "small": "Small (recommended, ~2.5GB)",
    "medium": "Medium (~5GB)",
    "large-v2": "Large-v2 (best quality, ~10GB)",
    "large-v3": "Large-v3 (latest & greatest, ~10GB)",
}

LANGUAGES = {
    "": "Auto-detect",
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "pt": "Portuguese",
    "it": "Italian",
    "ru": "Russian",
    "zh": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    "ar": "Arabic",
    "hi": "Hindi",
    "nl": "Dutch",
    "sv": "Swedish",
    "tr": "Turkish",
    "pl": "Polish",
}

# --------------------------------------------------------------------------------------
# FastAPI setup
# --------------------------------------------------------------------------------------
app = FastAPI(title=APP_NAME, description="Beautiful local-first speech-to-text")

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Mount static if you ever want separate css/js (currently everything is in the template for maximum ease)
static_dir = BASE_DIR / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


def get_model(model_size: str) -> WhisperModel:
    """Load (or return cached) WhisperModel. Downloads on first use."""
    if model_size not in MODEL_SIZES:
        model_size = "small"

    with model_lock:
        if model_size not in model_cache:
            print(f"[Sonara] Loading Whisper model: {model_size} (this may take a while on first run)...")
            # device="auto" picks CUDA if available, else CPU. compute_type="int8" is great for CPU speed/quality.
            model_cache[model_size] = WhisperModel(
                model_size,
                device="auto",
                compute_type="int8" if model_size in ("tiny", "base", "small") else "float16",
            )
        return model_cache[model_size]


def extract_audio_to_wav(src_path: str) -> str:
    """
    Convert any audio or video file to a clean 16kHz mono WAV using pydub + ffmpeg.
    Returns path to temporary wav file.
    """
    try:
        audio = AudioSegment.from_file(src_path)
        # Whisper works great with 16kHz mono
        audio = audio.set_frame_rate(16000).set_channels(1)
        fd, wav_path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        audio.export(wav_path, format="wav")
        return wav_path
    except Exception as e:
        raise RuntimeError(f"Failed to extract audio (is ffmpeg installed?): {e}")


def transcribe_job(job_id: str, original_filename: str, file_path: str, model_size: str, language: str):
    """Background worker that performs transcription and updates the job dict."""
    start_time = time.time()
    wav_path = None

    try:
        update_job(job_id, status="processing", progress="Extracting audio...")

        wav_path = extract_audio_to_wav(file_path)

        update_job(job_id, status="processing", progress=f"Loading {model_size} model...")

        model = get_model(model_size)

        update_job(job_id, status="processing", progress="Transcribing... (this can take a while)")

        # faster-whisper transcribe
        segments, info = model.transcribe(
            wav_path,
            language=language if language else None,
            beam_size=5,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
        )

        # Collect segments and full text
        segment_list = []
        full_text_parts = []
        for seg in segments:
            text = seg.text.strip()
            if text:
                segment_list.append({
                    "start": round(seg.start, 2),
                    "end": round(seg.end, 2),
                    "text": text,
                })
                full_text_parts.append(text)

        full_text = " ".join(full_text_parts).strip()

        duration = round(time.time() - start_time, 1)

        result = {
            "filename": original_filename,
            "model": model_size,
            "language": info.language or language or "auto",
            "duration_seconds": round(info.duration, 1) if info.duration else None,
            "processing_time": duration,
            "text": full_text,
            "segments": segment_list,
        }

        update_job(job_id, status="done", result=result, progress="Complete")

    except Exception as exc:
        update_job(job_id, status="error", error=str(exc), progress="Failed")
        print(f"[Sonara] Job {job_id} failed: {exc}")
    finally:
        # Cleanup temps
        for p in (wav_path, file_path):
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass


def update_job(job_id: str, **kwargs):
    with jobs_lock:
        if job_id not in jobs:
            jobs[job_id] = {}
        jobs[job_id].update(kwargs)
        jobs[job_id]["updated_at"] = time.time()


def create_job() -> str:
    job_id = uuid.uuid4().hex[:12]
    with jobs_lock:
        jobs[job_id] = {
            "status": "queued",
            "progress": "Queued...",
            "created_at": time.time(),
        }
    return job_id


def cleanup_old_jobs(max_age_seconds: int = 3600):
    """Simple housekeeping so the dict doesn't grow forever."""
    now = time.time()
    with jobs_lock:
        to_delete = [jid for jid, j in jobs.items() if now - j.get("created_at", 0) > max_age_seconds]
        for jid in to_delete:
            jobs.pop(jid, None)


# --------------------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    cleanup_old_jobs()
    # Use the underlying Jinja environment directly for maximum compatibility
    template = templates.env.get_template("index.html")
    html = template.render(
        request=request,
        app_name=APP_NAME,
        model_sizes=MODEL_SIZES,
        languages=LANGUAGES,
        max_mb=MAX_FILE_SIZE_MB,
    )
    return HTMLResponse(content=html)


@app.post("/transcribe")
async def start_transcription(
    file: UploadFile = File(...),
    model_size: str = Form("small"),
    language: str = Form(""),
):
    # Basic validation
    if not file.filename:
        raise HTTPException(400, "No file provided")

    # Read into temp file (we need the bytes on disk for pydub/ffmpeg)
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(413, f"File too large. Max {MAX_FILE_SIZE_MB} MB.")

    suffix = Path(file.filename).suffix or ".bin"
    fd, tmp_path = tempfile.mkstemp(suffix=suffix)
    os.write(fd, contents)
    os.close(fd)

    job_id = create_job()

    # Launch background thread
    thread = threading.Thread(
        target=transcribe_job,
        args=(job_id, file.filename, tmp_path, model_size, language),
        daemon=True,
    )
    thread.start()

    return JSONResponse({"job_id": job_id})


@app.get("/jobs/{job_id}")
async def get_job(job_id: str):
    with jobs_lock:
        job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found (it may have expired)")
    return JSONResponse(job)


@app.get("/health")
async def health():
    return {"status": "ok", "app": APP_NAME, "models_loaded": list(model_cache.keys())}


# --------------------------------------------------------------------------------------
# Entrypoint
# --------------------------------------------------------------------------------------
if __name__ == "__main__":
    print(f"\n{'='*56}")
    print(f"  {APP_NAME} — Beautiful Speech-to-Text")
    print(f"  Running at: http://{HOST}:{PORT}")
    print(f"  (Open in your browser)")
    print(f"{'='*56}\n")

    uvicorn.run(
        "app:app",
        host=HOST,
        port=PORT,
        reload=False,
        log_level="info",
    )
