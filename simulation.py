import time
from progression import JOBS, ITEMS, ROUTES, COSMETICS, COURSES, TRAINING, learning_title, course_for, mastery_bonus, work_title, migrate, qualifies
from knight_collection import KEEPSAKES
from activity_content import result_name
from activity_state import effective_activity

HOUR = 3600
from content_config import CONTENT
ACTIVITIES = {key: (rule['hours'], rule['max_hunger'], rule['min_energy']) for key, rule in CONTENT['activity_rules'].items()}


class Simulation:
    def __init__(self, data=None):
        self.data = data or dict(hunger=30., energy=85., stress=10., money=0.,
                                 xp=0., activity='自由活动', remaining=0., queue=[],
                                 updated=time.time(), logs=[])
        migrate(self.data)

    def choose_job(self, job):
        if job not in JOBS or not qualifies(self.data, job):
            return False
        self.data['job'] = job
        return True

    def buy(self, item):
        d = self.data
        if item not in ITEMS or item in d['owned'] or d['money'] < ITEMS[item][1]:
            return False
        d['money'] -= ITEMS[item][1]
        d['owned'].append(item)
        if item in COSMETICS:
            self.equip(item)
        return True

    def collect_keepsake(self, item):
        d = self.data
        if item not in KEEPSAKES or item in d['keepsakes'] or d['money'] < KEEPSAKES[item][1]:
            return False
        d['money'] -= KEEPSAKES[item][1]
        d['keepsakes'].append(item)
        return True

    def choose_training(self, route, choice):
        if route not in TRAINING or type(choice) is not int or not 0 <= choice < len(TRAINING[route]):
            return False
        self.data['study'] = route
        self.data['training_choice'][route] = choice
        return True

    def equip(self, item):
        if item not in COSMETICS or item not in self.data['owned']:
            return False
        self.data['appearance'][COSMETICS[item]] = item
        return True

    def unequip(self, slot):
        if slot not in self.data['appearance']:
            return False
        self.data['appearance'][slot] = None
        return True

    def log(self, message):
        self.data['logs'] = (self.data['logs'] + [message])[-30:]

    def schedule(self, activity, hours=None):
        d = self.data
        self.finish_session()
        duration, hunger, energy = ACTIVITIES[activity]
        d['plan_job'] = d['job']
        d['plan_study'] = d['study']
        d['plan_course'] = list(course_for(d))
        d['plan_training'] = d['training_choice'][d['plan_study']]
        d['plan_work'] = work_title(d)
        d['queue'] = []
        if activity != '进食' and d['hunger'] > hunger:
            d['queue'].append(['进食', .25])
        if d['energy'] < energy:
            d['queue'].append(['睡眠', min(8, (energy + 15 - d['energy']) / 12)])
            # 睡眠期间可能变饿，正式开始前再检查条件。
        d['queue'].append([activity, hours if hours is not None else duration])
        self.next_activity()

    def next_activity(self):
        d = self.data
        d['care_activity'] = None
        if not d['queue']:
            d['activity'], d['remaining'] = '自由活动', 0
            return
        activity, hours = d['queue'].pop(0)
        if activity != '进食' and d['hunger'] > ACTIVITIES[activity][1]:
            d['queue'].insert(0, [activity, hours])
            activity, hours = '进食', .25
        d['activity'], d['remaining'] = activity, hours * HOUR
        if activity in ('工作', '学习'):
            route, tier = d['plan_course']
            title = d['plan_work'] if activity == '工作' else learning_title(d, planned=True)
            d['session'] = {'activity': activity, 'title': title, 'money': 0., 'xp': 0., 'hours': 0.}
        self.log(f'开始{activity} · {hours:g} 小时')

    def finish_session(self, completed=False):
        d = self.data
        session = d['session']
        if not session:
            return
        if session['hours'] > 0:
            reward = f"{CONTENT['labels']['currency']} +{session['money']:.0f}" if session['activity'] == '工作' else f"经验 +{session['xp']:.0f}"
            d['last_result'] = f"{session['title']} · {reward}"
            if completed and session['hours'] >= 4:
                name = result_name(d, session)
                d['works'][name] = d['works'].get(name, 0) + 1
                d['last_result'] = f'{name} +1 · {reward}'
        d['session'] = None

    def free_activity(self):
        self.finish_session()
        self.data.update(activity='自由活动', remaining=0., queue=[], care_activity=None)

    def advance(self, now=None):
        d = self.data
        now = time.time() if now is None else now
        elapsed = max(0, now - d['updated'])
        # 所有可安排活动最多10小时；超长离线在30天后已进入稳定自主状态。
        elapsed = min(elapsed, 30 * 24 * HOUR)
        while elapsed > .001:
            step = min(elapsed, 300)
            if d['activity'] != '自由活动':
                step = min(step, d['remaining'])
            self.tick(step / HOUR)
            elapsed -= step
            if d['activity'] != '自由活动':
                d['remaining'] -= step
                if d['remaining'] <= .001:
                    self.finish_session(completed=True)
                    self.log(f"{d['activity']}完成")
                    self.next_activity()
        d['updated'] = max(now, d['updated'])

    def tick(self, hours):
        d = self.data
        activity = d['activity']
        effective = effective_activity(d)
        d['care_activity'] = effective if effective != activity else None
        if activity in ('工作', '学习'):
            if effective == '进食':
                d['hunger'] -= 100 * hours
            elif effective == '睡眠':
                d['energy'] += 30 * hours
            else:
                efficiency = max(.5, 1 - d['stress'] / 200)
                if activity == '工作':
                    _, route, _, wage, energy, stress = JOBS[d['plan_job']]
                    income = wage * (1.15 if 'computer' in d['owned'] else 1) * (1 + mastery_bonus(d, d['plan_job'])) * efficiency * hours
                    d['money'] += income
                    d['job_hours'][d['plan_job']] += hours
                    gain = efficiency * hours
                    d['xp'] += gain
                    if route:
                        d['skills'][route] += gain
                else:
                    route, tier = d['plan_course']
                    gain = CONTENT['experience_rates'][tier] * (1.2 if 'books' in d['owned'] else 1) * efficiency * hours
                    d['xp'] += gain
                    d['skills'][route] += gain
                    energy, stress = 6 + tier*.3, 2
                if d['session']:
                    d['session']['hours'] += hours
                    d['session']['xp'] += gain
                    if activity == '工作':
                        d['session']['money'] += income
                d['energy'] -= energy * hours
                d['hunger'] += 5 * hours
                d['stress'] += stress * hours
        elif activity == '睡眠':
            d['energy'] += 12 * (1.25 if 'bed' in d['owned'] else 1) * hours
            d['hunger'] += 2 * hours
            d['stress'] -= 2 * hours
        elif activity == '进食':
            d['hunger'] -= 280 * hours
        elif activity == '休闲':
            d['stress'] -= 9 * (1.3 if 'headphones' in d['owned'] else 1) * hours
            d['energy'] += 3 * hours
            d['hunger'] += 3 * hours
        else:
            d['hunger'] += (3 if d['hunger'] < 45 else -30) * hours
            d['energy'] += (-2 if d['energy'] > 65 else 12) * hours
            d['stress'] -= 5 * hours
        for key in ('hunger', 'energy', 'stress'):
            d[key] = max(0., min(100., d[key]))
