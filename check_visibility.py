"""Exercise native compositor resets on an isolated, disposable Tk window."""
import ctypes as c
from ctypes import wintypes as w
import tkinter as tk
from PIL import Image, ImageDraw
from alpha_window import AlphaWindow
from desktop_edges import Desktop
from unittest.mock import patch


def run():
    root = tk.Tk()
    root.withdraw()
    root.overrideredirect(True)
    root.geometry('220x240+350+150')
    root.configure(bg='#ff00ff')
    root.wm_attributes('-transparentcolor', '#ff00ff')
    tk.Canvas(root, width=220, height=240, bg='#ff00ff', highlightthickness=0).pack()
    alpha = AlphaWindow(root)
    user = alpha.user
    user.GetLayeredWindowAttributes.argtypes = [w.HWND, c.POINTER(w.DWORD), c.POINTER(c.c_ubyte), c.POINTER(w.DWORD)]
    user.GetLayeredWindowAttributes.restype = w.BOOL
    image = Image.new('RGBA', (220, 240))
    ImageDraw.Draw(image).ellipse((60, 55, 160, 190), fill='white')

    def mode():
        hwnd = user.GetAncestor(root.winfo_id(), 2)
        color, opacity, flags = w.DWORD(), c.c_ubyte(), w.DWORD()
        global_mode = user.GetLayeredWindowAttributes(hwnd, c.byref(color), c.byref(opacity), c.byref(flags))
        return bool(user.GetWindowLongPtrW(hwnd, -20) & 0x80000), bool(global_mode), opacity.value

    try:
        root.deiconify()
        root.update()
        alpha.show(image)
        print('Initial:', mode())
        user.SetLayeredWindowAttributes.argtypes = [w.HWND, w.DWORD, c.c_ubyte, w.DWORD]
        user.SetLayeredWindowAttributes.restype = w.BOOL
        hwnd = user.GetAncestor(root.winfo_id(), 2)
        assert user.SetLayeredWindowAttributes(hwnd, 0, 0, 2)
        alpha.show(image)
        after_global = mode()
        print('After global-opacity reset, same frame:', after_global)
        # Restore a fresh layered mode before independently testing style loss.
        style = user.GetWindowLongPtrW(hwnd, -20)
        user.SetWindowLongPtrW(hwnd, -20, style & ~0x80000)
        user.SetWindowLongPtrW(hwnd, -20, style | 0x80000)
        alpha.last_pixels = None
        alpha.show(image)
        user.SetWindowLongPtrW(hwnd, -20, style & ~0x80000)
        alpha.show(image)
        after_style = mode()
        print('After layered-style loss, same frame:', after_style)
        assert not after_global[1], 'Same-pixel cache failed to recover a zero-opacity window'
        assert after_style[0], 'Same-pixel cache failed to restore layered style'
        original = user.UpdateLayeredWindow
        with patch.object(user, 'UpdateLayeredWindow', wraps=original) as upload:
            alpha.last_upload = 100.
            with patch('alpha_window.time.monotonic', return_value=100.2):
                alpha.show(image)
            assert upload.call_count == 0
            with patch('alpha_window.time.monotonic', return_value=101.2):
                alpha.show(image)
            assert upload.call_count == 1, 'Quiet frames need periodic compositor refresh'
        root.withdraw()
        root.update()
        root.deiconify()
        root.update()
        alpha.show(image)
        assert mode()[0] and not mode()[1]
        desktop = Desktop()
        hwnd = user.GetAncestor(root.winfo_id(), 2)
        user.ShowWindow.argtypes, user.ShowWindow.restype = [w.HWND, c.c_int], w.BOOL
        user.ShowWindow(hwnd, 0)
        assert desktop.ensure_visible(root, False)
        alpha.invalidate()
        alpha.show(image)
        assert desktop.user.IsWindowVisible(user.GetAncestor(root.winfo_id(), 2))
        # Native display recovery must not clear a user-selected click-through.
        desktop.click_through(root, True)
        style = user.GetWindowLongPtrW(hwnd, -20)
        user.SetWindowLongPtrW(hwnd, -20, style & ~0x80000)
        alpha.show(image)
        assert desktop.is_click_through(root)
        print('PASS: compositor recovery, quiet refresh, remap, native visibility and click-through')
    finally:
        alpha.close()
        root.destroy()


if __name__ == '__main__':
    run()
