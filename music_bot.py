#!/usr/bin/env python3
import os
import sys
import random
import requests
import time
from pathlib import Path
from datetime import datetime

# ========== CONFIGURATION ==========
RUBIKA_TOKEN = os.environ.get("RUBIKA_TOKEN", "")
if not RUBIKA_TOKEN:
    print("❌ RUBIKA_TOKEN environment variable not set", flush=True)
    sys.exit(1)

# Your Rubika user ID (hardcoded)
RECIPIENT_IDS = [
    "b0JWE2R0cEO00b3bfc6eb91ee17556ca",   # your user ID
    # Add more user IDs here if needed, one per line
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

# MusicAPI endpoint (no API key required)
MUSIC_API = "https://musicapi.vercel.app/api/search"

# ========== HELPER FUNCTIONS ==========

def load_artists():
    """Load artist list from artists.txt (one per line)."""
    if not os.path.exists(ARTIST_FILE):
        print(f"❌ Artist file '{ARTIST_FILE}' not found", flush=True)
        return []
    with open(ARTIST_FILE, "r", encoding="utf-8") as f:
        artists = [line.strip() for line in f if line.strip()]
    return artists

def get_song_from_api(artist_name):
    """
    Search MusicAPI for a popular song by the artist.
    Returns (mp3_url, song_display_string) or (None, None).
    """
    params = {"q": artist_name}
    try:
        resp = requests.get(MUSIC_API, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if data.get("tracks") and len(data["tracks"]) > 0:
            # Pick a random track from the first few results
            track = random.choice(data["tracks"])
            mp3_url = track.get("url")
            song_title = track.get("title", "Unknown Title")
            artist = track.get("artist", artist_name)
            display = f"{song_title} - {artist}"
            return mp3_url, display
    except Exception as e:
        print(f"⚠️ MusicAPI error for {artist_name}: {e}", flush=True)
    return None, None

def download_mp3(url, filename):
    """Download MP3 from a direct URL to the downloads folder."""
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        file_path = DOWNLOADS_DIR / filename
        with open(file_path, "wb") as f:
            f.write(resp.content)
        return file_path
    except Exception as e:
        print(f"❌ Download failed: {e}", flush=True)
        return None

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
        print(f"❌ Send error to {chat_id}: {e}", flush=True)
        return False

def send_text_message(chat_id, text):
    """Send a plain text message (for error notifications)."""
    try:
        payload = {"chat_id": chat_id, "text": text}
        requests.post(SEND_MESSAGE_URL, json=payload, timeout=10)
    except Exception as e:
        print(f"⚠️ Text send error to {chat_id}: {e}", flush=True)

def cleanup():
    """Delete all temporary MP3 files."""
    for f in DOWNLOADS_DIR.glob("*.mp3"):
        try:
            f.unlink()
        except Exception:
            pass

# ========== MAIN LOOP ==========
def main():
    print("="*50, flush=True)
    print("🎵 MUSIC BOT STARTED (MusicAPI version)", flush=True)
    print(f"⏰ Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    print("⏳ Will run for ~5.9 hours, sending a song every 10 minutes", flush=True)
    print(f"📨 Recipients: {len(RECIPIENT_IDS)} user(s)", flush=True)
    print("="*50, flush=True)

    artists = load_artists()
    if not artists:
        print("❌ No artists found in artists.txt", flush=True)
        sys.exit(1)
    print(f"🎤 Loaded {len(artists)} artists", flush=True)

    sent_this_run = set()          # track songs sent in this 6-hour run
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
            mp3_url, song_display = get_song_from_api(artist)
            if not mp3_url:
                print(f"⚠️ No results for {artist}", flush=True)
                continue

            # Create a unique identifier to avoid duplicates
            song_id = f"{artist.lower()} - {song_display.lower()}"
            if song_id in sent_this_run:
                print(f"⏩ '{song_display}' already sent this run, skipping...", flush=True)
                continue

            # Download the MP3
            safe_filename = f"{song_display.replace(' ', '_')[:50]}.mp3"
            file_path = download_mp3(mp3_url, safe_filename)
            if not file_path:
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

    print("\n🏁 6-hour run completed. Exiting.", flush=True)
    cleanup()

if __name__ == "__main__":
    main()
