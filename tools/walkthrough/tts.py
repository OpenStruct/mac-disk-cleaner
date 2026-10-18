#!/usr/bin/env python3
"""Synthesises narration.json into vo/<id>.(aiff|mp3) and writes vo/durations.json.

TTS=say (default)          macOS voice, VOICE="Samantha"
TTS=elevenlabs             ElevenLabs voice, VOICE="Jessica"; key from $ELEVENLABS_API_KEY, or
                           KEY_FROM=<.env file or folder> to read ELEVEN*KEY from its .env files.
The API key is never printed or written anywhere.
"""
import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

API = "https://api.elevenlabs.io/v1"
JESSICA = "cgSgspJ2msm6clMCkdW9"   # ElevenLabs premade voice "Jessica"


def eleven_key():
    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if key:
        return key
    src = os.environ.get("KEY_FROM")
    if not src:
        sys.exit("Set ELEVENLABS_API_KEY or KEY_FROM=<path to .env file or folder>.")
    p = Path(src).expanduser()
    files = [p] if p.is_file() else sorted(p.glob(".env*"))
    pattern = re.compile(r"^\s*(?:export\s+)?([A-Z_]*ELEVEN[A-Z_]*KEY)\s*=\s*['\"]?([^'\"\s#]+)")
    for f in files:
        for line in f.read_text(errors="ignore").splitlines():
            m = pattern.match(line)
            if m:
                print(f"Using {m.group(1)} from {f.name}")
                return m.group(2)
    sys.exit(f"No ELEVEN…KEY variable found in {src}")


def request(method, path, key, body=None, accept="application/json"):
    req = urllib.request.Request(API + path, method=method, data=json.dumps(body).encode() if body else None,
                                 headers={"xi-api-key": key, "Content-Type": "application/json", "Accept": accept})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        sys.exit(f"ElevenLabs {e.code}: {e.read().decode(errors='ignore')[:300]}")


def voice_id(name, key):
    voices = json.loads(request("GET", "/voices", key)).get("voices", [])
    for v in voices:
        if v.get("name", "").lower().startswith(name.lower()):
            return v["voice_id"]
    if name.lower() == "jessica":
        return JESSICA
    sys.exit(f"Voice {name!r} not found in this ElevenLabs account.")


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return float(out)


def main():
    engine = os.environ.get("TTS", "say")
    lines = json.load(open("narration.json"))
    out = Path("vo")
    out.mkdir(exist_ok=True)
    for old in out.glob("*"):
        old.unlink()
    ids, texts = list(lines), list(lines.values())
    durs = {}

    if engine == "elevenlabs":
        key = eleven_key()
        vid = voice_id(os.environ.get("VOICE", "Jessica"), key)
        for i, (k, text) in enumerate(lines.items()):
            body = {
                "text": text,
                "model_id": os.environ.get("ELEVEN_MODEL", "eleven_multilingual_v2"),
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.8, "style": 0.2, "use_speaker_boost": True},
                # Neighbouring lines keep intonation continuous across separately generated clips.
                "previous_text": " ".join(texts[:i])[-500:] or None,
                "next_text": " ".join(texts[i + 1:])[:500] or None,
            }
            audio = request("POST", f"/text-to-speech/{vid}?output_format=mp3_44100_128", key, body, accept="audio/mpeg")
            f = out / f"{k}.mp3"
            f.write_bytes(audio)
            durs[k] = duration(f)
            print(f"  {k}: {durs[k]:.1f}s")
    else:
        voice = os.environ.get("VOICE", "Samantha")
        for k, text in lines.items():
            f = out / f"{k}.aiff"
            subprocess.run(["say", "-v", voice, "-r", "178", "-o", str(f), text], check=True)
            durs[k] = duration(f)

    json.dump(durs, open(out / "durations.json", "w"), indent=1)
    print(f"Narration: {len(durs)} lines, {sum(durs.values()):.1f}s with {engine}")


if __name__ == "__main__":
    main()
