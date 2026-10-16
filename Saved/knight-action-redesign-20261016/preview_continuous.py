"""Real renderer previews of continuous held poses, including every activity."""
import sys
from pathlib import Path
from collections import OrderedDict
from unittest.mock import MagicMock, patch
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from character_images import ImageRenderer
from character_config import CharacterFile
from simulation import Simulation

out = Path(__file__).resolve().parent/'continuous-review'
out.mkdir(exist_ok=True)
r = ImageRenderer.__new__(ImageRenderer)
r.frames, r.config = {}, None
r.frame_cache, r.source_cache, r.motion_cache = OrderedDict(), OrderedDict(), OrderedDict()
r.alpha_window = MagicMock()
r.select(CharacterFile().read())
sim = Simulation()
font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 14)
names = [('idle','待机'),('relax','放松'),('sleep','睡眠'),('eat','进食'),
         ('process_nail','骨钉修炼'),('process_shell','外壳修炼'),('process_soul','灵魂修炼'),
         ('process_battle','战斗'),('process_flower','送花'),('process_explore','探索')]
groups = [(side, names) for side in ('ground','left','right','top','bottom')]
groups.append(('interaction', [('drag','拖拽'),('feedback_look','观察'),('feedback_notes','笔记'),
                               ('feedback_bowl','进食回应'),('feedback_sit','陪伴')]))
for group, entries in groups:
    frames = []
    edge = group if group in ('left','right','top','bottom') else None
    for tick in range(32):
        sheet = Image.new('RGB',(1100,520),'#e1e5e9')
        for n, (base,label) in enumerate(entries):
            state = base+('_'+edge if edge else '')
            r.animation_state, r.animation_started = state, 0.
            with patch.dict('character_images.STATES', {'自由活动':base}):
                r.draw(MagicMock(), sim.data, tick/4, {}, edge)
            x, y = n%5*220, n//5*260
            sheet.paste(r.last_surface,(x,y+20),r.last_surface)
            ImageDraw.Draw(sheet).text((x+8,y+2),label,fill='#243144',font=font)
        frames.append(sheet)
    frames[0].save(out/f'{group}.png')
    frames[0].save(out/f'{group}.gif',save_all=True,append_images=frames[1:],duration=250,loop=0,disposal=2)
    print(group, 'complete', flush=True)
links = ''.join(f'<h2>{group}</h2><img src="{group}.gif">' for group,_ in groups)
(out/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>持续动作预览</title>'
    '<style>body{background:#e1e5e9;font:16px sans-serif;max-width:1100px;margin:30px auto}img{width:100%}</style>'
    '<h1>全活动持续动作 · 实际尺寸</h1><p>每组8秒循环，展示保持同一关键姿态时的微动。</p>'+links,encoding='utf-8')
