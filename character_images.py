import math
from collections import OrderedDict
import tkinter as tk
from PIL import Image
RESAMPLE = getattr(Image, "Resampling", Image)
TRANSPOSE = getattr(Image, "Transpose", Image)
from alpha_window import AlphaWindow
from character_config import STATES
from knight_animation import frame_index, static_offset, rig_phase, motion_kind
from knight_rig import deform
from activity_content import process
from activity_state import effective_activity


class ImageRenderer:
    def __init__(self, master):
        self.master = master
        self.config = None
        self.frames = {}
        self.frame_cache = OrderedDict()
        self.source_cache = OrderedDict()
        self.motion_cache = OrderedDict()
        self.alpha_window = AlphaWindow(master)

    def unload(self):
        self.config = None
        self.frames.clear()
        self.frame_cache.clear()
        self.source_cache.clear()
        self.motion_cache.clear()
        self.last_surface = None
        self.alpha_window.reset()

    def select(self, config):
        # Register specs without opening every animation PNG before first paint.
        # Headers/rectangles are checked when their image is first used.
        frames = {}
        for state, specs in config['files'].items():
            frames[state] = []
            for spec in specs:
                path = spec['image']
                rect = tuple(spec['rect']) if 'rect' in spec else None
                factor = spec.get('scale', 1)
                frame_canvas = tuple(spec['canvas']) if 'canvas' in spec else None
                offset = tuple(spec.get('offset', [0, 0]))
                if frame_canvas and rect and (offset[0] + rect[2]-rect[0] > frame_canvas[0] or offset[1] + rect[3]-rect[1] > frame_canvas[1]):
                    raise ValueError('对齐后的动画帧超出画布')
                frames[state].append((path, rect, factor, spec.get('flip', False), tuple(spec['fit']) if 'fit' in spec else None, frame_canvas, offset))
        previous = (self.frames, self.config, self.frame_cache, self.source_cache, self.motion_cache)
        self.frames, self.config = frames, config
        self.frame_cache, self.source_cache, self.motion_cache = OrderedDict(), OrderedDict(), OrderedDict()
        try:
            self.get_frame('idle', 0)
        except (OSError, ValueError):
            self.frames, self.config, self.frame_cache, self.source_cache, self.motion_cache = previous
            raise
        self.last_canvas_frame = None
        self.animation_state = None
        self.animation_started = 0.

    def get_frame(self, state, index=0):
        key = self.frames[state][index]
        if key in self.frame_cache:
            self.frame_cache.move_to_end(key)
            return self.frame_cache[key]
        path, rect, factor, flip, fit, frame_canvas, offset = key
        if path not in self.source_cache:
            with Image.open(path) as source:
                width, height = source.size
                if width > 4096 or height > 4096 or width*height > 2048*2048:
                    raise ValueError('图片边长不能超过4096，总像素不能超过2048×2048')
                self.source_cache[path] = source.convert('RGBA')
            # Only one full-resolution atlas is retained.
            while len(self.source_cache) > 1:
                self.source_cache.popitem(last=False)
        source = self.source_cache[path]
        rect = rect or (0, 0, source.width, source.height)
        if rect[2] > source.width or rect[3] > source.height:
            raise ValueError('图集矩形超出图片范围')
        if frame_canvas and (offset[0] + rect[2]-rect[0] > frame_canvas[0] or offset[1] + rect[3]-rect[1] > frame_canvas[1]):
            raise ValueError('对齐后的动画帧超出画布')
        factor = max(factor, math.ceil((rect[2]-rect[0])/200), math.ceil((rect[3]-rect[1])/200))
        image = source.crop(rect)
        if frame_canvas:
            registered = Image.new('RGBA', frame_canvas)
            registered.alpha_composite(image, offset)
            image = registered
        ratio = min(fit[0] / image.width, fit[1] / image.height) if fit else 1 / factor
        image = image.resize((max(1, round(image.width*ratio)), max(1, round(image.height*ratio))), RESAMPLE.LANCZOS)
        if flip:
            image = image.transpose(TRANSPOSE.FLIP_LEFT_RIGHT)
        if state == 'monarch_wings':
            opacity = self.config.get('wing_opacity', .72)
            image.putalpha(image.getchannel('A').point(lambda n: round(n*opacity)))
        self.frame_cache[key] = image
        while len(self.frame_cache) > 24:
            self.frame_cache.popitem(last=False)
        return image

    def draw(self, canvas, data, now, names, edge=None, reaction=None, dragging=False):
        if self.config is None:
            self.alpha_window.reset()
            return False
        actual = data['activity']
        activity = effective_activity(data)
        if activity != actual:
            reaction = None
        state = STATES[activity]
        if edge:
            if f'{state}_{edge}' in self.frames:
                state = f'{state}_{edge}'
            elif f'edge_{edge}' in self.frames:
                state = f'edge_{edge}'
            mode = process(data, now)
            if f'process_{mode}_{edge}' in self.frames:
                state = f'process_{mode}_{edge}'
        else:
            mode = process(data, now)
            mode = {'draw': 'sketch', 'type': 'code'}.get(mode, mode)
            if f'process_{mode}' in self.frames:
                state = f'process_{mode}'
        # Never substitute an upright pose for a hanging or wall pose.
        reaction_state = f'feedback_{reaction}_{edge}' if edge else f'feedback_{reaction}'
        if reaction and reaction_state in self.frames:
            state = reaction_state
        if dragging:
            edge, reaction = None, None
            state = 'drag' if 'drag' in self.frames else 'idle'
        frames = self.frames.get(state, self.frames['idle'])
        self.current_state = state
        if getattr(self, 'animation_state', None) != state:
            self.animation_state, self.animation_started = state, now
        elapsed = max(0., now - self.animation_started)
        index = frame_index(state, elapsed, len(frames), self.config)
        actual_state = state if state in self.frames else 'idle'
        image = self.get_frame(actual_state, index)
        x, y = 110, 209
        if edge == 'left':
            x = image.width / 2 + 2
        elif edge == 'right':
            x = 218 - image.width / 2
        elif edge == 'top':
            y = image.height + 3
        elif edge == 'bottom':
            y = 237
        if edge and self.config.get('screen_contacts'):
            bounds = image.getchannel('A').getbbox()
            if bounds:
                left, top, right, bottom = bounds
                if edge == 'left':
                    x = image.width / 2 - left
                elif edge == 'right':
                    x = 220 + image.width / 2 - right
                elif edge == 'top':
                    y = image.height - top
                elif edge == 'bottom':
                    y = 240 + image.height - bottom
        if self.config.get('motion') and len(frames) == 1 and not edge and not dragging:
            dx, dy = static_offset(state, elapsed)
            x, y = x + dx, y + dy
        marker = (actual_state, index, x, y, image.width, image.height)
        if marker != self.last_canvas_frame:
            canvas.delete('all')
            canvas.create_rectangle(x-image.width/2, y-image.height, x+image.width/2, y, outline='', tags='custom_character')
            self.last_canvas_frame = marker
        rgba = image
        rig = self.config.get('rigs', {}).get(actual_state)
        if not rig and self.config.get('micro_motion'):
            rig = 'micro'
        if rig:
            # Finite phase cache: no per-tick image rotation or repeated decoding.
            local_phase = (elapsed % 8.)/8. if rig == 'micro' else rig_phase(rig, elapsed, self.config)
            steps = 32 if rig == 'micro' else 16
            phase = int(local_phase * steps) % steps
            key = (actual_state, index, phase)
            if key not in self.motion_cache:
                self.motion_cache[key] = deform(image, rig, phase/steps, edge, motion_kind(actual_state))
                while len(self.motion_cache) > 32:
                    self.motion_cache.popitem(last=False)
            self.motion_cache.move_to_end(key)
            rgba = self.motion_cache[key]
        surface = Image.new('RGBA', (220, 240))
        if actual_state in self.config.get('flying_states', ()) and 'monarch_wings' in self.frames:
            wing_index = frame_index('monarch_wings', elapsed, len(self.frames['monarch_wings']), self.config)
            wing = self.get_frame('monarch_wings', wing_index)
            anchor = self.config.get('wing_anchors', {}).get(actual_state, [.5, .6])
            body_left, body_top = x-rgba.width/2, y-rgba.height
            wx = body_left+rgba.width*anchor[0]-wing.width/2
            wy = body_top+rgba.height*anchor[1]-wing.height*.68
            surface.alpha_composite(wing, (int(max(2, min(218-wing.width, wx))), int(max(3, wy))))
        surface.alpha_composite(rgba, (int(x - rgba.width/2), int(y - rgba.height)))
        self.last_surface = surface
        self.alpha_window.show(surface)
        return True
