"""Optional per-user Windows logon startup, independent of game saves."""
import subprocess
import sys
import winreg
from pathlib import Path
from app_paths import ROOT

KEY = r'Software\Microsoft\Windows\CurrentVersion\Run'
NAME = 'MyServant'


def command():
    executable = Path(sys.executable)
    if getattr(sys, 'frozen', False):
        return subprocess.list2cmdline([str(executable)])
    windowless = executable.with_name('pythonw.exe')
    return subprocess.list2cmdline([str(windowless if windowless.exists() else executable),
                                   str(ROOT / 'main.py')])


def enabled():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, KEY) as key:
            value, kind = winreg.QueryValueEx(key, NAME)
            return kind == winreg.REG_SZ and value == command()
    except FileNotFoundError:
        return False


def set_enabled(value):
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, KEY, 0, winreg.KEY_SET_VALUE) as key:
        if value:
            winreg.SetValueEx(key, NAME, 0, winreg.REG_SZ, command())
        else:
            try:
                winreg.DeleteValue(key, NAME)
            except FileNotFoundError:
                pass
