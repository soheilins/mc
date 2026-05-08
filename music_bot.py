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
    print("❌ RUBIKA_TOKEN environment variable not set", flush=True)
    sys.exit(1)

# Add all your recipient Rubika user IDs here
RECIPIENT_IDS = [
    "b0JWE2R0cEO00b3bfc6eb91ee17556ca",   # your user ID
    # add more if needed
]

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
    if not os.path.exists(ARTIST_FILE):
        return []
    with open(ARTIST_FILE, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

def search_and_download(artist_name):
    """
    Search YouTube for a popular song by the artist using yt-dlp
    with client fallbacks (web_safari, ios, tv, android).
    Returns (file_path, display_string) or (None, None).
    """
    search_query = f"ytsearch1:{artist_name} popular songs"
    output_template = str(DOWNLOADS_DIR / f"%(title)s.%(ext)s")

    # Client fallbacks in order of preference
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
            print(f"🔍 Trying client '{client}' for {artist_name}...", flush=True)
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
            if result.returncode == 0:
                downloaded = list(DOWNLOADS_DIR.glob("*.mp3"))
                if downloaded:
                    latest = max(downloaded, key=lambda f: f.stat().st_mtime)
                    song_title = latest.stem.replace("_", " ")
                    display = f"{song_title} - {artist_name}"
                    return latest, display
            else:
                # Print only last 200 chars of stderr for debugging
                print(f"⚠️ Client {client} failed: {result.stderr[-200:]}", flush=True)
        except subprocess.TimeoutExpired:
            print(f"⏰ Timeout with client {client}", flush=True)
        except Exception as e:
            print(f"⚠️ Exception with client {client}: {e}", flush=True)

    return None, None

def download_mp3(url, filename):
    """Download MP3 from a direct URL (not used here, but kept for compatibility)."""
    # In this version we already have the file from yt-dlp
    pass

def send_music_file(chat_id, file_path, caption):
    """Upload and send an MP3 file to a Rubika user."""
    try:
        # Step 1: Request upload URL
        resp = requests.post(REQUEST_SEND_FILE_URL, json={"type": "Music"}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != "OK":
            print(f"❌ requestSendFile error: {data}", flush=True)
            return False
        upload_url = data["data"]["upload_url"]

        # Step 2: Upload file
        with open(file_path, "rb") as f:
            files = {"file": (file_path.name, f, "audio/mpeg")}
            upload_resp = requests.post(upload_url, files=files, timeout=30)
            upload_resp.raise_for_status()
            upload_data = upload_resp.json()
            if upload_data.get("status") != "OK":
                print(f"❌ Upload error: {upload_data}", flush=True)
                return False
            file_id = upload_data["data"]["file_id"]

        # Step 3: Send file
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
    """Send a plain text message (for error notifications)."""
    try:
        payload = {"chat_id": chat_id, "text": text}
        requests.post(SEND_MESSAGE_URL, json=payload, timeout=10)
    except Exception as e:
        print(f"⚠️ Text send error: {e}", flush=True)

def cleanup():
    """Delete all temporary MP3 files."""
    for f in DOWNLOADS_DIR.glob("*.mp3"):
        try:
            f.unlink()
        except Exception:
            pass

# ========== MAIN LOOP (6‑hour run, send every 10 min) ==========

def main():
    print("="*50, flush=True)
    print("🎵 MUSIC BOT (Cloudflare WARP + yt-dlp client fallbacks)", flush=True)
    print(f"⏰ Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    print("⏳ Will run for ~5.9 hours, sending a song every 10 minutes", flush=True)
    print(f"📨 Recipients: {len(RECIPIENT_IDS)} user(s)", flush=True)
    print("="*50, flush=True)

    artists = load_artists()
    if not artists:
        print("❌ No artists found in artists.txt", flush=True)
        sys.exit(1)
    print(f"🎤 Loaded {len(artists)} artists", flush=True)

    sent_this_run = set()          # track songs sent in this 6‑hour run
    max_runtime_seconds = 5.9 * 3600
    start_time = time.time()
    iteration = 0

    while time.time() - start_time < max_runtime_seconds:
        iteration += 1
        print(f"\n🔄 ITERATION {iteration} at {datetime.now().strftime('%H:%M:%S')}", flush=True)

        # Shuffle artists for variety
        random.shuffle(artists)
        success = False

        for artist in artists:
            print(f"🎲 Trying artist: {artist}", flush=True)
            file_path, song_display = search_and_download(artist)
            if not file_path:
                print(f"⚠️ Could not download for {artist}", flush=True)
                continue

            # Create a unique identifier to avoid duplicates
            song_id = f"{artist.lower()} - {song_display.lower()}"
            if song_id in sent_this_run:
                print(f"⏩ '{song_display}' already sent this run, skipping...", flush=True)
                file_path.unlink(missing_ok=True)
                continue

            # Send to all recipients
            success_count = 0
            for uid in RECIPIENT_IDS:
                if send_music_file(uid, file_path, song_display):
                    success_count += 1

            # Delete temp file
            file_path.unlink(missing_ok=True)

            if success_count > 0:
                sent_this_run.add(song_id)
                print(f"📝 Logged '{song_display}'. Total sent this run: {len(sent_this_run)}", flush=True)
                success = True
                break
            else:
                print(f"⚠️ Could not send '{song_display}' to any recipient, not logging.", flush=True)

        if not success:
            error_msg = "❌ Could not find any new song this cycle. Check artists or try again later."
            for uid in RECIPIENT_IDS:
                send_text_message(uid, error_msg)
            print(error_msg, flush=True)

        # Wait 10 minutes, but respect the overall runtime limit
        elapsed = time.time() - start_time
        if elapsed + 600 > max_runtime_seconds:
            print("⏰ Reached runtime limit, exiting.", flush=True)
            break
        print("⏳ Sleeping 600 seconds...", flush=True)
        time.sleep(600)

    print("\n🏁 6‑hour run completed. Exiting.", flush=True)
    cleanup()

if __name__ == "__main__":
    main()
