#!/usr/bin/env python3
import os
import sys
import random
import requests
import subprocess
from pathlib import Path

# ========== CONFIGURATION ==========
RUBIKA_TOKEN = os.environ.get("RUBIKA_TOKEN", "")
if not RUBIKA_TOKEN:
    print("❌ RUBIKA_TOKEN missing", flush=True)
    sys.exit(1)

RECIPIENT_IDS = [
    "b0JWE2R0cEO00b3bfc6eb91ee17556ca",   # your user ID
]

ARTIST_FILE = "artists.txt"
LOG_FILE = "sent_songs.txt"
DOWNLOADS_DIR = Path("downloads")
DOWNLOADS_DIR.mkdir(exist_ok=True)

BASE_API = f"https://botapi.rubika.ir/v3/{RUBIKA_TOKEN}"
REQUEST_SEND_FILE_URL = f"{BASE_API}/requestSendFile"
SEND_FILE_URL = f"{BASE_API}/sendFile"
SEND_MESSAGE_URL = f"{BASE_API}/sendMessage"

# ========== FUNCTIONS ==========

def load_artists():
    if not os.path.exists(ARTIST_FILE):
        return []
    with open(ARTIST_FILE, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

def load_sent_songs():
    if not os.path.exists(LOG_FILE):
        return set()
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        return {line.strip() for line in f if line.strip()}

def save_sent_song(song_id):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(song_id + "\n")

def search_and_download(artist_name):
    """Download a random popular song by the artist using yt-dlp with client fallbacks."""
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
                print(f"⚠️ Client {client} failed (returncode {result.returncode})", flush=True)
        except Exception as e:
            print(f"⚠️ Exception with {client}: {e}", flush=True)
    return None, None

def send_music_file(chat_id, file_path, caption):
    try:
        resp = requests.post(REQUEST_SEND_FILE_URL, json={"type": "Music"}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != "OK":
            return False
        upload_url = data["data"]["upload_url"]
        with open(file_path, "rb") as f:
            files = {"file": (file_path.name, f, "audio/mpeg")}
            up_resp = requests.post(upload_url, files=files, timeout=30)
            up_resp.raise_for_status()
            up_data = up_resp.json()
            if up_data.get("status") != "OK":
                return False
            file_id = up_data["data"]["file_id"]
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

# ========== MAIN (ONE‑SHOT) ==========

def main():
    print("="*50, flush=True)
    print("🎵 MUSIC BOT (One‑Shot with WARP & commit)", flush=True)
    print("="*50, flush=True)

    artists = load_artists()
    if not artists:
        print("❌ No artists in artists.txt", flush=True)
        sys.exit(1)

    sent_songs = load_sent_songs()
    print(f"📝 Already sent (from log): {len(sent_songs)} songs", flush=True)

    # Shuffle and try artists until we find a new song
    random.shuffle(artists)
    success = False
    for artist in artists:
        print(f"🎲 Trying artist: {artist}", flush=True)
        file_path, song_display = search_and_download(artist)
        if not file_path:
            continue

        song_id = f"{artist.lower()} - {song_display.lower()}"
        if song_id in sent_songs:
            print(f"⏩ '{song_display}' already sent before, skipping.", flush=True)
            file_path.unlink(missing_ok=True)
            continue

        # Send to all recipients
        for uid in RECIPIENT_IDS:
            if send_music_file(uid, file_path, song_display):
                success = True
        file_path.unlink(missing_ok=True)

        if success:
            save_sent_song(song_id)
            print(f"📝 Logged '{song_display}' to {LOG_FILE}", flush=True)
            break
        else:
            print(f"⚠️ Failed to send '{song_display}', not logging.", flush=True)

    if not success:
        error_msg = "❌ Could not find any new song. Check artists or try again later."
        for uid in RECIPIENT_IDS:
            send_text_message(uid, error_msg)
        print(error_msg, flush=True)

    cleanup()
    print("🏁 One‑shot run finished.", flush=True)

if __name__ == "__main__":
    main()
