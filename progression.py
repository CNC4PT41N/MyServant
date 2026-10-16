from content_config import CONTENT

ROUTES = {key: value['name'] for key, value in CONTENT['routes'].items()}
JOBS = {key: (job['name'], job['route'], job['requirement'], job['income'], job['energy'], job['stress']) for key, job in CONTENT['jobs'].items()}
LABELS = CONTENT['labels']
ITEMS = {
    'books': ('参考书', 120, '学习经验 +20%'),
    'computer': ('电脑', 350, '工作收入 +15%'),
    'bed': ('床垫', 180, '睡眠恢复 +25%'),
    'headphones': ('耳机', 150, '放松减压 +30%'),
    'graphite': ('石墨', 80, '配色'),
    'mint': ('薄荷', 80, '配色'),
    'cap': ('棒球帽', 100, '饰品'),
    'glasses': ('眼镜', 100, '饰品'),
}
COSMETICS = {'graphite': 'palette', 'mint': 'palette', 'cap': 'accessory', 'glasses': 'accessory'}
COURSES = {key: tuple(route['courses']) for key, route in CONTENT['routes'].items()}
TRAINING = {key: tuple(route.get('training', ())) for key, route in CONTENT['routes'].items()}
WORK_CONTENT = {key: tuple(job['contents']) for key, job in CONTENT['jobs'].items()}


def course_for(data, route=None):
    route = route or data['study']
    experience = data['skills'][route]
    tier = sum(experience >= threshold for threshold in CONTENT['thresholds'])
    return route, tier


def learning_title(data, planned=False):
    route, tier = data['plan_course'] if planned else course_for(data)
    choice = data['plan_training'] if planned else data['training_choice'][route]
    if choice is not None and choice < len(TRAINING[route]):
        return TRAINING[route][choice]
    return COURSES[route][tier]


def mastery_bonus(data, job=None):
    job = job or data['job']
    return min(.15, data['job_hours'][job] / 100 * .15)


def work_title(data, job=None):
    job = job or data['job']
    titles = WORK_CONTENT[job]
    return titles[int(data['job_hours'][job] // 8) % len(titles)]


def migrate(data):
    data.setdefault('skills', {'office': data.get('xp', 0), 'tech': 0., 'design': 0.})
    data.setdefault('study', 'office')
    data.setdefault('job', 'temp')
    data.setdefault('plan_job', data['job'])
    data.setdefault('plan_study', data['study'])
    data.setdefault('owned', [])
    data.setdefault('keepsakes', [])
    data.setdefault('training_choice', {route: None for route in ROUTES})
    # Existing running sessions retain their original course until rescheduled.
    data.setdefault('plan_training', None)
    data.setdefault('version', 2)
    data.setdefault('appearance', {'palette': None, 'accessory': None})
    data.pop('character', None)  # Appearance now lives in character.json.
    data.setdefault('desktop', {'x': 100, 'y': 200, 'edge': None, 'hidden': False, 'topmost': True})
    if isinstance(data['desktop'], dict):
        data['desktop'].setdefault('click_through', False)
    data.setdefault('job_hours', {job: 0. for job in JOBS})
    if isinstance(data['job_hours'], dict):
        for job in JOBS:
            data['job_hours'].setdefault(job, 0.)
    data.setdefault('plan_course', list(course_for(data, data['plan_study'])))
    data.setdefault('plan_work', work_title(data, data['plan_job']))
    data.setdefault('session', None)
    data.setdefault('last_result', '')
    data.setdefault('works', {})
    if data.get('content_theme') != CONTENT['theme']:
        data['plan_work'] = work_title(data, data['plan_job'])
        if data['session']:
            route, tier = data['plan_course']
            data['session']['title'] = data['plan_work'] if data['session']['activity'] == '工作' else COURSES[route][tier]
        data['content_theme'] = CONTENT['theme']
    data.setdefault('screen_feedback', {'enabled': True, 'next_at': 0., 'day': '', 'count': 0, 'last_text': ''})
    return data


def qualifies(data, job):
    _, route, requirement, *_ = JOBS[job]
    return route is None or data['skills'][route] >= requirement
