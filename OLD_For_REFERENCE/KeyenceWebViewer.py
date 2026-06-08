#!/usr/bin/env python3
import tkinter as tk
from tkinter import messagebox
import json
import os
import webview
from urllib.parse import urlparse

os.environ["WEBKIT_DISABLE_COMPOSITING_MODE"] = "1"
os.environ["WEBKIT_FORCE_COMPOSITING_MODE"] = "0"

CONFIG_FILE = "browser_config.json"
DEFAULT_REFRESH_MS = 5000
DEFAULT_URL = "http://192.168.1.1/iv4-wm-i.html"
DEFAULT_NAME = "Camera"
MAX_WINDOWS = 9
MAX_COLUMNS = 3


# ================== CONFIG HANDLING ==================
def calculate_grid(count):
    if count == 1:
        return 1, 1
    elif count == 2:
        return 2, 1
    elif count <= 4:
        return 2, 2
    elif count <= 6:
        return 3, 2
    else:
        return 3, 3
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)

            count = min(max(1, data.get("window_count", 1)), MAX_WINDOWS)
            urls = data.get("urls", [DEFAULT_URL] * count)[:count]
            names = data.get("names", [DEFAULT_NAME] * count)[:count]
            refresh_ms = data.get("refresh_ms", DEFAULT_REFRESH_MS)
            auto_refresh = data.get("auto_refresh", True)
            show_config_on_start = data.get("show_config_on_start", True)
            window_size = data.get("window_size", (1200, 800))

            return count, urls, names, refresh_ms, auto_refresh, show_config_on_start, window_size

        except Exception as e:
            print("Config load failed:", e)

    return 1, [DEFAULT_URL], [DEFAULT_NAME], DEFAULT_REFRESH_MS, True, True, (1200, 800)


def save_config(count, urls, names, refresh_ms, auto_refresh, show_config_on_start, window_size):
    data = {
        "window_count": count,
        "urls": urls,
        "names": names,
        "refresh_ms": refresh_ms,
        "auto_refresh": auto_refresh,
        "show_config_on_start": show_config_on_start,
        "window_size": window_size
    }
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=2)


# ================== CONFIG WINDOW ==================

class ConfigWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("IV4 Viewer Configuration")
        self.geometry("500x600")
        self.resizable(False, False)
        self.result = None

        tk.Label(self, text="Number of Windows (1–9):").pack(pady=5)
        self.count_entry = tk.Entry(self)
        self.count_entry.pack(pady=5)

        tk.Label(self, text="Device URLs (one per line):").pack(pady=5)
        self.url_text = tk.Text(self, height=10)
        self.url_text.pack(fill=tk.BOTH, expand=True, padx=10)

        tk.Label(self, text="Window Names (one per line):").pack(pady=5)
        self.name_text = tk.Text(self, height=8)
        self.name_text.pack(fill=tk.BOTH, expand=True, padx=10)

        tk.Label(self, text="Refresh interval (ms):").pack(pady=5)
        self.refresh_entry = tk.Entry(self)
        self.refresh_entry.pack(pady=5)

        self.auto_refresh_var = tk.BooleanVar()
        tk.Checkbutton(self, text="Enable Auto Refresh", variable=self.auto_refresh_var).pack()

        self.show_config_var = tk.BooleanVar()
        tk.Checkbutton(self, text="Show config on startup", variable=self.show_config_var).pack()

        tk.Button(self, text="Save & Launch", command=self.save_and_close,
                  height=4).pack(pady=10, fill=tk.X)

        count, urls, names, refresh_ms, auto_refresh, show_config_on_start, _ = load_config()

        self.count_entry.insert(0, str(count))
        self.url_text.insert("1.0", "\n".join(urls))
        self.name_text.insert("1.0", "\n".join(names))
        self.refresh_entry.insert(0, str(refresh_ms))
        self.auto_refresh_var.set(auto_refresh)
        self.show_config_var.set(show_config_on_start)

    def save_and_close(self):
        try:
            count = int(self.count_entry.get())
            if not (1 <= count <= MAX_WINDOWS):
                raise ValueError("Window count must be 1–9.")

            urls = [u.strip() for u in self.url_text.get("1.0", tk.END).splitlines() if u.strip()]
            while len(urls) < count:
                urls.append(DEFAULT_URL)
            urls = urls[:count]

            names = [n.strip() if n.strip() else DEFAULT_NAME
                     for n in self.name_text.get("1.0", tk.END).splitlines()]
            while len(names) < count:
                names.append(DEFAULT_NAME)
            names = names[:count]

            for u in urls:
                parsed = urlparse(u)
                if not parsed.scheme or not parsed.netloc:
                    raise ValueError(f"Invalid URL: {u}")

            refresh_ms = int(self.refresh_entry.get())
            if refresh_ms < 500:
                raise ValueError("Refresh must be >= 500ms")

            auto_refresh = self.auto_refresh_var.get()
            show_config_on_start = self.show_config_var.get()

            _, _, _, _, _, _, window_size = load_config()

            save_config(count, urls, names, refresh_ms,
                        auto_refresh, show_config_on_start, window_size)

            self.result = (count, urls, names, refresh_ms, auto_refresh)
            self.destroy()

        except Exception as e:
            messagebox.showerror("Error", str(e))


# ================== HTML GENERATION ==================

def build_html(count, urls, names, refresh_ms, auto_refresh):
    columns, rows = calculate_grid(count)

    auto_refresh_script = f"""
        window.refreshInterval = setInterval(refreshAll, {refresh_ms});
    """ if auto_refresh else ""

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            html, body {{
                margin: 0;
                padding: 0;
                background: #0d0d0d;
                display: flex;
                flex-direction: column;
                font-family: Arial, sans-serif;
                
            }}

            #topBar {{
                background: #1a1a1a;
                padding: 6px;
                display: flex;
                gap: 8px;
                transition: transform 0.3s ease;
                z-index: 1000;
            }}

            #topBar.hidden {{
                transform: translateY(-100%);
            }}

            button {{
                background: #2a2a2a;
                border: 1px solid #444;
                color: white;
                padding: 6px 14px;
                cursor: pointer;
            }}

            button:hover {{
                background: #3a3a3a;
            }}

            #gridContainer {{
                flex: 1;
                display: grid;
                grid-template-columns: repeat({columns}, 1fr);
                grid-template-rows: repeat({rows}, 1fr);
                gap: 1px;
                width: 100vw;
                height: 100vh;
                min-height: 0;
                position: absolute;
                overflow: hidden;
            }}

            .pane {{
                display: flex;
                flex-direction: column;
                position: relative;
                border: 1px solid #222;
                width: calc(100vw/{columns});
                height: calc(100vh/{rows});
                align-items: center;
                margin: auto;
            }}
            
            .pane-name {{
                display: flex;
                flex: 0 0 20px;      /*  fixed banner height */
                color: white;
                font-size: 20px;
                background: grey;
                letter-spacing: 1px;
                z-index: 10;         /*  ensure it stays above iframe */
                position: absolute;
                
            }}
            
          .iframe-wrapper{{
                width: calc(100vw/{columns});
                height: calc(100vh/{rows});
                background: darkgrey;
                overflow: hidden;
                position: absolute;
                
               
          }}
          
            iframe{{
                display: flex;
                width: calc(100vw*{columns});
                height: calc(100vh*{rows});
                transform: Scale(calc(100vw/calc(100vw*{rows})));
                transform-origin: 0 0;
          }}
        

            .fullscreen {{
                position: fixed !important;
                top: 0;
                left: 0;
                width: 100vw;
                height: 100vh;
                background: blue;
                z-index: 5000;
            }}

        </style>

        <script>

            function refreshFrame(frame) {{
                let src = frame.src.split("?")[0];
                frame.src = src + "?" + new Date().getTime();
            }}

            function refreshAll() {{
                document.querySelectorAll("iframe").forEach(refreshFrame);
            }}

            function toggleFullscreen(pane) {{
                if (!document.fullscreenElement) {{
                    pane.requestFullscreen();
                }} else {{
                    document.exitFullscreen();
                }}
            }}

            function pauseRefresh() {{
                if(window.refreshInterval) {{
                    clearInterval(window.refreshInterval);
                }}
            }}

            function resumeRefresh() {{
                {auto_refresh_script}
            }}

            window.onblur = pauseRefresh;
            window.onfocus = resumeRefresh;

            function openConfig() {{
                if(window.pywebview) window.pywebview.api.open_config();
            }}

            // Auto-hide top bar
            let hideTimer;
            function showBar() {{
                const bar = document.getElementById("topBar");
                bar.classList.remove("hidden");
                clearTimeout(hideTimer);
                hideTimer = setTimeout(() => {{
                    bar.classList.add("hidden");
                }}, 3000);
            }}

            document.addEventListener("mousemove", showBar);
            window.onload = function() {{
                showBar();
                setTimeout(() => {{
                    document.querySelectorAll("iframe").forEach(frame => {{
                        frame.src = frame.dataset.src;
                }});
                }}, 100);
            }};

        </script>
    </head>

    <body>

        <div id="topBar">
            <button onclick="refreshAll()">Refresh</button>
            <button onclick="openConfig()">Config</button>
        </div>

        <div id="gridContainer">
    """

    for url, name in zip(urls, names):
        html += f"""
        <div class="pane">
            <div class="pane-name">{name}</div>
            <div class="iframe-wrapper">
                <iframe data-src="{url}"
                    oncontextmenu="event.preventDefault(); refreshFrame(this);">
                </iframe>
            </div>
        </div>
        """

    html += """
        </div>
    </body>
    </html>
    """

    return html

# ================== API ==================

class Api:
    def __init__(self, window):
        self.window = window

    def open_config(self):
        cfg = ConfigWindow()
        cfg.wait_window()

        if cfg.result:
            count, urls, names, refresh_ms, auto_refresh = cfg.result
            html = build_html(count, urls, names, refresh_ms, auto_refresh)
            self.window.load_html(html)
            
        return True


# ================== MAIN ==================

def launch():
    count, urls, names, refresh_ms, auto_refresh, show_config_on_start, window_size = load_config()

    if show_config_on_start or not os.path.exists(CONFIG_FILE):
        cfg = ConfigWindow()
        cfg.wait_window()
        if not cfg.result:
            return
        count, urls, names, refresh_ms, auto_refresh = cfg.result

    html = build_html(count, urls, names, refresh_ms, auto_refresh)

    window = webview.create_window(
        "IV4 Grid Monitor",
        html=html,
        fullscreen=True,
        resizable=True
    )

    api = Api(window)
    window._js_api = api

    def on_closed():
        size = window.width, window.height
        save_config(count, urls, names, refresh_ms,
                    auto_refresh, show_config_on_start, size)

    webview.start()
    

if __name__ == "__main__":
    launch()
