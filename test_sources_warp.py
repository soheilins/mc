#!/usr/bin/env python3
import subprocess
import requests
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

QUERY = "no one noticed the marias"
tests = []

def add_test(name, func):
    tests.append((name, func))

# ========== yt-dlp YouTube clients ==========
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

# ========== SoundCloud ==========
def test_soundcloud():
    cmd = ["yt-dlp", f"scsearch1:{QUERY}", "--simulate", "--print", "title", "--no-warnings"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode == 0 and result.stdout.strip():
        return f"✅ {result.stdout.strip()[:60]}"
    else:
        return f"❌ {result.stderr[:150]}"
add_test("yt-dlp SoundCloud", test_soundcloud)

# ========== Bandcamp ==========
def test_bandcamp():
    cmd = ["yt-dlp", f"bcsearch1:{QUERY}", "--simulate", "--print", "title", "--no-warnings"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode == 0 and result.stdout.strip():
        return f"✅ {result.stdout.strip()[:60]}"
    else:
        return f"❌ {result.stderr[:150]}"
add_test("yt-dlp Bandcamp", test_bandcamp)

# ========== JioSaavn API ==========
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

# ========== Audius API ==========
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

# ========== MusicAPI ==========
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

# ========== Invidious instances ==========
inv_instances = [
    "https://inv.vern.cc",
    "https://yewtu.be",
    "https://invidious.privacydev.net",
    "https://inv.riverside.rocks"
]
def test_invidious(instance):
    try:
        url = f"{instance}/api/v1/search"
        params = {"q": QUERY, "type": "video", "page": 1}
        r = requests.get(url, params=params, timeout=15)
        if r.status_code == 200:
            data = r.json()
            if data and len(data) > 0:
                title = data[0].get("title", "?")
                return f"✅ {title[:60]}"
        return f"❌ HTTP {r.status_code}"
    except Exception as e:
        return f"❌ {str(e)[:50]}"
for inst in inv_instances:
    add_test(f"Invidious ({inst.split('/')[2]})", lambda i=inst: test_invidious(i))

# ========== Piped instances ==========
piped_instances = [
    "https://pipedapi.kavin.rocks",
    "https://pipedapi.tokhmi.xyz"
]
def test_piped(instance):
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
    add_test(f"Piped ({inst.split('/')[2]})", lambda i=inst: test_piped(i))

# ========== Connectivity (basic) ==========
def test_connectivity(url, name):
    try:
        r = requests.head(url, timeout=10, allow_redirects=True)
        return f"✅ {r.status_code}" if r.status_code < 400 else f"❌ HTTP {r.status_code}"
    except Exception as e:
        return f"❌ {str(e)[:50]}"
add_test("YouTube.com reachable", lambda: test_connectivity("https://youtube.com", "YouTube"))
add_test("SoundCloud.com reachable", lambda: test_connectivity("https://soundcloud.com", "SoundCloud"))

# ========== RUN TESTS ==========
def run_all():
    print(f"🔍 Testing music sources with WARP for: '{QUERY}'")
    print("="*80)
    results = []
    for name, test_func in tests:
        print(f"\n⏳ Running: {name}")
        start = time.time()
        try:
            res = test_func()
        except Exception as e:
            res = f"❌ Exception: {e}"
        elapsed = time.time() - start
        print(f"   {res} ({elapsed:.1f}s)")
        results.append((name, res, elapsed))
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    successes = [r for r in results if r[1].startswith("✅")]
    failures = [r for r in results if r[1].startswith("❌")]
    print(f"✅ Working: {len(successes)}")
    for name, res, _ in successes:
        print(f"  ✅ {name}: {res}")
    print(f"❌ Failed: {len(failures)}")
    for name, res, _ in failures[:10]:
        print(f"  ❌ {name}: {res[:80]}")
    return results

if __name__ == "__main__":
    run_all()
