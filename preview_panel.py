"""Capture only an isolated app preview, on its own neutral backdrop."""
from pathlib import Path
import tempfile
import time
from unittest.mock import patch
import tkinter as tk
from PIL import ImageGrab
import main

with tempfile.TemporaryDirectory() as folder:
    path = Path(folder) / 'save.json'
    with patch.object(main, 'SAVE', path), patch.object(main, 'LEGACY_SAVE', path):
        app = main.App()
        app.hide_character()
        app.show_panel()
        app.root.update()
        width, height = app.panel.winfo_width(), app.panel.winfo_height()
        backdrop = tk.Toplevel(app.root)
        backdrop.overrideredirect(True)
        backdrop.configure(bg='#303543')
        backdrop.attributes('-topmost', True)
        backdrop.geometry(f'{width+60}x{height+60}+300+100')
        backdrop.update()
        app.desktop.move(app.panel, 330, 130)
        app.panel.lift()
        app.root.update()
        time.sleep(.2)
        app.root.update()
        output = Path('Saved/preview/panel-hollow.png').resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        ImageGrab.grab(bbox=(300, 100, 360+width, 160+height), all_screens=True).save(output)
        print('Preview:', output, 'panel:', width, height)
        backdrop.destroy()
        app.close()
