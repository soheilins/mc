#!/usr/bin/env python3
import requests
import json
import re
import time
from urllib.parse import quote

SONG_TITLE = "no one noticed"
ARTIST = "the marias"
QUERY = f"{SONG_TITLE} {ARTIST}"

def test_qq_music():
    print("\n🔍 Testing QQ Music MP3 extraction...")
    # QQ Music search endpoint
    search_url = "https://c.y.qq.com/soso/fcgi-bin/client_search_cp"
    params = {"p": 1, "n": 1, "w": QUERY, "format": "json"}
    try:
        resp = requests.get(search_url, params=params, timeout=10)
        if resp.status_code == 200:
            # Remove JSONP wrapper if present
            text = resp.text
            # QQ returns something like: ** callback({...})
            json_match = re.search(r'\(({.*})\)', text)
            if json_match:
                data = json.loads(json_match.group(1))
            else:
                data = json.loads(text)
            songs = data.get("data", {}).get("song", {}).get("list", [])
            if songs:
                song = songs[0]
                song_id = song.get("songmid") or song.get("songid")
                if song_id:
                    # Try to get play URL – QQ requires a vkey, but there's a public endpoint
                    # Some projects use: https://u.y.qq.com/cgi-bin/musicu.fcg
                    # Simpler: try the NetEase pattern? Not correct.
                    # Let's attempt a known public API that returns play URL for a given songmid
                    play_url = f"https://api.bzqll.com/music/qq/url?id={song_id}&type=json"
                    # This is a third‑party API, may be unreliable. We'll attempt direct.
                    # Better: use y.qq.com endpoint
                    vkey_url = f"https://u.y.qq.com/cgi-bin/musicu.fcg?data={quote(json.dumps({'req_0':{'module':'vkey.GetVkeyServer','method':'CgiGetVkey','param':{'guid':'123','songmid':[song_id],'uin':'0'}}}))}"
                    r_vkey = requests.get(vkey_url, timeout=10)
                    if r_vkey.status_code == 200:
                        vkey_data = r_vkey.json()
                        purl = vkey_data.get("req_0", {}).get("data", {}).get("midurlinfo", [{}])[0].get("purl")
                        if purl:
                            mp3 = f"https://dl.stream.qqmusic.qq.com/{purl}"
                            # Verify by downloading first 2KB
                            head = requests.head(mp3, timeout=5)
                            if head.status_code == 200:
                                return "✅", f"QQ Music MP3: {mp3[:80]}"
                            else:
                                return "⚠️", "Found URL but not accessible"
        return "❌", "Could not extract MP3"
    except Exception as e:
        return "❌", f"Exception: {str(e)[:100]}"

def test_jiosaavn():
    print("\n🔍 Testing JioSaavn MP3 extraction...")
    try:
        # Search
        search_url = "https://www.jiosaavn.com/api.php"
        params = {"__call": "search.getResults", "q": QUERY, "p": 1, "n": 1, "ctx": "web6dot0", "api_version": 4, "_format": "json"}
        resp = requests.get(search_url, params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            songs = data.get("results", [])
            if songs:
                song = songs[0]
                # JioSaavn API returns downloadUrl as an array
                download_urls = song.get("downloadUrl", [])
                if download_urls and isinstance(download_urls, list):
                    # The last item is often 320kbps
                    mp3 = download_urls[-1].get("link")
                    if mp3:
                        # Verify
                        head = requests.head(mp3, timeout=5)
                        if head.status_code == 200:
                            return "✅", f"JioSaavn MP3: {mp3[:80]}"
                        else:
                            return "⚠️", "URL exists but not accessible"
        return "❌", "No MP3 link found"
    except Exception as e:
        return "❌", f"Exception: {str(e)[:100]}"

def test_mixcloud():
    print("\n🔍 Testing Mixcloud MP3 extraction...")
    try:
        # Search for cloudcast
        search_url = "https://api.mixcloud.com/search/"
        params = {"q": QUERY, "type": "cloudcast", "limit": 1}
        resp = requests.get(search_url, params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("data"):
                cloudcast = data["data"][0]
                # Mixcloud provides stream URLs in the cloudcast object
                # Usually: audio_url or stream_url
                stream_url = cloudcast.get("audio_url") or cloudcast.get("stream_url")
                if stream_url:
                    # Check if it's a direct MP3
                    head = requests.head(stream_url, timeout=5, allow_redirects=True)
                    if head.status_code == 200 and 'audio/mpeg' in head.headers.get('content-type', ''):
                        return "✅", f"Mixcloud MP3: {stream_url[:80]}"
                    else:
                        # Some Mixcloud streams are HLS, not direct MP3
                        return "⚠️", "Found but not direct MP3"
                else:
                    # Try to get from the 'url' field
                    cloudcast_url = cloudcast.get("url")
                    if cloudcast_url:
                        # Mixcloud pages load player with JSON data; we'd need to scrape.
                        # For now, we'll mark as non‑functional for direct MP3.
                        return "⚠️", "Cloudcast found but no direct MP3 link"
        return "❌", "No cloudcast found"
    except Exception as e:
        return "❌", f"Exception: {str(e)[:100]}"

def test_bandcamp():
    print("\n🔍 Testing Bandcamp MP3 extraction...")
    try:
        # Bandcamp search returns HTML, we need to extract track file URL
        search_url = f"https://bandcamp.com/search?q={quote(QUERY)}"
        resp = requests.get(search_url, timeout=10)
        if resp.status_code == 200:
            # Look for the first track result and its data-file-url attribute
            # Pattern: data-file-url="https://...mp3"
            match = re.search(r'data-file-url="([^"]+\.mp3)"', resp.text)
            if match:
                mp3 = match.group(1)
                head = requests.head(mp3, timeout=5)
                if head.status_code == 200:
                    return "✅", f"Bandcamp MP3: {mp3[:80]}"
                else:
                    return "⚠️", "Found MP3 URL but not accessible"
            else:
                # Also check for data-audio-url
                match2 = re.search(r'data-audio-url="([^"]+\.mp3)"', resp.text)
                if match2:
                    mp3 = match2.group(1)
                    head = requests.head(mp3, timeout=5)
                    if head.status_code == 200:
                        return "✅", f"Bandcamp MP3: {mp3[:80]}"
                    else:
                        return "⚠️", "Found MP3 URL but not accessible"
        return "❌", "No MP3 found on search page"
    except Exception as e:
        return "❌", f"Exception: {str(e)[:100]}"

# ----------------------------------------------------------------------
def main():
    print("🎵 Testing MP3 extraction from music services")
    results = []
    for name, func in [("QQ Music", test_qq_music), ("JioSaavn", test_jiosaavn), ("Mixcloud", test_mixcloud), ("Bandcamp", test_bandcamp)]:
        print(f"\n{'='*50}\n{name}")
        status, msg = func()
        print(f"{status} {msg}")
        results.append((name, status, msg))
    print("\n" + "="*50)
    print("FINAL CONCLUSION")
    print("="*50)
    for name, status, msg in results:
        print(f"{name}: {status}")
    if any(r[1] == "✅" for r in results):
        print("\n💡 Some services returned a working MP3 link. You can use them in your music bot.")
    else:
        print("\n💡 None of the services returned a working MP3 link. Only Deezer preview works.")

if __name__ == "__main__":
    main()
