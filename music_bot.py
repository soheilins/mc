#!/usr/bin/env python3
import os
import sys
import random
import requests
import subprocess
import time
from pathlib import Path
from datetime import datetime

# ========== CONFIGURATION ==========
RUBIKA_TOKEN = os.environ.get("RUBIKA_TOKEN", "")
if not RUBIKA_TOKEN:
    print("❌ RUBIKA_TOKEN missing", flush=True)
    sys.exit(1)

RECIPIENT_IDS = [
    "b0JWE2R0cEO00b3bfc6eb91ee17556ca",   # your user ID
]

ARTIST_FILE = "artists.txt"
SENT_LOG = "sent_songs.txt"
DOWNLOADS_DIR = Path("downloads")
DOWNLOADS_DIR.mkdir(exist_ok=True)

BASE_API = f"https://botapi.rubika.ir/v3/{RUBIKA_TOKEN}"
REQUEST_SEND_FILE_URL = f"{BASE_API}/requestSendFile"
SEND_FILE_URL = f"{BASE_API}/sendFile"
SEND_MESSAGE_URL = f"{BASE_API}/sendMessage"

# ========== HELPER FUNCTIONS ==========

def load_artists():
    if not os.path.exists(ARTIST_FILE):
        return []
    with open(ARTIST_FILE, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

def load_sent_songs():
    if not os.path.exists(SENT_LOG):
        return set()
    with open(SENT_LOG, "r", encoding="utf-8") as f:
        return {line.strip() for line in f if line.strip()}

def save_sent_song(song_id):
    with open(SENT_LOG, "a", encoding="utf-8") as f:
        f.write(song_id + "\n")

def search_and_download_sc(artist_name):
    """
    Use yt-dlp with SoundCloud search.
    Returns (file_path, song_display) or (None, None).
    """
    search_query = f"scsearch1:{artist_name} popular"
    output_template = str(DOWNLOADS_DIR / f"%(title)s.%(ext)s")
    cmd = [
        "yt-dlp",
        search_query,
        "-x", "--audio-format", "mp3",
        "--audio-quality", "0",
        "-o", output_template,
        "--no-playlist",
        "--restrict-filenames",
        "--extractor-args", "soundcloud:formats=mp3"   # MP3 only
    ]
    try:
        print(f"🔍 Searching SoundCloud for {artist_name}...", flush=True)
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        if result.returncode == 0:
            downloaded = list(DOWNLOADS_DIR.glob("*.mp3"))
            if downloaded:
                latest = max(downloaded, key=lambda f: f.stat().st_mtime)
                song_title = latest.stem.replace("_", " ")
                display = f"{song_title} - {artist_name}"
                return latest, display
        else:
            print(f"⚠️ SoundCloud error: {result.stderr[-300:]}", flush=True)
    except Exception as e:
        print(f"⚠️ Exception: {e}", flush=True)
    return None, None

def send_music_file(chat_id, file_path, caption):
    try:
        # request upload URL
        resp = requests.post(REQUEST_SEND_FILE_URL, json={"type": "Music"}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != "OK":
            return False
        upload_url = data["data"]["upload_url"]

        # upload
        with open(file_path, "rb") as f:
            files = {"file": (file_path.name, f, "audio/mpeg")}
            up_resp = requests.post(upload_url, files=files, timeout=30)
            up_resp.raise_for_status()
            up_data = up_resp.json()
            if up_data.get("status") != "OK":
                return False
            file_id = up_data["data"]["file_id"]

        # send
        send_payload = {
            "chat_id": chat_id,
            "file_id": file_id,
            "text": f"🎵 {caption}"
        }
        send_resp = requests.post(SEND_FILE_URL, json=send_payload, timeout=15)
        send_resp.raise_for_status()
        print(f"✅ Sent '{caption}' to {chat_id}", flush=True)
        return True
    except Exception as e:
        print(f"❌ Send error: {e}", flush=True)
        return False

def send_text_message(chat_id, text):
    try:
        requests.post(SEND_MESSAGE_URL, json={"chat_id": chat_id, "text": text}, timeout=10)
    except Exception:
        pass

def cleanup():
    for f in DOWNLOADS_DIR.glob("*.mp3"):
        f.unlink(missing_ok=True)

# ========== MAIN LOOP (6‑hour run, send every 10 min) ==========

def main():
    print("="*50, flush=True)
    print("🎵 MUSIC BOT (SoundCloud)", flush=True)
    print(f"⏰ Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    print("⏳ Will run for ~5.9 hours, sending a song every 10 minutes", flush=True)
    print(f"📨 Recipients: {len(RECIPIENT_IDS)} user(s)", flush=True)
    print("="*50, flush=True)

    artists = load_artists()
    if not artists:
        print("❌ No artists found in artists.txt", flush=True)
        sys.exit(1)
    print(f"🎤 Loaded {len(artists)} artists", flush=True)

    sent_this_run = set()
    max_runtime = 5.9 * 3600
    start_time = time.time()
    iteration = 0

    while time.time() - start_time < max_runtime:
        iteration += 1
        print(f"\n🔄 ITERATION {iteration} at {datetime.now().strftime('%H:%M:%S')}", flush=True)
        random.shuffle(artists)
        success = False

        for artist in artists:
            print(f"🎲 Trying artist: {artist}", flush=True)
            file_path, song_display = search_and_download_sc(artist)
            if not file_path:
                continue

            song_id = f"{artist.lower()} - {song_display.lower()}"
            if song_id in sent_this_run:
                print(f"⏩ Already sent this run, skipping...", flush=True)
                file_path.unlink(missing_ok=True)
                continue

            sent_ok = False
            for uid in RECIPIENT_IDS:
                if send_music_file(uid, file_path, song_display):
                    sent_ok = True
            file_path.unlink(missing_ok=True)

            if sent_ok:
                sent_this_run.add(song_id)
                # Also persist to file for future runs (optional if you want cross-run memory)
                save_sent_song(song_id)
                print(f"📝 Logged. Total this run: {len(sent_this_run)}", flush=True)
                success = True
                break
            else:
                print(f"⚠️ Send failed, not logging", flush=True)

        if not success:
            error_msg = "❌ Could not find any new song this cycle."
            for uid in RECIPIENT_IDS:
                send_text_message(uid, error_msg)
            print(error_msg, flush=True)

        elapsed = time.time() - start_time
        if elapsed + 600 > max_runtime:
            print("⏰ Runtime limit reached, exiting.", flush=True)
            break
        print("⏳ Sleeping 600 seconds...", flush=True)
        time.sleep(600)

    cleanup()
    print("🏁 6‑hour run completed.", flush=True)

if __name__ == "__main__":
    main()
