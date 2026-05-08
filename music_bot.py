def search_and_download(artist_name):
    search_query = f"ytsearch1:{artist_name} popular songs"
    output_template = str(DOWNLOADS_DIR / f"%(title)s.%(ext)s")
    
    # The client fallback method from your workflow
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
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
            if result.returncode == 0:
                downloaded = list(DOWNLOADS_DIR.glob("*.mp3"))
                if downloaded:
                    latest = max(downloaded, key=lambda f: f.stat().st_mtime)
                    title = latest.stem.replace("_", " ")
                    return latest, f"{title} - {artist_name}"
        except Exception:
            continue
    return None, None
