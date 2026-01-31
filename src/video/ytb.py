import argparse
import os
import socket
import sys
from typing import Optional

import yt_dlp

## 让cookie成为可选 默认为空

def test_proxy(host: str, port: int) -> bool:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


def setup_proxy() -> Optional[str]:
    existing = os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY") or os.environ.get("ALL_PROXY")
    if existing:
        return existing

    proxy_ports = {
        7890: ("Clash", "http"),
        7891: ("Clash", "http"),
        10809: ("V2Ray", "http"),
        10808: ("V2Ray", "socks5h"),
        1080: ("SS/SSR", "socks5h"),
    }

    for port, (name, scheme) in proxy_ports.items():
        if test_proxy("127.0.0.1", port):
            proxy_url = f"{scheme}://127.0.0.1:{port}"
            print(f"[proxy] Detected {name}: {proxy_url}")
            os.environ["HTTP_PROXY"] = proxy_url
            os.environ["HTTPS_PROXY"] = proxy_url
            os.environ["ALL_PROXY"] = proxy_url
            return proxy_url

    return None


def build_format(max_height: int) -> str:
    # Prefer MP4/M4A over HLS to avoid slow m3u8 downloads.
    return (
        f"bv*[height<={max_height}][ext=mp4][protocol^=https]+"
        f"ba[ext=m4a][protocol^=https]/"
        f"b*[height<={max_height}][ext=mp4][protocol^=https]/"
        f"b*[height<={max_height}]"
    )


def base_opts(max_height: int, proxy: Optional[str]) -> dict:
    ydl_opts = {
        "outtmpl": "%(title).200s.%(ext)s",
        "format": build_format(max_height),
        "merge_output_format": "mp4",
        "continuedl": True,
        "retries": 10,
        "fragment_retries": 10,
        "socket_timeout": 30,
        "concurrent_fragment_downloads": 8,
        "noplaylist": True,
        "quiet": False,
        "cachedir": False,
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
        },
    }
    if proxy:
        ydl_opts["proxy"] = proxy
    return ydl_opts


def run_download(url: str, ydl_opts: dict) -> bool:
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return True


def download_video(url: str, proxy: Optional[str], max_height: int, cookies: str) -> bool:
    ydl_opts = base_opts(max_height, proxy)

    if cookies == "edge":
        ydl_opts["cookiesfrombrowser"] = ("edge",)
    elif cookies == "firefox":
        ydl_opts["cookiesfrombrowser"] = ("firefox",)
    elif cookies == "none":
        pass
    else:
        ydl_opts["cookiesfrombrowser"] = ("edge",)

    print(f"[download] url={url}")
    print(f"[download] max_height={max_height} proxy={proxy} cookies={cookies}")
    print("-" * 50)

    try:
        run_download(url, ydl_opts)
        print("-" * 50)
        print("Download complete.")
        return True
    except Exception as e:
        if cookies == "auto" and ("DPAPI" in str(e) or "decrypt" in str(e).lower()):
            print("Edge cookies failed, trying Firefox...")
            return try_firefox(url, proxy, max_height)
        if cookies == "auto":
            print(f"Download failed: {e}")
            return try_no_cookies(url, proxy, max_height)
        print(f"Download failed: {e}")
        print("Falling back to no-cookies mode...")
        return try_no_cookies(url, proxy, max_height)


def try_firefox(url: str, proxy: Optional[str], max_height: int) -> bool:
    ydl_opts = base_opts(max_height, proxy)
    ydl_opts["cookiesfrombrowser"] = ("firefox",)
    try:
        print("Trying Firefox cookies...")
        run_download(url, ydl_opts)
        print("Download complete.")
        return True
    except Exception:
        return try_no_cookies(url, proxy, max_height)


def try_no_cookies(url: str, proxy: Optional[str], max_height: int) -> bool:
    print("Trying Android client without cookies...")

    ydl_opts = base_opts(max_height, proxy)
    ydl_opts["extractor_args"] = {
        "youtube": {
            "player_client": ["android_vr", "android"],
            "player_skip": ["webpage"],
        }
    }
    ydl_opts["http_headers"] = {
        "User-Agent": "com.google.android.youtube/19.09.37 (Linux; U; Android 14; en_US; sdk_gphone64_arm64 Build/UE1A.230829.036) gzip",
    }

    try:
        run_download(url, ydl_opts)
        print("Download complete.")
        return True
    except Exception as e:
        print(f"Failed: {e}")
        show_manual_guide(url, proxy)
        return False


def show_manual_guide(url: str, proxy: Optional[str]) -> None:
    print("\n" + "=" * 50)
    print("Manual options")
    print("=" * 50)
    print("1) Update yt-dlp: python -m pip install -U yt-dlp")
    if proxy:
        print(f"2) Try CLI: yt-dlp --proxy {proxy} -f 136+140 --merge-output-format mp4 \"{url}\"")
    else:
        print(f"2) Try CLI: yt-dlp -f 136+140 --merge-output-format mp4 \"{url}\"")


def test_connection(proxy: Optional[str]) -> bool:
    import urllib.request

    print("Testing YouTube connection...")
    try:
        if proxy:
            handler = urllib.request.ProxyHandler({"http": proxy, "https": proxy})
        else:
            handler = urllib.request.ProxyHandler({})
        opener = urllib.request.build_opener(handler)
        opener.addheaders = [("User-Agent", "Mozilla/5.0")]
        response = opener.open("https://www.youtube.com", timeout=10)
        if response.status == 200:
            print("YouTube connection OK.")
            return True
    except Exception as e:
        print(f"Connection failed: {e}")
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="YouTube downloader")
    parser.add_argument("url", nargs="?", help="YouTube video URL")
    parser.add_argument("--quality", type=int, default=1080, choices=[360, 480, 720, 1080])
    parser.add_argument("--proxy", default=None, help="Proxy URL, e.g. http://127.0.0.1:7890")
    parser.add_argument("--no-proxy", action="store_true", help="Disable proxy auto-detection")
    parser.add_argument("--cookies", default="auto", choices=["auto", "edge", "firefox", "none"])
    args = parser.parse_args()

    proxy = args.proxy if args.proxy else (None if args.no_proxy else setup_proxy())
    if not test_connection(proxy):
        print("Warning: YouTube connection test failed. Will still try download.")

    video_url = args.url or input("Enter video URL: ").strip()
    if not video_url:
        print("URL cannot be empty.")
        return 1

    print()
    ok = download_video(video_url, proxy, max_height=args.quality, cookies=args.cookies)
    return 0 if ok else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nCancelled.")
        raise SystemExit(0)
