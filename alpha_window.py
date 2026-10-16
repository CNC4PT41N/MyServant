"""Per-pixel alpha composition for PNG desktop characters on Windows."""
import ctypes as c
from ctypes import wintypes as w
import time
from PIL import Image, ImageChops


class LayeredWindowError(OSError):
    """A transient native window/compositor failure, not a corrupt image."""


class SIZE(c.Structure):
    _fields_ = [('cx', c.c_long), ('cy', c.c_long)]


class BLEND(c.Structure):
    _fields_ = [('op', c.c_byte), ('flags', c.c_byte), ('opacity', c.c_ubyte), ('alpha', c.c_byte)]


class BITMAPINFO(c.Structure):
    _fields_ = [('size', w.DWORD), ('width', c.c_long), ('height', c.c_long),
                ('planes', w.WORD), ('bits', w.WORD), ('compression', w.DWORD),
                ('image_size', w.DWORD), ('xppm', c.c_long), ('yppm', c.c_long),
                ('colors', w.DWORD), ('important', w.DWORD), ('color', w.DWORD)]


class AlphaWindow:
    def __init__(self, root):
        self.root = root
        self.active = False
        self.buffer = None
        self.last_pixels = None
        self.hwnd = None
        self.last_upload = 0.
        self.user = c.WinDLL('user32', use_last_error=True)
        self.gdi = c.WinDLL('gdi32', use_last_error=True)
        signatures = {
            'GetAncestor': ([w.HWND, w.UINT], w.HWND),
            'GetDC': ([w.HWND], w.HDC),
            'GetWindowRect': ([w.HWND, c.POINTER(w.RECT)], w.BOOL),
            'GetLayeredWindowAttributes': ([w.HWND, c.POINTER(w.DWORD), c.POINTER(c.c_ubyte), c.POINTER(w.DWORD)], w.BOOL),
            'ReleaseDC': ([w.HWND, w.HDC], c.c_int),
            'GetWindowLongPtrW': ([w.HWND, c.c_int], c.c_ssize_t),
            'SetWindowLongPtrW': ([w.HWND, c.c_int, c.c_ssize_t], c.c_ssize_t),
            'UpdateLayeredWindow': ([w.HWND, w.HDC, c.POINTER(w.POINT), c.POINTER(SIZE), w.HDC, c.POINTER(w.POINT), w.DWORD, c.POINTER(BLEND), w.DWORD], w.BOOL),
        }
        for name, (args, result) in signatures.items():
            method = getattr(self.user, name)
            method.argtypes, method.restype = args, result
        signatures = {
            'CreateCompatibleDC': ([w.HDC], w.HDC),
            'CreateDIBSection': ([w.HDC, c.POINTER(BITMAPINFO), w.UINT, c.POINTER(c.c_void_p), w.HANDLE, w.DWORD], w.HBITMAP),
            'SelectObject': ([w.HDC, w.HANDLE], w.HANDLE),
            'DeleteObject': ([w.HANDLE], w.BOOL),
            'DeleteDC': ([w.HDC], w.BOOL),
        }
        for name, (args, result) in signatures.items():
            method = getattr(self.gdi, name)
            method.argtypes, method.restype = args, result
    def invalidate(self):
        # Tk may recreate its wrapper HWND or reapply color-key/global alpha
        # on mapping. Pixel equality alone cannot establish that it is visible.
        self.active = False
        self.last_pixels = None
        self.last_upload = 0.

    def configure_layered(self, hwnd):
        self.root.wm_attributes('-transparentcolor', '')
        style = self.user.GetWindowLongPtrW(hwnd, -20)
        # SetLayeredWindowAttributes (used by Tk) makes UpdateLayeredWindow
        # fail until WS_EX_LAYERED has been removed and applied again.
        self.user.SetWindowLongPtrW(hwnd, -20, style & ~0x80000)
        self.user.SetWindowLongPtrW(hwnd, -20, style | 0x80000)
        self.hwnd, self.active = hwnd, True
        self.last_pixels = None

    @staticmethod
    def native_error():
        error = c.WinError(c.get_last_error())
        return LayeredWindowError(str(error))

    def show(self, image):
        self.root.update_idletasks()
        hwnd = self.user.GetAncestor(self.root.winfo_id(), 2)
        style = self.user.GetWindowLongPtrW(hwnd, -20)
        color, opacity, flags = w.DWORD(), c.c_ubyte(), w.DWORD()
        global_alpha = self.user.GetLayeredWindowAttributes(hwnd, c.byref(color), c.byref(opacity), c.byref(flags))
        if not self.active or hwnd != self.hwnd or not style & 0x80000 or global_alpha:
            self.configure_layered(hwnd)
        r, g, b, a = image.split()
        premultiplied = Image.merge('RGBA', (ImageChops.multiply(r, a), ImageChops.multiply(g, a), ImageChops.multiply(b, a), a))
        data = premultiplied.tobytes('raw', 'BGRA')
        if self.buffer is None or self.buffer[-1] != image.size:
            self.release_buffer()
            screen = self.user.GetDC(None)
            dc = self.gdi.CreateCompatibleDC(screen)
            info = BITMAPINFO(size=40, width=image.width, height=-image.height, planes=1, bits=32)
            address = c.c_void_p()
            bitmap = self.gdi.CreateDIBSection(screen, c.byref(info), 0, c.byref(address), None, 0)
            if not bitmap or not dc:
                if bitmap:
                    self.gdi.DeleteObject(bitmap)
                if dc:
                    self.gdi.DeleteDC(dc)
                self.user.ReleaseDC(None, screen)
                raise self.native_error()
            old = self.gdi.SelectObject(dc, bitmap)
            self.buffer = (screen, dc, bitmap, old, address, image.size)
        screen, dc, bitmap, old, address, _ = self.buffer
        rect = w.RECT()
        if not self.user.GetWindowRect(hwnd, c.byref(rect)):
            raise self.native_error()
        stamp = (hwnd, data, rect.left, rect.top)
        now = time.monotonic()
        # A quiet pose can stay identical for 20+ seconds. Periodically upload
        # it anyway so compositor resets cannot leave the pet blank that long.
        if stamp == self.last_pixels and now - self.last_upload < 1.:
            return
        c.memmove(address, data, len(data))
        position = w.POINT(rect.left, rect.top)
        size, origin, blend = SIZE(image.width, image.height), w.POINT(0, 0), BLEND(0, 0, 255, 1)
        def upload():
            return self.user.UpdateLayeredWindow(hwnd, screen, c.byref(position), c.byref(size), dc, c.byref(origin), 0, c.byref(blend), 2)
        if not upload():
            self.configure_layered(hwnd)
            if not upload():
                self.invalidate()
                raise self.native_error()
        self.last_pixels = stamp
        self.last_upload = now

    def release_buffer(self):
        if self.buffer:
            screen, dc, bitmap, old, _, _ = self.buffer
            self.gdi.SelectObject(dc, old)
            self.gdi.DeleteObject(bitmap)
            self.gdi.DeleteDC(dc)
            self.user.ReleaseDC(None, screen)
            self.buffer = None
        self.last_pixels = None

    def close(self):
        self.release_buffer()

    def reset(self):
        self.release_buffer()
        if self.active:
            self.root.wm_attributes('-transparentcolor', '#ff00ff')
        self.hwnd = None
        self.invalidate()
