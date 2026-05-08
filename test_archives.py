#!/usr/bin/env python3
import requests
import json
import re
import time
from urllib.parse import quote

SONG_TITLE = "no one noticed"
ARTIST = "the marias"
QUERY = f"{SONG_TITLE} {ARTIST}"

results = []

def test(name, func):
    print(f"\n🔍 Testing {name}...", flush=True)
    start = time.time()
    try:
        status, msg = func()
    except Exception as e:
        status, msg = "❌", f"Exception: {str(e)[:100]}"
    elapsed = time.time() - start
    print(f"   {status} {msg[:140]} ({elapsed:.1f}s)", flush=True)
    results.append((name, status, msg))
    return status, msg

# ----------------------------------------------------------------------
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

def jamendo():
    url = "https://api.jamendo.com/v3.0/tracks/"
    params = {"client_id": "ec9122a4", "format": "json", "limit": 3, "search": QUERY}
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

def netease():
    url = "https://music.163.com/api/search/get/web"
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://music.163.com"}
    data = {"s": QUERY, "type": 1, "offset": 0, "limit": 1}
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

def qq_music():
    url = "https://c.y.qq.com/soso/fcgi-bin/client_search_cp"
    params = {"p": 1, "n": 1, "w": QUERY, "format": "json"}
    r = requests.get(url, params=params, timeout=10)
    if r.status_code == 200:
        text = r.text
        if "song" in text and "mid" in text:
            return "✅", "Search works, would need to extract song ID"
    return "❌", "No results"
test("QQ Music", qq_music)

def jiosaavn():
    url = "https://www.jiosaavn.com/api.php"
    params = {"__call": "search.getResults", "q": QUERY, "p": 1, "n": 1, "ctx": "web6dot0", "api_version": 4, "_format": "json"}
    r = requests.get(url, params=params, timeout=10)
    if r.status_code == 200:
        data = r.json()
        if data.get("results"):
            return "✅", "Working"
    return "❌", "Blocked"
test("JioSaavn API", jiosaavn)

def gaana():
    url = f"https://gaana.com/search?q={quote(QUERY)}"
    r = requests.get(url, timeout=10)
    if r.status_code == 200:
        if 'data-song' in r.text or 'play_btn' in r.text:
            return "✅", "Search page accessible"
        return "⚠️", "200 OK but no song data found"
    return "❌", f"HTTP {r.status_code}"
test("Gaana", gaana)

def soundcloud_rss():
    url = f"https://feeds.soundcloud.com/users/soundcloud:users:search?q={quote(ARTIST)}"
    r = requests.get(url, timeout=10)
    if r.status_code == 200:
        if SONG_TITLE.lower() in r.text.lower():
            m = re.search(r'<enclosure url="([^"]+)"', r.text)
            if m:
                return "✅", f"MP3: {m.group(1)}"
    return "⚠️", "RSS accessible but no track found"
test("SoundCloud RSS", soundcloud_rss)

def mixcloud():
    url = "https://api.mixcloud.com/search/"
    params = {"q": QUERY, "type": "cloudcast", "limit": 1}
    r = requests.get(url, params=params, timeout=10)
    if r.status_code == 200:
        data = r.json()
        if data.get("data"):
            return "✅", f"Found: {data['data'][0].get('name', '')}"
    return "❌", "No results"
test("Mixcloud", mixcloud)

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

def noisetrade():
    url = "https://api.noisetrade.com/api/v2/music/search"
    params = {"q": QUERY, "limit": 1}
    r = requests.get(url, params=params, timeout=10)
    if r.status_code == 200:
        data = r.json()
        if data.get("results"):
            return "✅", f"Found {len(data['results'])} results"
    return "❌", f"HTTP {r.status_code}"
test("NoiseTrade", noisetrade)

def tindeck():
    url = "https://tindeck.com/api/v1/search"
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

def lastfm():
    r = requests.get("https://www.last.fm/search?q=" + quote(ARTIST), timeout=10)
    if r.status_code == 200:
        if SONG_TITLE.lower() in r.text.lower():
            return "⚠️", "Search page OK, but full API needs key"
    return "❌", "No API key"
test("Last.fm", lastfm)

def invidious_test(instance):
    name = f"Invidious ({instance.split('/')[2]})"
    def inner():
        url = f"{instance}/api/v1/search"
        params = {"q": QUERY, "type": "video", "page": 1}
        r = requests.get(url, params=params, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code == 200:
            data = r.json()
            if data:
                return "✅", f"Found: {data[0].get('title', '')[:60]}"
        return "❌", f"HTTP {r.status_code}"
    test(name, inner)

for inst in ["https://inv.vern.cc", "https://yewtu.be", "https://invidious.privacydev.net", "https://inv.riverside.rocks"]:
    invidious_test(inst)

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

def kuwo():
    url = f"http://search.kuwo.cn/r.s?all={quote(QUERY)}&ft=music&rn=1&rformat=json"
    r = requests.get(url, timeout=10)
    if r.status_code == 200:
        if '"name"' in r.text.lower():
            return "✅", "Kuwo search endpoint works"
    return "❌", "No response"
test("Kuwo", kuwo)

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

def bandcamp():
    r = requests.get(f"https://bandcamp.com/search?q={quote(QUERY)}", timeout=10)
    if r.status_code == 200:
        return "✅", "Search page accessible"
    return "❌", f"HTTP {r.status_code}"
test("Bandcamp", bandcamp)

# ----------------------------------------------------------------------
print("\n" + "="*80)
print("SUMMARY")
print("="*80)
successes = [r for r in results if r[1].startswith("✅")]
warnings = [r for r in results if r[1].startswith("⚠️")]
failures = [r for r in results if r[1].startswith("❌")]

print(f"✅ Working: {len(successes)}")
for name, status, msg in successes:
    print(f"  ✅ {name}: {msg[:100]}")
print(f"⚠️ Partial: {len(warnings)}")
for name, status, msg in warnings[:5]:
    print(f"  ⚠️ {name}: {msg[:80]}")
print(f"❌ Failed: {len(failures)}")

if successes:
    print("\n💡 The working sources above may provide direct MP3 or streaming URLs.")
else:
    print("\n💡 No full-length MP3 found. Only Deezer preview (30s) works.")
