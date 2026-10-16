"""Readable, replaceable JSON save files with atomic background writes."""
import json
import math
import os
from pathlib import Path
from simulation import ACTIVITIES, Simulation
from progression import ROUTES, JOBS, ITEMS, COSMETICS, TRAINING, migrate, qualifies
from knight_collection import KEEPSAKES

from app_paths import ROOT
SAVE = ROOT / 'save.json'
LEGACY_SAVE = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'MyServant' / 'save.json'


def load(path=SAVE):
    if not path.exists():
        return Simulation().data
    data = json.loads(path.read_text(encoding='utf-8-sig'))
    default = Simulation().data
    if not isinstance(data, dict):
        raise ValueError('存档必须是 JSON 对象')
    # 在合并默认字段前迁移，确保旧总经验转为办公经验。
    default.update(migrate(data))
    if default['activity'] == '自主管理':
        default['activity'] = '自由活动'
    for key in ('hunger', 'energy', 'stress', 'money', 'xp', 'remaining', 'updated'):
        value = default[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise ValueError(f'{key} 必须是非负有限数字')
    for key in ('hunger', 'energy', 'stress'):
        if default[key] > 100:
            raise ValueError(f'{key} 必须在 0～100 之间')
    if default['activity'] not in (*ACTIVITIES, '自由活动'):
        raise ValueError('activity 活动名称无效')
    if default.get('care_activity') not in (None, '进食', '睡眠'):
        raise ValueError('care_activity 无效')
    if not isinstance(default['queue'], list):
        raise ValueError('queue 必须是列表')
    for item in default['queue']:
        if not isinstance(item, list) or len(item) != 2 or item[0] not in ACTIVITIES:
            raise ValueError('queue 项应为 [活动名称, 小时数]')
        if isinstance(item[1], bool) or not isinstance(item[1], (int, float)) or not math.isfinite(item[1]) or not 0 < item[1] <= 24:
            raise ValueError('queue 时长必须在 0～24 小时之间')
    if not isinstance(default['logs'], list) or not all(isinstance(x, str) for x in default['logs']):
        raise ValueError('logs 必须是文字列表')
    if not isinstance(default['skills'], dict) or set(default['skills']) != set(ROUTES):
        raise ValueError('skills 需要 office、tech、design 三项经验')
    for value in default['skills'].values():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise ValueError('技能经验必须是非负有限数字')
    if default['study'] not in ROUTES or default['plan_study'] not in ROUTES:
        raise ValueError('学习方向无效')
    if default['job'] not in JOBS or default['plan_job'] not in JOBS:
        raise ValueError('职业无效')
    if not isinstance(default['owned'], list) or any(item not in ITEMS for item in default['owned']):
        raise ValueError('owned 只能包含有效设备编号')
    if len(set(default['owned'])) != len(default['owned']):
        raise ValueError('owned 设备不能重复')
    keepsakes = default['keepsakes']
    if (not isinstance(keepsakes, list) or
            any(not isinstance(item, str) or item not in KEEPSAKES for item in keepsakes) or
            len(set(keepsakes)) != len(keepsakes)):
        raise ValueError('keepsakes 藏品编号无效或重复')
    choices = default['training_choice']
    if not isinstance(choices, dict) or set(choices) != set(ROUTES):
        raise ValueError('training_choice 修行方向无效')
    for route, choice in choices.items():
        if choice is not None and (type(choice) is not int or not 0 <= choice < len(TRAINING[route])):
            raise ValueError('training_choice 修行项目无效')
    planned = default['plan_training']
    if planned is not None and (type(planned) is not int or not 0 <= planned < len(TRAINING[default['plan_study']])):
        raise ValueError('plan_training 修行项目无效')
    appearance = default['appearance']
    if not isinstance(appearance, dict) or set(appearance) != {'palette', 'accessory'}:
        raise ValueError('appearance 需要 palette、accessory 两个外观栏位')
    for slot, item in appearance.items():
        if item is not None and (COSMETICS.get(item) != slot or item not in default['owned']):
            raise ValueError('外观必须属于对应栏位且已购买')
    desktop = default['desktop']
    if not isinstance(desktop, dict) or set(desktop) != {'x', 'y', 'edge', 'hidden', 'topmost', 'click_through'}:
        raise ValueError('desktop 桌面位置字段无效')
    if any(type(desktop[key]) is not int or abs(desktop[key]) > 100000 for key in ('x', 'y')):
        raise ValueError('桌面坐标必须是有效整数')
    if desktop['edge'] not in (None, 'left', 'right', 'top', 'bottom'):
        raise ValueError('贴边位置无效')
    if any(type(desktop[key]) is not bool for key in ('hidden', 'topmost', 'click_through')):
        raise ValueError('hidden、topmost、click_through 必须为布尔值')
    job_hours = default['job_hours']
    if not isinstance(job_hours, dict) or set(job_hours) != set(JOBS):
        raise ValueError('job_hours 职业熟练时间无效')
    for value in job_hours.values():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise ValueError('职业熟练时间必须为非负有限数字')
    course = default['plan_course']
    if not isinstance(course, list) or len(course) != 2 or course[0] != default['plan_study'] or type(course[1]) is not int or not 0 <= course[1] <= 3:
        raise ValueError('plan_course 课程无效')
    for key in ('plan_work', 'last_result'):
        if not isinstance(default[key], str) or len(default[key]) > 100:
            raise ValueError('活动内容或结果文字无效')
    session = default['session']
    works = default['works']
    feedback = default['screen_feedback']
    if not isinstance(feedback, dict) or set(feedback) != {'enabled', 'next_at', 'day', 'count', 'last_text'}:
        raise ValueError('screen_feedback 配置无效')
    if type(feedback['enabled']) is not bool or type(feedback['count']) is not int or not 0 <= feedback['count'] <= 4:
        raise ValueError('屏幕反馈开关或计数无效')
    if isinstance(feedback['next_at'], bool) or not isinstance(feedback['next_at'], (int, float)) or not math.isfinite(feedback['next_at']) or feedback['next_at'] < 0:
        raise ValueError('屏幕反馈时间无效')
    if not isinstance(feedback['day'], str) or len(feedback['day']) > 10 or not isinstance(feedback['last_text'], str) or len(feedback['last_text']) > 100:
        raise ValueError('屏幕反馈文字无效')
    if not isinstance(works, dict) or len(works) > 100 or any(not isinstance(key, str) or len(key) > 30 or type(value) is not int or value < 0 for key, value in works.items()):
        raise ValueError('works 成果记录无效')
    if session is not None:
        if not isinstance(session, dict) or set(session) != {'activity', 'title', 'money', 'xp', 'hours'}:
            raise ValueError('session 活动记录无效')
        if session['activity'] not in ('工作', '学习') or session['activity'] != default['activity'] or not isinstance(session['title'], str) or len(session['title']) > 60:
            raise ValueError('session 活动名称无效')
        for key in ('money', 'xp', 'hours'):
            value = session[key]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                raise ValueError('session 活动数值无效')
    return default


def write(data, path=SAVE):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    with temporary.open('w', encoding='utf-8') as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
