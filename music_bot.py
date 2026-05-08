#!/usr/bin/env python3
import sys
import os

# VERY FIRST PRINT
print("=== DEBUG: Python script started ===", flush=True)
print(f"DEBUG: Current working directory: {os.getcwd()}", flush=True)
print(f"DEBUG: Files in directory: {os.listdir('.')}", flush=True)

# Now import everything else
import random
import requests
import subprocess
import time
from pathlib import Path
from datetime import datetime

print("DEBUG: All modules imported successfully", flush=True)

# ========== CONFIGURATION ==========
RUBIKA_TOKEN = os.environ.get("RUBIKA_TOKEN", "")
print(f"DEBUG: RUBIKA_TOKEN present: {bool(RUBIKA_TOKEN)}", flush=True)
if not RUBIKA_TOKEN:
    print("❌ RUBIKA_TOKEN missing", flush=True)
    sys.exit(1)

RECIPIENT_IDS = [
    "b0JWE2R0cEO00b3bfc6eb91ee17556ca",
]
ARTIST_FILE = "artists.txt"
DOWNLOADS_DIR = Path("downloads")
DOWNLOADS_DIR.mkdir(exist_ok=True)
print(f"DEBUG: Downloads dir created at {DOWNLOADS_DIR}", flush=True)

BASE_API = f"https://botapi.rubika.ir/v3/{RUBIKA_TOKEN}"
REQUEST_SEND_FILE_URL = f"{BASE_API}/requestSendFile"
SEND_FILE_URL = f"{BASE_API}/sendFile"
SEND_MESSAGE_URL = f"{BASE_API}/sendMessage"

# ========== FUNCTIONS ==========

def load_artists():
    print(f"DEBUG: Loading artists from {ARTIST_FILE}", flush=True)
    if not os.path.exists(ARTIST_FILE):
        print(f"WARNING: {ARTIST_FILE} not found", flush=True)
        return []
    with open(ARTIST_FILE, "r", encoding="utf-8") as f:
        artists = [line.strip() for line in f if line.strip()]
    print(f"DEBUG: Loaded {len(artists)} artists", flush=True)
    return artists

def search_and_download(artist_name):
    print(f"DEBUG: search_and_download called for {artist_name}", flush=True)
    search_query = f"ytsearch1:{artist_name} popular songs"
    output_template = str(DOWNLOADS_DIR / f"%(title)s.%(ext)s")
    clients = ["web_safari", "ios", "tv", "android"]
    for client in clients:
        cmd = [
            "yt-dlp",
            search_query,
            "-x", "--audio-format", "mp3",
            "--audio-quality", "0",
            "-o", output_template,
            "--no-playlist",
            "--restrict-filenames",
            "--extractor-args", f"youtube:player_client={client};formats=missing_pot"
        ]
        try:
            print(f"DEBUG: Trying client {client}", flush=True)
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
            if result.returncode == 0:
                downloaded = list(DOWNLOADS_DIR.glob("*.mp3"))
                if downloaded:
                    latest = max(downloaded, key=lambda f: f.stat().st_mtime)
                    song_title = latest.stem.replace("_", " ")
                    display = f"{song_title} - {artist_name}"
                    print(f"DEBUG: Success with client {client}", flush=True)
                    return latest, display
            else:
                print(f"DEBUG: Client {client} failed, returncode {result.returncode}", flush=True)
        except Exception as e:
            print(f"DEBUG: Exception with client {client}: {e}", flush=True)
    return None, None

def send_music_file(chat_id, file_path, caption):
    print(f"DEBUG: send_music_file called for {chat_id}", flush=True)
    try:
        resp = requests.post(REQUEST_SEND_FILE_URL, json={"type": "Music"}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != "OK":
            print(f"❌ requestSendFile error: {data}", flush=True)
            return False
        upload_url = data["data"]["upload_url"]
        with open(file_path, "rb") as f:
            files = {"file": (file_path.name, f, "audio/mpeg")}
            upload_resp = requests.post(upload_url, files=files, timeout=30)
            upload_resp.raise_for_status()
            upload_data = upload_resp.json()
            if upload_data.get("status") != "OK":
                return False
            file_id = upload_data["data"]["file_id"]
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

def main():
    print("DEBUG: Entering main()", flush=True)
    print("="*50, flush=True)
    print("🎵 MUSIC BOT (Debug)", flush=True)
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
    max_runtime_seconds = 5.9 * 3600
    start_time = time.time()
    iteration = 0

    while time.time() - start_time < max_runtime_seconds:
        iteration += 1
        print(f"\n🔄 ITERATION {iteration} at {datetime.now().strftime('%H:%M:%S')}", flush=True)
        random.shuffle(artists)
        success = False
        for artist in artists:
            print(f"🎲 Trying artist: {artist}", flush=True)
            file_path, song_display = search_and_download(artist)
            if not file_path:
                print(f"⚠️ Could not download for {artist}", flush=True)
                continue
            song_id = f"{artist.lower()} - {song_display.lower()}"
            if song_id in sent_this_run:
                print(f"⏩ Already sent this run, skipping...", flush=True)
                file_path.unlink(missing_ok=True)
                continue
            success_count = 0
            for uid in RECIPIENT_IDS:
                if send_music_file(uid, file_path, song_display):
                    success_count += 1
            file_path.unlink(missing_ok=True)
            if success_count > 0:
                sent_this_run.add(song_id)
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
        if elapsed + 600 > max_runtime_seconds:
            print("⏰ Runtime limit reached, exiting.", flush=True)
            break
        print("⏳ Sleeping 600 seconds...", flush=True)
        time.sleep(600)
    print("\n🏁 6‑hour run completed. Exiting.", flush=True)
    cleanup()

if __name__ == "__main__":
    print("DEBUG: About to call main()", flush=True)
    main()
