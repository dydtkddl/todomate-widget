"""
TodoMate Floating Widget
todomate.net을 항상 최상위 플로팅 위젯으로 띄우는 Windows 데스크톱 앱
"""

import ctypes
import os
import sys
import threading
import webbrowser

import webview
from PIL import Image
from pystray import Icon, Menu, MenuItem

# ---------------------------------------------------------------------------
# 상수
# ---------------------------------------------------------------------------
APP_NAME = "TodoMate"
APP_URL = "https://www.todomate.net/"
WINDOW_WIDTH = 380
WINDOW_HEIGHT = 650
MIN_WIDTH = 300
MIN_HEIGHT = 400
TASKBAR_MARGIN = 68
EDGE_MARGIN = 20

# 투명도 기본값 (0~255, 255=불투명)
DEFAULT_OPACITY = 255

# Windows API 상수
GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
LWA_ALPHA = 0x00000002

# ---------------------------------------------------------------------------
# 리소스 경로 헬퍼 (PyInstaller 번들 호환)
# ---------------------------------------------------------------------------
def resource_path(relative_path):
    """PyInstaller 번들 환경에서도 리소스 경로를 올바르게 찾는다."""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# ---------------------------------------------------------------------------
# 화면 우측 하단 위치 계산
# ---------------------------------------------------------------------------
def get_bottom_right_position(width, height):
    """화면 우측 하단, 작업표시줄 위에 위치를 반환한다."""
    user32 = ctypes.windll.user32
    screen_w = user32.GetSystemMetrics(0)
    screen_h = user32.GetSystemMetrics(1)
    x = screen_w - width - EDGE_MARGIN
    y = screen_h - height - TASKBAR_MARGIN
    return x, y

# ---------------------------------------------------------------------------
# 투명도 제어 (Windows API)
# ---------------------------------------------------------------------------
_current_opacity = DEFAULT_OPACITY

def _get_hwnd(window):
    """pywebview 윈도우의 Windows HWND를 가져온다."""
    try:
        return window.native.Handle
    except Exception:
        return None

def set_window_opacity(window, opacity_byte):
    """
    윈도우 투명도를 설정한다.
    opacity_byte: 0(완전투명) ~ 255(불투명)
    """
    global _current_opacity
    hwnd = _get_hwnd(window)
    if hwnd is None:
        return

    user32 = ctypes.windll.user32

    # WS_EX_LAYERED 스타일 추가
    ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    if not (ex_style & WS_EX_LAYERED):
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style | WS_EX_LAYERED)

    # 투명도 적용
    user32.SetLayeredWindowAttributes(hwnd, 0, int(opacity_byte), LWA_ALPHA)
    _current_opacity = int(opacity_byte)

def opacity_up(window, step=25):
    """투명도를 올린다 (더 불투명하게)."""
    new_val = min(255, _current_opacity + step)
    set_window_opacity(window, new_val)

def opacity_down(window, step=25):
    """투명도를 내린다 (더 투명하게). 최소 30으로 제한."""
    new_val = max(30, _current_opacity - step)
    set_window_opacity(window, new_val)

# ---------------------------------------------------------------------------
# pywebview 설정
# ---------------------------------------------------------------------------
webview.settings["OPEN_EXTERNAL_LINKS_IN_BROWSER"] = True
webview.settings["ALLOW_DOWNLOADS"] = False

# ---------------------------------------------------------------------------
# JS API (Python ↔ JavaScript 브릿지)
# ---------------------------------------------------------------------------
class Api:
    """pywebview JS API — 리사이즈 핸들에서 호출한다."""

    def __init__(self, win_ref):
        self._win = win_ref  # lambda 등으로 나중에 주입

    def set_bounds(self, x, y, width, height):
        """JS 리사이즈 핸들에서 호출: 윈도우 위치+크기 동시 변경"""
        w = self._win()
        if w is None:
            return
        w.move(int(x), int(y))
        w.resize(int(width), int(height))

# ---------------------------------------------------------------------------
# CSS + 리사이즈 핸들 주입 (페이지 로드 완료 후)
# ---------------------------------------------------------------------------
def on_loaded(window):
    """페이지 로드 완료 후 위젯 CSS 및 리사이즈 핸들을 주입한다."""

    # 1) CSS 주입
    css = """
    /* 스크롤바 얇게 */
    ::-webkit-scrollbar { width: 4px; }
    ::-webkit-scrollbar-thumb { background: #ccc; border-radius: 2px; }
    ::-webkit-scrollbar-track { background: transparent; }
    """
    window.load_css(css)

    # 2) 리사이즈 핸들 주입 (JS)
    resize_js = """
    (function() {
        if (document.querySelector('.tm-resize-handle')) return;

        // 스타일 삽입
        const style = document.createElement('style');
        style.textContent = `
            .tm-resize-handle {
                position: fixed;
                background: transparent;
                z-index: 99999;
            }
            .tm-resize-handle.right  { right:0; top:0; bottom:0; width:6px; cursor:ew-resize; }
            .tm-resize-handle.bottom { left:0; right:0; bottom:0; height:6px; cursor:ns-resize; }
            .tm-resize-handle.corner { right:0; bottom:0; width:14px; height:14px; cursor:nwse-resize; }
        `;
        document.head.appendChild(style);

        // 리사이즈 로직
        let resizing = false, dir = null;
        let startX, startY, startW, startH, startWinX, startWinY;
        const MIN_W = """ + str(MIN_WIDTH) + """, MIN_H = """ + str(MIN_HEIGHT) + """;

        function onDown(d, e) {
            e.preventDefault();
            e.stopPropagation();
            resizing = true;
            dir = d;
            startX = e.screenX;
            startY = e.screenY;
            startW = window.innerWidth;
            startH = window.innerHeight;
            startWinX = window.screenX;
            startWinY = window.screenY;
            document.addEventListener('mousemove', onMove, true);
            document.addEventListener('mouseup', onUp, true);
        }

        function onMove(e) {
            if (!resizing) return;
            e.preventDefault();
            e.stopPropagation();
            let dx = e.screenX - startX;
            let dy = e.screenY - startY;
            let newW = startW, newH = startH, newX = startWinX, newY = startWinY;

            if (dir === 'right' || dir === 'corner') {
                newW = Math.max(MIN_W, startW + dx);
            }
            if (dir === 'bottom' || dir === 'corner') {
                newH = Math.max(MIN_H, startH + dy);
            }

            if (window.pywebview && window.pywebview.api && window.pywebview.api.set_bounds) {
                window.pywebview.api.set_bounds(newX, newY, newW, newH);
            }
        }

        function onUp(e) {
            resizing = false;
            document.removeEventListener('mousemove', onMove, true);
            document.removeEventListener('mouseup', onUp, true);
        }

        // 핸들 요소 생성 (우측, 하단, 우측하단 코너)
        ['right', 'bottom', 'corner'].forEach(function(d) {
            const el = document.createElement('div');
            el.className = 'tm-resize-handle ' + d;
            el.addEventListener('mousedown', function(e) { onDown(d, e); }, true);
            document.body.appendChild(el);
        });
    })();
    """
    window.evaluate_js(resize_js)

# ---------------------------------------------------------------------------
# 시스템 트레이
# ---------------------------------------------------------------------------
_window_visible = True

def create_tray(window):
    """시스템 트레이 아이콘 + 메뉴를 생성하고 실행한다."""
    global _window_visible
    image = Image.open(resource_path("icon.png"))

    def toggle_window(icon, item):
        """위젯 보이기/숨기기 토글"""
        global _window_visible
        if _window_visible:
            window.hide()
            _window_visible = False
        else:
            window.show()
            window.on_top = True
            _window_visible = True

    def reset_position(icon, item):
        """위치를 우측 하단 기본 위치로 리셋"""
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

    def open_in_browser(icon, item):
        webbrowser.open(APP_URL)

    def quit_app(icon, item):
        icon.stop()
        window.destroy()

    menu = Menu(
        MenuItem("보이기/숨기기", toggle_window, default=True),
        MenuItem("위치 초기화", reset_position),
        Menu.SEPARATOR,
        MenuItem("투명도", Menu(
            MenuItem("투명도 올리기 (불투명)", do_opacity_up),
            MenuItem("투명도 내리기 (투명)", do_opacity_down),
            MenuItem("투명도 초기화", do_opacity_reset),
        )),
        MenuItem("창 크기", Menu(
            MenuItem("작게 (320×550)", size_small),
            MenuItem("기본 (380×650)", size_default),
            MenuItem("크게 (440×750)", size_large),
        )),
        Menu.SEPARATOR,
        MenuItem("브라우저에서 열기", open_in_browser),
        Menu.SEPARATOR,
        MenuItem("종료", quit_app),
    )

    icon = Icon(APP_NAME, image, "TodoMate Widget", menu)
    icon.run()

# ---------------------------------------------------------------------------
# webview 시작 콜백
# ---------------------------------------------------------------------------
def on_started():
    """webview GUI 루프 시작 후 호출. 트레이 실행 + 초기 투명도 설정."""
    # 기본 투명도 적용 (약간 반투명으로 시작하고 싶으면 여기서 조정)
    # set_window_opacity(window, 230)  # 예: 90% 불투명

    tray_thread = threading.Thread(target=create_tray, args=(window,), daemon=True)
    tray_thread.start()

# ---------------------------------------------------------------------------
# 메인
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    x, y = get_bottom_right_position(WINDOW_WIDTH, WINDOW_HEIGHT)

    # JS API 객체 생성 (window 참조는 lambda로 지연 바인딩)
    api = Api(lambda: window)

    window = webview.create_window(
        title=APP_NAME,
        url=APP_URL,
        js_api=api,
        width=WINDOW_WIDTH,
        height=WINDOW_HEIGHT,
        x=x,
        y=y,
        resizable=True,
        min_size=(MIN_WIDTH, MIN_HEIGHT),
        frameless=True,
        easy_drag=True,
        on_top=True,
        shadow=True,
        background_color="#FFFFFF",
        text_select=True,
        zoomable=True,
    )

    # 이벤트 등록
    window.events.loaded += on_loaded

    # GUI 루프 시작
    webview.start(
        func=on_started,
        private_mode=False,
        storage_path=None,
        debug=False,
    )
