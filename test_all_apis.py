#!/usr/bin/env python3
import requests
import json
import time
import re

QUERY = "no one noticed the marias"
SONG_TITLE = "no one noticed"
ARTIST = "the marias"

tests = []

def add_test(name, func):
    tests.append((name, func))

# ----------------------------------------------------------------------
# 1. JioSaavn
def jiosaavn():
    url = "https://saavn.me/search/songs"
    params = {"query": QUERY}
    try:
        r = requests.get(url, params=params, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get("data", {}).get("results"):
                t = data["data"]["results"][0]
                mp3 = t.get("downloadUrl", [{}])[-1].get("link")
                return "✅", f"{t['name']} - {t['primaryArtists']} | MP3: {mp3[:50] if mp3 else 'no'}"
        return "❌", f"HTTP {r.status_code}"
    except Exception as e:
        return "❌", str(e)
add_test("JioSaavn", jiosaavn)

# ----------------------------------------------------------------------
# 2. Audius
def audius():
    url = "https://discoveryprovider.audius.co/v1/tracks/search"
    params = {"query": QUERY, "limit": 1}
    try:
        r = requests.get(url, params=params, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get("data"):
                t = data["data"][0]
                track_id = t["id"]
                stream_url = f"https://discoveryprovider.audius.co/v1/tracks/{track_id}/stream"
                sr = requests.head(stream_url, allow_redirects=True, timeout=5)
                if sr.status_code in (200, 302):
                    return "✅", f"{t['title']} - {t['user']['name']} | STREAM: {stream_url}"
                else:
                    return "⚠️", f"{t['title']} but stream not accessible"
        return "❌", f"HTTP {r.status_code}"
    except Exception as e:
        return "❌", str(e)
add_test("Audius", audius)

# ----------------------------------------------------------------------
# 3. Archive.org
def archive_org():
    url = "https://archive.org/advancedsearch.php"
    params = {
        "q": f"title:({SONG_TITLE}) AND creator:({ARTIST}) AND mediatype:(audio)",
        "fl[]": "identifier,title,creator,downloads",
        "rows": 1,
        "page": 1,
        "output": "json"
    }
    try:
        r = requests.get(url, params=params, timeout=15)
        if r.status_code == 200:
            data = r.json()
            docs = data.get("response", {}).get("docs", [])
            if docs:
                ident = docs[0]["identifier"]
                mp3 = f"https://archive.org/download/{ident}/{ident}_vbr.mp3"
                h = requests.head(mp3, timeout=5)
                if h.status_code == 200:
                    return "✅", f"{docs[0]['title']} | MP3: {mp3}"
                else:
                    return "⚠️", f"Found but MP3 not available"
        return "❌", "No results"
    except Exception as e:
        return "❌", str(e)
add_test("Archive.org", archive_org)

# ----------------------------------------------------------------------
# 4. Jamendo
def jamendo():
    url = "https://api.jamendo.com/v3.0/tracks/"
    params = {
        "client_id": "ec9122a4",
        "format": "json",
        "limit": 1,
        "search": QUERY
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get("results"):
                t = data["results"][0]
                audio = t.get("audio")
                if audio:
                    return "✅", f"{t['name']} - {t['artist_name']} | MP3: {audio}"
        return "❌", f"No results"
    except Exception as e:
        return "❌", str(e)
add_test("Jamendo", jamendo)

# ----------------------------------------------------------------------
# 5. Deezer preview
def deezer():
    url = f"https://api.deezer.com/search?q={QUERY.replace(' ', '%20')}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get("data"):
                t = data["data"][0]
                preview = t.get("preview")
                if preview:
                    return "✅", f"{t['title']} - {t['artist']['name']} | PREVIEW: {preview}"
                else:
                    return "⚠️", f"{t['title']} but no preview"
        return "❌", "No results"
    except Exception as e:
        return "❌", str(e)
add_test("Deezer (preview)", deezer)

# ----------------------------------------------------------------------
# 6. Audiomack (scrape)
def audiomack():
    url = f"https://audiomack.com/search/songs?q={QUERY.replace(' ', '+')}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            if 'data-stream-url' in r.text:
                match = re.search(r'data-stream-url="([^"]+)"', r.text)
                if match:
                    return "✅", f"MP3 found: {match.group(1)}"
                else:
                    return "⚠️", "Page loaded but no direct MP3 extracted"
        return "❌", f"HTTP {r.status_code}"
    except Exception as e:
        return "❌", str(e)
add_test("Audiomack (scrape)", audiomack)

# ----------------------------------------------------------------------
# 7. Free Music Archive
def fma():
    url = "https://freemusicarchive.org/api/get/tracks.json"
    params = {"limit": 1, "search": QUERY}
    try:
        r = requests.get(url, params=params, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get("rows"):
                t = data["rows"][0]
                mp3 = t.get("track_file_url")
                if mp3:
                    return "✅", f"{t['track_title']} - {t['artist_name']} | MP3: {mp3}"
        return "❌", "No results"
    except Exception as e:
        return "❌", str(e)
add_test("Free Music Archive", fma)

# ----------------------------------------------------------------------
# 8. NoiseTrade
def noisetrade():
    url = "https://api.noisetrade.com/api/v2/music/search"
    params = {"q": QUERY, "limit": 1}
    try:
        r = requests.get(url, params=params, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get("results"):
                return "⚠️", f"Found {len(data['results'])} results but no direct MP3"
        return "❌", f"HTTP {r.status_code}"
    except Exception as e:
        return "❌", str(e)
add_test("NoiseTrade", noisetrade)

# ----------------------------------------------------------------------
# 9. Mixcloud
def mixcloud():
    url = f"https://api.mixcloud.com/search/?q={QUERY.replace(' ', '%20')}&type=cloudcast"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get("data"):
                return "⚠️", f"Found {len(data['data'])} cloudcasts, but MP3 not direct"
        return "❌", "No results"
    except Exception as e:
        return "❌", str(e)
add_test("Mixcloud", mixcloud)

# ----------------------------------------------------------------------
# 10. HearThis.at
def hearthis():
    url = f"https://hearthis.at/api-v2/search/?q={QUERY}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get("results"):
                t = data["results"][0]
                stream = t.get("stream_url")
                if stream:
                    return "✅", f"{t['title']} - {t['user']['username']} | MP3: {stream}"
        return "❌", "No results"
    except Exception as e:
        return "❌", str(e)
add_test("HearThis.at", hearthis)

# ----------------------------------------------------------------------
# 11. ReverbNation
def reverbnation():
    url = f"https://api.reverbnation.com/artist/search?name={ARTIST.replace(' ', '%20')}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get("artists"):
                artist_id = data["artists"][0]["id"]
                songs_url = f"https://api.reverbnation.com/artist/{artist_id}/songs"
                sr = requests.get(songs_url, timeout=10)
                if sr.status_code == 200:
                    songs = sr.json()
                    if songs:
                        mp3 = songs[0].get("url") or songs[0].get("file_url")
                        if mp3:
                            return "✅", f"{songs[0]['name']} | MP3: {mp3}"
        return "❌", "No MP3 found"
    except Exception as e:
        return "❌", str(e)
add_test("ReverbNation", reverbnation)

# ----------------------------------------------------------------------
# 12. Tindeck
def tindeck():
    url = f"https://tindeck.com/api/v1/search?q={QUERY}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get("tracks"):
                mp3 = data["tracks"][0].get("url")
                if mp3:
                    return "✅", f"{data['tracks'][0]['title']} | MP3: {mp3}"
        return "❌", "No results"
    except Exception as e:
        return "❌", str(e)
add_test("Tindeck", tindeck)

# ----------------------------------------------------------------------
# 13. GitHub code search (for .mp3 files)
def github_audio():
    url = "https://api.github.com/search/code"
    headers = {"Accept": "application/vnd.github.v3+json"}
    params = {"q": f"{SONG_TITLE} extension:mp3"}
    try:
        r = requests.get(url, headers=headers, params=params, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get("items"):
                item = data["items"][0]
                raw_url = f"https://raw.githubusercontent.com/{item['repository']['full_name']}/main/{item['path']}"
                return "✅", f"Potential MP3: {raw_url}"
        return "❌", "No MP3s found"
    except Exception as e:
        return "❌", str(e)
add_test("GitHub code search", github_audio)

# ----------------------------------------------------------------------
# 14. Acast (podcast)
def acast():
    url = f"https://feeds.acast.com/api/v1/search?q={QUERY}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get("episodes"):
                audio = data["episodes"][0].get("audioUrl")
                if audio:
                    return "✅", f"{data['episodes'][0]['title']} | MP3: {audio}"
        return "❌", "No results"
    except Exception as e:
        return "❌", str(e)
add_test("Acast", acast)

# ----------------------------------------------------------------------
# 15. Internet Archive (broader search)
def archive_wide():
    url = "https://archive.org/advancedsearch.php"
    params = {
        "q": f"({SONG_TITLE}) AND ({ARTIST})",
        "fl[]": "identifier,title",
        "rows": 1,
        "output": "json"
    }
    try:
        r = requests.get(url, params=params, timeout=15)
        if r.status_code == 200:
            data = r.json()
            docs = data.get("response", {}).get("docs", [])
            if docs:
                ident = docs[0]["identifier"]
                mp3 = f"https://archive.org/download/{ident}/{ident}_vbr.mp3"
                return "✅", f"Found: {mp3}"
        return "❌", "No results"
    except Exception as e:
        return "❌", str(e)
add_test("Archive.org (broad)", archive_wide)

# ----------------------------------------------------------------------
# 16-20: Other sources (some may be unavailable)
def not_implemented(name):
    return "⚠️", "Not implemented / API unavailable"
add_test("Bandcamp (no public API)", lambda: not_implemented("Bandcamp"))
add_test("SoundCloud (requires dynamic client_id)", lambda: not_implemented("SoundCloud"))
add_test("Spotify (requires API key)", lambda: not_implemented("Spotify"))
add_test("Last.fm (requires key)", lambda: not_implemented("Last.fm"))
add_test("Genius (lyrics only)", lambda: not_implemented("Genius"))

# ----------------------------------------------------------------------
# Run all
def main():
    print(f"🔍 Testing {len(tests)} API sources for '{QUERY}'")
    print("="*80)
    results = []
    for name, test_func in tests:
        print(f"\n⏳ {name}...")
        start = time.time()
        try:
            status, msg = test_func()
        except Exception as e:
            status, msg = "❌", str(e)
        elapsed = time.time() - start
        print(f"   {status} {msg[:150]} ({elapsed:.1f}s)")
        results.append((name, status, msg))
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    successes = [r for r in results if r[1].startswith("✅")]
    warnings = [r for r in results if r[1].startswith("⚠️")]
    failures = [r for r in results if r[1].startswith("❌")]
    print(f"✅ Working (direct MP3 or stream): {len(successes)}")
    for name, status, msg in successes:
        print(f"  ✅ {name}: {msg[:100]}")
    print(f"⚠️ Partial/Unknown: {len(warnings)}")
    for name, status, msg in warnings[:5]:
        print(f"  ⚠️ {name}: {msg[:80]}")
    print(f"❌ Failed: {len(failures)}")
    if successes:
        print("\n💡 Good news! You can use any of the ✅ sources above to build your music bot.")
    else:
        print("\n💡 No source returned a direct MP3. You would need to use a service that requires login or run the bot outside GitHub Actions.")

if __name__ == "__main__":
    main()
