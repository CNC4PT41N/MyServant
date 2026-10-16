"""Windows notification-area icon; uses Tk's native message loop."""
import ctypes as c
from ctypes import wintypes as w
import queue
import struct
import startup

LRESULT = c.c_ssize_t
WNDPROC = c.WINFUNCTYPE(LRESULT, w.HWND, w.UINT, w.WPARAM, w.LPARAM)


class WNDCLASS(c.Structure):
    _fields_ = [('style', w.UINT), ('proc', WNDPROC), ('extra', c.c_int),
                ('window_extra', c.c_int), ('instance', w.HINSTANCE),
                ('icon', w.HICON), ('cursor', w.HANDLE), ('background', w.HBRUSH),
                ('menu', w.LPCWSTR), ('name', w.LPCWSTR)]


class NOTIFYICON(c.Structure):
    _fields_ = [('size', w.DWORD), ('window', w.HWND), ('id', w.UINT),
                ('flags', w.UINT), ('message', w.UINT), ('icon', w.HICON),
                ('tip', w.WCHAR * 128), ('state', w.DWORD), ('state_mask', w.DWORD),
                ('info', w.WCHAR * 256), ('version', w.UINT),
                ('title', w.WCHAR * 64), ('info_flags', w.DWORD),
                ('guid', c.c_byte * 16), ('balloon_icon', w.HICON)]


class Tray:
    def __init__(self):
        self.events = queue.Queue()
        self.hidden = False
        self.click_through = False
        self.screen_feedback = True
        self.user = c.WinDLL('user32', use_last_error=True)
        self.shell = c.WinDLL('shell32', use_last_error=True)
        self.kernel = c.WinDLL('kernel32', use_last_error=True)
        signatures = {
            'DefWindowProcW': ([w.HWND, w.UINT, w.WPARAM, w.LPARAM], LRESULT),
            'RegisterClassW': ([c.POINTER(WNDCLASS)], w.WORD),
            'CreateWindowExW': ([w.DWORD, w.LPCWSTR, w.LPCWSTR, w.DWORD, c.c_int, c.c_int, c.c_int, c.c_int, w.HWND, w.HMENU, w.HINSTANCE, c.c_void_p], w.HWND),
            'CreatePopupMenu': ([], w.HMENU),
            'AppendMenuW': ([w.HMENU, w.UINT, c.c_size_t, w.LPCWSTR], w.BOOL),
            'TrackPopupMenu': ([w.HMENU, w.UINT, c.c_int, c.c_int, c.c_int, w.HWND, c.c_void_p], w.UINT),
            'GetCursorPos': ([c.POINTER(w.POINT)], w.BOOL),
            'SetForegroundWindow': ([w.HWND], w.BOOL),
            'PostMessageW': ([w.HWND, w.UINT, w.WPARAM, w.LPARAM], w.BOOL),
            'DestroyMenu': ([w.HMENU], w.BOOL),
            'DestroyWindow': ([w.HWND], w.BOOL),
            'DestroyIcon': ([w.HICON], w.BOOL),
            'RegisterWindowMessageW': ([w.LPCWSTR], w.UINT),
            'CreateIconFromResourceEx': ([c.c_void_p, w.DWORD, w.BOOL, w.DWORD, c.c_int, c.c_int, w.UINT], w.HICON),
            'UnregisterClassW': ([w.LPCWSTR, w.HINSTANCE], w.BOOL),
        }
        for name, (args, result) in signatures.items():
            method = getattr(self.user, name)
            method.argtypes, method.restype = args, result
        self.kernel.GetModuleHandleW.argtypes = [w.LPCWSTR]
        self.kernel.GetModuleHandleW.restype = w.HINSTANCE
        self.shell.Shell_NotifyIconW.argtypes = [w.DWORD, c.POINTER(NOTIFYICON)]
        self.shell.Shell_NotifyIconW.restype = w.BOOL
        self.restart = self.user.RegisterWindowMessageW('TaskbarCreated')
        self.callback = WNDPROC(self.window_proc)
        self.instance = self.kernel.GetModuleHandleW(None)
        self.class_name = f'MyServantTray_{id(self)}'
        wc = WNDCLASS(proc=self.callback, instance=self.instance, name=self.class_name)
        if not self.user.RegisterClassW(c.byref(wc)):
            raise c.WinError(c.get_last_error())
        self.window = self.user.CreateWindowExW(0, self.class_name, 'MyServant', 0, 0, 0, 0, 0, None, None, self.instance, None)
        if not self.window:
            raise c.WinError(c.get_last_error())
        self.icon = self.make_icon()
        self.notification = NOTIFYICON(size=c.sizeof(NOTIFYICON), window=self.window,
                                       id=1, flags=7, message=0x8001,
                                       icon=self.icon, tip='MyServant')
        if not self.shell.Shell_NotifyIconW(0, c.byref(self.notification)):
            self.close()
            raise OSError('无法添加系统托盘图标')

    def make_icon(self):
        # 原生位图图标：浅底青绿色火柴人，不依赖额外图像库。
        pixels = bytearray()
        segments = [(16, 12, 16, 22), (16, 15, 8, 20), (16, 15, 24, 20),
                    (16, 22, 10, 29), (16, 22, 22, 29)]
        for y in range(31, -1, -1):
            for x in range(32):
                on = 3.1 <= ((x - 16)**2 + (y - 7)**2)**.5 <= 5.1
                for ax, ay, bx, by in segments:
                    t = max(0, min(1, ((x-ax)*(bx-ax)+(y-ay)*(by-ay))/((bx-ax)**2+(by-ay)**2)))
                    on |= (x-ax-t*(bx-ax))**2 + (y-ay-t*(by-ay))**2 <= 1.8
                pixels.extend((135, 146, 38, 255) if on else (244, 247, 246, 255))
        data = struct.pack('<IiiHHIIiiII', 40, 32, 64, 1, 32, 0, 4096, 0, 0, 0, 0) + pixels + bytes(128)
        buffer = c.create_string_buffer(data)
        icon = self.user.CreateIconFromResourceEx(buffer, len(data), True, 0x30000, 32, 32, 0)
        if not icon:
            raise c.WinError(c.get_last_error())
        return icon

    def window_proc(self, hwnd, message, wp, lp):
        if message == self.restart and hasattr(self, 'notification'):
            self.shell.Shell_NotifyIconW(0, c.byref(self.notification))
        elif message == 0x8001:
            if lp == 0x202:  # left release
                self.events.put('show')
            elif lp == 0x205:  # right release
                self.popup()
            return 0
        return self.user.DefWindowProcW(hwnd, message, wp, lp)

    def popup(self):
        menu = self.user.CreatePopupMenu()
        try:
            for ident, title in [(1, '显示角色' if self.hidden else '隐藏角色'), (2, '活动菜单'), (3, '退出')]:
                self.user.AppendMenuW(menu, 0, ident, title)
            self.user.AppendMenuW(menu, 8 if self.click_through else 0, 4, '鼠标穿透')
            self.user.AppendMenuW(menu, 8 if self.screen_feedback else 0, 5, '屏幕反馈')
            self.user.AppendMenuW(menu, 8 if startup.enabled() else 0, 6, '开机启动')
            point = w.POINT()
            self.user.GetCursorPos(c.byref(point))
            self.user.SetForegroundWindow(self.window)
            selected = self.user.TrackPopupMenu(menu, 0x100 | 0x2, point.x, point.y, 0, self.window, None)
            self.user.PostMessageW(self.window, 0, 0, 0)
            action = {1: 'show' if self.hidden else 'hide', 2: 'panel', 3: 'quit', 4: 'click_through', 5: 'screen_feedback', 6: 'startup'}.get(selected)
            if action:
                self.events.put(action)
        finally:
            self.user.DestroyMenu(menu)

    def close(self):
        if hasattr(self, 'notification'):
            self.shell.Shell_NotifyIconW(2, c.byref(self.notification))
        if getattr(self, 'window', None):
            self.user.DestroyWindow(self.window)
            self.window = None
        if getattr(self, 'icon', None):
            self.user.DestroyIcon(self.icon)
            self.icon = None
        self.user.UnregisterClassW(self.class_name, self.instance)
