"""Edge snapping in monitor work areas, including negative-coordinate displays."""
import ctypes as c
from ctypes import wintypes as w


def snap_position(x, y, width, height, area, previous=None, threshold=24):
    left, top, right, bottom = area
    x = max(left, min(x, right - width))
    y = max(top, min(y, bottom - height))
    distances = {'left': x-left, 'right': right-x-width,
                 'top': y-top, 'bottom': bottom-y-height}
    # Keep a stable pose in corners instead of alternating on each frame.
    candidates = [edge for edge, distance in distances.items() if distance <= threshold]
    edge = previous if previous in candidates else min(candidates, key=distances.get) if candidates else None
    if edge == 'left':
        x = left
    elif edge == 'right':
        x = right-width
    elif edge == 'top':
        y = top
    elif edge == 'bottom':
        y = bottom-height
    return x, y, edge


class MONITORINFO(c.Structure):
    _fields_ = [('size', w.DWORD), ('monitor', w.RECT), ('work', w.RECT), ('flags', w.DWORD)]


class Desktop:
    def __init__(self):
        self.user = c.WinDLL('user32', use_last_error=True)
        self.user.MonitorFromPoint.argtypes = [w.POINT, w.DWORD]
        self.user.MonitorFromPoint.restype = w.HANDLE
        self.user.GetMonitorInfoW.argtypes = [w.HANDLE, c.POINTER(MONITORINFO)]
        self.user.GetMonitorInfoW.restype = w.BOOL
        self.user.GetAncestor.argtypes = [w.HWND, w.UINT]
        self.user.GetAncestor.restype = w.HWND
        self.user.GetWindowRect.argtypes = [w.HWND, c.POINTER(w.RECT)]
        self.user.GetWindowRect.restype = w.BOOL
        self.user.GetWindowLongPtrW.argtypes = [w.HWND, c.c_int]
        self.user.GetWindowLongPtrW.restype = c.c_ssize_t
        self.user.SetWindowLongPtrW.argtypes = [w.HWND, c.c_int, c.c_ssize_t]
        self.user.SetWindowLongPtrW.restype = c.c_ssize_t
        self.user.SetWindowPos.argtypes = [w.HWND, w.HWND, c.c_int, c.c_int, c.c_int, c.c_int, w.UINT]
        self.user.SetWindowPos.restype = w.BOOL
        for name in ('IsWindowVisible', 'IsIconic'):
            method = getattr(self.user, name)
            method.argtypes, method.restype = [w.HWND], w.BOOL

    def work_area(self, x, y):
        monitor = self.user.MonitorFromPoint(w.POINT(int(x), int(y)), 2)
        info = MONITORINFO(size=c.sizeof(MONITORINFO))
        if not self.user.GetMonitorInfoW(monitor, c.byref(info)):
            raise c.WinError(c.get_last_error())
        r = info.work
        return r.left, r.top, r.right, r.bottom

    def move(self, window, x, y, width=None, height=None):
        # Tk interprets negative geometry offsets relative to the far screen edge.
        # SetWindowPos uses absolute desktop coordinates on every monitor.
        hwnd = self.user.GetAncestor(window.winfo_id(), 2)
        flags = 0x4 | 0x10  # no Z-order change, no activation
        if width is None:
            flags |= 0x1  # preserve size
        if not self.user.SetWindowPos(hwnd, None, int(x), int(y), width or 0, height or 0, flags):
            raise c.WinError(c.get_last_error())

    def position(self, window):
        hwnd = self.user.GetAncestor(window.winfo_id(), 2)
        rect = w.RECT()
        if not self.user.GetWindowRect(hwnd, c.byref(rect)):
            raise c.WinError(c.get_last_error())
        return rect.left, rect.top

    def click_through(self, window, enabled):
        hwnd = self.user.GetAncestor(window.winfo_id(), 2)
        style = self.user.GetWindowLongPtrW(hwnd, -20)
        style = style | 0x20 if enabled else style & ~0x20
        self.user.SetWindowLongPtrW(hwnd, -20, style)
        self.user.SetWindowPos(hwnd, None, 0, 0, 0, 0, 0x37)

    def is_click_through(self, window):
        hwnd = self.user.GetAncestor(window.winfo_id(), 2)
        return bool(self.user.GetWindowLongPtrW(hwnd, -20) & 0x20)

    def ensure_visible(self, window, topmost):
        """Called only for a pet the user has chosen to show; never activate it."""
        restored = False
        if window.state() != 'normal':
            window.deiconify()
            window.update_idletasks()
            restored = True
        hwnd = self.user.GetAncestor(window.winfo_id(), 2)
        if not self.user.IsWindowVisible(hwnd) or self.user.IsIconic(hwnd):
            # Use Tk to remap its own window. A synchronous native ShowWindow
            # can re-enter Tcl/Python event handlers outside a Tk call on 3.6.
            position = self.position(window)
            window.withdraw()
            window.deiconify()
            window.update_idletasks()
            self.move(window, *position)
            hwnd = self.user.GetAncestor(window.winfo_id(), 2)
            restored = True
        if topmost and not self.user.GetWindowLongPtrW(hwnd, -20) & 0x8:
            if not self.user.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x13):
                raise c.WinError(c.get_last_error())
            restored = True
        return restored
