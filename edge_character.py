"""Activity-specific poses at each screen edge, without labels or extra UI."""
import math
from activity_content import process


def draw_edge(c, activity, side, now, head, line, ink, outline, owned, data=None):
    breath = math.sin(now * 1.8) * 1.3
    beat = math.sin(now * 3)
    tag = f'edge_{side}'

    def points(values):
        return tuple(214 - n if i % 2 == 0 and side == 'right' else n for i, n in enumerate(values))

    def limb(values):
        line(points(values), tag=tag)

    def polygon(values, fill, prop):
        c.create_polygon(*points(values), fill=fill, outline=outline, width=2, tags=prop)

    def stroke(values, color, prop, width=2):
        c.create_line(*points(values), fill=color, width=width, tags=prop)

    def face(x, y):
        head(214 - x if side == 'right' else x, y)

    if activity == '睡眠':
        if side in ('left', 'right'):
            face(28, 148 + breath)
            limb((22, 168, 18, 190, 59, 172, 73, 202))
            limb((18, 190, 45, 198, 49, 207))
            limb((22, 173, 48, 170, 55, 176))
            limb((23, 177, 37, 185, 52, 176))
            stroke((3, 103, 3, 212), '#a6b6c4', tag)
            zx, zy = (78 if side == 'left' else 140), 114
        elif side == 'top':
            # A hammock tied to the upper edge, rather than the floor pose moved up.
            stroke((25, 5, 27, 113), '#91a7b6', tag, 2)
            stroke((188, 5, 183, 113), '#91a7b6', tag, 2)
            polygon((27, 110, 55, 124, 151, 124, 183, 110, 161, 137, 51, 137), '#cad6df', 'bed')
            face(55, 86 + breath)
            limb((74, 100, 111, 111, 141, 95, 165, 114))
            limb((111, 111, 142, 122, 166, 121))
            limb((89, 105, 104, 121, 118, 116))
            if 'bed' in owned:
                stroke((56, 130, 151, 130), '#77b7ac', 'equipment', 4)
            zx, zy = 146, 73
        else:
            # Curl up on the floor, head tucked toward the knees.
            face(141, 197 + breath)
            limb((123, 210, 92, 222, 70, 205, 104, 200))
            limb((92, 222, 75, 224, 92, 207, 112, 208))
            limb((118, 212, 107, 227, 86, 217))
            polygon((55, 231, 177, 231, 177, 237, 55, 237), '#cad6df', 'bed')
            if 'bed' in owned:
                stroke((62, 231, 169, 231), '#77b7ac', 'equipment', 3)
            zx, zy = 84, 182
        c.create_text(zx, zy + breath * 2, text='z z', fill='#65768a', font=('Segoe UI', -17), tags='sleep')
        return

    # Each activity has a different silhouette, not merely a different prop.
    if side in ('left', 'right'):
        poses = {
            '工作': ((49, 84), (49, 105, 40, 154, 39, 211), (40, 154, 63, 180, 69, 212), (48, 118), (109, 145)),
            '学习': ((39, 74), (39, 94, 34, 154, 49, 215), (34, 154, 66, 133, 12, 125), (38, 108), (87, 120)),
            '进食': ((30, 124), (25, 144, 20, 180, 66, 174, 73, 205), (20, 180, 47, 192, 54, 209), (28, 155), (85, 174)),
            '休闲': ((28, 126), (21, 145, 17, 183, 62, 172, 74, 201), (17, 183, 48, 190, 52, 208), (22, 156), (85, 170)),
            '自由活动': ((44, 101), (42, 121, 33, 163, 12, 189), (33, 163, 61, 143, 13, 130), (42, 133), (85, 167)),
        }
        (hx, hy), body, legs, shoulder, (px, py) = poses[activity]
        hy += breath
        face(hx, hy)
        limb(body)
        limb(legs)
        stroke((3, 47, 3, 215), '#a6b6c4', tag)
        if activity == '工作':
            stroke((5, 151, 140, 151), '#91a7b6', 'desk', 3)
        elif activity == '学习':
            # One foot braced against the wall while reading at eye level.
            stroke((7, 121, 21, 121), '#91a7b6', tag)
        elif activity == '休闲':
            limb((22, 155, 42, 164, 62, 173+breath))
            limb((23, 158, 35, 181, 49, 185))
        elif activity == '自由活动':
            # Climbing in place, alternating the upper grip.
            limb((42, 133, 27, 94, 8, 67 + beat*5))
            limb((42, 133, 58, 105, 8, 95 - beat*5))
    elif side == 'top':
        if activity == '学习':
            # Knees hooked over the edge, reading upside down.
            face(104, 158 + breath)
            limb((104, 138, 106, 79, 82, 46, 79, 7))
            limb((106, 79, 133, 44, 139, 7))
            hx, hy, shoulder, px, py = 104, 158+breath, (106, 120), 158, 142
        elif activity == '进食':
            # One-handed hang, bowl balanced close to the other hand.
            face(94, 76 + breath)
            limb((94, 96, 95, 137, 77, 174, 87, 190))
            limb((95, 137, 121, 163, 141, 160+beat*3))
            limb((94, 110, 72, 57, 75, 7))
            hx, hy, shoulder, px, py = 94, 76+breath, (95, 109), 148, 116
        elif activity == '工作':
            # Suspended seat and dangling feet, leaning over a laptop.
            stroke((41, 5, 48, 5, 48, 131, 118, 131), '#91a7b6', tag, 3)
            face(80, 63 + breath)
            limb((81, 83, 78, 122, 111, 129, 117, 170+beat*2))
            limb((78, 122, 98, 150, 91, 174-beat*2))
            hx, hy, shoulder, px, py = 80, 63+breath, (82, 98), 140, 116
        else:
            # Relaxation is a loose swing; free activity is a slow pull-up.
            swing = math.sin(now*1.5)*6 if activity == '休闲' else 0
            pull = (math.sin(now*.9)+1)*9 if activity == '自由活动' else 0
            hx, hy = 110+swing*.5, 68+breath-pull
            face(hx, hy)
            limb((hx, hy+20, 110+swing, 133-pull))
            limb((hx, hy+30, 82, 45-pull*.4, 76, 7))
            limb((hx, hy+30, 138, 45-pull*.4, 144, 7))
            limb((110+swing, 133-pull, 89+swing, 166-pull, 95+swing, 186-pull))
            limb((110+swing, 133-pull, 131+swing, 166-pull, 139+swing, 181-pull))
        stroke((66, 3, 154, 3), '#a6b6c4', tag)
    else:
        poses = {
            '工作': ((86, 133), (86, 153, 96, 196, 141, 224, 176, 229), (96, 196, 89, 226, 123, 230), (88, 166), (144, 192)),
            '学习': ((124, 183), (111, 201, 62, 220, 25, 204), (62, 220, 37, 230, 15, 211), (105, 207), (168, 211)),
            '进食': ((108, 147), (109, 167, 109, 202, 77, 225, 141, 229), (109, 202, 146, 220, 84, 231), (110, 181), (144, 204)),
            '休闲': ((65, 159), (74, 178, 102, 221, 151, 211, 184, 230), (102, 221, 151, 231, 184, 231), (78, 188), (140, 202)),
            '自由活动': ((110, 161), (110, 181, 110, 217, 141, 214, 169, 230), (110, 217, 88, 224, 76, 232), (110, 191), (149, 200)),
        }
        (hx, hy), body, legs, shoulder, (px, py) = poses[activity]
        hy += breath
        face(hx, hy)
        limb(body)
        limb(legs)
        if activity == '工作':
            # Kneeling rather than sitting, absorbed in typing.
            stroke((119, 197, 174, 197), '#91a7b6', 'desk', 3)
        elif activity == '休闲':
            # Lean back on both palms, feet stretched out.
            limb((78, 188, 58, 211, 47, 231))
            limb((78, 188, 91, 209, 101, 213))
        elif activity == '自由活动':
            limb((110, 191, 92, 209, 88, 221))
            limb((110, 191, 131, 207, 145, 213+beat*3))
            limb((141, 214, 163, 215+beat*4, 177, 218+beat*4))
        stroke((12, 237, 198, 237), '#a6b6c4', tag, 1)

    if activity == '工作':
        # Side-view laptop: display facing the character, keyboard toward the hands.
        polygon((px+15, py-32, px+23, py-29, px+20, py-3, px+12, py-6), '#a7cbc6', 'laptop')
        polygon((px-26, py-3, px+12, py-6, px+20, py, px-20, py+4), '#758799', 'laptop')
        for offset in (-14, -5, 4):
            stroke((px+offset, py-2, px+offset+2, py+1), '#38495b', 'laptop', 1)
        sx, sy = shoulder
        limb((sx, sy, sx+16, sy+14, px-12, py-2+beat))
        limb((sx+2, sy+4, sx+24, sy+18, px+1, py-beat))
    elif activity == '学习':
        polygon((px-23, py-13, px, py-9, px+23, py-13, px+23, py+8, px, py+12, px-23, py+8), '#edf0e5', 'book')
        stroke((px, py-9, px, py+11), '#4b5c67', 'book')
        stroke((px+5, py-3, px+17, py-6+beat), '#93a19b', 'book', 1)
        sx, sy = shoulder
        limb((sx, sy, sx+15, sy+13, px-23, py+8))
        limb((sx+2, sy+4, sx+20, sy+20, px+20, py+8+breath))
    elif activity == '进食':
        polygon((px-19, py, px+19, py, px+12, py+17, px-12, py+17), '#8bbcaf', 'bowl')
        sx, sy = shoulder
        limb((sx, sy, sx+15, sy+17, px-15, py+8))
        lift = (beat + 1) / 2
        hand_x = px - (px-hx-15)*lift
        hand_y = py - (py-hy-8)*lift
        limb((sx+2, sy+4, sx+26, sy+5, hand_x, hand_y))
        stroke((hand_x, hand_y, hand_x-6, hand_y-6), '#9daaba', 'spoon')
    elif activity == '休闲' and 'headphones' in owned:
        # Keep purchased equipment visible in edge poses too.
        x = 214-hx if side == 'right' else hx
        c.create_arc(x-22, hy-24, x+22, hy+18, start=0, extent=180, outline='#6cb8a7', width=4, style='arc', tags='equipment')
        for dx in (-21, 17):
            c.create_rectangle(x+dx, hy-4, x+dx+5, hy+10, fill='#6cb8a7', outline=outline, tags='equipment')
    if data and activity in ('工作', '学习') and process(data, now) in ('notes', 'sketch', 'draw', 'organize'):
        polygon((px-22, py-9, px+19, py-9, px+23, py+9, px-20, py+9), '#ede8d7', 'process')
        stroke((px-12, py, px, py-5, px+12, py+5), '#8b9897', 'process')
        stroke((px+3+beat, py-12, px+12+beat, py+2), '#bfa26b', 'process', 3)
