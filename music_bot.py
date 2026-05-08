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
    print("❌ RUBIKA_TOKEN missing", flush=True)
    sys.exit(1)

# Your Rubika user ID
RECIPIENT_IDS = [
    "b0JWE2R0cEO00b3bfc6eb91ee17556ca",
]

ARTIST_FILE = "artists.txt"
DOWNLOADS_DIR = Path("downloads")
DOWNLOADS_DIR.mkdir(exist_ok=True)

# Rubika endpoints
BASE_API = f"https://botapi.rubika.ir/v3/{RUBIKA_TOKEN}"
REQUEST_SEND_FILE_URL = f"{BASE_API}/requestSendFile"
SEND_FILE_URL = f"{BASE_API}/sendFile"
SEND_MESSAGE_URL = f"{BASE_API}/sendMessage"

# JioSaavn API (no key required)
JIO_SAVN_API = "https://saavn.me/search/songs"

# ========== HELPER FUNCTIONS ==========

def load_artists():
    if not os.path.exists(ARTIST_FILE):
        return []
    with open(ARTIST_FILE, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

def get_song_from_jiosaavn(artist_name):
    """Search JioSaavn for a popular song by artist, return (mp3_url, song_title, artist)."""
    try:
        resp = requests.get(JIO_SAVN_API, params={"query": artist_name}, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if data.get("data", {}).get("results"):
            songs = data["data"]["results"]
            # Filter for songs where artist name matches (case insensitive)
            matched = []
            for song in songs:
                if artist_name.lower() in song.get("artist", "").lower():
                    matched.append(song)
            if not matched:
                # fallback: take first few results anyway
                matched = songs[:5]
            if matched:
                track = random.choice(matched)
                mp3_url = track.get("downloadUrl", [{}])[-1].get("link") if track.get("downloadUrl") else None
                if not mp3_url:
                    return None, None
                song_title = track.get("name", "Unknown")
                song_artist = track.get("primaryArtists", artist_name)
                display = f"{song_title} - {song_artist}"
                return mp3_url, display
    except Exception as e:
        print(f"⚠️ JioSaavn error for {artist_name}: {e}", flush=True)
    return None, None

def download_mp3(url, filename):
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
        print(f"✅ Sent '{caption}'", flush=True)
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

# ========== MAIN LOOP ==========

def main():
    print("="*50, flush=True)
    print("🎵 MUSIC BOT (JioSaavn API)", flush=True)
    print(f"⏰ Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    print("⏳ Running for ~5.9 hours, song every 10 minutes", flush=True)
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
            mp3_url, song_display = get_song_from_jiosaavn(artist)
            if not mp3_url:
                print(f"⚠️ No song found for {artist}", flush=True)
                continue

            song_id = f"{artist.lower()} - {song_display.lower()}"
            if song_id in sent_this_run:
                print(f"⏩ Already sent this run, skipping...", flush=True)
                continue

            # download MP3
            safe_fn = f"{song_display.replace(' ', '_')[:50]}.mp3"
            file_path = download_mp3(mp3_url, safe_fn)
            if not file_path:
                continue

            # send
            sent_ok = False
            for uid in RECIPIENT_IDS:
                if send_music_file(uid, file_path, song_display):
                    sent_ok = True
            file_path.unlink(missing_ok=True)

            if sent_ok:
                sent_this_run.add(song_id)
                print(f"📝 Logged. Total this run: {len(sent_this_run)}", flush=True)
                success = True
                break
            else:
                print(f"⚠️ Send failed, not logging", flush=True)

        if not success:
            error_msg = "❌ Could not find/send any new song this cycle."
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
    print("🏁 6-hour run completed.", flush=True)

if __name__ == "__main__":
    main()
