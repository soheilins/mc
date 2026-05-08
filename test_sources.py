#!/usr/bin/env python3
import subprocess
import requests
import json
import sys

def test_ytdlp_youtube():
    print("\n=== Testing yt-dlp YouTube (web_safari) ===")
    cmd = [
        "yt-dlp",
        "ytsearch1:no one noticed the marias",
        "-x", "--audio-format", "mp3",
        "--extractor-args", "youtube:player_client=web_safari;formats=missing_pot",
        "--simulate", "--print", "title"
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0 and result.stdout.strip():
            print(f"✅ SUCCESS - Found: {result.stdout.strip()}")
        else:
            print(f"❌ FAILED - Return code {result.returncode}")
            print(f"   stderr: {result.stderr[:200]}")
    except Exception as e:
        print(f"❌ Exception: {e}")

def test_ytdlp_youtube_ios():
    print("\n=== Testing yt-dlp YouTube (ios) ===")
    cmd = [
        "yt-dlp",
        "ytsearch1:no one noticed the marias",
        "-x", "--audio-format", "mp3",
        "--extractor-args", "youtube:player_client=ios;formats=missing_pot",
        "--simulate", "--print", "title"
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0 and result.stdout.strip():
            print(f"✅ SUCCESS - Found: {result.stdout.strip()}")
        else:
            print(f"❌ FAILED - Return code {result.returncode}")
            print(f"   stderr: {result.stderr[:200]}")
    except Exception as e:
        print(f"❌ Exception: {e}")

def test_ytdlp_soundcloud():
    print("\n=== Testing yt-dlp SoundCloud ===")
    cmd = [
        "yt-dlp",
        "scsearch1:no one noticed marias",
        "-x", "--audio-format", "mp3",
        "--simulate", "--print", "title"
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0 and result.stdout.strip():
            print(f"✅ SUCCESS - Found: {result.stdout.strip()}")
        else:
            print(f"❌ FAILED - Return code {result.returncode}")
            print(f"   stderr: {result.stderr[:200]}")
    except Exception as e:
        print(f"❌ Exception: {e}")

def test_jiosaavn_api():
    print("\n=== Testing JioSaavn API ===")
    url = "https://saavn.me/search/songs"
    params = {"query": "no one noticed the marias"}
    try:
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("data", {}).get("results"):
                track = data["data"]["results"][0]
                title = track.get("name")
                artist = track.get("primaryArtists")
                print(f"✅ SUCCESS - Found: {title} by {artist}")
            else:
                print("❌ FAILED - No results")
        else:
            print(f"❌ FAILED - HTTP {resp.status_code}")
    except Exception as e:
        print(f"❌ Exception: {e}")

def test_audius_api():
    print("\n=== Testing Audius API (public gateway) ===")
    # Audius public API (no key)
    url = "https://discoveryprovider.audius.co/v1/tracks/search"
    params = {"query": "no one noticed marias", "limit": 1}
    try:
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("data"):
                track = data["data"][0]
                title = track.get("title")
                artist = track.get("user", {}).get("name")
                print(f"✅ SUCCESS - Found: {title} by {artist}")
                # Audius provides streaming URLs but often require a token.
                # For now just metadata.
            else:
                print("❌ FAILED - No results")
        else:
            print(f"❌ FAILED - HTTP {resp.status_code}")
    except Exception as e:
        print(f"❌ Exception: {e}")

def test_ytdlp_invidious_via_proxy():
    print("\n=== Testing yt-dlp with Invidious proxy ===")
    # Use a known Invidious instance as proxy
    cmd = [
        "yt-dlp",
        "ytsearch1:no one noticed the marias",
        "-x", "--audio-format", "mp3",
        "--proxy", "https://inv.vern.cc",
        "--simulate", "--print", "title"
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode == 0 and result.stdout.strip():
            print(f"✅ SUCCESS - Found: {result.stdout.strip()}")
        else:
            print(f"❌ FAILED - Return code {result.returncode}")
            print(f"   stderr: {result.stderr[:200]}")
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    print("🔍 Testing music sources from GitHub Actions...")
    test_ytdlp_youtube()
    test_ytdlp_youtube_ios()
    test_ytdlp_soundcloud()
    test_jiosaavn_api()
    test_audius_api()
    test_ytdlp_invidious_via_proxy()
    print("\n🏁 Tests complete.")
