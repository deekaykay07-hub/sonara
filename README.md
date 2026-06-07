# Sonara

**Beautiful, easy-to-use speech-to-text (STT) web app.**  
Upload audio or video → get accurate transcription instantly. Powered by [faster-whisper](https://github.com/SYSTRAN/faster-whisper).

### 🌐 Live Demo
A public instance is running here: **http://165.22.112.6:6574**

![Sonara UI](https://raw.githubusercontent.com/deekaykay07-hub/sonara/main/.github/preview.png)

## ✨ Features

- **Drag & drop or click to upload** — supports audio (mp3, wav, m4a, flac, ogg…) and video (mp4, mov, mkv, avi, webm…)
- **Really cool modern UI** — dark glassmorphism, smooth interactions, animated processing
- **Multiple model sizes** — Tiny (fastest) → Large-v3 (highest quality)
- **Auto language detection** or pick a specific language
- **Native copy support** — Ctrl/Cmd+C, right-click → Copy, or big Copy button. Works exactly like a normal text area.
- **Download** as `.txt` (plain text) or `.srt` (subtitles with timestamps)
- **Timestamped segments** — clickable rows for easy copy of individual lines
- **100% local & private** — nothing is sent to the cloud (unless you want to use an OpenAI key in the future)
- **One-command run** from GitHub

## 🚀 Quick Start (from GitHub)

```bash
# 1. Clone
git clone https://github.com/deekaykay07-hub/sonara.git
cd sonara

# 2. Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate          # Linux / macOS
# venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install ffmpeg (required to handle video + various audio formats)
# --- Ubuntu / Debian / Pop!_OS
sudo apt update && sudo apt install -y ffmpeg

# --- macOS (Homebrew)
brew install ffmpeg

# --- Windows (winget)
winget install ffmpeg

# 5. Run it!
python app.py
```

Then open your browser at: **http://localhost:6574**

## Running on a specific host / port

```bash
HOST=0.0.0.0 PORT=6574 python app.py
```

Or with uvicorn directly:

```bash
uvicorn app:app --host 0.0.0.0 --port 6574
```

## Production / Persistent Run (Linux server example)

```bash
# Simple background
nohup python app.py > sonara.log 2>&1 &

# Or using uvicorn
nohup uvicorn app:app --host 0.0.0.0 --port 6574 > sonara.log 2>&1 &
```

To stop:
```bash
pkill -f "uvicorn app:app"
# or
pkill -f "python app.py"
```

## Requirements

- Python 3.9+
- ~2–12 GB disk space for the chosen Whisper model (downloaded automatically on first use)
- ffmpeg (for video/audio conversion)

## How to Use

1. Drag an audio or video file onto the big drop zone, or click it to browse.
2. (Optional) Choose model size and language.
3. Click **Transcribe**.
4. Wait for processing (first time is slower because the model is downloaded).
5. Your transcript appears in a big beautiful box.
6. **Copy** using:
   - The big **Copy** button
   - `Ctrl` / `Cmd` + `C` (the box is a standard textarea)
   - Right-click → Copy
7. Download `.txt` or `.srt` subtitles.

## Model Sizes (choose in the UI)

| Model     | Size   | Speed     | Quality     | Recommended for          |
|-----------|--------|-----------|-------------|--------------------------|
| tiny      | ~1 GB  | ⚡⚡⚡     | Good        | Quick drafts             |
| base      | ~1.5GB | ⚡⚡       | Very good   | Everyday use             |
| **small** | ~2.5GB | ⚡         | Excellent   | **Best balance (default)** |
| medium    | ~5 GB  | 🐢        | Outstanding | High accuracy            |
| large-v2  | ~10GB  | 🐢        | Best        | Maximum quality          |
| large-v3  | ~10GB  | 🐢        | Latest best | Latest & greatest        |

## Architecture (for developers)

- **Backend**: FastAPI + Uvicorn
- **STT Engine**: `faster-whisper` (CTranslate2 optimized)
- **Audio handling**: `pydub` + ffmpeg
- **Frontend**: Single-file Tailwind + vanilla JS (zero build step)

Everything is designed so you can clone → pip install → run in under 3 minutes.

## Environment Variables

- `HOST` — default `0.0.0.0`
- `PORT` — default `6574`
- `MAX_FILE_SIZE_MB` (edit in code if you really need bigger files)

## Troubleshooting

**"Failed to extract audio (is ffmpeg installed?)"**
→ Install ffmpeg using the instructions above.

**First transcription is very slow**
→ Normal. The model is being downloaded (hundreds of MB to several GB). Subsequent runs are fast.

**Out of memory / CUDA errors**
→ Try a smaller model (`base` or `small`). The app will fall back gracefully on CPU.

**Port already in use**
→ Change the port:
```bash
PORT=8000 python app.py
```

## Contributing

Pull requests welcome! Ideas for future:
- Speaker diarization
- OpenAI Whisper API fallback option
- Batch processing
- Export to Notion / Obsidian / Markdown with timestamps

## License

MIT — do whatever you want.

---

Made with care. Enjoy transcribing. 🎙️📝
