"""Quiet, pose-based animation timing. No whole-sprite rotation."""
import math

TIMINGS = {
    'idle': (18., 1.2, 1.4, 1.2), 'relax': (22., 1.2, 1.8, 1.2),
    'sleep': (3., 2.8, 3.2, 3.), 'eat': (10., 1.2, 1.5, 1.3),
    'nail': (17., 1., 1., 1.2), 'shell': (20., 1.4, 1.8, 1.4),
    'soul': (21., 1.6, 1.8, 1.6), 'battle': (19., 1.2, 1., 1.2),
    'flower': (25., 1.6, 2., 1.5), 'explore': (22., 1.4, 2., 1.3),
    'drag': (.5, .5, .5, .5),
    'look': (.6, .6, 1.2, .7), 'notes': (.7, .5, .8, .6),
    'bowl': (.9, .5, 1., .6), 'sit': (1.6, .65, 1., .65),
    'work': (19., 1.2, 1., 1.2), 'study': (17., 1., 1., 1.2),
}


def motion_kind(state):
    name = state
    for suffix in ('_left', '_right', '_top', '_bottom'):
        if name.endswith(suffix):
            name = name[:-len(suffix)]
    for prefix in ('process_', 'feedback_'):
        if name.startswith(prefix):
            name = name[len(prefix):]
    return name


def frame_index(state, elapsed, count, config):
    if count <= 1:
        return 0
    durations = config.get('timings', {}).get(state)
    if durations is None and config.get('animation_style') == 'knight-frames':
        durations = TIMINGS.get(motion_kind(state))
    if durations is None or len(durations) != count:
        return int(max(0., elapsed) * config['fps']) % count
    position = max(0., elapsed) % sum(durations)
    for index, duration in enumerate(durations):
        if position < duration:
            return config.get('frame_sequences', {}).get(state, list(range(count)))[index]
        position -= duration
    return count - 1


def rig_phase(kind, elapsed, config):
    if kind == 'sleep':
        return (elapsed % 10.) / 10.
    if kind == 'drag':
        return (elapsed % 3.) / 3.
    period = config.get('rig_intervals', {}).get(kind, {
        'idle': 24., 'relax': 28., 'eat': 16., 'nail': 22., 'battle': 24.,
        'shell': 26., 'soul': 28., 'flower': 30., 'explore': 28.,
        'look': 12., 'notes': 16., 'bowl': 16., 'sit': 26.,
    }.get(kind, 26.))
    local = elapsed % period
    duration = 4.
    return 0. if local < period-duration else (local-(period-duration))/duration


def static_offset(state, elapsed):
    # Legacy single-frame files get at most one pixel of breath, never rotation.
    return 0, int(math.sin(elapsed * 1.2) > .3)
