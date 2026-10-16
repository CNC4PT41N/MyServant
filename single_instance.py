"""One desktop pet per Windows session; repeated launch restores the existing pet."""
import ctypes as c
from ctypes import wintypes as w


class SingleInstance:
    def __init__(self, name='Local\\MyServant.DesktopPet'):
        self.kernel = c.WinDLL('kernel32', use_last_error=True)
        for method, args, result in (
            ('CreateMutexW', [c.c_void_p, w.BOOL, w.LPCWSTR], w.HANDLE),
            ('CreateEventW', [c.c_void_p, w.BOOL, w.BOOL, w.LPCWSTR], w.HANDLE),
            ('SetEvent', [w.HANDLE], w.BOOL),
            ('WaitForSingleObject', [w.HANDLE, w.DWORD], w.DWORD),
            ('CloseHandle', [w.HANDLE], w.BOOL),
        ):
            function = getattr(self.kernel, method)
            function.argtypes, function.restype = args, result
        self.event = self.kernel.CreateEventW(None, False, False, name + '.Restore')
        if not self.event:
            raise c.WinError(c.get_last_error())
        self.mutex = self.kernel.CreateMutexW(None, False, name)
        error = c.get_last_error()
        if not self.mutex:
            self.kernel.CloseHandle(self.event)
            raise c.WinError(error)
        self.primary = error != 183
        if not self.primary:
            self.kernel.SetEvent(self.event)

    def restore_requested(self):
        return self.kernel.WaitForSingleObject(self.event, 0) == 0

    def close(self):
        for key in ('mutex', 'event'):
            handle = getattr(self, key, None)
            if handle:
                self.kernel.CloseHandle(handle)
                setattr(self, key, None)
