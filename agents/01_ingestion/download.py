import os
import sys
import subprocess

def get_transcript(video_id):
    cache_dir = os.environ.get("APP_CACHE_DIR", ".cache")
    cookies_path = os.path.abspath(os.path.join(cache_dir, "cookies.txt"))
    
    os.makedirs(cache_dir, exist_ok=True)
    if os.path.exists(cookies_path):
        os.remove(cookies_path)
        
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
    
    # Отключаем прокси для yt-dlp, чтобы качать в обход VPN
    env = os.environ.copy()
    for k in ['http_proxy', 'https_proxy', 'all_proxy', 'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY']:
        env.pop(k, None)
    
    print(f"Exporting cookies from browser to {cookies_path}...")
    # Command 1: Extract cookies from browser to file
    subprocess.run([
        "./venv/bin/yt-dlp",
        f"https://www.youtube.com/watch?v={video_id}",
        "--cookies-from-browser", "chrome",
        "--cookies", cookies_path,
        "--impersonate", "chrome",
        "--remote-components", "ejs:github",
        "--skip-download"
    ], cwd=root_dir, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Command 2: Use the cookies file to download
    out_template = f"raw_transcripts/{video_id}.%(ext)s"
    cmd = [
        "./venv/bin/yt-dlp",
        f"https://www.youtube.com/watch?v={video_id}",
        "--cookies", cookies_path,
        "--impersonate", "chrome",
        "--remote-components", "ejs:github",
        "--write-sub", "--write-auto-sub",
        "--sub-lang", "ru,en",
        "--skip-download",
        "--sub-format", "vtt",
        "-o", out_template
    ]
    
    print(f"Running yt-dlp for {video_id} using {cookies_path}...")
    res = subprocess.run(cmd, cwd=root_dir, env=env)
    
    if res.returncode == 0:
        print(f"Successfully downloaded transcript for {video_id}")
    else:
        print(f"Error downloading transcript for {video_id}")

if __name__ == '__main__':
    for vid in sys.argv[1:]:
        get_transcript(vid)
