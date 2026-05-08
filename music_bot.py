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

# Hardcoded recipients (add as many as you need)
RECIPIENT_IDS = [
    "b0JWE2R0cEO00b3bfc6eb91ee17556ca",
    # "another_user_id",
]

# Paths
ARTIST_FILE = "artists.txt"
DOWNLOADS_DIR = Path("downloads")
DOWNLOADS_DIR.mkdir(exist_ok=True)

# Rubika API endpoints
BASE_API = f"https://botapi.rubika.ir/v3/{RUBIKA_TOKEN}"
REQUEST_SEND_FILE_URL = f"{BASE_API}/requestSendFile"
SEND_FILE_URL = f"{BASE_API}/sendFile"
SEND_MESSAGE_URL = f"{BASE_API}/sendMessage"

# ========== HELPER FUNCTIONS ==========

def load_artists():
    """Load artist list from artists.txt (one per line)."""
    if not os.path.exists(ARTIST_FILE):
        print(f"❌ Artist file '{ARTIST_FILE}' not found", flush=True)
        return []
    with open(ARTIST_FILE, "r", encoding="utf-8") as f:
        artists = [line.strip() for line in f if line.strip()]
    return artists

def search_and_download(artist_name, retries=2):
    """
    Search for a popular song by the artist using yt-dlp.
    Returns (file_path, song_title, song_id) or (None, None, None).
    """
    search_queries = [
        f"{artist_name} popular songs",
        f"{artist_name} top track",
        f"{artist_name} best song"
    ]
    search_query = random.choice(search_queries)
    output_template = str(DOWNLOADS_DIR / f"%(title)s.%(ext)s")

    cmd = [
        "yt-dlp",
        f"ytsearch1:{search_query}",
        "-x", "--audio-format", "mp3",
        "--audio-quality", "0",
        "-o", output_template,
        "--no-playlist",
        "--restrict-filenames",
    ]

    for attempt in range(retries):
        try:
            print(f"🔍 Searching for '{artist_name}'... (attempt {attempt+1})", flush=True)
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            downloaded = list(DOWNLOADS_DIR.glob("*.mp3"))
            if not downloaded:
                continue
            latest = max(downloaded, key=lambda f: f.stat().st_mtime)
            song_title = latest.stem.replace("_", " ")
            song_id = f"{artist_name.lower()} - {song_title.lower()}"
            return latest, song_title, song_id
        except subprocess.CalledProcessError:
            time.sleep(1)
    return None, None, None

def send_music_file(chat_id, file_path, song_title, artist_name):
    """Upload MP3 and send to Rubika user."""
    try:
        # 1. Request upload URL
        resp = requests.post(REQUEST_SEND_FILE_URL, json={"type": "Music"}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != "OK":
            return False
        upload_url = data["data"]["upload_url"]

        # 2. Upload file
        with open(file_path, "rb") as f:
            files = {"file": (file_path.name, f, "audio/mpeg")}
            up_resp = requests.post(upload_url, files=files, timeout=30)
            up_resp.raise_for_status()
            up_data = up_resp.json()
            if up_data.get("status") != "OK":
                return False
            file_id = up_data["data"]["file_id"]

        # 3. Send file
        caption = f"🎵 **{song_title}**\n👤 {artist_name}"
        send_payload = {
            "chat_id": chat_id,
            "file_id": file_id,
            "text": caption
        }
        send_resp = requests.post(SEND_FILE_URL, json=send_payload, timeout=15)
        send_resp.raise_for_status()
        print(f"✅ Sent '{song_title}' to {chat_id}", flush=True)
        return True
    except Exception as e:
        print(f"❌ Send error to {chat_id}: {e}", flush=True)
        return False

def send_text_message(chat_id, text):
    """Send a plain text message."""
    try:
        requests.post(SEND_MESSAGE_URL, json={"chat_id": chat_id, "text": text}, timeout=10)
    except Exception as e:
        print(f"⚠️ Text send error: {e}", flush=True)

def cleanup():
    """Delete all downloaded MP3 files."""
    for f in DOWNLOADS_DIR.glob("*.mp3"):
        try:
            f.unlink()
        except:
            pass

# ========== MAIN LOOP (6‑HOUR RUN, SEND EVERY 10 MINUTES) ==========

def main():
    print("="*50, flush=True)
    print("🎵 MUSIC BOT STARTED", flush=True)
    print(f"⏰ Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    print("⏳ Will run for ~5.9 hours, sending a song every 10 minutes", flush=True)
    print("="*50, flush=True)

    artists = load_artists()
    if not artists:
        print("❌ No artists found in artists.txt", flush=True)
        sys.exit(1)

    print(f"🎤 Loaded {len(artists)} artists", flush=True)

    # Track songs sent during this run to avoid duplicates
    sent_this_run = set()
    max_runtime_seconds = 5.9 * 3600   # 5.9 hours
    start_time = time.time()

    iteration = 0

    while time.time() - start_time < max_runtime_seconds:
        iteration += 1
        print(f"\n🔄 ITERATION {iteration} at {datetime.now().strftime('%H:%M:%S')}", flush=True)

        # Shuffle artists for randomness
        random.shuffle(artists)

        success = False
        for artist in artists:
            print(f"🎲 Trying artist: {artist}", flush=True)
            file_path, song_title, song_id = search_and_download(artist)
            if not file_path:
                print(f"⚠️ Could not find song for {artist}, trying next...", flush=True)
                continue

            # Check if this song was already sent in this 6-hour run
            if song_id in sent_this_run:
                print(f"⏩ '{song_title}' already sent this run, skipping...", flush=True)
                file_path.unlink(missing_ok=True)
                continue

            # New song found – send to all recipients
            print(f"🎉 New song: '{song_title}' by {artist}", flush=True)
            success_count = 0
            for uid in RECIPIENT_IDS:
                if send_music_file(uid, file_path, song_title, artist):
                    success_count += 1

            file_path.unlink(missing_ok=True)   # delete temp file

            if success_count > 0:
                sent_this_run.add(song_id)
                print(f"📝 Logged '{song_title}' for this run. Total sent: {len(sent_this_run)}", flush=True)
                success = True
                break
            else:
                print(f"⚠️ Could not send '{song_title}' to anyone, not logging.", flush=True)
                # Continue to next artist

        if not success:
            # No new song found this iteration – send error message
            error_msg = "❌ Could not find a new song this cycle. Check artists or try again later."
            for uid in RECIPIENT_IDS:
                send_text_message(uid, error_msg)
            print(error_msg, flush=True)

        # Wait 10 minutes (600 seconds) but subtract elapsed time of this iteration
        elapsed = time.time() - start_time
        if elapsed + 600 > max_runtime_seconds:
            print("⏰ Reached runtime limit, exiting.", flush=True)
            break
        print(f"⏳ Sleeping 600 seconds...", flush=True)
        time.sleep(600)

    print("\n🏁 6-hour run completed. Exiting.", flush=True)
    cleanup()

if __name__ == "__main__":
    main()
