"""Render the real image renderer without creating desktop windows or saves."""
import sys
from pathlib import Path
from unittest.mock import MagicMock
from collections import OrderedDict
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from character_config import CharacterFile
from character_images import ImageRenderer
from simulation import Simulation

OUT = Path(__file__).resolve().parent/'integrated-review'
OUT.mkdir(exist_ok=True)
renderer = ImageRenderer.__new__(ImageRenderer)
renderer.frames = {}
renderer.config = None
renderer.alpha_window = MagicMock()
renderer.frame_cache = OrderedDict()
renderer.source_cache = OrderedDict()
renderer.motion_cache = OrderedDict()
renderer.select(CharacterFile().read())
config = renderer.config
original = renderer.frames.copy()
font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 12)
sim = Simulation()
all_states = list(original)
for page in range((len(all_states)+11)//12):
    canvases = [Image.new('RGB', (880, 780), '#e1e5e9') for _ in range(4)]
    for j, state in enumerate(all_states[page*12:page*12+12]):
        edge = next((side for side in ('left','right','top','bottom') if state.endswith('_'+side)), None)
        key = 'idle_'+edge if edge else 'idle'
        renderer.frames = {'idle': original[state], key: original[state]}
        renderer.motion_cache.clear()
        # Preserve the actual source sequence while exercising draw and contacts.
        renderer.config = dict(config, timings={key: config['timings'][state]},
                               frame_sequences={key: config['frame_sequences'][state]})
        snapshots = []
        for index, elapsed in enumerate((0., 12.1, 14.1, 16.1)):
            renderer.animation_state = None
            renderer.draw(MagicMock(), sim.data, 0., {}, edge)
            renderer.draw(MagicMock(), sim.data, elapsed, {}, edge)
            surface = renderer.last_surface
            assert surface.mode == 'RGBA'
            bounds = surface.getbbox()
            assert bounds
            if edge:
                contact, expected = {'left':(0,0),'right':(2,220),'top':(1,0),'bottom':(3,240)}[edge]
                assert bounds[contact] == expected, (state,bounds)
            x, y = j%4*220, j//4*260
            canvases[index].paste(surface, (x,y+20), surface)
            draw = ImageDraw.Draw(canvases[index])
            draw.text((x+5,y+3), state, fill='#243144',font=font)
            if edge == 'left': draw.line((x,y+20,x,y+259),fill='#b0805a',width=1)
            if edge == 'right': draw.line((x+219,y+20,x+219,y+259),fill='#b0805a',width=1)
            if edge == 'top': draw.line((x,y+20,x+219,y+20),fill='#b0805a',width=1)
            if edge == 'bottom': draw.line((x,y+259,x+219,y+259),fill='#b0805a',width=1)
    canvases[0].save(OUT/f'page-{page+1}.png')
    canvases[0].save(OUT/f'page-{page+1}.gif', save_all=True, append_images=canvases[1:],
                     duration=[12000,2000,2000,8000], loop=0, disposal=2)
print(f'Validated {len(original)} states, real renderer and all screen contacts; previews: {OUT}')

motion_frames = []
for tick in range(32):
    sheet = Image.new('RGB', (660, 260), '#e1e5e9')
    for column, state in enumerate(('idle', 'process_shell', 'drag')):
        renderer.frames = {'idle': original[state]}
        renderer.config = dict(config, timings={'idle': [30., 2., 2., 8.]},
                               frame_sequences={'idle': [0, 1, 2, 3]})
        renderer.motion_cache.clear()
        renderer.animation_state = 'idle'
        renderer.animation_started = 0.
        renderer.draw(MagicMock(), sim.data, tick/4, {})
        surface = renderer.last_surface
        sheet.paste(surface, (column*220,20), surface)
        ImageDraw.Draw(sheet).text((column*220+8,3), state, fill='#243144',font=font)
    motion_frames.append(sheet)
motion_frames[0].save(OUT/'scale-and-micro.gif', save_all=True, append_images=motion_frames[1:],
                      duration=250, loop=0, disposal=2)
