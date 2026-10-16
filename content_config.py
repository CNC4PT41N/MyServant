"""Externally editable activity content; loaded once per application launch."""
import json
import os
import math
from pathlib import Path

from app_paths import ROOT
PATH = Path(os.environ.get('MYSERVANT_CONTENT_FILE', str(ROOT / 'activities.json')))
MODES = {'read', 'notes', 'organize', 'code', 'sketch', 'draw', 'review', 'type', 'nail', 'shell', 'soul', 'battle', 'flower', 'explore'}


def number(value, minimum=0, maximum=1000):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not minimum <= value <= maximum:
        raise ValueError('活动数值超出范围')


def text(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 40:
        raise ValueError('名称必须为1～40个字符')


def texts(values, count=None):
    if not isinstance(values, list) or not values or len(values) > 12 or (count is not None and len(values) != count):
        raise ValueError('内容列表长度无效')
    for value in values:
        text(value)


def read_content(path=PATH):
    data = json.loads(path.read_text(encoding='utf-8-sig'))
    if not isinstance(data, dict):
        raise ValueError('活动配置必须为JSON对象')
    text(data['theme'])
    for key in ('study', 'work', 'currency', 'growth', 'job', 'learning'):
        text(data['labels'][key])
    thresholds = data['thresholds']
    if not isinstance(thresholds, list) or len(thresholds) != 3:
        raise ValueError('需要三个成长门槛')
    for value in thresholds:
        number(value, 1, 100000)
    if thresholds != sorted(set(thresholds)):
        raise ValueError('成长门槛必须严格递增')
    rates = data['experience_rates']
    if not isinstance(rates, list) or len(rates) != 4:
        raise ValueError('需要四个学习经验速度')
    for value in rates:
        number(value, .1, 1000)
    routes, jobs = data['routes'], data['jobs']
    if not isinstance(routes, dict) or set(routes) != {'office', 'tech', 'design'}:
        raise ValueError('保留office、tech、design三个路线编号，名称可修改')
    core_jobs = {'temp', 'clerk', 'admin', 'coordinator', 'tester', 'developer', 'engineer', 'assistant', 'designer', 'independent'}
    if not isinstance(jobs, dict) or not core_jobs <= set(jobs) or len(jobs) > 30:
        raise ValueError('保留原有工作编号，可新增工作')
    for route in routes.values():
        text(route['name'])
        texts(route['courses'], 4)
        texts(route['results'], 4)
        texts(route['abilities'], 3)
        texts(route['animations'])
        if 'training' in route:
            texts(route['training'], 3)
        if any(mode not in MODES for mode in route['animations']):
            raise ValueError('学习动作编号无效')
    for key, job in jobs.items():
        text(key)
        text(job['name'])
        text(job['result'])
        if job['route'] not in (None, *routes):
            raise ValueError('工作路线无效')
        for field in ('requirement', 'income', 'energy', 'stress'):
            number(job[field], 0, 100000 if field == 'requirement' else 1000)
        texts(job['contents'])
        texts(job['animations'])
        if any(mode not in MODES for mode in job['animations']):
            raise ValueError('工作动作编号无效')
    if jobs['temp']['route'] is not None or jobs['temp']['requirement'] != 0:
        raise ValueError('temp 必须保留为无需门槛的基础工作')
    rules = data['activity_rules']
    if set(rules) != {'工作', '学习', '睡眠', '进食', '休闲'}:
        raise ValueError('保留五个基础活动编号')
    for rule in rules.values():
        number(rule['hours'], .05, 24)
        number(rule['max_hunger'], 0, 100)
        number(rule['min_energy'], 0, 80)
    return data


ERROR = ''
try:
    CONTENT = read_content()
except (OSError, ValueError, KeyError, TypeError) as error:
    ERROR = str(error)
    CONTENT = read_content(ROOT / 'activities-default.json')
