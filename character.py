"""Code-drawn stick figure, props and activity animations."""
import math
from edge_character import draw_edge
from ambient_motion import gesture
from activity_content import process
from activity_state import effective_activity

PALETTES = {None: '#e7edf3', 'graphite': '#45566a', 'mint': '#70c6b2'}


def draw_character(canvas, data, now, names, base_color='#e7edf3', edge_pose=None, dragging=False):
    c = canvas
    c.delete('all')
    ink = PALETTES[data['appearance']['palette']] if data['appearance']['palette'] else base_color
    edge = '#253346'
    accent = '#70bba9'
    actual = data['activity']
    activity = effective_activity(data)
    breath = math.sin(now * 1.8) * 1.3
    kind, amount = gesture(now, data)
    beat = math.sin(now * 3)
    mode = process(data, now)
    c.create_oval(38, 199, 185, 209, fill='#84909f', outline='', tags='shadow')

    def line(points, color=ink, width=4, tag='body'):
        c.create_line(*points, fill=edge, width=width + 2, capstyle='round', joinstyle='round', tags=tag)
        c.create_line(*points, fill=color, width=width, capstyle='round', joinstyle='round', tags=tag)

    def head(x, y, profile=False):
        if edge_pose and kind == 'drowsy':
            y += 4 * amount
        # A right-facing profile matches the laptop's side view.
        left, right = (x - 13, x + 12) if profile else (x - 17, x + 17)
        c.create_oval(left, y - 17, right, y + 17, fill='#ff00ff', outline=edge, width=6, tags='head')
        c.create_oval(left, y - 17, right, y + 17, outline=ink, width=3, tags='head')
        if profile:
            c.create_oval(x + 4, y - 6, x + 7, y - 3, fill=edge, outline='', tags='profile')
        accessory = data['appearance']['accessory']
        if accessory == 'cap':
            c.create_arc(x - 21, y - 24, x + 21, y + 6, start=0, extent=180, fill=accent, outline=edge, width=2, tags='accessory')
            c.create_line(x - 21, y - 9, x + 29, y - 9, fill=edge, width=3, tags='accessory')
        elif accessory == 'glasses':
            for left in ((x + 2,) if profile else (x - 14, x + 3)):
                c.create_rectangle(left, y - 3, left + 11, y + 5, outline='#7598b5', width=2, tags='accessory')
            c.create_line(x - 10 if profile else x - 3, y, x + 3, y, fill='#7598b5', width=2, tags='accessory')

    if dragging:
        c.delete('shadow')
        sway = math.sin(now * 3) * 5
        head(110, 61)
        line((110, 81, 110+sway*.6, 139), tag='drag')
        line((110, 101, 87+sway, 122, 83+sway, 142), tag='drag')
        line((110, 101, 136+sway, 116, 146+sway, 134), tag='drag')
        line((110+sway*.6, 139, 91+sway, 168, 98+sway, 185), tag='drag')
        line((110+sway*.6, 139, 133+sway, 159, 136+sway, 178), tag='drag')
    elif edge_pose in ('left', 'right', 'top', 'bottom'):
        c.delete('shadow')
        draw_edge(c, activity, edge_pose, now, head, line, ink, edge, data['owned'], data)
    elif activity == '睡眠':
        c.create_rectangle(39, 179, 185, 195, fill='#d1dae2', outline=edge, width=2, tags='bed')
        c.create_rectangle(40, 170, 78, 182, fill='#f0f3f6', outline=edge, tags='bed')
        if 'bed' in data['owned']:
            c.create_rectangle(79, 162, 183, 181, fill='#77b7ac', outline=edge, tags='equipment')
        head(59, 153 + breath)
        line((77, 161, 125, 163, 153, 174, 177, 174))
        line((100, 162, 115, 176))
        c.create_text(146, 128 + breath * 3, text='z  z', fill='#65768a', font=('Segoe UI', -20), tags='sleep')
    elif activity in ('工作', '学习'):
        # Seated pose, with independent typing / page motion.
        c.create_line(74, 126, 74, 175, 110, 175, fill='#728296', width=4, tags='chair')
        fatigue = max(0, 35-data['energy']) / 35 * 5
        head(100 if activity == '工作' else 94, 78 + breath + fatigue, profile=activity == '工作')
        line((98 if activity == '工作' else 94, 97 + breath, 94, 145, 121, 148, 124, 193))
        line((94, 145, 116, 153, 117, 193))
        if activity == '工作':
            # Keyboard extends toward the figure; screen faces left toward him.
            c.create_polygon(174, 105, 184, 110, 181, 140, 171, 137,
                             fill='#a7cbc6', outline=edge, width=2, tags='laptop')
            c.create_line(184, 110, 188, 108, 185, 140, 181, 140,
                          fill='#38495b', width=3, tags='laptop')
            c.create_polygon(125, 141, 171, 137, 181, 142, 131, 146,
                             fill='#758799', outline=edge, tags='laptop')
            for x in (138, 148, 158):
                c.create_line(x, 140, x + 3, 143, fill='#38495b', tags='laptop')
            line((98, 108, 109, 129, 140, 140 + beat))
            line((96, 112, 112, 135, 152, 140 - beat))
        else:
            line((95, 110, 111, 126, 125, 135))
            line((95, 114, 91, 133, 112, 139 + beat))
            c.create_polygon(109, 129, 132, 134, 155, 129, 155, 150, 132, 155, 109, 150,
                             fill='#edf0e5', outline='#4b5c67', width=2, tags='book')
            c.create_line(132, 134, 132, 153, fill='#4b5c67', tags='book')
            c.create_line(138, 140, 149, 137 + beat, fill='#93a19b', tags='book')
        c.create_line(119, 146, 192, 146, fill='#7c8b9b', width=5, tags='desk')
        c.create_line(184, 147, 184, 196, fill='#7c8b9b', width=4, tags='desk')
        if mode in ('notes', 'sketch', 'draw', 'organize'):
            c.create_polygon(109, 126, 152, 126, 158, 147, 113, 151, fill='#ede8d7', outline='#667780', tags='process')
            if mode in ('sketch', 'draw'):
                c.create_line(119, 142, 129, 132, 140, 143, 148, 137, fill='#667780', tags='process')
            else:
                for y in (132, 138, 144):
                    c.create_line(118, y, 140 + beat, y, fill='#8b9897', tags='process')
            c.create_line(129 + beat, 125, 140 + beat, 142, fill='#bfa26b', width=3, tags='process')
        elif mode == 'review':
            line((96, 112, 120, 109, 117, 88 + beat))
    elif activity == '进食':
        head(102, 77 + breath)
        line((102, 97, 102, 149, 86, 195))
        line((102, 149, 127, 195))
        line((102, 110, 81, 132, 121, 141))
        # Spoon moves between bowl and face.
        lift = (beat + 1) / 2
        hand_x, hand_y = 137 - 21 * lift, 130 - 39 * lift
        line((103, 112, 132, 116, hand_x, hand_y))
        c.create_line(hand_x, hand_y, hand_x - 8, hand_y - 6, fill='#9daaba', width=2, tags='spoon')
        c.create_oval(hand_x - 14, hand_y - 12, hand_x - 7, hand_y - 6, fill='#d5c49e', outline=edge, tags='spoon')
        c.create_arc(119, 124, 166, 153, start=180, extent=180, fill='#8bbcaf', outline=edge, width=2, tags='bowl')
        c.create_line(119, 139, 166, 139, fill=edge, width=2, tags='bowl')
    elif activity == '休闲':
        c.create_line(71, 110, 82, 164, 136, 164, fill='#8597aa', width=8, tags='chair')
        c.create_line(83, 164, 79, 196, 137, 196, 137, 164, fill='#8597aa', width=4, tags='chair')
        head(91, 81 + breath + (5 * amount if kind == 'drowsy' else 0))
        line((94, 99, 103, 143, 134, 147, 155, 182))
        line((103, 143, 127, 171, 150, 159 + beat))
        if kind == 'stomach':
            line((98, 112, 79, 133, 67 + 38*amount, 125 + 13*amount))
        elif kind in ('stretch', 'release'):
            line((98, 112, 82, 132-40*amount, 67, 125-68*amount))
        else:
            line((98, 112, 82, 132, 67, 125))
        line((98, 112, 117, 129, 137, 121))
        if 'headphones' in data['owned']:
            c.create_arc(69, 57 + breath, 112, 98 + breath, start=0, extent=180, outline='#6cb8a7', width=5, style='arc', tags='equipment')
            for x in (70, 108):
                c.create_rectangle(x, 77 + breath, x + 6, 90 + breath, fill='#6cb8a7', outline=edge, tags='equipment')
            c.create_text(151, 79 + beat * 2, text='♪', fill='#6cb8a7', font=('Segoe UI', -24), tags='music')
    else:
        # Gentle weight shift; short stretches without moving the desktop window.
        shift = math.sin(now * .8) * 3
        head(110 + shift, 70 + breath + (6*amount if kind == 'drowsy' else 0))
        line((110 + shift, 89 + breath, 110, 145, 88, 196))
        line((110, 145, 139, 196))
        lift = amount if kind in ('stretch', 'release') else 0
        if kind == 'stomach':
            line((110 + shift, 109, 88, 124, 73 + 34*amount, 147-12*amount))
        else:
            line((110 + shift, 109, 88, 124-18*lift, 73, 147-65*lift))
        line((110 + shift, 109, 132, 124-18*lift, 148, 147-65*lift))
