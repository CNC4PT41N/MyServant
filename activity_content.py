"""Small automatic activity variations and tangible results."""
from content_config import CONTENT
from activity_state import effective_activity
STUDY_RESULTS = {key: tuple(route['results']) for key, route in CONTENT['routes'].items()}
ABILITIES = {key: tuple(zip(CONTENT['thresholds'], route['abilities'])) for key, route in CONTENT['routes'].items()}


def abilities(data):
    return [name for route, entries in ABILITIES.items() for threshold, name in entries if data['skills'][route] >= threshold]


def process(data, now):
    if effective_activity(data) != data['activity']:
        return None
    if data['activity'] == '学习':
        modes = CONTENT['routes'][data['plan_course'][0]]['animations']
    elif data['activity'] == '工作':
        modes = CONTENT['jobs'][data['plan_job']]['animations']
    else:
        return None
    return modes[int(now // 12) % len(modes)]


def result_name(data, session):
    if session['activity'] == '学习':
        if data.get('plan_training') is not None:
            return session['title'] + '心得'
        route, tier = data['plan_course']
        return STUDY_RESULTS[route][tier]
    return CONTENT['jobs'][data['plan_job']]['result']
