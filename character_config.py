"""One editable character.json beside the application, independent of saves."""
import json
import math
import os
from pathlib import Path
import re
import stat as stat_module

from app_paths import ROOT
CHARACTER = ROOT / 'character.json'
DEFAULT_CHARACTER = ROOT / 'character-hollow-knight-v3.json'
STATES = {'自由活动': 'idle', '工作': 'work', '学习': 'study',
          '睡眠': 'sleep', '进食': 'eat', '休闲': 'relax'}
EDGE_STATES = {'edge_left', 'edge_right', 'edge_top', 'edge_bottom'}
EDGE_STATES.add('drag')
EDGE_STATES.add('monarch_wings')
THEME_MODES = {'nail', 'shell', 'soul', 'battle', 'flower', 'explore'}
EDGE_STATES |= {f'process_{mode}' for mode in THEME_MODES}
EDGE_STATES |= {f'process_{mode}_{side}' for mode in THEME_MODES for side in ('left', 'right', 'top', 'bottom')}
EDGE_STATES |= {f'{state}_{side}' for state in STATES.values() for side in ('left', 'right', 'top', 'bottom')}
EDGE_STATES |= {f'process_{mode}' for mode in ('read', 'notes', 'code', 'sketch', 'organize', 'review')}
EDGE_STATES |= {f'feedback_{mode}' for mode in ('look', 'notes', 'bowl', 'sit')}
EDGE_STATES |= {f'feedback_{mode}_{side}' for mode in ('look', 'notes', 'bowl', 'sit') for side in ('left', 'right', 'top', 'bottom')}


class CharacterFile:
    def __init__(self, path=None):
        self.path = path or CHARACTER
        if not self.path.exists():
            if self.path.resolve() == CHARACTER.resolve():
                self.write(json.loads(DEFAULT_CHARACTER.read_text(encoding='utf-8-sig')))
            else:
                self.write(self.default())

    @staticmethod
    def default():
        return {'name': 'MyServant', 'renderer': 'stickman', 'color': '#e7edf3', 'fps': 6, 'states': {}}

    def stamp(self):
        try:
            stat = self.path.stat()
            return stat.st_mtime_ns, stat.st_size
        except OSError:
            return 'missing'

    def read(self):
        raw = json.loads(self.path.read_text(encoding='utf-8-sig'))
        if not isinstance(raw, dict):
            raise ValueError('角色文件必须是 JSON 对象')
        config = self.default()
        config.update(raw)
        name = config['name']
        if not isinstance(name, str) or not name.strip() or len(name.strip()) > 20 or any(ord(x) < 32 for x in name):
            raise ValueError('名称需要 1～20 个字符')
        config['name'] = name.strip()
        if config['renderer'] not in ('stickman', 'images'):
            raise ValueError('renderer 必须为 stickman 或 images')
        if not isinstance(config['color'], str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', config['color']):
            raise ValueError('color 必须为六位十六进制颜色')
        fps = config['fps']
        if isinstance(fps, bool) or not isinstance(fps, (int, float)) or not math.isfinite(fps) or not 1 <= fps <= 20:
            raise ValueError('fps 必须在 1～20 之间')
        timings = config.get('timings', {})
        if not isinstance(timings, dict):
            raise ValueError('timings 必须是动画帧时长对象')
        sequences = config.get('frame_sequences', {})
        if not isinstance(sequences, dict):
            raise ValueError('frame_sequences 必须为动画帧索引对象')
        intervals = config.get('rig_intervals', {})
        if not isinstance(intervals, dict) or any(isinstance(n, bool) or not isinstance(n, (int, float)) or not math.isfinite(n) or not 10 <= n <= 300 for n in intervals.values()):
            raise ValueError('rig_intervals 必须在10～300秒之间')
        rigs = config.get('rigs', {})
        if not isinstance(rigs, dict) or any(not isinstance(key, str) or not isinstance(value, str) or value not in {'idle', 'relax', 'sleep', 'eat', 'work', 'study', 'nail', 'shell', 'soul', 'battle', 'flower', 'explore', 'look', 'notes', 'bowl', 'sit', 'drag', 'read', 'review', 'organize', 'code', 'sketch'} for key, value in rigs.items()):
            raise ValueError('rigs 局部动画配置无效')
        flying = config.get('flying_states', [])
        if not isinstance(flying, list) or any(not isinstance(state, str) for state in flying):
            raise ValueError('flying_states 必须为动画名称列表')
        anchors = config.get('wing_anchors', {})
        if not isinstance(anchors, dict) or any(not isinstance(point, list) or len(point) != 2 or any(isinstance(n, bool) or not isinstance(n, (int, float)) or not math.isfinite(n) or not 0 <= n <= 1 for n in point) for point in anchors.values()):
            raise ValueError('wing_anchors 须为0～1之间的相对位置')
        opacity = config.get('wing_opacity', .72)
        if isinstance(opacity, bool) or not isinstance(opacity, (int, float)) or not math.isfinite(opacity) or not 0 <= opacity <= 1:
            raise ValueError('wing_opacity 须在0～1之间')
        files, total = {}, 0
        counted_paths = set()
        resolved_paths = {}
        base = self.path.parent.resolve()
        allowed_states = set(STATES.values()) | EDGE_STATES
        if config['renderer'] == 'images':
            states = config['states']
            if not isinstance(states, dict) or not states.get('idle'):
                raise ValueError('图片角色需要 idle 图片')
            for state, frames in states.items():
                if state not in allowed_states or not isinstance(frames, list) or not 1 <= len(frames) <= 60:
                    raise ValueError('动画名称或帧列表无效')
                files[state] = []
                for frame in frames:
                    spec = frame if isinstance(frame, dict) else {'image': frame}
                    if not isinstance(spec.get('image'), str):
                        raise ValueError('图片路径必须为文字')
                    rect = spec.get('rect')
                    if rect is not None and (not isinstance(rect, list) or len(rect) != 4 or any(type(n) is not int for n in rect) or not (0 <= rect[0] < rect[2] and 0 <= rect[1] < rect[3])):
                        raise ValueError('图集矩形必须为 [左, 上, 右, 下]')
                    scale = spec.get('scale')
                    if scale is not None and (type(scale) is not int or not 1 <= scale <= 16):
                        raise ValueError('缩小倍数必须为1～16的整数')
                    fit = spec.get('fit')
                    if fit is not None and (not isinstance(fit, list) or len(fit) != 2 or any(type(n) is not int or not 1 <= n <= 200 for n in fit)):
                        raise ValueError('fit 必须是1～200的目标宽高')
                    for key in ('canvas', 'offset'):
                        value = spec.get(key)
                        if value is not None and (not isinstance(value, list) or len(value) != 2 or any(type(n) is not int or not (1 if key == 'canvas' else 0) <= n <= 2048 for n in value)):
                            raise ValueError('canvas/offset 必须是有效的宽高或对齐偏移')
                    if type(spec.get('flip', False)) is not bool:
                        raise ValueError('flip 必须为布尔值')
                    name = spec['image']
                    if name not in resolved_paths:
                        path = (base / name).resolve()
                        if base not in path.parents or path.suffix.lower() not in ('.png', '.gif'):
                            raise ValueError('图片须位于程序目录中，格式为 PNG 或 GIF')
                        if path not in counted_paths:
                            info = path.stat()
                            if not stat_module.S_ISREG(info.st_mode):
                                raise ValueError('图片须位于程序目录中，格式为 PNG 或 GIF')
                            if info.st_size > 4 * 1024 * 1024:
                                raise ValueError('单张图片不能超过 4MB')
                            total += info.st_size
                            counted_paths.add(path)
                        resolved_paths[name] = path
                    path = resolved_paths[name]
                    files[state].append(dict(spec, image=path))
            if total > 32 * 1024 * 1024:
                raise ValueError('图片总大小不能超过 32MB')
            for state, durations in timings.items():
                if state not in states or not isinstance(durations, list) or len(durations) != len(states[state]) or any(isinstance(n, bool) or not isinstance(n, (int, float)) or not math.isfinite(n) or not .08 <= n <= 30 for n in durations):
                    raise ValueError('timings 的帧时长须与图片数量对应，范围为0.08～30秒')
            for state, sequence in sequences.items():
                if state not in states or not isinstance(sequence, list) or len(sequence) != len(states[state]) or any(type(n) is not int or not 0 <= n < len(states[state]) for n in sequence):
                    raise ValueError('frame_sequences 必须使用有效帧索引')
        config['files'] = files
        return config

    def write(self, data):
        temporary = self.path.with_suffix('.tmp')
        with temporary.open('w', encoding='utf-8') as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, self.path)

    def rename(self, name):
        name = name.strip()
        if not name or len(name) > 20 or any(ord(x) < 32 for x in name):
            raise ValueError('名称需要 1～20 个字符')
        self.read()  # Preserve invalid externally edited files.
        raw = json.loads(self.path.read_text(encoding='utf-8-sig'))
        raw['name'] = name
        self.write(raw)
