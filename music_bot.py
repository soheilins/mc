#!/usr/bin/env python3
import subprocess
import sys

# Test a simple search with verbose output
artist = "Taylor Swift"
cmd = [
    "yt-dlp",
    f"ytsearch1:{artist} popular songs",
    "-x", "--audio-format", "mp3",
    "--audio-quality", "0",
    "-o", "test.%(ext)s",
    "--no-playlist",
    "--restrict-filenames",
    "--verbose"   # add verbose output
]

print("Running command:", " ".join(cmd))
result = subprocess.run(cmd, capture_output=True, text=True)
print("STDOUT:", result.stdout)
print("STDERR:", result.stderr)
print("Return code:", result.returncode)
