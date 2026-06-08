import webview
import os

html_file = os.path.abspath("index.html")

window = webview.create_window(
    title="HTML Viewer",
    url=f"file:///{html_file}",
    fullscreen=True
)

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
    
webview.start(gui="edgechromium")