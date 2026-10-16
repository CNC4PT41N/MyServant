"""Crisp code-drawn, chamfered game-menu silhouette."""
import ctypes as c
from ctypes import wintypes as w
import tkinter as tk


def enable_dpi_awareness():
    user = c.WinDLL('user32', use_last_error=True)
    try:
        user.SetProcessDpiAwarenessContext.argtypes = [c.c_void_p]
        user.SetProcessDpiAwarenessContext.restype = w.BOOL
        user.SetProcessDpiAwarenessContext(c.c_void_p(-4))
    except AttributeError:
        user.SetProcessDPIAware()


class PanelShell(tk.Canvas):
    def __init__(self, window, theme):
        colors = theme['colors']
        super().__init__(window, bg=colors['surface'], highlightthickness=0, borderwidth=0)
        self.window, self.theme = window, theme
        self.margin = theme['padding'] + 12
        self.top = self.margin + 18
        self.body = tk.Frame(self, bg=colors['surface'])
        self.body_item = self.create_window(self.margin, self.top, window=self.body, anchor='nw')
        self.body.bind('<Configure>', self.resize)
        self.bind('<Configure>', self.outline)
        self.user = c.WinDLL('user32', use_last_error=True)
        self.gdi = c.WinDLL('gdi32', use_last_error=True)
        self.user.GetAncestor.argtypes, self.user.GetAncestor.restype = [w.HWND, w.UINT], w.HWND
        self.user.SetWindowRgn.argtypes, self.user.SetWindowRgn.restype = [w.HWND, w.HANDLE, w.BOOL], c.c_int
        self.gdi.CreatePolygonRgn.argtypes, self.gdi.CreatePolygonRgn.restype = [c.POINTER(w.POINT), c.c_int, c.c_int], w.HANDLE
        self.gdi.DeleteObject.argtypes = [w.HANDLE]

    def resize(self, event=None):
        width = self.body.winfo_reqwidth() + self.margin*2
        height = self.body.winfo_reqheight() + self.top + self.margin
        if width != int(self.cget('width')) or height != int(self.cget('height')):
            self.configure(width=width, height=height)

    def outline(self, event=None):
        width, height = self.winfo_width(), self.winfo_height()
        if width < 50 or height < 50:
            return
        cut = 20
        coords = [(cut, 0), (width-cut, 0), (width, cut), (width, height-cut),
                  (width-cut, height), (cut, height), (0, height-cut), (0, cut)]
        points = (w.POINT * len(coords))(*(w.POINT(x, y) for x, y in coords))
        region = self.gdi.CreatePolygonRgn(points, len(coords), 2)
        hwnd = self.user.GetAncestor(self.window.winfo_id(), 2)
        if not self.user.SetWindowRgn(hwnd, region, True):
            self.gdi.DeleteObject(region)
        self.delete('ornament')
        border = self.theme['colors']['border']
        muted = self.theme['colors']['muted']
        self.create_polygon(20, 5, width-20, 5, width-5, 20, width-5, height-20,
                            width-20, height-5, 20, height-5, 5, height-20, 5, 20,
                            fill='', outline=border, width=1, tags='ornament')
        middle = width/2
        self.create_line(25, 22, middle-30, 22, fill=muted, tags='ornament')
        self.create_line(middle+30, 22, width-25, 22, fill=muted, tags='ornament')
        self.create_line(middle-15, 27, middle-22, 14, middle-12, 18, middle, 25,
                         middle+12, 18, middle+22, 14, middle+15, 27, fill=border, smooth=True, tags='ornament')
        self.create_polygon(middle-4, height-15, middle, height-20, middle+4, height-15,
                            middle, height-10, fill=border, outline='', tags='ornament')
        self.tag_lower('ornament')
