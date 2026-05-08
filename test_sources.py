#!/usr/bin/env python3
import subprocess
import requests
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# The target song
QUERY = "no one noticed the marias"
FALLBACK_QUERY = "Billie Eilish bad guy"   # in case the first returns nothing

# List of test methods
tests = []

def add_test(name, func):
    tests.append((name, func))

# ========== 1. yt-dlp with various YouTube clients ==========
for client in ["web_safari", "ios", "android", "tv", "web", "web_embedded", "web_creator", "android_vr", "android_embedded", "web_music", "web_remix"]:
    def make_youtube_test(client_name):
        def test():
            cmd = [
                "yt-dlp",
                f"ytsearch1:{QUERY}",
                "--simulate", "--print", "title",
                "--extractor-args", f"youtube:player_client={client_name};formats=missing_pot",
                "--no-warnings"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0 and result.stdout.strip():
                return f"✅ Found: {result.stdout.strip()[:60]}"
            else:
                err = result.stderr[:150].replace('\n', ' ')
                return f"❌ Failed (rc={result.returncode}): {err}"
        return test
    add_test(f"yt-dlp YouTube client={client}", make_youtube_test(client))

# ========== 2. SoundCloud ==========
def test_soundcloud():
    cmd = ["yt-dlp", f"scsearch1:{QUERY}", "--simulate", "--print", "title", "--no-warnings"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode == 0 and result.stdout.strip():
        return f"✅ {result.stdout.strip()[:60]}"
    else:
        return f"❌ {result.stderr[:150]}"
add_test("yt-dlp SoundCloud", test_soundcloud)

# ========== 3. Bandcamp ==========
def test_bandcamp():
    cmd = ["yt-dlp", f"bcsearch1:{QUERY}", "--simulate", "--print", "title", "--no-warnings"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode == 0 and result.stdout.strip():
        return f"✅ {result.stdout.strip()[:60]}"
    else:
        return f"❌ {result.stderr[:150]}"
add_test("yt-dlp Bandcamp", test_bandcamp)

# ========== 4. Audiomack ==========
def test_audiomack():
    cmd = ["yt-dlp", f"amsearch1:{QUERY}", "--simulate", "--print", "title", "--no-warnings"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode == 0 and result.stdout.strip():
        return f"✅ {result.stdout.strip()[:60]}"
    else:
        return f"❌ {result.stderr[:150]}"
add_test("yt-dlp Audiomack", test_audiomack)

# ========== 5. Vimeo ==========
def test_vimeo():
    cmd = ["yt-dlp", f"vimeosearch1:{QUERY}", "--simulate", "--print", "title", "--no-warnings"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode == 0 and result.stdout.strip():
        return f"✅ {result.stdout.strip()[:60]}"
    else:
        return f"❌ {result.stderr[:150]}"
add_test("yt-dlp Vimeo", test_vimeo)

# ========== 6. Dailymotion ==========
def test_dailymotion():
    cmd = ["yt-dlp", f"dailymotionsearch1:{QUERY}", "--simulate", "--print", "title", "--no-warnings"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode == 0 and result.stdout.strip():
        return f"✅ {result.stdout.strip()[:60]}"
    else:
        return f"❌ {result.stderr[:150]}"
add_test("yt-dlp Dailymotion", test_dailymotion)

# ========== 7. JioSaavn API ==========
def test_jiosaavn():
    url = "https://saavn.me/search/songs"
    params = {"query": QUERY}
    try:
        r = requests.get(url, params=params, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get("data", {}).get("results"):
                t = data["data"]["results"][0]
                return f"✅ {t.get('name')} - {t.get('primaryArtists')}"
        return f"❌ HTTP {r.status_code} or no results"
    except Exception as e:
        return f"❌ {e}"
add_test("JioSaavn API", test_jiosaavn)

# ========== 8. Audius API ==========
def test_audius():
    url = "https://discoveryprovider.audius.co/v1/tracks/search"
    params = {"query": QUERY, "limit": 1}
    try:
        r = requests.get(url, params=params, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get("data"):
                t = data["data"][0]
                return f"✅ {t.get('title')} - {t.get('user',{}).get('name')}"
        return f"❌ HTTP {r.status_code}"
    except Exception as e:
        return f"❌ {e}"
add_test("Audius API", test_audius)

# ========== 9. MusicAPI (unofficial) ==========
def test_musicapi():
    url = "https://musicapi.vercel.app/api/search"
    params = {"q": QUERY}
    try:
        r = requests.get(url, params=params, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get("tracks"):
                t = data["tracks"][0]
                return f"✅ {t.get('title')} - {t.get('artist')}"
        return f"❌ HTTP {r.status_code}"
    except Exception as e:
        return f"❌ {e}"
add_test("MusicAPI (vercel)", test_musicapi)

# ========== 10. Invidious instances (direct API) ==========
invidious_instances = [
    "https://inv.vern.cc",
    "https://yewtu.be",
    "https://invidious.privacydev.net",
    "https://inv.riverside.rocks",
    "https://invidious.snopyta.org",
    "https://vid.puffyan.us"
]
def test_invidious_api(instance):
    try:
        url = f"{instance}/api/v1/search"
        params = {"q": QUERY, "type": "video", "page": 1}
        r = requests.get(url, params=params, timeout=15)
        if r.status_code == 200:
            data = r.json()
            if data and len(data) > 0:
                video = data[0]
                title = video.get("title", "?")
                return f"✅ {title[:60]}"
        return f"❌ HTTP {r.status_code}"
    except Exception as e:
        return f"❌ {str(e)[:50]}"
for inst in invidious_instances:
    add_test(f"Invidious API ({inst.split('/')[2]})", lambda i=inst: test_invidious_api(i))

# ========== 11. Piped API (alternative) ==========
piped_instances = [
    "https://pipedapi.kavin.rocks",
    "https://pipedapi.tokhmi.xyz",
    "https://pipedapi.adminforge.de"
]
def test_piped_api(instance):
    try:
        url = f"{instance}/search"
        params = {"q": QUERY, "filter": "videos"}
        r = requests.get(url, params=params, timeout=15)
        if r.status_code == 200:
            data = r.json()
            if data and len(data) > 0:
                title = data[0].get("title", "?")
                return f"✅ {title[:60]}"
        return f"❌ HTTP {r.status_code}"
    except Exception as e:
        return f"❌ {str(e)[:50]}"
for inst in piped_instances:
    add_test(f"Piped API ({inst.split('/')[2]})", lambda i=inst: test_piped_api(i))

# ========== 12. Free Music Archive (FMA) ==========
def test_fma():
    # FMA API: https://freemusicarchive.org/api
    # No specific search for our song, but test general access
    url = "https://freemusicarchive.org/api/get/tracks.json?limit=1"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return "✅ API reachable"
        return f"❌ HTTP {r.status_code}"
    except Exception as e:
        return f"❌ {e}"
add_test("Free Music Archive (general)", test_fma)

# ========== 13. Jamendo API (free, no key) ==========
def test_jamendo():
    url = "https://api.jamendo.com/v3.0/tracks/"
    params = {"client_id": "ec9122a4", "format": "json", "limit": 1, "search": "pop"}
    try:
        r = requests.get(url, params=params, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get("results"):
                return f"✅ {data['results'][0].get('name')[:60]}"
        return f"❌ HTTP {r.status_code}"
    except Exception as e:
        return f"❌ {e}"
add_test("Jamendo API (free key)", test_jamendo)

# ========== 14. Disk DJ (public) ==========
def test_diskdj():
    url = "https://api.diskdj.fun/api"
    params = {"type": "search", "query": QUERY}
    try:
        r = requests.get(url, params=params, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get("data"):
                return f"✅ {data['data'][0].get('title')[:60]}"
        return f"❌ HTTP {r.status_code}"
    except Exception as e:
        return f"❌ {e}"
add_test("Disk DJ API", test_diskdj)

# ========== 15. NoiseTrade (public domain) ==========
def test_noisetrade():
    # No direct search, test endpoint
    url = "https://api.noisetrade.com/api/v2/music/genres/pop"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return "✅ API reachable"
        return f"❌ HTTP {r.status_code}"
    except Exception as e:
        return f"❌ {e}"
add_test("NoiseTrade API (general)", test_noisetrade)

# ========== 16. yt-dlp with proxy (free public proxies) ==========
free_proxies = [
    "http://103.152.112.162:80",
    "http://80.78.23.49:8080",
    "http://45.94.31.152:8080"
]
def test_proxy(proxy):
    cmd = [
        "yt-dlp",
        f"ytsearch1:{QUERY}",
        "--simulate", "--print", "title",
        "--extractor-args", "youtube:player_client=android",
        "--proxy", proxy,
        "--no-warnings",
        "--socket-timeout", "10"
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=40)
        if result.returncode == 0 and result.stdout.strip():
            return f"✅ {result.stdout.strip()[:60]}"
        else:
            err = result.stderr[:100].replace('\n', ' ')
            return f"❌ proxy {proxy} failed: {err}"
    except Exception as e:
        return f"❌ {e}"
for proxy in free_proxies[:3]:  # test a few
    add_test(f"yt-dlp via proxy {proxy}", lambda p=proxy: test_proxy(p))

# ========== 17. Direct HEAD request to known CDNs (test connectivity) ==========
def test_connectivity(url, name):
    try:
        r = requests.head(url, timeout=10, allow_redirects=True)
        if r.status_code < 400:
            return f"✅ reachable ({r.status_code})"
        else:
            return f"❌ HTTP {r.status_code}"
    except Exception as e:
        return f"❌ {e}"
add_test("YouTube.com connectivity", lambda: test_connectivity("https://youtube.com", "YouTube"))
add_test("SoundCloud.com connectivity", lambda: test_connectivity("https://soundcloud.com", "SoundCloud"))
add_test("JioSaavn.com connectivity", lambda: test_connectivity("https://jiosaavn.com", "JioSaavn"))

# ========== RUN ALL TESTS ==========
def run_all_tests():
    print(f"🔍 Testing music sources for query: '{QUERY}'")
    print("="*80)
    results = []
    for name, test_func in tests:
        print(f"\n⏳ Running: {name}")
        start = time.time()
        try:
            result = test_func()
        except Exception as e:
            result = f"❌ Exception: {e}"
        elapsed = time.time() - start
        print(f"   {result} ({elapsed:.1f}s)")
        results.append((name, result, elapsed))
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    successes = [r for r in results if r[1].startswith("✅")]
    failures = [r for r in results if r[1].startswith("❌")]
    print(f"✅ Working: {len(successives)}")
    for name, res, _ in successes:
        print(f"  ✅ {name}: {res}")
    print(f"❌ Failed: {len(failures)}")
    for name, res, _ in failures[:10]:  # show first 10 failures
        print(f"  ❌ {name}: {res[:80]}")
    return results

if __name__ == "__main__":
    run_all_tests()
