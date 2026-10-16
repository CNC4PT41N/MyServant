"""Short idle CPU and memory sample, isolated save and no real observation."""
import ctypes as c
from ctypes import wintypes as w
from pathlib import Path
import tempfile
import time
import sys
from unittest.mock import patch
import main


class MEMORY(c.Structure):
    _fields_ = [('cb', w.DWORD), ('faults', w.DWORD)] + [(key, c.c_size_t) for key in ('peak_working', 'working', 'peak_paged', 'paged', 'peak_nonpaged', 'nonpaged', 'pagefile', 'peak_pagefile', 'private')]


with tempfile.TemporaryDirectory() as folder:
    path = Path(folder) / 'save.json'
    with patch.object(main, 'SAVE', path), patch.object(main, 'LEGACY_SAVE', path):
        app = main.App()
        app.root.update()
        if '--edge' in sys.argv:
            app.assign('工作')
            left, top, right, bottom = app.desktop.work_area(0, 0)
            app.desktop.move(app.root, left+1, top+(bottom-top)//2-120)
            app.snap_character()
        for hidden in (False, True):
            if hidden:
                app.hide_character()
            wall, cpu = time.perf_counter(), time.process_time()
            while time.perf_counter()-wall < 4:
                app.root.update()
                time.sleep(.015)
            elapsed, used = time.perf_counter()-wall, time.process_time()-cpu
            print('%s CPU (one core): %.2f%%' % ('hidden' if hidden else 'visible', used/elapsed*100))
        kernel, psapi = c.WinDLL('kernel32'), c.WinDLL('psapi')
        kernel.GetCurrentProcess.restype = w.HANDLE
        psapi.GetProcessMemoryInfo.argtypes = [w.HANDLE, c.POINTER(MEMORY), w.DWORD]
        info = MEMORY(cb=c.sizeof(MEMORY))
        assert psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), c.byref(info), info.cb)
        print('working set: %.1f MiB; private: %.1f MiB' % (info.working/1048576, info.private/1048576))
        print('frame cache: %d; motion cache: %d; full atlas cache: %d' % (len(app.image_renderer.frame_cache), len(app.image_renderer.motion_cache), len(app.image_renderer.source_cache)))
        app.close()
