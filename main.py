"""
TodoMate Floating Widget v1.1.0
todomate.net always-on-top floating widget for Windows
"""

import ctypes
import ctypes.wintypes
import json
import os
import sys
import threading
import time
import webbrowser
import winreg

import webview
from PIL import Image
from pystray import Icon, Menu, MenuItem

# ===========================================================================
# Constants
# ===========================================================================
APP_NAME = "TodoMate"
APP_URL = "https://www.todomate.net/"
WINDOW_WIDTH = 380
WINDOW_HEIGHT = 650
MIN_WIDTH = 300
MIN_HEIGHT = 400
TASKBAR_MARGIN = 68
EDGE_MARGIN = 20
DEFAULT_OPACITY = 240
MUTEX_NAME = "TodoMateWidgetMutex_v1"
HOTKEY_ID = 1
MOD_CTRL = 0x0002
MOD_SHIFT = 0x0004
VK_T = 0x54  # Ctrl+Shift+T
GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
LWA_ALPHA = 0x00000002
WM_HOTKEY = 0x0312
CONFIG_FILE = os.path.join(os.getenv("APPDATA", ""), "TodoMateWidget", "config.json")

# ===========================================================================
# Single Instance (Mutex)
# ===========================================================================
def ensure_single_instance():
    kernel32 = ctypes.windll.kernel32
    mutex = kernel32.CreateMutexW(None, False, MUTEX_NAME)
    if ctypes.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        ctypes.windll.user32.MessageBoxW(
            0,
            "TodoMate Widget is already running.\nCheck system tray.",
            "TodoMate Widget",
            0x40  # MB_ICONINFORMATION
        )
        sys.exit(0)
    return mutex

# ===========================================================================
# Config (position/size/opacity persistence)
# ===========================================================================
def load_config():
    defaults = {
        "x": None, "y": None,
        "width": WINDOW_WIDTH, "height": WINDOW_HEIGHT,
        "opacity": DEFAULT_OPACITY,
        "auto_start": False,
    }
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                defaults.update(data)
    except Exception:
        pass
    return defaults


def save_config(cfg):
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception:
        pass

# ===========================================================================
# Auto Start (Registry)
# ===========================================================================
def get_exe_path():
    if getattr(sys, "frozen", False):
        return sys.executable
    return None


def set_auto_start(enable):
    exe = get_exe_path()
    if exe is None:
        return
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        if enable:
            winreg.SetValueEx(key, "TodoMateWidget", 0, winreg.REG_SZ, f'"{exe}"')
        else:
            try:
                winreg.DeleteValue(key, "TodoMateWidget")
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
    except Exception:
        pass


def is_auto_start_enabled():
    exe = get_exe_path()
    if exe is None:
        return False
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
        val, _ = winreg.QueryValueEx(key, "TodoMateWidget")
        winreg.CloseKey(key)
        return exe.lower() in val.lower()
    except Exception:
        return False

# ===========================================================================
# Resource path helper (PyInstaller compatible)
# ===========================================================================
def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# ===========================================================================
# Screen position
# ===========================================================================
def get_bottom_right_position(width, height):
    user32 = ctypes.windll.user32
    screen_w = user32.GetSystemMetrics(0)
    screen_h = user32.GetSystemMetrics(1)
    x = screen_w - width - EDGE_MARGIN
    y = screen_h - height - TASKBAR_MARGIN
    return x, y

# ===========================================================================
# Opacity (Windows API)
# ===========================================================================
_current_opacity = DEFAULT_OPACITY


def _get_hwnd(window):
    try:
        return window.native.Handle
    except Exception:
        return None


def set_window_opacity(window, opacity_byte):
    global _current_opacity
    hwnd = _get_hwnd(window)
    if hwnd is None:
        return
    user32 = ctypes.windll.user32
    ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    if not (ex_style & WS_EX_LAYERED):
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style | WS_EX_LAYERED)
    user32.SetLayeredWindowAttributes(hwnd, 0, int(opacity_byte), LWA_ALPHA)
    _current_opacity = int(opacity_byte)


def opacity_up(window, step=25):
    new_val = min(255, _current_opacity + step)
    set_window_opacity(window, new_val)


def opacity_down(window, step=25):
    new_val = max(30, _current_opacity - step)
    set_window_opacity(window, new_val)

# ===========================================================================
# pywebview settings
# ===========================================================================
webview.settings["OPEN_EXTERNAL_LINKS_IN_BROWSER"] = True
webview.settings["ALLOW_DOWNLOADS"] = False

# ===========================================================================
# JS API bridge
# ===========================================================================
class Api:
    def __init__(self, win_ref):
        self._win = win_ref

    def set_bounds(self, x, y, width, height):
        w = self._win()
        if w is None:
            return
        w.move(int(x), int(y))
        w.resize(int(width), int(height))

    def hide_window(self):
        w = self._win()
        if w is None:
            return
        global _window_visible
        w.hide()
        _window_visible = False

    def refresh_page(self):
        w = self._win()
        if w is None:
            return
        w.load_url(APP_URL)

# ===========================================================================
# Drag bar + Resize handles + Close/Refresh buttons (JS injection)
# ===========================================================================
def on_loaded(window):
    css = """
    ::-webkit-scrollbar { width: 4px; }
    ::-webkit-scrollbar-thumb { background: #ccc; border-radius: 2px; }
    ::-webkit-scrollbar-track { background: transparent; }
    """
    window.load_css(css)

    # Drag bar with close & refresh buttons
    drag_js = """
    (function() {
        if (document.getElementById('widget-drag-bar')) return;

        const bar = document.createElement('div');
        bar.id = 'widget-drag-bar';
        bar.className = 'pywebview-drag-region';
        bar.style.cssText = 'position:fixed;top:0;left:0;right:0;height:32px;background:linear-gradient(135deg,#1a1a1a,#2d2d2d);cursor:move;z-index:99999;display:flex;align-items:center;padding:0 8px;-webkit-user-select:none;user-select:none;';

        bar.innerHTML = `
            <span style="color:#aaa;font-size:11px;font-weight:600;flex:1;pointer-events:none;">\u2630 TodoMate</span>
            <button id="btn-refresh" style="background:none;border:none;color:#888;font-size:14px;cursor:pointer;padding:4px 8px;border-radius:4px;margin-right:2px;"
                onmouseover="this.style.background='#444';this.style.color='#fff'"
                onmouseout="this.style.background='none';this.style.color='#888'"
                title="Refresh">\u21BB</button>
            <button id="btn-close" style="background:none;border:none;color:#888;font-size:14px;cursor:pointer;padding:4px 8px;border-radius:4px;"
                onmouseover="this.style.background='#e74c3c';this.style.color='#fff'"
                onmouseout="this.style.background='none';this.style.color='#888'"
                title="Hide to tray">\u2715</button>
        `;

        document.body.prepend(bar);
        document.body.style.paddingTop = '32px';

        document.getElementById('btn-close').addEventListener('click', function(e) {
            e.stopPropagation();
            if (window.pywebview && window.pywebview.api) {
                window.pywebview.api.hide_window();
            }
        });

        document.getElementById('btn-refresh').addEventListener('click', function(e) {
            e.stopPropagation();
            if (window.pywebview && window.pywebview.api) {
                window.pywebview.api.refresh_page();
            }
        });
    })();
    """
    window.evaluate_js(drag_js)

    # Resize handles
    resize_js = (
        "(function(){"
        "if(document.querySelector('.tm-resize-handle'))return;"
        "const s=document.createElement('style');"
        "s.textContent='"
        ".tm-resize-handle{position:fixed;background:transparent;z-index:99999;}"
        ".tm-resize-handle.right{right:0;top:0;bottom:0;width:6px;cursor:ew-resize;}"
        ".tm-resize-handle.bottom{left:0;right:0;bottom:0;height:6px;cursor:ns-resize;}"
        ".tm-resize-handle.corner{right:0;bottom:0;width:14px;height:14px;cursor:nwse-resize;}"
        "';"
        "document.head.appendChild(s);"
        "let r=false,d=null,sx,sy,sw,sh,swx,swy;"
        "const MW=" + str(MIN_WIDTH) + ",MH=" + str(MIN_HEIGHT) + ";"
        "function dn(dd,e){e.preventDefault();e.stopPropagation();"
        "r=true;d=dd;sx=e.screenX;sy=e.screenY;"
        "sw=window.innerWidth;sh=window.innerHeight;"
        "swx=window.screenX;swy=window.screenY;"
        "document.addEventListener('mousemove',mv,true);"
        "document.addEventListener('mouseup',up,true);}"
        "function mv(e){if(!r)return;e.preventDefault();e.stopPropagation();"
        "let dx=e.screenX-sx,dy=e.screenY-sy;"
        "let nw=sw,nh=sh,nx=swx,ny=swy;"
        "if(d==='right'||d==='corner')nw=Math.max(MW,sw+dx);"
        "if(d==='bottom'||d==='corner')nh=Math.max(MH,sh+dy);"
        "if(window.pywebview&&window.pywebview.api&&window.pywebview.api.set_bounds)"
        "{window.pywebview.api.set_bounds(nx,ny,nw,nh);}}"
        "function up(){r=false;"
        "document.removeEventListener('mousemove',mv,true);"
        "document.removeEventListener('mouseup',up,true);}"
        "['right','bottom','corner'].forEach(function(dd){"
        "const el=document.createElement('div');"
        "el.className='tm-resize-handle '+dd;"
        "el.addEventListener('mousedown',function(e){dn(dd,e);},true);"
        "document.body.appendChild(el);});"
        "})();"
    )
    window.evaluate_js(resize_js)

# ===========================================================================
# Global Hotkey (Ctrl+Shift+T) - toggle show/hide
# ===========================================================================
def start_hotkey_listener(window):
    def listener():
        user32 = ctypes.windll.user32
        if not user32.RegisterHotKey(None, HOTKEY_ID, MOD_CTRL | MOD_SHIFT, VK_T):
            return
        msg = ctypes.wintypes.MSG()
        while True:
            if user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
                if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_ID:
                    toggle_visibility(window)
            time.sleep(0.01)

    t = threading.Thread(target=listener, daemon=True)
    t.start()

# ===========================================================================
# on_top periodic enforcer
# ===========================================================================
def start_on_top_enforcer(window):
    def enforcer():
        while True:
            time.sleep(5)
            try:
                if _window_visible and window:
                    window.on_top = True
            except Exception:
                pass
    t = threading.Thread(target=enforcer, daemon=True)
    t.start()

# ===========================================================================
# Position/Size saver
# ===========================================================================
def start_position_saver(window, config):
    def saver():
        while True:
            time.sleep(10)
            try:
                if window and _window_visible:
                    config["x"] = window.x
                    config["y"] = window.y
                    config["width"] = window.width
                    config["height"] = window.height
                    config["opacity"] = _current_opacity
                    save_config(config)
            except Exception:
                pass
    t = threading.Thread(target=saver, daemon=True)
    t.start()

# ===========================================================================
# Toggle visibility
# ===========================================================================
_window_visible = True


def toggle_visibility(window):
    global _window_visible
    if _window_visible:
        window.hide()
        _window_visible = False
    else:
        window.show()
        window.on_top = True
        _window_visible = True

# ===========================================================================
# System Tray
# ===========================================================================
def create_tray(window, config):
    global _window_visible
    image = Image.open(resource_path("icon.png"))

    def toggle_window(icon, item):
        toggle_visibility(window)

    def reset_position(icon, item):
        x, y = get_bottom_right_position(WINDOW_WIDTH, WINDOW_HEIGHT)
        window.move(x, y)
        window.resize(WINDOW_WIDTH, WINDOW_HEIGHT)

    def do_opacity_up(icon, item):
        opacity_up(window)

    def do_opacity_down(icon, item):
        opacity_down(window)

    def do_opacity_reset(icon, item):
        set_window_opacity(window, 255)

    def size_small(icon, item):
        window.resize(320, 550)

    def size_default(icon, item):
        window.resize(380, 650)

    def size_large(icon, item):
        window.resize(440, 750)

    def do_refresh(icon, item):
        window.load_url(APP_URL)

    def toggle_auto_start(icon, item):
        current = is_auto_start_enabled()
        set_auto_start(not current)
        config["auto_start"] = not current
        save_config(config)

    def auto_start_checked(item):
        return is_auto_start_enabled()

    def open_in_browser(icon, item):
        webbrowser.open(APP_URL)

    def quit_app(icon, item):
        # Save final state
        try:
            config["x"] = window.x
            config["y"] = window.y
            config["width"] = window.width
            config["height"] = window.height
            config["opacity"] = _current_opacity
            save_config(config)
        except Exception:
            pass
        icon.stop()
        window.destroy()

    menu = Menu(
        MenuItem('Show/Hide (Ctrl+Shift+T)', toggle_window, default=True),
        MenuItem('Refresh', do_refresh),
        MenuItem('Reset Position', reset_position),
        Menu.SEPARATOR,
        MenuItem('Opacity', Menu(
            MenuItem('More Opaque (+)', do_opacity_up),
            MenuItem('More Transparent (-)', do_opacity_down),
            MenuItem('Reset (100%)', do_opacity_reset),
        )),
        MenuItem('Window Size', Menu(
            MenuItem('Small (320x550)', size_small),
            MenuItem('Default (380x650)', size_default),
            MenuItem('Large (440x750)', size_large),
        )),
        Menu.SEPARATOR,
        MenuItem('Start with Windows', toggle_auto_start, checked=auto_start_checked),
        MenuItem('Open in Browser', open_in_browser),
        Menu.SEPARATOR,
        MenuItem('Quit', quit_app),
    )

    icon = Icon(APP_NAME, image, 'TodoMate Widget', menu)
    icon.run()

# ===========================================================================
# webview started callback
# ===========================================================================
def on_started(window, config):
    # Apply saved opacity
    time.sleep(0.5)
    set_window_opacity(window, config.get("opacity", DEFAULT_OPACITY))

    # Start background services
    start_hotkey_listener(window)
    start_on_top_enforcer(window)
    start_position_saver(window, config)

    # Start tray
    tray_thread = threading.Thread(target=create_tray, args=(window, config), daemon=True)
    tray_thread.start()

# ===========================================================================
# Main
# ===========================================================================
if __name__ == "__main__":
    # Prevent duplicate instances
    _mutex = ensure_single_instance()

    # Load saved config
    config = load_config()

    # Determine position
    if config["x"] is not None and config["y"] is not None:
        x, y = config["x"], config["y"]
    else:
        x, y = get_bottom_right_position(WINDOW_WIDTH, WINDOW_HEIGHT)

    w = config.get("width", WINDOW_WIDTH)
    h = config.get("height", WINDOW_HEIGHT)

    # JS API
    api = Api(lambda: window)

    window = webview.create_window(
        title=APP_NAME,
        url=APP_URL,
        js_api=api,
        width=w,
        height=h,
        x=x,
        y=y,
        resizable=True,
        min_size=(MIN_WIDTH, MIN_HEIGHT),
        frameless=True,
        easy_drag=False,
        on_top=True,
        shadow=True,
        background_color="#FFFFFF",
        text_select=True,
        zoomable=True,
    )

    window.events.loaded += on_loaded

    webview.start(
        func=on_started,
        args=(window, config),
        private_mode=False,
        storage_path=None,
        debug=False,
    )
