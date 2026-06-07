#!/bin/bash
# Convenience launcher for Sonara
set -e

echo "🚀 Starting Sonara (STT Transcriber)..."

# Allow overriding host/port via env
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-6574}"

# Activate venv if it exists
if [ -d "venv" ]; then
  echo "Activating virtual environment..."
  source venv/bin/activate
fi

echo "Serving on http://${HOST}:${PORT}"
echo "Press Ctrl+C to stop."

exec python app.py
