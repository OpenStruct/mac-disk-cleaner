#!/bin/bash
# Regenerates docs/walkthrough.mp4: narrated, captioned walkthrough of the real app on a demo folder.
# Needs: Node, Google Chrome, ffmpeg. Voice:  VOICE="Ava (Premium)" ./make-video.sh
set -euo pipefail
cd "$(dirname "$0")"
REPO="$(cd ../.. && pwd)"; VOICE="${VOICE:-Samantha}"; PORT=8820; DEMO="$HOME/.mdc-demo"
[ -d node_modules/playwright ] || npm install --no-save playwright@1 >/dev/null
npx playwright install ffmpeg >/dev/null

rm -rf vo raw && mkdir -p vo raw
python3 - "$VOICE" <<'PY'
import json, subprocess, sys
durs = {}
for k, text in json.load(open("narration.json")).items():
    subprocess.run(["say", "-v", sys.argv[1], "-r", "178", "-o", f"vo/{k}.aiff", text], check=True)
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f"vo/{k}.aiff"], capture_output=True, text=True).stdout
    durs[k] = float(out)
json.dump(durs, open("vo/durations.json", "w"))
PY

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
    args += ["-i", f"vo/{t['id']}.aiff"]
    parts.append(f"[{i}:a]aresample=48000,adelay={t['ms']}|{t['ms']}[a{i}]")
mix = "".join(f"[a{i}]" for i in range(1, len(tl) + 1))
args += ["-filter_complex", ";".join(parts) + f";{mix}amix=inputs={len(tl)}:normalize=0:dropout_transition=0,loudnorm=I=-16:TP=-1.5:LRA=11,apad[a]",
         "-map", "0:v", "-map", "[a]", "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-preset", "slow", "-crf", "24",
         "-c:a", "aac", "-b:a", "128k", "-ac", "2", "-shortest", "-movflags", "+faststart", "../../docs/walkthrough.mp4"]
subprocess.run(args, check=True)
PY
ffmpeg -loglevel error -y -ss 1.5 -i ../../docs/walkthrough.mp4 -frames:v 1 ../../docs/walkthrough-poster.jpg
echo "Wrote docs/walkthrough.mp4"
