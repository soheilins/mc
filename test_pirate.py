#!/usr/bin/env python3
import requests
import re
import time
import urllib.parse

QUERY = "The Marías no one noticed"

def test_y2mate():
    print("\n--- Testing Y2Mate (YouTube converter) ---")
    try:
        # Y2Mate requires a search or direct video URL. We'll use a direct YouTube video ID (search first? too heavy)
        # Instead, we use a known public converter API.
        # Many projects use y2mate's API: https://www.y2mate.com/mates/analyze/ajax
        # But it's complex. We'll skip to a simpler one.
        return "Skipped - requires video URL"
    except Exception as e:
        return f"Error: {e}"

def test_savefrom():
    print("\n--- Testing SaveFrom.net API ---")
    try:
        url = "https://en.savefrom.net/1-download-youtube-mp3/"
        # This is a website, not an API. We would need to scrape.
        return "Skipped - scraping required"
    except Exception as e:
        return f"Error: {e}"

def test_invidious_audio():
    print("\n--- Testing Invidious direct audio (fallback) ---")
    instances = [
        "https://inv.vern.cc",
        "https://yewtu.be",
        "https://invidious.privacydev.net"
    ]
    for inst in instances:
        try:
            # Search for video
            search_url = f"{inst}/api/v1/search?q={urllib.parse.quote(QUERY)}&type=video"
            r = requests.get(search_url, timeout=10)
            if r.status_code == 200:
                data = r.json()
                if data:
                    video_id = data[0].get("videoId")
                    if video_id:
                        # Get audio stream
                        stream_url = f"{inst}/api/v1/videos/{video_id}"
                        sr = requests.get(stream_url, timeout=10)
                        if sr.status_code == 200:
                            video_data = sr.json()
                            for fmt in video_data.get("adaptiveFormats", []):
                                if fmt.get("type", "").startswith("audio/"):
                                    audio_url = fmt.get("url")
                                    if audio_url:
                                        return f"✅ Working: {audio_url[:80]}..."
                            return "⚠️ Found video but no audio URL"
        except Exception as e:
            continue
    return "❌ No working Invidious instance"

def test_youtube_audio_direct():
    print("\n--- Testing YouTube direct audio via yt-dlp (with client spoof) ---")
    # This requires yt-dlp, which we don't want to use, but we already know it fails.
    return "youtube-dl required, but we know it's blocked"

def test_music_api():
    print("\n--- Testing MusicAPI (unofficial) ---")
    url = "https://musicapi.vercel.app/api/search"
    params = {"q": QUERY}
    try:
        r = requests.get(url, params=params, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get("tracks"):
                track = data["tracks"][0]
                mp3 = track.get("url")
                if mp3:
                    return f"✅ MP3: {mp3[:80]}..."
                else:
                    return "⚠️ No URL in response"
        return f"❌ HTTP {r.status_code}"
    except Exception as e:
        return f"❌ {e}"

def test_audiomack_direct():
    print("\n--- Testing Audiomack direct stream (scrape) ---")
    search_url = f"https://audiomack.com/search/songs?q={urllib.parse.quote(QUERY)}"
    try:
        r = requests.get(search_url, timeout=10)
        if r.status_code == 200:
            # Look for data-stream-url attribute
            match = re.search(r'data-stream-url="([^"]+)"', r.text)
            if match:
                mp3 = match.group(1)
                return f"✅ MP3: {mp3[:80]}..."
            else:
                return "⚠️ No stream URL found"
        return f"❌ HTTP {r.status_code}"
    except Exception as e:
        return f"❌ {e}"

def test_jiosaavn_direct():
    print("\n--- Testing JioSaavn (already did) ---")
    # Already tested, fails
    return "Known to fail (404/rate limit)"

def test_netdisaster():
    print("\n--- Testing NetDisaster (public YouTube proxy) ---")
    # NetDisaster is a public Invidious-like instance
    url = "https://netdisaster.me/api/v1/search?q=" + urllib.parse.quote(QUERY)
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data:
                video_id = data[0].get("videoId")
                if video_id:
                    audio_url = f"https://netdisaster.me/api/v1/videos/{video_id}/dash/audio"
                    return f"✅ Audio URL: {audio_url}"
        return "❌ Failed"
    except Exception as e:
        return f"❌ {e}"

def main():
    print("Testing pirate/unofficial music sources...")
    results = []
    for test_func in [test_invidious_audio, test_music_api, test_audiomack_direct, test_netdisaster]:
        res = test_func()
        print(res)
        results.append(res)
    print("\nSummary:")
    for r in results:
        if r.startswith("✅"):
            print(r)

if __name__ == "__main__":
    main()
