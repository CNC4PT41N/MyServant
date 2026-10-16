"""Low-frequency local observation and fixed, non-intrusive reactions."""
import ctypes as c
from ctypes import wintypes as w
import datetime
import os
from pathlib import Path
import random
import subprocess
import tempfile
import time
from PIL import ImageGrab

WORDS = {
    'code': ('visual studio', 'vscode', 'pycharm', 'github', 'def ', 'function ', '代码', '编程', 'python', 'javascript', 'c++'),
    'design': ('photoshop', 'illustrator', 'figma', 'blender', 'krita', '配色', '绘画', '设计稿', '画布'),
    'document': ('excel', 'word', 'powerpoint', '文档', '表格', '报表', '论文'),
    'food': ('菜谱', '食谱', '美食', '做菜', '烹饪', 'recipe'),
    'travel': ('旅行', '风景', '旅游', '山脉', '湖泊', 'landscape'),
    'game': ('steam', 'epic games', 'minecraft', '空洞骑士', '原神', '游戏'),
    'media': ('bilibili', 'youtube', 'netflix', 'spotify', '音乐', '视频', '电影'),
}
RESPONSES = {
    ('学习', 'code'): ('这部分我还没学到。', 'notes'),
    ('学习', 'design'): ('这个配色可以记下来。', 'notes'),
    ('学习', 'document'): ('这页值得记点笔记。', 'notes'),
    ('学习', 'travel'): ('书里可没有这幅风景。', 'look'),
    ('工作', 'code'): ('你那边也在写代码。', 'look'),
    ('工作', 'design'): ('这份稿子挺有意思。', 'look'),
    ('工作', 'document'): ('你这边也在整理资料。', 'look'),
    ('工作', 'game'): ('你那边比我这边热闹。', 'look'),
    ('进食', 'food'): ('我这碗突然显得有点普通。', 'bowl'),
    ('进食', 'media'): ('边吃边看，刚好。', 'bowl'),
    ('休闲', 'media'): ('这会儿倒是很适合放松。', 'sit'),
    ('休闲', 'travel'): ('这里看起来适合待一会儿。', 'sit'),
    ('休闲', 'game'): ('这一局看起来挺热闹。', 'look'),
    ('自由活动', 'travel'): ('这里看起来适合待一会儿。', 'sit'),
    ('自由活动', 'food'): ('看起来不错。', 'look'),
    ('自由活动', 'media'): ('我也看一会儿。', 'sit'),
    ('自由活动', 'game'): ('让我看看。', 'look'),
    ('自由活动', 'design'): ('这个颜色挺特别。', 'look'),
}


def day_key(now):
    return datetime.datetime.fromtimestamp(now, datetime.timezone(datetime.timedelta(hours=8))).strftime('%Y-%m-%d')


def default_state():
    return {'enabled': True, 'next_at': 0., 'day': '', 'count': 0, 'last_text': ''}


class FeedbackSchedule:
    def __init__(self, state, now=None, rng=None):
        self.state = state
        self.rng = rng or random
        now = time.time() if now is None else now
        # Restart never triggers a backlog or immediate observation.
        if state['next_at'] <= now:
            self.defer(now)

    def defer(self, now):
        self.state['next_at'] = now + self.rng.uniform(3, 4) * 3600

    def due(self, now, activity, hidden):
        state = self.state
        today = day_key(now)
        if state['day'] != today:
            state.update(day=today, count=0)
        if not state['enabled'] or now < state['next_at']:
            return False
        self.defer(now)
        return not hidden and activity != '睡眠' and state['count'] < 4

    def response(self, activity, category):
        result = RESPONSES.get((activity, category))
        if result and result[0] == self.state['last_text']:
            return None
        return result

    def delivered(self, text):
        self.state['count'] += 1
        self.state['last_text'] = text


def classify(title, text=''):
    title, text = title.lower(), text.lower()
    scores = {category: sum(3 for word in words if word in title) + sum(1 for word in words if word in text) for category, words in WORDS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] >= 2 else None


def observe(excluded_windows=(), cancel=None):
    """One foreground-window capture, local Windows OCR, no network or retained image."""
    if cancel and cancel.is_set():
        return None
    user = c.WinDLL('user32', use_last_error=True)
    user.GetForegroundWindow.restype = w.HWND
    user.GetWindowTextW.argtypes = [w.HWND, w.LPWSTR, c.c_int]
    user.GetWindowRect.argtypes = [w.HWND, c.POINTER(w.RECT)]
    hwnd = user.GetForegroundWindow()
    if not hwnd or hwnd in excluded_windows:
        return None
    title = c.create_unicode_buffer(512)
    user.GetWindowTextW(hwnd, title, 512)
    rect = w.RECT()
    if not user.GetWindowRect(hwnd, c.byref(rect)) or rect.right <= rect.left or rect.bottom <= rect.top:
        return None
    # Clip to the virtual desktop; only the visible foreground area is sampled.
    user.GetSystemMetrics.argtypes = [c.c_int]
    left, top = user.GetSystemMetrics(76), user.GetSystemMetrics(77)
    right, bottom = left + user.GetSystemMetrics(78), top + user.GetSystemMetrics(79)
    bbox = (max(left, rect.left), max(top, rect.top), min(right, rect.right), min(bottom, rect.bottom))
    if bbox[2] <= bbox[0] or bbox[3] <= bbox[1]:
        return None
    text = ''
    try:
        with tempfile.TemporaryDirectory(prefix='myservant-observation-') as folder:
            if cancel and cancel.is_set():
                return None
            image = ImageGrab.grab(bbox=bbox, all_screens=True)
            if cancel and cancel.is_set():
                return None
            image.thumbnail((1600, 1200))
            path = Path(folder) / 'frame.png'
            image.save(path)
            powershell = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
            from app_paths import ROOT
            script = ROOT / 'local_ocr.ps1'
            with subprocess.Popen([str(powershell), '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', str(script), str(path)], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, creationflags=0x08000000) as process:
                started = time.monotonic()
                while True:
                    if (cancel and cancel.is_set()) or time.monotonic()-started > 20:
                        process.kill()
                        process.communicate()
                        return None
                    try:
                        output, _ = process.communicate(timeout=.1)
                        break
                    except subprocess.TimeoutExpired:
                        continue
                if process.returncode == 0:
                    text = output.decode('utf-8-sig', errors='replace')[:12000]
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None if cancel and cancel.is_set() else classify(title.value, text)
