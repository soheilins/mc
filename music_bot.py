#!/usr/bin/env python3
import subprocess
import sys

def test_ytdlp():
    print("Testing yt-dlp...")
    cmd = ["yt-dlp", "--version"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(f"yt-dlp version: {result.stdout.strip()}")
    print(f"yt-dlp error: {result.stderr.strip()}")
    print(f"Return code: {result.returncode}")

    print("\nTesting simple search...")
    artist = "Adele"
    cmd = [
        "yt-dlp",
        f"ytsearch1:{artist} popular songs",
        "-x", "--audio-format", "mp3",
        "-o", "test.%(ext)s",
        "--no-playlist",
        "--extractor-args", "youtube:player_client=android"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    print(f"Return code: {result.returncode}")
    print("STDOUT (last 500 chars):")
    print(result.stdout[-500:])
    print("STDERR (last 500 chars):")
    print(result.stderr[-500:])

if __name__ == "__main__":
    test_ytdlp()
