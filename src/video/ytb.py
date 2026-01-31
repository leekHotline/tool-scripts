import sys
import os
import socket
import yt_dlp


def test_proxy(host: str, port: int) -> bool:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except:
        return False


def setup_proxy() -> str | None:
    existing = os.environ.get("HTTP_PROXY") or os.environ.get("HTTPS_PROXY")
    if existing:
        return existing
    
    proxy_ports = {7890: "Clash", 7891: "Clash", 10809: "V2Ray", 1080: "SS/SSR"}
    
    for port, name in proxy_ports.items():
        if test_proxy("127.0.0.1", port):
            proxy_url = f"http://127.0.0.1:{port}"
            print(f"🔍 检测到 {name} 代理: {proxy_url}")
            os.environ["HTTP_PROXY"] = proxy_url
            os.environ["HTTPS_PROXY"] = proxy_url
            return proxy_url
    
    return None


def download_video(url: str, proxy: str = None):
    ydl_opts = {
        "outtmpl": "%(title).200s.%(ext)s",
        "format": "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
        "merge_output_format": "mp4",
        "continuedl": True,
        "retries": 10,
        "fragment_retries": 10,
        "socket_timeout": 30,
        "noplaylist": True,
        "quiet": False,
        "cachedir": False,
        
        # 关键：使用 Edge 浏览器（通常没有 DPAPI 问题）
        "cookiesfrombrowser": ("edge",),
        
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
        },
    }
    
    if proxy:
        ydl_opts["proxy"] = proxy
    
    print(f"🍪 从 Edge 获取 cookies")
    print(f"🌐 使用代理: {proxy}")
    print(f"⏳ 开始下载: {url}")
    print("-" * 50)
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        print("-" * 50)
        print("✅ 下载完成！")
        return True
        
    except Exception as e:
        if "DPAPI" in str(e) or "decrypt" in str(e).lower():
            print(f"⚠️ Edge cookies 也失败，尝试 Firefox...")
            return try_firefox(url, proxy)
        else:
            print(f"❌ 下载失败: {e}")
            return try_no_cookies(url, proxy)


def try_firefox(url: str, proxy: str = None) -> bool:
    """尝试 Firefox"""
    ydl_opts = {
        "outtmpl": "%(title).200s.%(ext)s",
        "format": "bestvideo[height<=1080]+bestaudio/best",
        "merge_output_format": "mp4",
        "noplaylist": True,
        "cookiesfrombrowser": ("firefox",),
    }
    
    if proxy:
        ydl_opts["proxy"] = proxy
    
    try:
        print("🦊 尝试 Firefox cookies...")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        print("✅ 下载完成！")
        return True
    except:
        return try_no_cookies(url, proxy)


def try_no_cookies(url: str, proxy: str = None) -> bool:
    """不使用 cookies，用 Android 客户端"""
    print("\n🔄 尝试 Android 客户端模式...")
    
    ydl_opts = {
        "outtmpl": "%(title).200s.%(ext)s",
        "format": "best[height<=720]/best",
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": False,
        
        "extractor_args": {
            "youtube": {
                "player_client": ["android_vr", "android"],
                "player_skip": ["webpage"],
            }
        },
        
        "http_headers": {
            "User-Agent": "com.google.android.youtube/19.09.37 (Linux; U; Android 14; en_US; sdk_gphone64_arm64 Build/UE1A.230829.036) gzip",
        },
    }
    
    if proxy:
        ydl_opts["proxy"] = proxy
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        print("✅ 下载完成！")
        return True
    except Exception as e:
        print(f"❌ 失败: {e}")
        show_manual_guide(url, proxy)
        return False


def show_manual_guide(url: str, proxy: str):
    """显示手动解决方案"""
    print("\n" + "=" * 50)
    print("💡 手动解决方案")
    print("=" * 50)
    print("\n方法1: 安装浏览器扩展导出 cookies")
    print("  1. Chrome 安装: Get cookies.txt LOCALLY")
    print("  2. 打开 YouTube 并登录")
    print("  3. 点扩展导出 cookies.txt 到当前目录")
    print("  4. 运行: yt-dlp --cookies cookies.txt <URL>")
    print("\n方法2: 使用 Firefox (关闭后运行)")
    print(f'  yt-dlp --cookies-from-browser firefox --proxy {proxy} "{url}"')
    print("\n方法3: 更新 yt-dlp")
    print("  uv pip install -U yt-dlp")


def test_connection(proxy: str) -> bool:
    import urllib.request
    
    print("🧪 测试 YouTube 连接...")
    try:
        handler = urllib.request.ProxyHandler({'http': proxy, 'https': proxy})
        opener = urllib.request.build_opener(handler)
        opener.addheaders = [('User-Agent', 'Mozilla/5.0')]
        response = opener.open('https://www.youtube.com', timeout=10)
        if response.status == 200:
            print("✅ YouTube 连接成功！")
            return True
    except Exception as e:
        print(f"❌ 连接失败: {e}")
    return False


if __name__ == "__main__":
    try:
        print("=" * 50)
        print("     YouTube 视频下载器 v3")
        print("=" * 50)
        
        proxy = setup_proxy()
        if not proxy:
            print("⚠️ 未检测到代理")
            sys.exit(1)
        
        if not test_connection(proxy):
            sys.exit(1)
        
        # 提示关闭浏览器
        print("\n⚠️  请确保已关闭 Edge/Chrome 浏览器窗口")
        input("   按 Enter 继续...")
        
        video_url = input("\n请输入视频链接: ").strip()
        if not video_url:
            print("⚠️ 链接不能为空")
            sys.exit(1)
        
        print()
        download_video(video_url, proxy)
        
    except KeyboardInterrupt:
        print("\n👋 已取消")
        sys.exit(0)