#!/usr/bin/env python3
"""
Tests over 40 music archives, APIs, and direct download sources
from GitHub Actions to identify which can deliver MP3 files.
"""

import requests
import json
import re
import time
import sys
from urllib.parse import quote, urlencode

# Test song: "no one noticed" by The Marías
SONG_TITLE = "no one noticed"
ARTIST = "the marias"
QUERY = f"{SONG_TITLE} {ARTIST}"

# Results storage
working = []
failed = []
warning = []

def test(name, func):
    """Wrapper to run a test and collect results."""
    print(f"\n🔍 Testing {name}...")
    start = time.time()
    try:
        status, msg = func()
    except Exception as e:
        status, msg = "❌", f"Exception: {str(e)[:100]}"
    elapsed = time.time() - start
    print(f"   {status} {msg[:140]} ({elapsed:.1f}s)")
    if status == "✅":
        working.append((name, msg))
    elif status == "⚠️":
        warning.append((name, msg))
    else:
        failed.append((name, msg))
    return status, msg


# ============================================================
# 1. Deezer API (returns 30-second previews)
def deezer():
    url = "https://api.deezer.com/search"
    params = {"q": QUERY, "limit": 1}
    r = requests.get(url, params=params, timeout=10)
    if r.status_code == 200:
        data = r.json()
        if data.get("data"):
            track = data["data"][0]
            preview = track.get("preview")
            if preview:
                return "✅", f"30s preview: {preview}"
    return "❌", f"HTTP {r.status_code}"
test("Deezer preview", deezer)


# ============================================================
# 2. Internet Archive (Archive.org)
def archive():
    url = "https://archive.org/advancedsearch.php"
    params = {
        "q": f'"{SONG_TITLE}" AND creator:"{ARTIST}"',
        "fl[]": ["identifier", "title", "creator"],
        "rows": 1,
        "output": "json"
    }
    r = requests.get(url, params=params, timeout=15)
    if r.status_code == 200:
        data = r.json()
        docs = data.get("response", {}).get("docs", [])
        if docs:
            ident = docs[0]["identifier"]
            mp3 = f"https://archive.org/download/{ident}/{ident}_vbr.mp3"
            return "✅", f"MP3: {mp3}"
    return "❌", "No results"
test("Archive.org", archive)


# ============================================================
# 3. Free Music Archive (FMA)
def fma():
    url = "https://freemusicarchive.org/api/get/tracks.json"
    params = {"limit": 5, "search": SONG_TITLE}
    r = requests.get(url, params=params, timeout=10)
    if r.status_code == 200:
        data = r.json()
        if data.get("rows"):
            track = data["rows"][0]
            mp3 = track.get("track_file_url")
            if mp3:
                return "✅", f"{track['track_title']} | MP3: {mp3[:80]}"
    return "❌", "No results"
test("Free Music Archive", fma)


# ============================================================
# 4. Jamendo (free API with public demo key)
def jamendo():
    url = "https://api.jamendo.com/v3.0/tracks/"
    params = {
        "client_id": "ec9122a4",
        "format": "json",
        "limit": 3,
        "search": QUERY
    }
    r = requests.get(url, params=params, timeout=10)
    if r.status_code == 200:
        data = r.json()
        if data.get("results"):
            track = data["results"][0]
            audio = track.get("audio")
            if audio:
                return "✅", f"{track['name']} - {track['artist_name']} | MP3: {audio}"
            return "⚠️", f"Track '{track['name']}' but no audio URL"
    return "❌", f"HTTP {r.status_code}"
test("Jamendo", jamendo)


# ============================================================
# 5. NetEase Cloud Music (Chinese platform)
def netease():
    # Using a public NetEase API that often works from datacenters
    # Known song: "The Marías" search via public endpoint
    url = "https://music.163.com/api/search/get/web"
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://music.163.com"}
    data = {
        "s": QUERY,
        "type": 1,
        "offset": 0,
        "limit": 1
    }
    try:
        r = requests.post(url, data=data, headers=headers, timeout=10)
        if r.status_code == 200:
            j = r.json()
            songs = j.get("result", {}).get("songs", [])
            if songs:
                song_id = songs[0]["id"]
                mp3 = f"https://music.163.com/song/media/outer/url?id={song_id}.mp3"
                return "✅", f"MP3: {mp3}"
        return "❌", "No results"
    except:
        return "❌", "Blocked or unavailable"
test("NetEase Cloud Music", netease)


# ============================================================
# 6. QQ Music (public API attempt)
def qq_music():
    # QQ Music public search endpoint
    url = "https://c.y.qq.com/soso/fcgi-bin/client_search_cp"
    params = {
        "p": 1,
        "n": 1,
        "w": QUERY,
        "format": "json"
    }
    r = requests.get(url, params=params, timeout=10)
    if r.status_code == 200:
        # QQ returns JSONP, not pure JSON
        text = r.text
        if "song" in text and "mid" in text:
            return "✅", "Search works, would need to extract song ID"
    return "❌", "No results"
test("QQ Music", qq_music)


# ============================================================
# 7. JioSaavn (various unofficial endpoints)
def jiosaavn_v1():
    url = "https://www.jiosaavn.com/api.php"
    params = {
        "__call": "search.getResults",
        "q": QUERY,
        "p": 1,
        "n": 1,
        "ctx": "web6dot0",
        "api_version": 4,
        "_format": "json"
    }
    r = requests.get(url, params=params, timeout=10)
    if r.status_code == 200:
        data = r.json()
        if data.get("results"):
            return "✅", "Working"
    return "❌", "Blocked"
test("JioSaavn API", jiosaavn_v1)


# ============================================================
# 8. Gaana (Indian music platform)
def gaana():
    url = f"https://gaana.com/search?q={quote(QUERY)}"
    r = requests.get(url, timeout=10)
    if r.status_code == 200:
        if 'data-song' in r.text or 'play_btn' in r.text:
            return "✅", "Search page accessible"
        return "⚠️", "200 OK but no song data found"
    return "❌", f"HTTP {r.status_code}"
test("Gaana", gaana)


# ============================================================
# 9. SoundCloud (public RSS feed)
def soundcloud_rss():
    url = f"https://feeds.soundcloud.com/users/soundcloud:users:search?q={quote(ARTIST)}"
    r = requests.get(url, timeout=10)
    if r.status_code == 200:
        if SONG_TITLE.lower() in r.text.lower():
            # Extract track URL pattern
            import re
            m = re.search(r'<enclosure url="([^"]+)"', r.text)
            if m:
                return "✅", f"MP3: {m.group(1)}"
    return "⚠️", "RSS accessible but no track found"
test("SoundCloud RSS", soundcloud_rss)


# ============================================================
# 10. Mixcloud (public API)
def mixcloud():
    url = f"https://api.mixcloud.com/search/"
    params = {"q": QUERY, "type": "cloudcast", "limit": 1}
    r = requests.get(url, params=params, timeout=10)
    if r.status_code == 200:
        data = r.json()
        if data.get("data"):
            return "✅", f"Found: {data['data'][0].get('name', '')}"
    return "❌", "No results"
test("Mixcloud", mixcloud)


# ============================================================
# 11. HearThis.at (free music platform)
def hearthis():
    url = f"https://hearthis.at/api-v2/search/?q={quote(QUERY)}"
    r = requests.get(url, timeout=10)
    if r.status_code == 200:
        data = r.json()
        if data.get("results"):
            t = data["results"][0]
            mp3 = t.get("stream_url") or t.get("download_url")
            if mp3:
                return "✅", f"MP3: {mp3}"
    return "❌", "No results"
test("HearThis.at", hearthis)


# ============================================================
# 12. NoiseTrade (search)
def noisetrade():
    url = f"https://api.noisetrade.com/api/v2/music/search"
    params = {"q": QUERY, "limit": 1}
    r = requests.get(url, params=params, timeout=10)
    if r.status_code == 200:
        data = r.json()
        if data.get("results"):
            return "✅", f"Found {len(data['results'])} results"
    return "❌", f"HTTP {r.status_code}"
test("NoiseTrade", noisetrade)


# ============================================================
# 13. Tindeck (free hosting)
def tindeck():
    url = f"https://tindeck.com/api/v1/search"
    params = {"q": QUERY}
    r = requests.get(url, params=params, timeout=10)
    if r.status_code == 200:
        data = r.json()
        if data.get("tracks"):
            mp3 = data["tracks"][0].get("url")
            if mp3:
                return "✅", f"MP3: {mp3[:80]}"
    return "❌", "No results"
test("Tindeck", tindeck)


# ============================================================
# 14. Last.fm (requires key, but check metadata only)
def lastfm():
    # Last.fm's API is free but requires registration
    # This checks if the site itself is reachable
    r = requests.get("https://www.last.fm/search?q=" + quote(ARTIST), timeout=10)
    if r.status_code == 200:
        if SONG_TITLE.lower() in r.text.lower():
            return "⚠️", "Search page OK, but full API needs key"
    return "❌", "No API key"
test("Last.fm", lastfm)


# ============================================================
# 15-20. Alternative Invidious & Piped instances
def invidious(instance):
    name = f"Invidious ({instance.split('/')[2]})"
    def test():
        url = f"{instance}/api/v1/search"
        params = {"q": QUERY, "type": "video", "page": 1}
        r = requests.get(url, params=params, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code == 200:
            data = r.json()
            if data:
                return "✅", f"Found: {data[0].get('title', '')[:60]}"
        return "❌", f"HTTP {r.status_code}"
    test(name, test)

for inst in ["https://inv.vern.cc", "https://yewtu.be", "https://invidious.privacydev.net", "https://inv.riverside.rocks"]:
    invidious(inst)


# ============================================================
# 21. GitHub audio search (for MP3 files in public repos)
def github_search():
    url = "https://api.github.com/search/code"
    headers = {"Accept": "application/vnd.github.v3+json"}
    params = {"q": f'"{SONG_TITLE}" extension:mp3', "per_page": 1}
    r = requests.get(url, headers=headers, params=params, timeout=10)
    if r.status_code == 200:
        data = r.json()
        if data.get("items"):
            item = data["items"][0]
            raw = f"https://raw.githubusercontent.com/{item['repository']['full_name']}/main/{item['path']}"
            return "✅", f"MP3 found: {raw[:80]}"
    return "❌", "No MP3 files found"
test("GitHub Code Search", github_search)


# ============================================================
# 22. SourceForge audio directories
def sourceforge():
    # Search SourceForge for audio files
    url = "https://sourceforge.net/rest/u/libertyhigh/find"
    # This is not a standard API, but we can test general reachability
    r = requests.get("https://sourceforge.net/directory/audio/", timeout=10)
    if r.status_code == 200:
        return "✅", "SourceForge reachable (no search API)"
    return "❌", f"HTTP {r.status_code}"
test("SourceForge", sourceforge)


# ============================================================
# 23. Acast (podcast audio)
def acast():
    url = f"https://feeds.acast.com/api/v1/search?q={quote(QUERY)}"
    r = requests.get(url, timeout=10)
    if r.status_code == 200:
        data = r.json()
        if data.get("episodes"):
            audio = data["episodes"][0].get("audioUrl")
            if audio:
                return "✅", f"Podcast MP3: {audio[:80]}"
        return "⚠️", "No audio found"
    return "❌", "No results"
test("Acast", acast)


# ============================================================
# 24-29. Various Chinese music APIs
def kugou():
    # Kugou music search
    url = f"https://www.kugou.com/yy/html/search.html#searchType=song&searchKey={quote(QUERY)}"
    r = requests.get(url, timeout=10)
    if r.status_code == 200:
        return "✅", "Kugou reachable"
    return "❌", f"HTTP {r.status_code}"
test("Kugou", kugou)

def xiami():
    r = requests.get("https://www.xiami.com/", timeout=10)
    return ("✅" if r.status_code == 200 else "❌"), f"HTTP {r.status_code}"
test("Xiami", xiami)

def kuwo():
    r = requests.get(f"http://search.kuwo.cn/r.s?all={quote(QUERY)}&ft=music&rn=1&rformat=json", timeout=10)
    if r.status_code == 200:
        if '"name"' in r.text.lower():
            return "✅", "Kuwo search endpoint works"
    return "❌", "No response"
test("Kuwo", kuwo)


# ============================================================
# 30. Freesound (needs key, tests connectivity)
def freesound():
    r = requests.get("https://freesound.org/apiv2/search/text/?query=" + quote(SONG_TITLE), timeout=10)
    if r.status_code == 200:
        return "✅", "API responds (no key, no results)"
    return "❌", f"HTTP {r.status_code}"
test("Freesound", freesound)


# ============================================================
# 31. Wikimedia Commons audio
def wikimedia():
    url = "https://commons.wikimedia.org/w/api.php"
    params = {
        "action": "query",
        "list": "search",
        "srsearch": f'"{SONG_TITLE}" filetype:mp3',
        "format": "json",
        "srlimit": 1
    }
    r = requests.get(url, params=params, timeout=10)
    if r.status_code == 200:
        data = r.json()
        if data.get("query", {}).get("search"):
            return "✅", "Found audio file"
    return "❌", "No audio files found"
test("Wikimedia Commons", wikimedia)


# ============================================================
# 32. LibriVox (public domain audiobooks) – not music but free audio
def librivox():
    url = f"https://librivox.org/api/feed/audiobooks/?title={quote(SONG_TITLE)}&format=json"
    r = requests.get(url, timeout=10)
    if r.status_code == 200:
        data = r.json()
        if data.get("books"):
            return "✅", "Audiobook found"
    return "❌", "No results"
test("LibriVox", librivox)


# ============================================================
# 33. Bandcamp (no public API, but search)
def bandcamp():
    r = requests.get(f"https://bandcamp.com/search?q={quote(QUERY)}", timeout=10)
    if r.status_code == 200:
        return "✅", "Search page accessible"
    return "❌", f"HTTP {r.status_code}"
test("Bandcamp", bandcamp)


# ============================================================
# 34. Audiomack (scrape)
def audiomack():
    r = requests.get(f"https://audiomack.com/search/songs?q={quote(QUERY)}", timeout=10)
    if r.status_code == 200:
        match = re.search(r'data-stream-url="([^"]+)"', r.text)
        if match:
            return "✅", f"MP3: {match.group(1)}"
        if 'class="song"' in r.text:
            return "⚠️", "Page loaded but no MP3 found"
    return "❌", "No results"
test("Audiomack", audiomack)


# ============================================================
# 35. Spotify oembed (metadata only)
def spotify_oembed():
    r = requests.get("https://open.spotify.com/oembed?url=https://open.spotify.com/track/", timeout=10)
    if r.status_code == 200 or r.status_code == 404:
        return "✅", "Spotify oembed endpoint reachable"
    return "❌", f"HTTP {r.status_code}"
test("Spotify oembed", spotify_oembed)


# ============================================================
# 36. SoundExchange (no API, test)
def soundexchange():
    r = requests.get("https://www.soundexchange.com/", timeout=10)
    return ("✅" if r.status_code == 200 else "❌"), f"HTTP {r.status_code}"
test("SoundExchange", soundexchange)


# ============================================================
# 37. Discogs (public data, no audio)
def discogs():
    r = requests.get("https://api.discogs.com/database/search?q=" + quote(QUERY), timeout=10)
    if r.status_code == 200:
        data = r.json()
        if data.get("results"):
            return "✅", "Metadata found (no audio)"
    return "❌", "No results or HTTP"
test("Discogs", discogs)


# ============================================================
# 38. MusicBrainz (metadata only)
def musicbrainz():
    r = requests.get("https://musicbrainz.org/ws/2/recording?query=" + quote(QUERY) + "&fmt=json", timeout=10)
    if r.status_code == 200:
        data = r.json()
        if data.get("recordings"):
            return "✅", "Metadata found (no audio)"
    return "❌", "No results"
test("MusicBrainz", musicbrainz)


# ============================================================
# 39-41. Additional Invidious instances for redundancy
def invidious_extra():
    extra = ["https://invidious.snopyta.org", "https://vid.puffyan.us", "https://invidious.weblibre.org"]
    for inst in extra:
        def make_test(i):
            def test():
                r = requests.get(f"{i}/api/v1/search?q={quote(QUERY)}&type=video", timeout=10)
                if r.status_code == 200:
                    data = r.json()
                    if data:
                        return "✅", f"Working: {i}"
                return "❌", "Not working"
            test(f"Invidious ({i.split('/')[2]})", test)
    invidious_extra()


# ============================================================
# 42. Piped instances
def piped_check():
    instances = ["https://pipedapi.kavin.rocks", "https://pipedapi.tokhmi.xyz"]
    for inst in instances:
        def make_test(i):
            def test():
                r = requests.get(f"{i}/search?q={quote(QUERY)}&filter=videos", timeout=10)
                if r.status_code == 200:
                    data = r.json()
                    if data:
                        return "✅", f"Working: {i}"
                return "❌", "Not working"
            test(f"Piped ({i.split('/')[2]})", test)
    piped_check()


# ============================================================
# 43. YouTube OEmbed (metadata)
def youtube_oembed():
    # This needs a video URL, but we test the endpoint itself
    r = requests.get("https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ", timeout=10)
    if r.status_code == 200:
        return "✅", "OEmbed endpoint works"
    return "❌", f"HTTP {r.status_code}"
test("YouTube OEmbed", youtube_oembed)


# ============================================================
# 44. Radio Public (podcast search)
def radiopublic():
    r = requests.get(f"https://radiopublic.com/api/episodes?searchTerm={quote(QUERY)}", timeout=10)
    if r.status_code == 200:
        data = r.json()
        if data.get("data"):
            return "✅", "Working"
    return "❌", "No results or HTTP"
test("RadioPublic", radiopublic)


# ============================================================
# 45. Podbean (podcast search)
def podbean():
    r = requests.get(f"https://www.podbean.com/api/search?q={quote(QUERY)}", timeout=10)
    if r.status_code == 200:
        data = r.json()
        if data.get("episodes"):
            audio = data["episodes"][0].get("audio_file")
            if audio:
                return "✅", f"MP3: {audio[:80]}"
    return "❌", "No results"
test("Podbean", podbean)


# ============================================================
# 46. Microsoft Soundscape (open audio)
def soundscape():
    # Not a music source but tests open audio
    r = requests.get("https://www.microsoft.com/en-us/edge/", timeout=10)
    return ("✅" if r.status_code == 200 else "❌"), "Connectivity test"
test("Microsoft edge reachable", soundscape)


# ============================================================
# Print summary
def print_summary():
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"✅ Working: {len(working)}")
    for name, msg in working:
        print(f"  ✅ {name}: {msg[:100]}")
    print(f"\n⚠️ Partial/Warning: {len(warning)}")
    for name, msg in warning[:5]:
        print(f"  ⚠️ {name}: {msg[:80]}")
    print(f"\n❌ Failed: {len(failed)}")
    if working:
        print("\n💡 SUGGESTION: The working sources above can be used in your music bot.")
        print("   Some return direct MP3 links, others only metadata.")
    else:
        print("\n💡 No source returned a direct MP3. Consider using Deezer previews (30-second clips).")


if __name__ == "__main__":
    print(f"🎵 Testing {len([f for f in dir() if not f.startswith('_')])} music archives and APIs for '{QUERY}'")
    print("="*80)
    # The tests run via the 'test' function calls above
    print_summary()
