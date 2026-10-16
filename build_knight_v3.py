"""Build the approved action sheets into registered, quiet runtime frames.

Artwork extraction is performed by imagegen. This script only indexes, crops,
registers and scales its transparent output; original concept boards are kept.
"""
import json
import shutil
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / 'assets/hollow_knight/animation-v3'
ROWS = ('idle', 'relax', 'sleep', 'eat', 'nail', 'shell', 'soul', 'battle', 'flower', 'explore')
SIDES = ('left', 'right', 'top', 'bottom')


def bands(values, minimum, gap=2):
    result, start, last = [], None, 0
    for i, value in enumerate(values):
        if value >= minimum:
            if start is None:
                start = i
            last = i
        elif start is not None and i-last > gap:
            result.append((start, last+1))
            start = None
    if start is not None:
        result.append((start, last+1))
    return result


def index_sheet(path, row_count):
    with Image.open(path) as source:
        image = source.convert('RGBA')
    alpha = image.getchannel('A')
    assert alpha.getextrema()[0] == 0, f'{path}: missing transparency'
    mask = alpha.point(lambda a: 255 if a > 128 else 0)
    w, h = image.size
    rows = bands([sum(mask.crop((0, y, w, y+1)).getdata())/255 for y in range(h)], 12)
    rows = [r for r in rows if r[1]-r[0] >= 35]
    if path.stem == 'top' and len(rows) == 9:
        # Hammock ropes start immediately below the preceding seated pose.
        rows[1:2] = [(rows[1][0], 293), (294, rows[1][1])]
    if len(rows) != row_count:
        raise ValueError(f'{path.name}: expected {row_count} rows, got {rows}')
    indexed = []
    columns = {
        'ground': (0, 345, 560, 790, 1024),
        'sides': (0, 310, 535, 775, 1024),
        'top': (0, 333, 558, 790, 1024),
        'bottom': (0, 312, 550, 790, 1024),
        'interaction': (0, 300, 550, 790, 1024),
    }[path.stem]
    for top, bottom in rows:
        # The sheets retain four source columns; gaps in wings/props may split
        # components, so assign by cell rather than counting components.
        row = []
        for left, right in zip(columns, columns[1:]):
            cell = image.crop((left, top, right, bottom))
            bbox = cell.getchannel('A').point(lambda a: 255 if a > 40 else 0).getbbox()
            if not bbox:
                raise ValueError(f'{path.name}: empty frame in row {len(indexed)}')
            row.append(cell.crop(bbox))
        indexed.append(row)
    return indexed


def register(frames, edge=None, head_width=None):
    # Shared scale and canvas for each row prevent size pumping. Contact remains
    # fixed at the screen border, never at a drawn platform or transparent pad.
    if head_width is not None:
        normalized = []
        for frame in frames:
            ratio = head_width/head_geometry(frame)[1]
            normalized.append(frame.resize((max(1, round(frame.width*ratio)),
                                            max(1, round(frame.height*ratio))), Image.Resampling.LANCZOS))
        frames = normalized
    anchors = [head_anchor(frame) for frame in frames]
    left_room = max(anchors)
    right_room = max(frame.width-anchor for frame, anchor in zip(frames, anchors))
    width = max(frame.width for frame in frames) if edge in ('left', 'right') else left_room+right_room
    height = max(frame.height for frame in frames)
    scale = min(196/width, 150/height)
    if head_width is not None:
        # Activity silhouettes vary in height; normalize the mask first. Only
        # reduce further if wings or a prop genuinely exceed the window.
        scale = min(1., 196/width, 200/height)
    size = (max(1, round(width*scale)), max(1, round(height*scale)))
    result = []
    for frame, anchor in zip(frames, anchors):
        target = frame.resize((max(1, round(frame.width*scale)), max(1, round(frame.height*scale))), Image.Resampling.LANCZOS)
        x = 0 if edge == 'left' else size[0]-target.width if edge == 'right' else round((left_room-anchor)*scale)
        x = max(0, min(size[0]-target.width, x))
        y = 0 if edge == 'top' else size[1]-target.height
        canvas = Image.new('RGBA', size)
        canvas.alpha_composite(target, (x, y))
        result.append(canvas)
    return result


def head_anchor(frame):
    return head_geometry(frame)[0]


def head_geometry(frame):
    # Largest pale component is the mask, separate from wings, blade and props.
    pixels = frame.load()
    points = {(x, y) for y in range(frame.height) for x in range(frame.width)
              if pixels[x, y][3] > 128 and min(pixels[x, y][:3]) > 175}
    largest = []
    while points:
        seed = points.pop()
        component, pending = [], [seed]
        while pending:
            x, y = pending.pop()
            component.append((x, y))
            for neighbor in ((x-1,y), (x+1,y), (x,y-1), (x,y+1)):
                if neighbor in points:
                    points.remove(neighbor)
                    pending.append(neighbor)
        if len(component) > len(largest):
            largest = component
    if not largest:
        return frame.width//2, frame.width
    xs = [x for x, _ in largest]
    return round(sum(xs)/len(xs)), max(xs)-min(xs)+1


def build():
    manifest = json.loads((ROOT/'Saved/knight-action-redesign-20261016/review/manifest.json').read_text(encoding='utf-8'))
    sheets = {name: index_sheet(ASSETS/f'{name}.png', 5 if name == 'interaction' else 10)
              for name in ('ground', 'sides', 'top', 'bottom', 'interaction')}
    states, timings, sequences = {}, {}, {}
    standing_head_width = head_geometry(register(sheets['ground'][0])[0])[1]
    for group in ('ground', 'left', 'right', 'top', 'bottom', 'interaction'):
        rows = sheets['sides' if group in ('left', 'right') else group]
        for i, frames in enumerate(rows):
            if group == 'interaction' and i == 4:
                continue  # Wings already belong to each complete flying pose.
            name = ('drag', 'feedback_look', 'feedback_notes', 'feedback_bowl', 'feedback_sit')[i] if group == 'interaction' else ROWS[i]
            if name in ROWS[4:]:
                name = 'process_'+name
            if group in SIDES:
                name += '_'+group
            selected = [n-1 for n in manifest['groups'][group][i]['quiet_sequence']]
            if group in ('left', 'right'):
                selected = [0, 1, 0, 0] if group == 'left' else [2, 3, 2, 2]
            elif ((group == 'ground' and i in (4, 7)) or
                  (group == 'top' and i == 4) or (group == 'bottom' and i == 6)):
                selected = [0, 1, 3, 0]
            entries = []
            # Unused broad action poses must not shrink the quiet body's scale.
            registered = register([frames[n] for n in selected], group,
                                  standing_head_width)
            for n, frame in enumerate(registered):
                relative = f'assets/hollow_knight/animation-v3/frames/{name}-{n}.png'
                target = ROOT/relative
                target.parent.mkdir(exist_ok=True)
                frame.save(target)
                entries.append(relative)
            states[name] = entries
            timings[name] = [12., 2., 2., 8.] if name != 'drag' else [2., 1., 1., 2.]
            sequences[name] = [0, 1, 2, 3]
    states['feedback_sit'] = states['relax']
    timings['feedback_sit'] = timings['relax']
    sequences['feedback_sit'] = sequences['relax']
    for suffix in ('', '_left', '_right', '_top', '_bottom'):
        for alias, source in (('work', 'process_battle'), ('study', 'process_nail')):
            states[alias+suffix] = states[source+suffix]
            timings[alias+suffix] = timings[source+suffix]
            sequences[alias+suffix] = sequences[source+suffix]
        if suffix:
            for reaction, source in (('look', 'idle'), ('notes', 'process_explore'), ('bowl', 'eat'), ('sit', 'relax')):
                key = 'feedback_'+reaction+suffix
                states[key], timings[key], sequences[key] = states[source+suffix], timings[source+suffix], sequences[source+suffix]
    old = json.loads((ROOT/'character.json').read_text(encoding='utf-8-sig'))
    config = dict(name=old['name'], renderer='images', color=old.get('color', '#e7edf3'), fps=6,
                  motion=False, micro_motion=True, animation_style='knight-frames-v3', screen_contacts=True,
                  states=states, timings=timings, frame_sequences=sequences)
    backup = ROOT/'Saved/knight-action-redesign-20261016/character-before-v3.json'
    if not backup.exists():
        shutil.copy2(ROOT/'character.json', backup)
    for name in ('character.json', 'character-hollow-knight.json', 'character-hollow-knight-v3.json'):
        (ROOT/name).write_text(json.dumps(config, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(f'Built {len(states)} states; no rigs, independent wing layer or scenery')


if __name__ == '__main__':
    build()
