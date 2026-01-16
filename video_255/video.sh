#!/bin/bash

if ! command -v ffmpeg &> /dev/null; then
    echo "ffmpeg not installed. Installing..."
    sudo apt update && sudo apt install -y ffmpeg
fi

if [ -z "$1" ]; then
    echo "Usage: ./force_fix_video.sh <input_video>"
    exit 1
fi

INPUT="$1"
OUTPUT="repaired_${INPUT%.*}.mp4"

# Fully re-encode both video and audio to guaranteed-phone-safe formats
ffmpeg -y -i "$INPUT" \
  -vf "format=yuv420p" \
  -c:v libx264 -preset slow -crf 20 \
  -c:a aac -b:a 128k \
  -movflags +faststart \
  "$OUTPUT"

echo "Done. Output file: $OUTPUT"
