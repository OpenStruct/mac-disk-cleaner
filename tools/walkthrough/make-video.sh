#!/bin/bash
# Regenerates docs/walkthrough.mp4: narrated, captioned walkthrough of the real app on a demo folder.
# Needs: Node, Google Chrome, ffmpeg.
#   macOS voice:  VOICE="Ava (Premium)" ./make-video.sh
#   ElevenLabs:   TTS=elevenlabs VOICE=Jessica KEY_FROM=/path/to/project ./make-video.sh   (or ELEVENLABS_API_KEY=...)
set -euo pipefail
cd "$(dirname "$0")"
REPO="$(cd ../.. && pwd)"; PORT=8820; DEMO="$HOME/.mdc-demo"
[ -d node_modules/playwright ] || npm install --no-save playwright@1 >/dev/null
npx playwright install ffmpeg >/dev/null

rm -rf raw && mkdir -p raw
python3 tts.py

./build-demo.sh "$DEMO"
HOME="$DEMO" python3 "$REPO/diskclean.py" --no-open --no-scan --port $PORT >/dev/null 2>&1 &
SERVER=$!; trap 'kill $SERVER 2>/dev/null; rm -rf "$DEMO"' EXIT
sleep 1
node walkthrough.mjs "http://127.0.0.1:$PORT/" raw

python3 - <<'PY'
import json, subprocess, glob
tl = json.load(open("raw/timeline.json")); webm = glob.glob("raw/*.webm")[0]
args = ["ffmpeg", "-loglevel", "error", "-y", "-i", webm]; parts = []
for i, t in enumerate(tl, start=1):
    args += ["-i", glob.glob(f"vo/{t['id']}.*[!n]")[0]]   # .aiff or .mp3, not durations.json
    parts.append(f"[{i}:a]aresample=48000,adelay={t['ms']}|{t['ms']}[a{i}]")
mix = "".join(f"[a{i}]" for i in range(1, len(tl) + 1))
args += ["-filter_complex", ";".join(parts) + f";{mix}amix=inputs={len(tl)}:normalize=0:dropout_transition=0,loudnorm=I=-16:TP=-1.5:LRA=11,apad[a]",
         "-map", "0:v", "-map", "[a]", "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-preset", "slow", "-crf", "24",
         "-c:a", "aac", "-b:a", "128k", "-ac", "2", "-shortest", "-movflags", "+faststart", "../../docs/walkthrough.mp4"]
subprocess.run(args, check=True)
PY
ffmpeg -loglevel error -y -ss 1.5 -i ../../docs/walkthrough.mp4 -frames:v 1 ../../docs/walkthrough-poster.jpg
echo "Wrote docs/walkthrough.mp4"
