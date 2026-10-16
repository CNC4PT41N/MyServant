"""The same effective activity drives simulation, sprites and feedback."""


def effective_activity(data):
    activity = data['activity']
    if activity not in ('工作', '学习'):
        return activity
    care = data.get('care_activity')
    if care == '进食' and data['hunger'] > 35:
        return care
    if data['hunger'] >= 80:
        return '进食'
    if care == '睡眠' and data['energy'] < 50:
        return care
    if data['energy'] <= 15:
        return '睡眠'
    return activity
