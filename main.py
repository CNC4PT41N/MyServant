import time
import threading
import queue
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from simulation import Simulation, ACTIVITIES

from storage import SAVE, LEGACY_SAVE, load, write
from tray import Tray
from activity_state import effective_activity
from progression import ROUTES, JOBS, ITEMS, COSMETICS, COURSES, LABELS, course_for, mastery_bonus, work_title, qualifies
from content_config import CONTENT, ERROR as CONTENT_ERROR
from character import draw_character
from character_config import CharacterFile
from character_images import ImageRenderer
from desktop_edges import Desktop, snap_position
from single_instance import SingleInstance
from ambient_motion import MotionClock
from activity_content import abilities
from screen_feedback import FeedbackSchedule, observe
from panel_style import load_style
from panel_shell import PanelShell, enable_dpi_awareness
from hollow_panel import HollowPanel
from alpha_window import LayeredWindowError
from runtime_diagnostics import record_error

ACTIVITY_NAMES = {'工作': LABELS['work'], '学习': LABELS['study'], '睡眠': '睡觉',
                  '进食': '吃饭', '休闲': '放松', '自由活动': '自由活动'}


class App:
    def __init__(self, instance=None):
        enable_dpi_awareness()
        self.instance = instance
        self.theme, self.theme_error = load_style()
        try:
            source = SAVE if SAVE.exists() or not LEGACY_SAVE.exists() else LEGACY_SAVE
            self.sim = Simulation(load(source))
            self.sim.advance()
        except (OSError, ValueError, KeyError, TypeError) as error:
            alert = tk.Tk()
            alert.withdraw()
            messagebox.showerror('无法读取存档', f'请检查存档文件：{source}\n{error}\n原文件未被覆盖。', parent=alert)
            alert.destroy()
            raise SystemExit(1)
        self.root = tk.Tk()
        self.root.report_callback_exception = lambda _kind, error, _trace: record_error('Tk callback', error)
        if CONTENT_ERROR:
            messagebox.showerror('活动配置无法读取', CONTENT_ERROR + '\n原文件未修改，本次使用默认内容。', parent=self.root)
        if self.theme_error:
            messagebox.showerror('面板配置无法读取', self.theme_error + '\n原文件未修改，本次使用简洁浅色。', parent=self.root)
        self.root.withdraw()
        self.root.title('MyServant · 桌宠')
        self.root.overrideredirect(True)
        self.root.geometry('220x240+100+200')
        self.root.attributes('-topmost', self.sim.data['desktop']['topmost'])
        self.root.configure(bg='#ff00ff')
        self.root.wm_attributes('-transparentcolor', '#ff00ff')
        self.canvas = tk.Canvas(self.root, width=220, height=240, bg='#ff00ff', highlightthickness=0)
        self.canvas.pack()
        self.desktop = Desktop()
        self.edge_pose = self.sim.data['desktop']['edge']
        self.dragging = False
        self.motion_clock = MotionClock()
        self.feedback_schedule = FeedbackSchedule(self.sim.data['screen_feedback'])
        self.feedback_queue = queue.Queue()
        self.feedback_busy = False
        self.feedback_epoch = 0
        self.observation_cancel = threading.Event()
        self.feedback_pose = None
        self.feedback_activity = None
        self.feedback_until = 0.
        self.bubble = tk.Toplevel(self.root)
        self.bubble.withdraw()
        self.bubble.overrideredirect(True)
        self.bubble.attributes('-topmost', True)
        self.bubble.attributes('-alpha', .98)
        self.bubble_label = tk.Label(self.bubble, bg=self.theme['colors']['bubble'], fg=self.theme['colors']['bubble_text'], font=(self.theme['font'], self.theme['font_size']+1),
                                     wraplength=240, padx=12, pady=9, relief='solid', borderwidth=1)
        self.bubble_label.pack()
        self.bubble.update_idletasks()
        hwnd = self.desktop.user.GetAncestor(self.bubble.winfo_id(), 2)
        style = self.desktop.user.GetWindowLongPtrW(hwnd, -20)
        self.desktop.user.SetWindowLongPtrW(hwnd, -20, style | 0x08000000 | 0x20)
        self.character_file = CharacterFile()
        self.image_renderer = ImageRenderer(self.root)
        self.character_error = ''
        self.character_stamp = None
        self.reload_character()
        self.canvas.bind('<ButtonPress-1>', self.drag_start)
        self.canvas.bind('<B1-Motion>', self.drag)
        self.canvas.bind('<ButtonRelease-1>', self.drag_end)
        self.canvas.bind('<Button-3>', lambda e: self.menu.tk_popup(e.x_root, e.y_root))
        self.menu = tk.Menu(self.root, tearoff=False)
        self.menu.add_command(label='操作面板', command=self.show_panel)
        self.menu.add_command(label='改名', command=self.rename_character)
        self.menu.add_command(label='切换置顶', command=self.toggle_top)
        self.menu.add_command(label='隐藏角色', command=self.hide_character)
        self.menu.add_command(label='鼠标穿透', command=self.toggle_click_through)
        self.menu.add_command(label='退出', command=self.close)
        self.panel = tk.Toplevel(self.root)
        self.panel.title('MyServant · 操作面板')
        self.panel.withdraw()
        self.panel.overrideredirect(True)
        self.panel.attributes('-topmost', True)
        self.panel.configure(bg=self.theme['colors']['background'])
        self.panel.protocol('WM_DELETE_WINDOW', self.panel.withdraw)
        self.panel_entered = False
        self.panel.bind('<Enter>', self.panel_enter, add='+')
        self.panel.bind('<Leave>', self.panel_leave, add='+')
        self.dialog_open = False
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TFrame', background=self.theme['colors']['background'])
        style.configure('TLabel', background=self.theme['colors']['background'], foreground=self.theme['colors']['text'], font=(self.theme['font'], self.theme['font_size']+1))
        style.configure('Card.TFrame', background=self.theme['colors']['surface'])
        style.configure('Card.TLabel', background=self.theme['colors']['surface'], foreground=self.theme['colors']['text'], font=(self.theme['font'], self.theme['font_size']+1))
        style.configure('TButton', font=(self.theme['font'], self.theme['font_size']+1), padding=(12, 12), background=self.theme['colors']['button'], foreground=self.theme['colors']['text'], borderwidth=0, relief='flat')
        style.map('TButton', background=[('pressed', self.theme['colors']['pressed']), ('active', self.theme['colors']['hover'])], foreground=[('disabled', self.theme['colors']['disabled'])])
        style.configure('Primary.TButton', background=self.theme['colors']['accent'], foreground=self.theme['colors']['accent_text'])
        style.map('Primary.TButton', background=[('pressed', self.theme['colors']['pressed']), ('active', self.theme['colors']['hover'])])
        style.configure('TCombobox', fieldbackground=self.theme['colors']['button'], background=self.theme['colors']['button'], foreground=self.theme['colors']['text'], arrowcolor=self.theme['colors']['subtle'], borderwidth=0, padding=6)
        style.map('TCombobox', fieldbackground=[('readonly', self.theme['colors']['button'])], foreground=[('readonly', self.theme['colors']['text'])], selectbackground=[('readonly', self.theme['colors']['button'])], selectforeground=[('readonly', self.theme['colors']['text'])])
        self.panel.option_add('*TCombobox*Listbox.background', self.theme['colors']['button'])
        self.panel.option_add('*TCombobox*Listbox.foreground', self.theme['colors']['text'])
        for key, color in [('hunger', self.theme['colors']['hunger']), ('energy', self.theme['colors']['energy']), ('stress', self.theme['colors']['stress'])]:
            style.configure(f'{key}.Horizontal.TProgressbar', troughcolor=self.theme['colors']['track'], background=color, borderwidth=0, lightcolor=color, darkcolor=color)
        self.hollow_layout = self.theme['layout'] == 'hollow'
        if self.hollow_layout:
            self.duration = tk.StringVar(value='4')
            self.page = '活动'
            self.menu_view = HollowPanel(self)
            self.menu_view.pack(fill='both', expand=True)
        else:
            self.build_classic_panel()
        self.last_save = 0
        self.last_disk_check = 0
        self.next_panel_refresh = 0
        self.last_visibility_check = 0
        self.update_timer = None
        self.last_saved_state = None
        self.tray = Tray()
        self.tray.screen_feedback = self.sim.data['screen_feedback']['enabled']
        self.closed = False
        self.root.update_idletasks()
        position = self.sim.data['desktop']
        self.desktop.move(self.root, position['x'], position['y'])
        self.tray.hidden = position['hidden']
        self.tray.click_through = position['click_through']
        self.desktop.click_through(self.root, self.tray.click_through)
        if not self.tray.hidden:
            self.root.deiconify()
            self.root.update_idletasks()
            self.desktop.move(self.root, position['x'], position['y'])
            self.snap_character()
        self.update()

    def build_classic_panel(self):
        if self.hollow_layout:
            self.panel_shell = PanelShell(self.panel, self.theme)
            self.panel_shell.pack(fill='both', expand=True)
            frame = self.panel_shell.body
        else:
            frame = tk.Frame(self.panel, bg=self.theme['colors']['surface'], highlightbackground=self.theme['colors']['border'], highlightthickness=1, padx=self.theme['padding'], pady=self.theme['padding'])
            frame.pack(fill='both', expand=True)
        shell = frame
        if self.hollow_layout:
            self.panel_name = tk.Label(shell, bg=self.theme['colors']['surface'], fg=self.theme['colors']['text'],
                                       text=self.character_config['name'], font=(self.theme['font'], self.theme['font_size']+3), pady=6)
            self.panel_name.pack(fill='x', pady=(0, 8))
        if self.theme['show_header']:
            header = tk.Frame(shell, bg=self.theme['colors']['header'])
            header.pack(fill='x', pady=(0, 8))
            tk.Label(header, text='◇', bg=self.theme['colors']['header'], fg=self.theme['colors']['header_text'], font=(self.theme['title_font'], 13)).pack(side='left', padx=8)
            tk.Label(header, text=self.theme['header_text'], bg=self.theme['colors']['header'], fg=self.theme['colors']['header_text'], font=(self.theme['title_font'], self.theme['font_size']+1), pady=5).pack(side='left')
            tk.Label(header, text='◇', bg=self.theme['colors']['header'], fg=self.theme['colors']['header_text'], font=(self.theme['title_font'], 13)).pack(side='right', padx=8)
        tabs = tk.Frame(shell, bg=self.theme['colors']['surface'])
        tabs.pack(fill='x', pady=(0, 10))
        self.pages = {}
        self.tab_buttons = {}
        self.page = '活动'
        for name in ('活动', '成长', '商店'):
            button = tk.Button(tabs, text=name, command=lambda n=name: self.switch_page(n),
                               bg=self.theme['colors']['button'], fg=self.theme['colors']['text'], relief='flat', borderwidth=0,
                               padx=18, pady=5, font=(self.theme['font'], self.theme['font_size']), cursor='hand2',
                               activebackground=self.theme['colors']['surface'], activeforeground=self.theme['colors']['accent'])
            button.pack(side='left', padx=2)
            self.tab_buttons[name] = button
            self.pages[name] = tk.Frame(shell, bg=self.theme['colors']['surface'])
        frame = self.pages['活动']
        frame.pack(fill='both', expand=True)
        self.status = tk.Label(frame, bg=self.theme['colors']['surface'], fg=self.theme['colors']['text'], font=(self.theme['font'], self.theme['font_size']+1, 'bold'), anchor='w')
        self.status.pack(fill='x')
        self.queue = tk.Label(frame, bg=self.theme['colors']['surface'], fg=self.theme['colors']['subtle'], font=(self.theme['font'], self.theme['font_size']-1), anchor='w', wraplength=280)
        self.queue.pack(fill='x', pady=(3, 10))
        self.result_label = self.plain_label(frame, wraplength=300)
        self.result_label.pack(fill='x', pady=(0, 6))
        strip = tk.Frame(frame, bg=self.theme['colors']['surface'])
        strip.pack(fill='x')
        self.stats = {}
        for i, (key, title) in enumerate([('hunger', '饥饿'), ('energy', '活力'), ('stress', '压力')]):
            cell = tk.Frame(strip, bg=self.theme['colors']['surface'])
            cell.grid(row=0, column=i, sticky='ew', padx=(0 if i == 0 else 10, 0))
            strip.columnconfigure(i, weight=1)
            label = tk.Label(cell, bg=self.theme['colors']['surface'], fg=self.theme['colors']['muted'], anchor='w', font=(self.theme['font'], self.theme['font_size']))
            label.pack(fill='x', pady=(0, 4))
            bar = ttk.Progressbar(cell, maximum=100, style=f'{key}.Horizontal.TProgressbar', length=76)
            bar.pack(fill='x')
            self.stats[key] = (title, label, bar)
        self.resources = tk.Label(frame, bg=self.theme['colors']['surface'], fg=self.theme['colors']['subtle'], font=(self.theme['font'], self.theme['font_size']-1), anchor='w')
        self.resources.pack(fill='x', pady=(9, 10))
        ttk.Separator(frame).pack(fill='x', pady=(0, 10))
        row = tk.Frame(frame, bg=self.theme['colors']['surface'])
        row.pack(fill='x')
        tk.Label(row, text='时长', bg=self.theme['colors']['surface'], fg=self.theme['colors']['muted'], font=(self.theme['font'], self.theme['font_size'])).pack(side='left')
        self.duration = tk.StringVar(value='10')
        for hours in ('4', '8', '10'):
            tk.Radiobutton(row, text=hours + 'h', variable=self.duration, value=hours,
                           indicatoron=False, bg=self.theme['colors']['button'], fg=self.theme['colors']['text'], selectcolor=self.theme['colors']['selected'],
                           activebackground=self.theme['colors']['hover'], relief='flat', borderwidth=0,
                           padx=10, pady=4, font=(self.theme['font'], self.theme['font_size']), cursor='hand2').pack(side='left', padx=(8, 0))
        buttons = tk.Frame(frame, bg=self.theme['colors']['surface'])
        buttons.pack(fill='x', pady=(10, 0))
        self.action_buttons = []
        for i, activity in enumerate([*ACTIVITIES, '自由活动']):
            command = self.autonomous if activity == '自由活动' else lambda a=activity: self.assign(a)
            button = tk.Button(buttons, text=ACTIVITY_NAMES[activity], command=command, bg=self.theme['colors']['button'], fg=self.theme['colors']['text'],
                               activebackground=self.theme['colors']['hover'], activeforeground=self.theme['colors']['accent_text'], relief='flat',
                               borderwidth=0, padx=12, pady=8, font=(self.theme['font'], self.theme['font_size']), cursor='hand2')
            if self.hollow_layout:
                button.configure(text=ACTIVITY_NAMES[activity], anchor='center', pady=4)
                button.bind('<Enter>', lambda event, label=ACTIVITY_NAMES[activity]: event.widget.configure(text='›  ' + label + '  ‹'))
                button.bind('<Leave>', lambda event, label=ACTIVITY_NAMES[activity]: event.widget.configure(text=label))
                button.grid(row=i // 2, column=i % 2, sticky='ew', padx=4, pady=3)
            else:
                button.grid(row=i // 3, column=i % 3, sticky='ew', padx=2, pady=2)
            self.action_buttons.append(button)
        for i in range(2 if self.hollow_layout else 3):
            buttons.columnconfigure(i, weight=1)
        self.build_growth()
        self.build_shop()
        self.tab_buttons['活动'].configure(bg=self.theme['colors']['selected'])

    def reload_character(self):
        stamp = self.character_file.stamp()
        if stamp == self.character_stamp:
            return
        self.character_stamp = stamp
        try:
            config = self.character_file.read()
            if config['renderer'] == 'images':
                self.image_renderer.select(config)
            else:
                self.image_renderer.unload()
            self.character_config = config
            self.character_error = ''
        except (OSError, ValueError, TypeError, tk.TclError) as error:
            self.character_error = str(error)
            if not hasattr(self, 'character_config'):
                from character_config import DEFAULT_CHARACTER
                fallback = CharacterFile(DEFAULT_CHARACTER).read()
                self.image_renderer.select(fallback)
                self.character_config = fallback
        self.root.title(self.character_config['name'])

    def rename_character(self):
        self.dialog_open = True
        try:
            name = simpledialog.askstring('改名', '名称', initialvalue=self.character_config['name'], parent=self.root)
            if name is not None:
                try:
                    self.character_file.rename(name)
                    self.character_stamp = None
                    self.reload_character()
                except (OSError, ValueError) as error:
                    messagebox.showerror('无法改名', str(error), parent=self.root)
        finally:
            self.dialog_open = False

    def plain_label(self, parent, text='', **options):
        return tk.Label(parent, text=text, bg=self.theme['colors']['surface'], fg=self.theme['colors']['muted'],
                        font=(self.theme['font'], self.theme['font_size']), anchor='w', **options)

    def small_button(self, parent, text, command):
        return tk.Button(parent, text=text, command=command, bg=self.theme['colors']['button'], fg=self.theme['colors']['text'],
                         activebackground=self.theme['colors']['hover'], relief='flat', borderwidth=0,
                         padx=10, pady=7, font=(self.theme['font'], self.theme['font_size']), cursor='hand2')

    def build_growth(self):
        frame = self.pages['成长']
        self.growth_summary = self.plain_label(frame)
        self.growth_summary.pack(fill='x', pady=(0, 8))
        self.plain_label(frame, LABELS['learning']).pack(fill='x')
        routes = tk.Frame(frame, bg=self.theme['colors']['surface'])
        routes.pack(fill='x', pady=(6, 10))
        self.route_buttons = {}
        for route, name in ROUTES.items():
            button = self.small_button(routes, name, lambda r=route: self.choose_route(r))
            button.pack(side='left', expand=True, fill='x', padx=2)
            self.route_buttons[route] = button
        self.skills_label = self.plain_label(frame)
        self.skills_label.pack(fill='x', pady=(0, 10))
        self.course_label = self.plain_label(frame)
        self.course_label.pack(fill='x', pady=(0, 10))
        self.ability_label = self.plain_label(frame, wraplength=310)
        self.ability_label.pack(fill='x', pady=(0, 6))
        self.works_label = self.plain_label(frame, wraplength=310)
        self.works_label.pack(fill='x', pady=(0, 10))
        self.plain_label(frame, LABELS['job']).pack(fill='x', pady=(0, 5))
        self.jobs_frame = tk.Frame(frame, bg=self.theme['colors']['surface'])
        self.jobs_frame.pack(fill='x')
        self.job_buttons = {}
        self.job_labels = {}
        self.rebuild_jobs()

    def rebuild_jobs(self):
        for child in self.jobs_frame.winfo_children():
            child.destroy()
        self.job_buttons = {}
        self.job_labels = {}
        route = self.sim.data['study']
        for job, (name, skill, requirement, wage, energy, stress) in JOBS.items():
            if skill not in (None, route):
                continue
            row = tk.Frame(self.jobs_frame, bg=self.theme['colors']['surface'])
            row.pack(fill='x', pady=3)
            text = f'{name} · {wage}/小时\n' + (f'{ROUTES[skill]} {requirement} · 活力 −{energy}/小时' if skill else f'活力 −{energy}/小时')
            label = self.plain_label(row, text)
            label.pack(side='left')
            self.job_labels[job] = label
            button = self.small_button(row, '选择', lambda j=job: self.choose_job(j))
            button.pack(side='right', padx=(10, 0))
            self.job_buttons[job] = button

    def choose_route(self, route):
        if self.hollow_layout:
            self.menu_view.choose_route(route)
            return
        self.sim.advance()
        self.sim.data['study'] = route
        self.save()
        self.rebuild_jobs()
        self.refresh_progression()
        self.show_panel()

    def choose_job(self, job):
        self.sim.advance()
        if self.sim.choose_job(job):
            self.save()
        self.refresh_progression()

    def build_shop(self):
        frame = self.pages['商店']
        self.shop_summary = self.plain_label(frame)
        self.shop_summary.pack(fill='x', pady=(0, 10))
        categories = tk.Frame(frame, bg=self.theme['colors']['surface'])
        categories.pack(fill='x', pady=(0, 6))
        self.shop_category = '设备'
        self.category_buttons = {}
        for name in ('设备', '外观'):
            button = self.small_button(categories, name, lambda n=name: self.change_category(n))
            button.pack(side='left', padx=2)
            self.category_buttons[name] = button
        self.shop_list = tk.Frame(frame, bg=self.theme['colors']['surface'])
        self.shop_list.pack(fill='x')
        self.reset_appearance = tk.Frame(frame, bg=self.theme['colors']['surface'])
        self.small_button(self.reset_appearance, '原始配色', lambda: self.reset_slot('palette')).pack(side='left', padx=2)
        self.small_button(self.reset_appearance, '取下饰品', lambda: self.reset_slot('accessory')).pack(side='left', padx=2)
        self.rebuild_shop()

    def change_category(self, name):
        self.shop_category = name
        self.rebuild_shop()
        self.refresh_progression()
        self.show_panel()

    def rebuild_shop(self):
        for child in self.shop_list.winfo_children():
            child.destroy()
        self.shop_buttons = {}
        for category, button in self.category_buttons.items():
            button.configure(bg=self.theme['colors']['selected'] if category == self.shop_category else self.theme['colors']['button'])
        for item, (name, cost, effect) in ITEMS.items():
            if (item in COSMETICS) != (self.shop_category == '外观'):
                continue
            row = tk.Frame(self.shop_list, bg=self.theme['colors']['surface'])
            row.pack(fill='x', pady=5)
            self.plain_label(row, f'{name} · {cost}\n{effect}').pack(side='left')
            button = self.small_button(row, '购买', lambda i=item: self.purchase(i))
            button.pack(side='right', padx=(14, 0))
            self.shop_buttons[item] = button
        self.reset_appearance.pack_forget()
        if self.shop_category == '外观':
            self.reset_appearance.pack(fill='x', pady=(8, 0))

    def reset_slot(self, slot):
        self.sim.unequip(slot)
        self.save()
        self.refresh_progression()
        self.draw()

    def purchase(self, item):
        self.sim.advance()
        if item in COSMETICS and item in self.sim.data['owned']:
            changed = self.sim.equip(item)
        else:
            changed = self.sim.buy(item)
        if changed:
            self.save()
        self.refresh_progression()
        self.draw()

    def refresh_progression(self):
        if self.hollow_layout:
            self.menu_view.refresh()
            return
        d = self.sim.data
        self.growth_summary.configure(text=f"{LABELS['job']}：{JOBS[d['job']][0]}")
        self.skills_label.configure(text='   '.join(f'{name} {d["skills"][key]:.0f}' for key, name in ROUTES.items()))
        route, tier = course_for(d)
        self.course_label.configure(text=f"{COURSES[route][tier]} · 经验 {CONTENT['experience_rates'][tier]:g}/小时")
        self.result_label.configure(text=d['last_result'])
        if self.hollow_layout:
            if d['last_result']:
                self.result_label.pack(fill='x', pady=(0, 6), after=self.status)
            else:
                self.result_label.pack_forget()
        learned = abilities(d)
        self.ability_label.configure(text=' · '.join(learned[-3:]))
        self.works_label.configure(text=' · '.join(f'{name} ×{count}' for name, count in list(d['works'].items())[-3:]))
        for route, button in self.route_buttons.items():
            button.configure(bg=self.theme['colors']['selected'] if route == d['study'] else self.theme['colors']['button'])
        for job, button in self.job_buttons.items():
            available = qualifies(d, job)
            chosen = job == d['job']
            button.configure(text='已选择' if chosen else ('选择' if available else '未解锁'),
                             state='normal' if available and not chosen else 'disabled')
            name, skill, requirement, wage, energy, _ = JOBS[job]
            bonus = mastery_bonus(d, job)
            requirement_text = f'{ROUTES[skill]} {requirement}' if skill else '无门槛'
            self.job_labels[job].configure(text=f'{name} · {wage*(1+bonus):.1f}/小时\n{requirement_text} · 熟练 +{bonus:.0%}')
        self.shop_summary.configure(text=f"{LABELS['currency']}：{d['money']:.0f}")
        for item, button in self.shop_buttons.items():
            owned = item in d['owned']
            available = d['money'] >= ITEMS[item][1]
            if item in COSMETICS and owned:
                wearing = d['appearance'][COSMETICS[item]] == item
                button.configure(text='使用中' if wearing else '使用', state='disabled' if wearing else 'normal')
            else:
                button.configure(text='已拥有' if owned else ('购买' if available else '资金不足'),
                                 state='normal' if available and not owned else 'disabled')

    def switch_page(self, name):
        if self.hollow_layout:
            self.menu_view.switch_page(name)
            return
        for key, frame in self.pages.items():
            frame.pack_forget()
            self.tab_buttons[key].configure(bg=self.theme['colors']['selected'] if key == name else self.theme['colors']['button'])
        self.pages[name].pack(fill='both', expand=True)
        self.page = name
        self.refresh_progression()
        self.show_panel()

    def hide_character(self):
        self.cancel_observation()
        self.clear_feedback()
        self.panel.withdraw()
        self.root.withdraw()
        self.image_renderer.alpha_window.invalidate()
        self.tray.hidden = True
        self.save()

    def show_character(self):
        position = self.sim.data['desktop']
        self.root.deiconify()
        self.root.update_idletasks()
        self.desktop.move(self.root, position['x'], position['y'])
        self.tray.hidden = False
        self.tray.click_through = False
        self.desktop.click_through(self.root, False)
        self.snap_character()
        self.image_renderer.alpha_window.invalidate()
        self.desktop.ensure_visible(self.root, bool(self.root.attributes('-topmost')))
        self.draw()
        self.save()

    def handle_tray_events(self):
        while not self.tray.events.empty():
            action = self.tray.events.get()
            if action == 'quit':
                self.close()
                return
            if action == 'hide':
                self.hide_character()
            elif action == 'show':
                self.show_character()
            elif action == 'panel':
                self.show_character()
                self.show_panel()
            elif action == 'click_through':
                self.toggle_click_through()
            elif action == 'screen_feedback':
                self.cancel_observation()
                self.tray.screen_feedback = not self.tray.screen_feedback
                self.sim.data['screen_feedback']['enabled'] = self.tray.screen_feedback
                self.feedback_schedule.defer(time.time())
                self.clear_feedback()
                self.save()
            elif action == 'startup':
                import startup
                try:
                    startup.set_enabled(not startup.enabled())
                except OSError as error:
                    messagebox.showerror('开机启动', str(error), parent=self.root)

    def clear_feedback(self):
        self.feedback_pose = None
        self.feedback_activity = None
        self.feedback_until = 0.
        self.bubble.withdraw()

    def cancel_observation(self):
        self.feedback_epoch += 1
        self.observation_cancel.set()

    def position_bubble(self):
        self.bubble.update_idletasks()
        width, height = self.bubble.winfo_reqwidth(), self.bubble.winfo_reqheight()
        px, py = self.desktop.position(self.root)
        x0, y0, x1, y1 = self.desktop.work_area(px + 110, py + 120)
        x = min(max(x0, px + 30), x1-width)
        y = py-height-8 if py-height-8 >= y0 else py+245
        y = min(max(y0, y), y1-height)
        self.desktop.move(self.bubble, x, y, width, height)

    def poll_feedback(self):
        now = time.time()
        while not self.feedback_queue.empty():
            epoch, activity, category = self.feedback_queue.get()
            self.feedback_busy = False
            if epoch != self.feedback_epoch or self.tray.hidden or activity != effective_activity(self.sim.data) or not self.tray.screen_feedback or self.dragging:
                continue
            result = self.feedback_schedule.response(activity, category)
            if result:
                text, self.feedback_pose = result
                self.feedback_activity = activity
                self.feedback_until = time.monotonic() + 6
                self.bubble_label.configure(text=text)
                self.bubble.deiconify()
                self.position_bubble()
                self.feedback_schedule.delivered(text)
                self.save()
        if self.feedback_pose:
            if time.monotonic() >= self.feedback_until or effective_activity(self.sim.data) != self.feedback_activity or self.sim.data['activity'] == '睡眠':
                self.clear_feedback()
            else:
                self.position_bubble()
        if self.feedback_busy or self.dragging or self.dialog_open or self.panel.winfo_viewable():
            return
        activity = self.sim.data['activity']
        if effective_activity(self.sim.data) != activity:
            return
        if not self.feedback_schedule.due(now, activity, self.tray.hidden):
            return
        self.save()
        self.feedback_busy = True
        epoch = self.feedback_epoch
        self.observation_cancel = threading.Event()
        cancel = self.observation_cancel
        excluded = tuple(self.desktop.user.GetAncestor(window.winfo_id(), 2) for window in (self.root, self.panel, self.bubble))
        def worker():
            try:
                category = observe(excluded, cancel)
            except Exception:
                category = None
            self.feedback_queue.put((epoch, activity, category))
        threading.Thread(target=worker, daemon=True).start()

    def toggle_click_through(self):
        self.tray.click_through = not self.tray.click_through
        self.desktop.click_through(self.root, self.tray.click_through)
        self.panel.withdraw()
        self.save()

    def drag_start(self, event):
        self.dragging = True
        self.cancel_observation()
        self.clear_feedback()
        left, top = self.desktop.position(self.root)
        self.origin = (event.x_root, event.y_root, left, top)
        self.moved = False
        self.panel.withdraw()
        self.draw()

    def drag(self, event):
        x, y, left, top = self.origin
        dx, dy = event.x_root - x, event.y_root - y
        if abs(dx) + abs(dy) > 5:
            self.moved = True
            self.desktop.move(self.root, left + dx, top + dy)

    def drag_end(self, event):
        self.dragging = False
        self.snap_character()
        self.draw()
        if self.moved:
            self.save()
        if not self.moved:
            self.show_panel()

    def snap_character(self):
        if self.dragging:
            return
        x, y = self.desktop.position(self.root)
        width, height = self.root.winfo_width(), self.root.winfo_height()
        area = self.desktop.work_area(x + width // 2, y + height // 2)
        left, top, edge = snap_position(x, y, width, height, area, self.edge_pose)
        self.edge_pose = edge
        if (left, top) != (x, y):
            self.desktop.move(self.root, left, top)

    def show_panel(self):
        self.panel_entered = False
        pet_x, pet_y = self.desktop.position(self.root)
        x0, y0, x1, y1 = self.desktop.work_area(pet_x + 110, pet_y + 120)
        if self.hollow_layout:
            self.menu_view.fit((x0, y0, x1, y1))
        self.refresh_panel()
        self.panel.update_idletasks()
        width, height = (self.menu_view.size if self.hollow_layout else
                         (self.panel.winfo_reqwidth(), self.panel.winfo_reqheight()))
        left = pet_x + self.root.winfo_width() - 30
        top = pet_y + 30
        if left + width > x1:
            left = pet_x - width + 30
        left = max(x0, min(left, x1 - width))
        top = max(y0, min(top, y1 - height))
        self.panel.deiconify()
        self.desktop.move(self.panel, left, top, width, height)
        self.panel.lift()
        if self.hollow_layout:
            self.menu_view.focus_set()

    def panel_enter(self, event):
        self.panel_entered = True

    def panel_leave(self, event):
        # 子控件之间移动也会触发 Leave，延迟后检查整个窗口边界。
        self.panel.after(250, self.hide_if_outside)

    def hide_if_outside(self):
        if not self.panel_entered or self.dialog_open or not self.panel.winfo_viewable():
            return
        # 下拉选项属于独立弹出窗口，选择期间保持面板可见。
        if self.panel.grab_current() is not None:
            return
        x, y = self.panel.winfo_pointerxy()
        left, top = self.panel.winfo_rootx(), self.panel.winfo_rooty()
        if not (left <= x < left + self.panel.winfo_width() and
                top <= y < top + self.panel.winfo_height()):
            self.panel.withdraw()
            self.panel_entered = False

    def toggle_top(self):
        self.root.attributes('-topmost', not self.root.attributes('-topmost'))
        self.image_renderer.alpha_window.invalidate()
        self.save()

    def assign(self, activity):
        self.cancel_observation()
        self.clear_feedback()
        self.sim.advance()
        hours = float(self.duration.get()) if activity in ('工作', '学习', '休闲') else None
        self.sim.schedule(activity, hours)
        self.draw()
        self.save()
        self.panel.withdraw()

    def autonomous(self):
        self.cancel_observation()
        self.clear_feedback()
        self.sim.advance()
        self.sim.free_activity()
        self.draw()
        self.sim.log('已转入自由活动')
        self.save()
        self.panel.withdraw()

    def save(self):
        x, y = self.desktop.position(self.root)
        self.sim.data['desktop'] = dict(x=x, y=y,
                                       edge=self.edge_pose, hidden=self.tray.hidden,
                                       topmost=bool(self.root.attributes('-topmost')),
                                       click_through=self.tray.click_through)
        import json
        state = dict(self.sim.data)
        state.pop('updated', None)
        fingerprint = json.dumps(state, ensure_ascii=False, sort_keys=True)
        if fingerprint != self.last_saved_state or time.time() - self.last_save >= 30:
            write(self.sim.data, SAVE)
            self.last_saved_state = fingerprint
            self.last_save = time.time()

    def draw(self):
        now = self.motion_clock.step(time.monotonic(), self.sim.data)
        edge = None if self.dragging else self.edge_pose
        try:
            drawn = self.image_renderer.draw(self.canvas, self.sim.data, now, ACTIVITY_NAMES, edge, self.feedback_pose, self.dragging)
        except LayeredWindowError as error:
            record_error('Layered character upload; retry on next frame', error)
            return
        except (OSError, ValueError) as error:
            record_error('Character image load', error)
            self.character_error = '角色图片无法读取'
            self.image_renderer.unload()
            drawn = False
        if not drawn:
            draw_character(self.canvas, self.sim.data, now, ACTIVITY_NAMES, self.character_config['color'], edge, self.dragging)

    def refresh_panel(self):
        if self.hollow_layout:
            self.menu_view.refresh()
            return
        d = self.sim.data
        for key, (title, label, bar) in self.stats.items():
            label.configure(text=f'{title} {d[key]:.0f}')
            bar['value'] = d[key]
        self.resources.configure(text=f"{LABELS['currency']}  {d['money']:.0f}    经验  {d['xp']:.0f}    等级  {1 + int(d['xp'] / 100)}")
        self.refresh_progression()
        seconds = max(0, int(d['remaining']))
        content = ''
        if d['activity'] == '学习':
            route, tier = d['plan_course']
            content = COURSES[route][tier]
        elif d['activity'] == '工作':
            content = d['plan_work']
        effective = effective_activity(d)
        if effective != d['activity']:
            content = ACTIVITY_NAMES[effective] + ' · ' + content
        prefix = '' if self.hollow_layout else self.character_config['name'] + ' · '
        if self.hollow_layout:
            self.panel_name.configure(text=self.character_config['name'])
        self.status.configure(text=prefix + (content or ACTIVITY_NAMES[d['activity']]) + (f'   {seconds // 3600:02}:{seconds % 3600 // 60:02}:{seconds % 60:02}' if seconds else ''))
        self.queue.configure(text=' → '.join(ACTIVITY_NAMES[a] for a, h in d['queue']) if d['queue'] else '')
        if self.hollow_layout:
            if d['queue']:
                self.queue.pack(fill='x', pady=(3, 8), after=self.status)
            else:
                self.queue.pack_forget()

    def update(self):
        if self.closed:
            return
        try:
            if self.instance and self.instance.restore_requested():
                self.show_character()
            self.handle_tray_events()
            if self.closed:
                return
            self.sim.advance()
            self.poll_feedback()
            now = time.monotonic()
            if now - self.last_disk_check >= 2:
                self.reload_character()
                self.last_disk_check = now
            if self.panel.winfo_viewable() and now >= self.next_panel_refresh:
                self.refresh_panel()
                self.next_panel_refresh = now + 1
            if not self.tray.hidden:
                if now - self.last_visibility_check >= 1:
                    if self.desktop.ensure_visible(self.root, self.sim.data['desktop']['topmost']):
                        self.image_renderer.alpha_window.invalidate()
                    self.last_visibility_check = now
                if not self.dragging:
                    self.snap_character()
                self.draw()
            if time.time() - self.last_save >= 5:
                self.save()
        except (OSError, tk.TclError) as error:
            record_error('Desktop update; retry on next tick', error)
        finally:
            # A failed save, monitor query or repaint must not stop all future
            # frames. Previously an exception could permanently end this timer.
            if not self.closed:
                interval = 40 if self.dragging else 1000 if self.tray.hidden else 250 if self.sim.data['activity'] == '睡眠' else 125
                self.update_timer = self.root.after(interval, self.update)

    def close(self):
        if self.closed:
            return
        self.cancel_observation()
        self.sim.advance()
        self.save()
        self.closed = True
        if self.update_timer is not None:
            self.root.after_cancel(self.update_timer)
        self.image_renderer.alpha_window.close()
        self.tray.close()
        self.root.destroy()


if __name__ == '__main__':
    import sys
    if '--smoke-test' in sys.argv:
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory(prefix='MyServant-check-') as temporary:
            SAVE = LEGACY_SAVE = Path(temporary) / 'save.json'
            app = App()
            app.root.after(1500, app.close)
            app.root.mainloop()
            (Path(sys.executable).parent / 'smoke-test.ok').write_text('OK', encoding='utf-8')
    else:
        instance = SingleInstance()
        try:
            if instance.primary:
                App(instance).root.mainloop()
        finally:
            instance.close()
