"""Review player for the supplied action boards; no game files are written.

The source artwork is sampled as-is, including its paper background. This is
keyframe playback, not background removal, repainting or a game asset build.
"""
import hashlib
import json
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
OUT = HERE / 'review'
ROOT = HERE.parents[1]
ACTIVITIES = ['待机', '放松', '睡眠', '进食', '骨钉', '外壳', '灵魂', '战斗', '娇嫩花', '探索']
FONT = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 15)
SMALL = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 12)
BOARDS = {
    'ground': ('01-ground.png', [121, 342, 563, 784, 1007], [73, 222, 367, 504, 656, 811, 955, 1105, 1257, 1394, 1534]),
    'sides': ('02-side-edges.png', [92, 310, 535, 775, 1007], [100, 236, 374, 507, 649, 787, 924, 1068, 1212, 1354, 1505]),
    'top': ('03-top.png', [114, 337, 560, 783, 1007], [60, 199, 340, 482, 617, 770, 918, 1078, 1229, 1375, 1534]),
    'bottom': ('04-bottom.png', [114, 337, 560, 783, 1007], [65, 216, 358, 499, 650, 800, 943, 1093, 1249, 1380, 1534]),
    'interaction': ('05-interaction.png', [140, 355, 570, 785, 1007], [82, 342, 579, 808, 1051, 1295, 1534]),
}
LABELS = {'ground': '普通位置', 'left': '左侧贴边', 'right': '右侧贴边',
          'top': '顶部', 'bottom': '底部', 'interaction': '拖拽与互动'}
PREFIX = {'ground': 'G', 'left': 'L', 'right': 'R', 'top': 'T', 'bottom': 'B', 'interaction': 'I'}
# Only the supplied keys are selected. No synthesized motion or modified anatomy.
QUIET = {
    'ground': [[0,1,3,0], [0,1,3,0], [1,3,1,3], [0,1,3,0], [0,3,0,3],
               [0,2,3,0], [0,1,3,0], [0,3,0,3], [0,1,3,0], [0,1,3,0]],
    'top': [[0,1,3,0], [0,1,3,0], [1,3,1,3], [0,1,3,0], [0,3,0,3],
            [0,3,0,3], [0,1,0,1], [0,3,0,3], [0,3,0,3], [0,1,3,0]],
    'bottom': [[0,1,3,0], [0,1,3,0], [0,1,3,0], [0,1,3,0], [0,1,0,1],
               [0,1,3,0], [0,0,0,0], [0,3,0,3], [0,1,3,0], [0,1,3,0]],
    'interaction': [[0,1,3,0], [0,1,3,0], [0,1,3,0], [0,1,3,0], [0,1,3,0], [0,3,0,3]],
}
TILE = (220, 226)
BG = '#eeece7'
TIMES = {'quiet': [2000, 1500, 1500, 3000], 'cadence': [12000, 2000, 2000, 8000],
         'raw': [2000, 1500, 1500, 3000]}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inspect_grid():
    for filename, _, _ in BOARDS.values():
        image = Image.open(HERE/filename)
        pixels = image.load()
        lines = []
        for y in range(50, image.height):
            count = sum(1 for x in range(20, 1005)
                        if max(pixels[x,y])-min(pixels[x,y]) < 35 and sum(pixels[x,y]) < 580)
            if count > 810:
                lines.append(y)
        print(filename, lines)


def tiles(image, columns, rows, row, title, special=None):
    frames, rects = [], []
    for column in range(4):
        rect = [columns[column]+3, rows[row]+2, columns[column+1]-3, rows[row+1]-1]
        if special:
            rect[0], rect[2] = special[column]
        panel = image.crop(rect)
        panel.thumbnail((210, 192), Image.Resampling.LANCZOS)
        tile = Image.new('RGB', TILE, BG)
        tile.paste(panel, ((TILE[0]-panel.width)//2, 30+(192-panel.height)//2))
        draw = ImageDraw.Draw(tile)
        draw.text((10, 7), title, fill='#25313f', font=FONT)
        frames.append(tile)
        rects.append(rect)
    return frames, rects


def save_gif(path, frames, durations):
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=durations,
                   loop=0, disposal=2, optimize=False)


def build():
    OUT.mkdir(exist_ok=True)
    (OUT/'actions').mkdir(exist_ok=True)
    source_hashes = {name: digest(HERE/name) for name, _, _ in BOARDS.values()}
    game_files = ('main.py', 'character.json', 'character-hollow-knight.json', 'character_images.py', 'knight_animation.py')
    game_hashes = {name: digest(ROOT/name) for name in game_files}
    groups, manifest = {}, {'review_only': True, 'source_hashes': source_hashes, 'groups': {}}
    names = ACTIVITIES
    for board, (filename, columns, rows) in BOARDS.items():
        image = Image.open(HERE/filename).convert('RGB')
        if board == 'interaction':
            names = ['拖拽', '转头观察', '记录笔记', '进食回应', '安静陪伴', '帝王之翼']
        else:
            names = ACTIVITIES
        target_groups = ('left', 'right') if board == 'sides' else (board,)
        for group in target_groups:
            groups[group] = []
            manifest['groups'][group] = []
            for row, name in enumerate(names):
                code = PREFIX[group]+str(row+1).zfill(2)
                special = [(104,354), (350,575), (548,806), (770,1014)] if board == 'interaction' and row == 5 else None
                frames, rects = tiles(image, columns, rows, row, code+' · '+name, special)
                if board == 'sides':
                    base = 0 if group == 'left' else 2
                    raw = [base, base+1, base, base]
                    # Keep concentration, guard and flower-holding steady where
                    # the alternate key contains a flash or larger motion.
                    quiet = [base]*4 if row in (6,7,8) else raw
                else:
                    raw = [0,1,2,3]
                    quiet = QUIET[group][row]
                groups[group].append((frames, quiet, raw))
                manifest['groups'][group].append(dict(code=code, name=name, source=filename,
                    rects=rects, quiet_sequence=[i+1 for i in quiet], raw_sequence=[i+1 for i in raw],
                    steady_pose=len(set(quiet)) == 1,
                    excluded_frames=[i+1 for i in range(4) if i not in quiet]))
                save_gif(OUT/'actions'/(code+'.gif'), [frames[i] for i in quiet], TIMES['quiet'])
                # Preserve all original keys for review of proposed exclusions.
                save_gif(OUT/'actions'/(code+'-raw.gif'), [frames[i] for i in raw], TIMES['raw'])
            width = 5*TILE[0]
            height = ((len(names)+4)//5)*TILE[1]
            for mode in ('quiet', 'cadence', 'raw'):
                sheets = []
                for step in range(4):
                    sheet = Image.new('RGB', (width,height), BG)
                    for row, (frames, quiet, raw) in enumerate(groups[group]):
                        sequence = raw if mode == 'raw' else quiet
                        sheet.paste(frames[sequence[step]], ((row%5)*TILE[0], (row//5)*TILE[1]))
                    sheets.append(sheet)
                save_gif(OUT/(group+'-'+mode+'.gif'), sheets, TIMES[mode])
                if mode == 'quiet':
                    sheets[0].save(OUT/(group+'-poster.png'))
            print(group, len(names), 'actions')
    (OUT/'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    write_page(manifest)
    (OUT/'README.md').write_text('''# 动作板审阅版

直接使用上一级文件夹的五张动作板，原图未修改，也未接入游戏。

- 打开 index.html 切换六组动作。也可以直接查看各组 GIF。
- 默认是「轻缓选帧·动作片段」，省略长时间的静置，便于审阅。
- 「24秒节奏」使用相同选帧，展示低密度的实际节奏建议。
- 「原始全部关键帧」保留素材的动作，供比较哪些帧需要保留或舍弃。
- 左右贴边分别只有两帧，按左右两套播放，没有把四列串成一个动作。
- 部分灵魂、战斗、护花状态建议先保持固定姿态，避免原图里的闪光或大动作。

这是动作板关键帧预览，保留了纸色、线条和原有标记，尚未制作透明游戏精灵，也未补绘中间帧。
审阅可以直接报编号，例如 T01、G05、I06。manifest.json 记录了每个动作的来源及选帧。
''', encoding='utf-8')
    assert source_hashes == {name: digest(HERE/name) for name in source_hashes}, 'Source artwork changed'
    assert game_hashes == {name: digest(ROOT/name) for name in game_hashes}, 'Game files changed'
    print('Verified: supplied images and active game files unchanged; 56 action previews')


def write_page(manifest):
    data = json.dumps(manifest['groups'], ensure_ascii=False)
    page = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>小骑士动作 · 审阅</title>
<style>body{font:16px 'Microsoft YaHei UI',sans-serif;color:#293340;background:#f6f5f2;max-width:1140px;margin:28px auto;padding:0 20px}h1{font-size:26px;margin:0 0 12px}p{line-height:1.8;color:#64707c}.controls{display:flex;gap:9px;flex-wrap:wrap;margin:20px 0}button,select{font:inherit;padding:9px 13px;border:1px solid #c4cbd0;border-radius:7px;background:#fff;cursor:pointer}button.on{background:#35485a;color:#fff}#preview{display:block;width:100%;max-width:1100px;border-radius:8px}small{color:#74808b}table{width:100%;border-collapse:collapse;font-size:14px}td,th{border-bottom:1px solid #dce0e2;text-align:left;padding:10px}a{color:#345b7d}</style>
<h1>小骑士动作审阅</h1><p>使用你提供的五张动作板，原图和游戏均未改动。先看造型、动作幅度与节奏。</p>
<div class="controls" id="tabs"></div><div class="controls"><select id="mode"><option value="quiet">轻缓选帧 · 动作片段</option><option value="cadence">轻缓选帧 · 24秒节奏</option><option value="raw">原始全部关键帧</option></select><button id="restart">重新播放</button><button id="pause">暂停</button></div>
<p id="note"></p><img id="preview" alt="动作关键帧动图"><p><small>预览保留动作板纸色和标记；不是透明精灵成品。默认片段省略静置间隔，实际节奏建议在「24秒节奏」中查看。</small></p>
<details><summary>动作编号、选帧和原图对照</summary><table><thead><tr><th>编号</th><th>动作</th><th>轻缓选帧（列号）</th><th>查看</th></tr></thead><tbody id="rows"></tbody></table></details>
<script>const groups=GROUPS,labels={ground:'普通位置',left:'左侧贴边',right:'右侧贴边',top:'顶部',bottom:'底部',interaction:'拖拽与互动'};let current='ground',paused=false;const tabs=document.getElementById('tabs'),preview=document.getElementById('preview'),mode=document.getElementById('mode');
Object.keys(labels).forEach(key=>{const b=document.createElement('button');b.textContent=labels[key];b.dataset.key=key;b.onclick=()=>{current=key;show()};tabs.append(b)});
function show(){paused=false;document.getElementById('pause').textContent='暂停';tabs.querySelectorAll('button').forEach(b=>b.classList.toggle('on',b.dataset.key===current));preview.src=current+'-'+mode.value+'.gif';document.getElementById('note').textContent=labels[current]+' · '+(current==='left'||current==='right'?'两帧独立播放':'四个关键帧')+'。可按编号反馈。';const rows=document.getElementById('rows');rows.textContent='';groups[current].forEach(a=>{const tr=document.createElement('tr');[a.code,a.name,a.quiet_sequence.join(' → ')+(a.steady_pose?'（固定姿态）':'')].forEach(s=>{const td=document.createElement('td');td.textContent=s;tr.append(td)});const td=document.createElement('td');const l=document.createElement('a');l.href='actions/'+a.code+'.gif';l.textContent='轻缓';td.append(l,' / ');const r=document.createElement('a');r.href='actions/'+a.code+'-raw.gif';r.textContent='原始';td.append(r);tr.append(td);rows.append(tr)})}
mode.onchange=show;document.getElementById('restart').onclick=()=>{show()};document.getElementById('pause').onclick=()=>{paused=!paused;preview.src=paused?current+'-poster.png':current+'-'+mode.value+'.gif';document.getElementById('pause').textContent=paused?'继续':'暂停'};show();</script></html>'''
    (OUT/'index.html').write_text(page.replace('GROUPS',data), encoding='utf-8')


if __name__ == '__main__':
    inspect_grid() if '--inspect-grid' in sys.argv else build()
