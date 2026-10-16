"""Fixed-size, ink-and-text menus. Only the content canvas can scroll."""
import json
import tkinter as tk

from activity_state import effective_activity
from content_config import CONTENT
from knight_collection import KEEPSAKES
from progression import ROUTES, JOBS, TRAINING, learning_title, qualifies


class HollowPanel(tk.Canvas):
    WIDTH = 280
    HEIGHT = 420
    BG = '#0b0f15'
    INK = '#deded4'
    MUTED = '#969a9e'
    DIM = '#606970'

    def __init__(self, app):
        self.app = app
        colors = app.theme['colors']
        self.BG, self.INK = colors['surface'], colors['text']
        self.MUTED, self.DIM = colors['muted'], colors['subtle']
        super().__init__(app.panel, bg=self.BG, highlightthickness=0, borderwidth=0)
        self.body = tk.Canvas(self, bg=self.BG, highlightthickness=0, borderwidth=0,
                              yscrollincrement=24)
        self.page = '活动'
        self.exploring = False
        self.collection_tab = '寻觅'
        self.selected_item = 'folded_map'
        self.scale = 1.
        self.size = (self.WIDTH, self.HEIGHT)
        self.focus_key = None
        self.hover_key = None
        self.targets = []
        self.signature = None
        for canvas in (self, self.body):
            canvas.bind('<Button-1>', lambda event, cv=canvas: self.click(cv, event))
            canvas.bind('<Motion>', lambda event, cv=canvas: self.hover(cv, event))
            canvas.bind('<Leave>', self.unhover)
            canvas.bind('<MouseWheel>', self.wheel)
            canvas.bind('<Tab>', self.navigate)
            canvas.bind('<Shift-Tab>', lambda event: self.navigate(event, -1))
            canvas.bind('<Down>', lambda event: self.navigate(event, 1))
            canvas.bind('<Up>', lambda event: self.navigate(event, -1))
            canvas.bind('<Return>', self.activate)
            canvas.bind('<space>', self.activate)
            canvas.bind('<Escape>', self.back)
        self.fit((0, 0, 1920, 1080))

    def fit(self, area):
        dpi = float(self.winfo_fpixels('1i')) / 96
        available_w, available_h = area[2] - area[0] - 24, area[3] - area[1] - 24
        # This is a pet-side popup: large OS text scales must not turn it into
        # a full-height game menu. Render crisp native text at the compact scale.
        self.scale = min(dpi, 1.25, max(1, available_w) / self.WIDTH)
        self.size = (round(self.WIDTH * self.scale), min(round(self.HEIGHT * self.scale), available_h))
        self.configure(width=self.size[0], height=self.size[1])
        self.logical_h = self.size[1] / self.scale
        self.body_h = max(40, self.logical_h - 130)
        self.body.place(x=18*self.scale, y=82*self.scale,
                        width=244*self.scale, height=self.body_h*self.scale)
        self.refresh(force=True)

    def font(self, size):
        return (self.app.theme['font'], -max(10, round(size*self.scale)))

    def text(self, cv, x, y, value, size=16, color=None, anchor='center', width=None):
        options = dict(text=value, fill=color or self.INK, font=self.font(size), anchor=anchor)
        if width:
            options['width'] = width*self.scale
        return cv.create_text(x*self.scale, y*self.scale, **options)

    def line(self, cv, points, color=None, smooth=False, width=1):
        return cv.create_line(*[v*self.scale for v in points], fill=color or self.DIM,
                              width=max(1, width*self.scale), smooth=smooth, splinesteps=24)

    def flourish(self, cv, cx, y, span=125):
        self.line(cv, (cx-span, y, cx-28, y), '#535c64')
        self.line(cv, (cx+28, y, cx+span, y), '#535c64')
        self.line(cv, (cx-24, y, cx-15, y-3, cx-10, y+3, cx-5, y), self.MUTED, True)
        self.line(cv, (cx+24, y, cx+15, y-3, cx+10, y+3, cx+5, y), self.MUTED, True)
        self.line(cv, (cx, y-3, cx+3, y, cx, y+3, cx-3, y, cx, y-3), self.INK)

    def button(self, cv, key, x, y, label, command, size=18, selected=False,
               enabled=True, width=200, emphasis=False):
        color = self.INK if selected or emphasis else self.MUTED
        if not enabled:
            color = self.DIM
        self.text(cv, x, y, label, size, color)
        if selected:
            offset = min(width/2-7, len(label)*size/2+20)
            self.pointer(cv, x-offset, y, 1)
            self.pointer(cv, x+offset, y, -1)
        target = dict(cv=cv, key=key, x=x*self.scale, y=y*self.scale,
                      w=width*self.scale, h=(size+18)*self.scale,
                      command=command, enabled=enabled)
        self.targets.append(target)

    def pointer(self, cv, x, y, direction, tag=None):
        coords = (x-6*direction, y-7, x-11*direction, y-6, x-12*direction, y,
                  x-6*direction, y+6, x+2*direction, y, x-5*direction, y-2,
                  x-7*direction, y+2)
        item = self.line(cv, coords, self.INK, True)
        if tag:
            cv.addtag_withtag(tag, item)

    def refresh(self, force=False):
        d = self.app.sim.data
        signature = json.dumps([self.page, self.exploring, self.collection_tab, self.selected_item,
                                self.app.character_config['name'], self.app.duration.get(),
                                d['activity'], int(d['remaining']), d.get('care_activity'), d['queue'],
                                [round(d[k]) for k in ('money', 'hunger', 'energy', 'stress')],
                                d['study'], d['job'], d['training_choice'], d['plan_course'],
                                d['plan_training'], d['plan_work'], d['keepsakes'],
                                [round(n) for n in d['skills'].values()], d['last_result'], d['works']],
                               ensure_ascii=False)
        if not force and signature == self.signature:
            return
        self.signature = signature
        old_y = self.body.canvasy(0)
        self.delete('all')
        self.body.delete('all')
        self.targets = []
        self.draw_frame()
        self.text(self, 140, 27, self.app.character_config['name'], 14, width=214)
        for i, name in enumerate(('活动', '修行', '收藏')):
            self.button(self, 'tab-'+name, 60+i*80, 55, name,
                        lambda n=name: self.switch_page(n), width=72, size=16,
                        emphasis=name == self.page)
            if name == self.page:
                self.text(self, 60+i*80, 69, '·', 14)
        self.flourish(self, 140, 77, 110)
        if self.page == '活动':
            height = self.draw_exploration() if self.exploring else self.draw_activity()
        elif self.page == '修行':
            height = self.draw_training()
        else:
            height = self.draw_collection()
        self.content_h = max(height, self.body_h)
        self.body.configure(scrollregion=(0, 0, 244*self.scale, self.content_h*self.scale))
        self.body.yview_moveto(max(0, old_y) / (self.content_h*self.scale))
        if self.content_h > self.body_h + 1:
            self.text(self, 264, self.logical_h-48, '↕', 11, self.MUTED)
        self.flourish(self, 140, self.logical_h-34, 110)
        self.text(self, 26, self.logical_h-19, f"◇ {CONTENT['labels']['currency']} {d['money']:.0f}",
                  12, anchor='w')
        self.button(self, 'back', 236, self.logical_h-19, '返回', self.back, size=12, width=48)
        self.mark_focus()

    def draw_frame(self):
        h = self.logical_h
        self.line(self, (24, 11, 12, 14, 9, 25, 9, h-24, 14, h-11, 26, h-8,
                         254, h-8, 268, h-14, 271, h-25, 271, 25, 266, 14, 256, 11),
                  '#afb3b2', True)
        self.line(self, (25, 11, 115, 11), '#afb3b2')
        self.line(self, (165, 11, 255, 11), '#afb3b2')
        for x, sign in ((26, 1), (254, -1)):
            for y, sy in ((21, 1), (h-18, -1)):
                self.line(self, (x, y, x-9*sign, y, x-11*sign, y+7*sy,
                                 x-4*sign, y+6*sy, x-3*sign, y+3*sy,
                                 x-7*sign, y+2*sy), self.MUTED, True)
        self.line(self, (116, 12, 122, 8, 129, 14, 127, 16, 120, 15), self.INK, True)
        self.line(self, (164, 12, 158, 8, 151, 14, 153, 16, 160, 15), self.INK, True)
        self.icon(self, 'mask', 140, 12, .24)

    def draw_activity(self):
        d, cv = self.app.sim.data, self.body
        names = {'工作': '探险', '学习': '修行', '睡眠': '睡觉', '进食': '吃饭',
                 '休闲': '放松', '自由活动': '自由活动'}
        current = effective_activity(d)
        label = names[current]
        if d['activity'] == '学习' and current == '学习':
            label = learning_title(d, planned=True)
        elif d['activity'] == '工作' and current == '工作':
            label = d['plan_work']
        seconds = max(0, int(d['remaining']))
        if seconds:
            label += f'  {seconds//3600:02}:{seconds%3600//60:02}'
        self.text(cv, 122, 17, label, 12, self.MUTED, width=232)
        commands = [('探险', self.open_exploration), ('修行', lambda: self.switch_page('修行')),
                    ('睡觉', lambda: self.app.assign('睡眠')), ('吃饭', lambda: self.app.assign('进食')),
                    ('放松', lambda: self.app.assign('休闲')), ('自由活动', self.app.autonomous)]
        for i, (name, callback) in enumerate(commands):
            self.button(cv, 'activity-'+name, 64+(i%2)*116, 62+(i//2)*47,
                        name, callback, size=18, selected=name == names[current], width=112)
        self.text(cv, 122, 201, '时长', 12, self.MUTED)
        self.durations(cv, 226)
        self.text(cv, 122, 262, '   '.join(f'{name} {d[key]:.0f}' for name, key in
                  (('饥饿', 'hunger'), ('活力', 'energy'), ('压力', 'stress'))), 11, self.MUTED)
        # Actual queued care and results are functional information, never filler copy.
        detail = (' → '.join(names[a] for a, _ in d['queue'])) or d['last_result']
        if detail:
            self.text(cv, 122, 300, detail, 11, self.MUTED, width=232)
        return 326 if detail else 280

    def durations(self, cv, y):
        for i, hours in enumerate(('4', '8', '10')):
            self.button(cv, 'duration-'+hours, 66+i*56, y, hours+'h',
                        lambda value=hours: self.set_duration(value), width=52, size=14,
                        emphasis=self.app.duration.get() == hours)
            if self.app.duration.get() == hours:
                self.line(cv, (56+i*56, y+12, 76+i*56, y+12), self.INK)

    def draw_training(self):
        d, cv = self.app.sim.data, self.body
        route = d['study']
        for i, (key, name) in enumerate(ROUTES.items()):
            self.button(cv, 'route-'+key, 42+i*80, 19, name,
                        lambda r=key: self.choose_route(r), width=74, size=16, emphasis=key == route)
            if key == route:
                self.line(cv, (28+i*80, 32, 56+i*80, 32), self.INK)
        self.icon(cv, {'office': 'nail', 'tech': 'mask', 'design': 'soul'}[route], 122, 65, .48)
        choice = d['training_choice'][route]
        choice = 0 if choice is None else choice
        options = TRAINING[route] or tuple(CONTENT['routes'][route]['courses'][:3])
        for i, name in enumerate(options):
            self.button(cv, 'training-'+str(i), 122, 104+i*37, name,
                        lambda n=i: self.choose_training(n), size=18, selected=i == choice, width=226)
        self.flourish(cv, 122, 201, 90)
        self.text(cv, 122, 217, f'{ROUTES[route]}经验 {d["skills"][route]:.0f}', 11, self.MUTED)
        self.durations(cv, 241)
        self.button(cv, 'start-training', 122, 271, '开始修行', self.start_training,
                    size=17, width=226)
        return 290

    def draw_exploration(self):
        d, cv = self.app.sim.data, self.body
        self.text(cv, 122, 20, '探险目的地', 18)
        y = 63
        for key, (name, route, requirement, *_rest) in JOBS.items():
            unlocked = qualifies(d, key)
            self.button(cv, 'job-'+key, 122, y, name, lambda k=key: self.choose_job(k),
                        selected=key == d['job'], enabled=unlocked, width=234, size=16)
            if not unlocked:
                self.text(cv, 122, y+20, f'需要{ROUTES[route]}经验 {requirement}', 11, self.DIM)
            y += 49
        self.durations(cv, y+2)
        self.button(cv, 'start-exploration', 122, y+42, '开始探险', lambda: self.app.assign('工作'),
                    size=18, width=226)
        return y+68

    def draw_collection(self):
        d, cv = self.app.sim.data, self.body
        self.text(cv, 122, 18, '旅途藏品', 18)
        for i, name in enumerate(('已收藏', '寻觅')):
            self.button(cv, 'collection-'+name, 80+i*88, 51, name,
                        lambda n=name: self.change_collection(n), width=82, size=14,
                        emphasis=name == self.collection_tab)
            if name == self.collection_tab:
                self.line(cv, (65+i*88, 64, 95+i*88, 64), self.INK)
        entries = [(key, item) for key, item in KEEPSAKES.items()
                   if self.collection_tab == '寻觅' or key in d['keepsakes']]
        if entries and self.selected_item not in dict(entries):
            self.selected_item = entries[0][0]
        for i, (key, (name, price, icon)) in enumerate(entries):
            y = 99+i*45
            self.icon(cv, icon, 24, y, .32)
            self.button(cv, 'item-'+key, 140, y-5, name, lambda k=key: self.select_item(k),
                        selected=key == self.selected_item, size=17, width=172)
            self.text(cv, 140, y+14, '已收藏' if key in d['keepsakes'] else f'◇ {price}',
                      11, self.MUTED)
        if not entries:
            self.text(cv, 122, 150, '暂无藏品', 14, self.DIM)
        if self.collection_tab == '寻觅' and entries:
            owned = self.selected_item in d['keepsakes']
            affordable = d['money'] >= KEEPSAKES[self.selected_item][1]
            self.button(cv, 'purchase', 122, 272,
                        '已收藏' if owned else '带走藏品' if affordable else '吉欧不足',
                        self.purchase, size=17, enabled=not owned and affordable, width=226)
        return 290

    def icon(self, cv, kind, x, y, size):
        def stroke(points, color=None, smooth=False):
            self.line(cv, tuple(v*size + (x if i%2 == 0 else y) for i, v in enumerate(points)),
                      color or self.MUTED, smooth)
        if kind == 'nail':
            stroke((-8, 30, 1, -19, 11, -15, -8, 30, -1, -13, 1, -19))
            stroke((-4, -21, 13, -17))
            stroke((3, -20, 7, -37, 11, -36, 7, -18))
            for k in range(3):
                stroke((5+k, -24-k*4, 10+k, -23-k*4))
        elif kind == 'mask':
            stroke((-15, -8, -26, -22, -20, -37, -12, -40, -18, -26, -10, -16,
                    10, -16, 18, -26, 12, -40, 20, -37, 26, -22, 15, -8,
                    15, 17, 0, 24, -15, 17, -15, -8), smooth=True)
            stroke((-8, 2, -7, 9), self.INK)
            stroke((8, 2, 7, 9), self.INK)
        elif kind == 'soul':
            stroke((-25, 20, -16, 9, -27, -8, -14, -26, 7, -31, 26, -16,
                    23, 6, 11, 20, -7, 18, -14, 4, -3, -8, 9, -7, 12, 3,
                    4, 8, 0, 3), smooth=True)
            stroke((-13, 23, -5, 28, 8, 25), smooth=True)
        elif kind == 'map':
            stroke((-26, -23, -9, -16, 9, -23, 26, -16, 26, 24, 9, 17,
                    -9, 24, -26, 17, -26, -23))
            stroke((-9, -16, -9, 24))
            stroke((9, -23, 9, 17))
            stroke((-22, 2, -10, -2, -2, 7, 10, -7, 21, 3), smooth=True)
        elif kind == 'quill':
            stroke((-20, 29, 23, -30, 20, -8, 2, 12, -15, 18, 23, -30), smooth=True)
            for i in range(4):
                stroke((-10+i*7, 16-i*10, 5+i*4, 9-i*10))
        elif kind == 'bell':
            stroke((-23, 20, -15, 8, -15, -13, -6, -24, 6, -24, 15, -13,
                    15, 8, 23, 20, -23, 20), smooth=True)
            stroke((-6, 23, 0, 30, 6, 23), smooth=True)
            stroke((-4, -25, -4, -33, 4, -33, 4, -25), smooth=True)
        elif kind == 'cloak':
            stroke((0, -27, -12, -20, -26, 28, -10, 23, -5, 32, 5, 23, 16, 29,
                    25, 21, 12, -20, 0, -27), smooth=True)
            stroke((-2, -21, -9, 6, -18, 23), smooth=True)
            stroke((4, -20, 7, 7, 16, 24), smooth=True)

    def switch_page(self, name):
        self.page = {'成长': '修行', '商店': '收藏'}.get(name, name)
        self.app.page = self.page
        self.exploring = False
        self.reset_scroll()

    def reset_scroll(self):
        self.body.yview_moveto(0)
        self.focus_key = self.hover_key = None
        self.refresh(force=True)

    def open_exploration(self):
        self.exploring = True
        self.reset_scroll()

    def choose_route(self, route):
        self.app.sim.advance()
        self.app.sim.data['study'] = route
        self.app.save()
        self.refresh()

    def choose_training(self, choice):
        self.app.sim.advance()
        self.app.sim.choose_training(self.app.sim.data['study'], choice)
        self.app.save()
        self.refresh()

    def start_training(self):
        d = self.app.sim.data
        self.app.sim.choose_training(d['study'], d['training_choice'][d['study']] or 0)
        self.app.assign('学习')

    def choose_job(self, job):
        self.app.sim.advance()
        if self.app.sim.choose_job(job):
            self.app.save()
        self.refresh()

    def set_duration(self, value):
        self.app.duration.set(value)
        self.refresh()

    def change_collection(self, name):
        self.collection_tab = name
        self.reset_scroll()

    def select_item(self, key):
        self.selected_item = key
        self.refresh()

    def purchase(self):
        self.app.sim.advance()
        if self.app.sim.collect_keepsake(self.selected_item):
            self.app.save()
        self.refresh()

    def back(self, event=None):
        if self.exploring:
            self.exploring = False
            self.reset_scroll()
        else:
            self.app.panel.withdraw()
        return 'break'

    def target_at(self, cv, event):
        x, y = cv.canvasx(event.x), cv.canvasy(event.y)
        return next((t for t in self.targets if t['cv'] is cv and t['enabled'] and
                     abs(t['x']-x) <= t['w']/2 and abs(t['y']-y) <= t['h']/2), None)

    def click(self, cv, event):
        target = self.target_at(cv, event)
        cv.focus_set()
        if target:
            self.focus_key = target['key']
            target['command']()
            self.mark_focus()

    def hover(self, cv, event):
        target = self.target_at(cv, event)
        key = target['key'] if target else None
        cv.configure(cursor='hand2' if key else '')
        if key != self.hover_key:
            self.hover_key = key
            self.mark_focus()

    def unhover(self, event=None):
        self.hover_key = None
        self.mark_focus()

    def mark_focus(self):
        self.delete('focus-marker')
        self.body.delete('focus-marker')
        key = self.hover_key or self.focus_key
        target = next((t for t in self.targets if t['key'] == key and t['enabled']), None)
        if target:
            cv, s = target['cv'], self.scale
            item = self.line(cv, (target['x']/s-10, (target['y']+target['h']/2)/s-2,
                                 target['x']/s+10, (target['y']+target['h']/2)/s-2), self.INK)
            cv.addtag_withtag('focus-marker', item)

    def navigate(self, event, step=None):
        step = step if step is not None else -1 if event.state & 1 else 1
        targets = [t for t in self.targets if t['enabled']]
        if targets:
            keys = [t['key'] for t in targets]
            index = keys.index(self.focus_key) if self.focus_key in keys else (-1 if step > 0 else 0)
            target = targets[(index+step) % len(targets)]
            self.focus_key, self.hover_key = target['key'], None
            if target['cv'] is self.body:
                top = self.body.canvasy(0)
                bottom = top+self.body.winfo_height()
                y, half = target['y'], target['h']/2
                if y-half < top:
                    self.body.yview_moveto(max(0, y-half) / (self.content_h*self.scale))
                elif y+half > bottom:
                    self.body.yview_moveto((y+half-self.body.winfo_height()) / (self.content_h*self.scale))
            self.mark_focus()
        return 'break'

    def activate(self, event=None):
        target = next((t for t in self.targets if t['key'] == self.focus_key and t['enabled']), None)
        if target:
            target['command']()
        return 'break'

    def wheel(self, event):
        if self.content_h > self.body_h:
            delta = -int(event.delta/120) if abs(event.delta) >= 120 else (-1 if event.delta > 0 else 1)
            self.body.yview_scroll(delta*2, 'units')
            self.hover_key = None
            self.mark_focus()
        return 'break'
