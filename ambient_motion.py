"""Quiet visual responses; no rewards, prompts, or changes to simulation state."""
import math


def speed(data):
    if data['activity'] == '睡眠':
        return .65
    return .45 + .55 * min(1., data['energy'] / 65.)


class MotionClock:
    def __init__(self):
        self.previous = None
        self.phase = 0.

    def step(self, now, data):
        if self.previous is not None:
            self.phase += max(0., min(1., now-self.previous)) * speed(data)
        self.previous = now
        return self.phase


def gesture(now, data):
    if data['activity'] not in ('自由活动', '休闲'):
        return None, 0.
    if data['energy'] < 35:
        kind, period, duration = 'drowsy', 29, 4
    elif data['hunger'] > 65:
        kind, period, duration = 'stomach', 37, 4
    elif data['stress'] > 65:
        kind, period, duration = 'release', 43, 5
    else:
        kind, period, duration = 'stretch', 61, 5
    cycle = int(now // period)
    start = 12 + ((cycle * 7 + 3) % 9)
    elapsed = now % period - start
    if not 0 < elapsed < duration:
        return None, 0.
    return kind, math.sin(math.pi * elapsed / duration) ** 2
