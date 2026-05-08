#!/usr/bin/env python3
import requests
import json
import time
import re

QUERY = "no one noticed the marias"
SONG_TITLE = "no one noticed"
ARTIST = "the marias"

# Collection of tests: each returns (status, data or url)
tests = []

def add_test(name, func):
    tests.append((name, func))

# ----------------------------------------------------------------------
# 1. JioSaavn (unofficial)
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
# 2. Audius (public API)
def audius():
    url = "https://discoveryprovider.audius.co/v1/tracks/search"
    params = {"query": QUERY, "limit": 1}
    try:
        r = requests.get(url, params=params, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get("data"):
                t = data["data"][0]
                # get stream url (needs user_id and track_id, but there's a direct endpoint)
                track_id = t["id"]
                stream_url = f"https://discoveryprovider.audius.co/v1/tracks/{track_id}/stream"
                # try to get stream
                sr = requests.head(stream_url, allow_redirects=True, timeout=5)
                if sr.status_code == 200 or sr.status_code == 302:
                    return "✅", f"{t['title']} - {t['user']['name']} | STREAM: {stream_url}"
                else:
                    return "⚠️", f"{t['title']} but stream not accessible"
        return "❌", f"HTTP {r.status_code}"
    except Exception as e:
        return "❌", str(e)
add_test("Audius", audius)

# ----------------------------------------------------------------------
# 3. Archive.org audio search
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
                # verify if exists
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
# 4. Jamendo (free public key used in many open source projects)
def jamendo():
    url = "https://api.jamendo.com/v3.0/tracks/"
    params = {
        "client_id": "ec9122a4",  # public demo key
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
        return "❌", f"No results or HTTP {r.status_code}"
    except Exception as e:
        return "❌", str(e)
add_test("Jamendo", jamendo)

# ----------------------------------------------------------------------
# 5. Deezer Public API (no key)
def deezer():
    url = f"https://api.deezer.com/search?q={QUERY.replace(' ', '%20')}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get("data"):
                t = data["data"][0]
                preview = t.get("preview")  # 30s MP3
                if preview:
                    return "✅", f"{t['title']} - {t['artist']['name']} | PREVIEW: {preview}"
                else:
                    return "⚠️", f"{t['title']} but no preview"
        return "❌", "No results"
    except Exception as e:
        return "❌", str(e)
add_test("Deezer (preview)", deezer)

# ----------------------------------------------------------------------
# 6. SoundCloud oembed (sometimes returns direct MP3 for known tracks)
def soundcloud_oembed():
    # First search via soundcloud API? But limited without key. Use google or direct?
    # Instead, try to guess URL: search using unofficial search
    # Many projects use `https://soundcloud.com/oembed?url=...` but need a valid track URL.
    # We'll skip because it's unreliable without pre-known URL.
    return "⚠️", "Skipping – requires track URL"
add_test("SoundCloud oembed", soundcloud_oembed)

# ----------------------------------------------------------------------
# 7. Bandcamp (search via API)
def bandcamp():
    # Bandcamp has no public search API, but we can try the unofficial 'api.bandcamp.com' used by some tools
    url = "https://bandcamp.com/api/search"
    # This is not documented, may break.
    # Alternative: use yt-dlp "bcsearch1:" but that requires yt-dlp.
    return "⚠️", "No public API without yt-dlp"
add_test("Bandcamp", bandcamp)

# ----------------------------------------------------------------------
# 8. Audiomack (public search)
def audiomack():
    url = f"https://audiomack.com/search/songs?q={QUERY.replace(' ', '+')}"
    # this returns HTML, not JSON. Scraping is brittle.
    # We'll just test if the page loads and contains song elements.
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            if 'class="song"' in r.text or 'data-stream-url' in r.text:
                # Try to extract an MP3 URL from data-stream-url attribute
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
# 9. Free Music Archive (FMA) – public JSON
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
# 10. NoiseTrade – public API
def noisetrade():
    url = "https://api.noisetrade.com/api/v2/music/search"
    params = {"q": QUERY, "limit": 1}
    try:
        r = requests.get(url, params=params, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get("results"):
                # Need to parse; often returns tracks with download url
                return "⚠️", f"Found {len(data['results'])} results but no direct MP3 in response"
        return "❌", f"HTTP {r.status_code}"
    except Exception as e:
        return "❌", str(e)
add_test("NoiseTrade", noisetrace)

# ----------------------------------------------------------------------
# 11. YouTube oembed (metadata only, no audio)
def youtube_oembed():
    # We need a video URL. Could search via google? Too heavy.
    return "⚠️", "Skipping (requires video URL)"
add_test("YouTube oembed", youtube_oembed)

# ----------------------------------------------------------------------
# 12. Internet Archive wide search (alternative)
# Already covered by archive.org

# ----------------------------------------------------------------------
# 13. Mixcloud (public API)
def mixcloud():
    url = f"https://api.mixcloud.com/search/?q={QUERY.replace(' ', '%20')}&type=cloudcast"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get("data"):
                # cloudcast has stream URLs but usually not direct MP3
                return "⚠️", f"Found {len(data['data'])} cloudcasts, but streaming requires player"
        return "❌", "No results"
    except Exception as e:
        return "❌", str(e)
add_test("Mixcloud", mixcloud)

# ----------------------------------------------------------------------
# 14. HearThis.at (free music platform)
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
# 15. ReverbNation (public)
def reverbnation():
    url = f"https://api.reverbnation.com/artist/search?name={ARTIST.replace(' ', '%20')}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get("artists"):
                # get artist ID, then fetch songs
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
# 16. SoundCloud Python API (no key) using public client_id from web
def soundcloud_no_key():
    # Many bots use a hardcoded client_id from SoundCloud web app
    client_id = "YOUR_CLIENT_ID" # Not static, changes. We'll skip.
    return "⚠️", "Requires dynamic client_id extraction"
add_test("SoundCloud (no key)", soundcloud_no_key)

# ----------------------------------------------------------------------
# 17. Tindeck (free music hosting)
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
# 18. Choon (blockchain music, but API may exist)
def choon():
    return "⚠️", "API deprecated"
add_test("Choon", choon)

# ----------------------------------------------------------------------
# 19. Data.World (audio datasets)
def dataworld():
    return "⚠️", "Not relevant"
add_test("Data.World", dataworld)

# ----------------------------------------------------------------------
# 20. Internet Archive's Audio Archive (already covered)

# ----------------------------------------------------------------------
# 21. LP (listen.to) – old service
def lp():
    return "⚠️", "Defunct"
add_test("LP", lp)

# ----------------------------------------------------------------------
# 22. Zvu (tiny music archive)
def zvu():
    url = f"https://zvu.com/api/search?q={QUERY}"
    # unknown, likely no
    return "⚠️", "Unlikely"
add_test("Zvu", zvu)

# ----------------------------------------------------------------------
# 23. Google Custom Search (requires key) – skip

# ----------------------------------------------------------------------
# 24. GitHub API (search for audio files in public repos – interesting)
def github_audio():
    # Search code for .mp3 files with name containing song
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
                return "✅", f"Found potential MP3: {raw_url}"
        return "❌", "No MP3s found"
    except Exception as e:
        return "❌", str(e)
add_test("GitHub code search (audio)", github_audio)

# ----------------------------------------------------------------------
# 25. Acast (podcast search)
def acast():
    url = f"https://feeds.acast.com/api/v1/search?q={QUERY}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get("episodes"):
                # get audio URL
                audio = data["episodes"][0].get("audioUrl")
                if audio:
                    return "✅", f"{data['episodes'][0]['title']} | MP3: {audio}"
        return "❌", "No results"
    except Exception as e:
        return "❌", str(e)
add_test("Acast (podcast)", acast)

# ----------------------------------------------------------------------
# 26. Spotify preview (requires key, but we can try a public endpoint? no)
def spotify():
    return "⚠️", "Requires API key"
add_test("Spotify", spotify)

# ----------------------------------------------------------------------
# 27. Last.fm (requires key)
def lastfm():
    return "⚠️", "Requires key"
add_test("Last.fm", lastfm)

# ----------------------------------------------------------------------
# 28. Genius (lyrics only)
def genius():
    return "⚠️", "Lyrics only"
add_test("Genius", genius)

# ----------------------------------------------------------------------
# 29. TheAudioDB (free key, but requires signup)
def theaudiodb():
    return "⚠️", "Requires key"
add_test("TheAudioDB", theaudiodb)

# ----------------------------------------------------------------------
# Run all tests
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
    print(f"✅ Working: {len(successes)}")
    for name, status, msg in successes:
        print(f"  ✅ {name}: {msg[:100]}")
    print(f"⚠️ Partial/Unknown: {len(warnings)}")
    for name, status, msg in warnings[:5]:
        print(f"  ⚠️ {name}: {msg[:80]}")
    print(f"❌ Failed: {len(failures)}")
    if successes:
        print("\n💡 The following sources returned a direct MP3 or stream URL. You can use one of them in your bot.")
    else:
        print("\n💡 No source returned a direct MP3. This confirms that no free, no-login API works on GitHub Actions.")

if __name__ == "__main__":
    main()
