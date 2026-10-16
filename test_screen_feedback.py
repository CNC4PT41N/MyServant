import unittest
import threading
from unittest.mock import Mock
from screen_feedback import FeedbackSchedule, default_state, classify
from screen_feedback import observe


class ScreenFeedbackTests(unittest.TestCase):
    def test_cancelled_observation_does_not_capture(self):
        event = threading.Event()
        event.set()
        self.assertIsNone(observe(cancel=event))
    def make(self):
        state = default_state()
        rng = Mock()
        rng.uniform.return_value = 3.5
        return state, FeedbackSchedule(state, 100000, rng)

    def test_enabled_by_default_no_backlog(self):
        state, schedule = self.make()
        self.assertTrue(state['enabled'])
        self.assertEqual(state['next_at'], 112600)
        self.assertFalse(schedule.due(100000, '工作', False))

    def test_sleep_and_hidden_defer_without_notification(self):
        for activity, hidden in [('睡眠', False), ('工作', True)]:
            state, schedule = self.make()
            self.assertFalse(schedule.due(112600, activity, hidden))
            self.assertGreater(state['next_at'], 112600)
            self.assertEqual(state['count'], 0)

    def test_daily_limit_and_no_duplicate_lines(self):
        state, schedule = self.make()
        state['day'] = '1970-01-02'
        self.assertTrue(schedule.due(112600, '学习', False))
        result = schedule.response('学习', 'code')
        schedule.delivered(result[0])
        self.assertIsNone(schedule.response('学习', 'code'))
        state['count'] = 4
        self.assertFalse(schedule.due(125200, '工作', False))

    def test_unknown_screen_is_quiet(self):
        _, schedule = self.make()
        self.assertIsNone(schedule.response('工作', None))
        self.assertIsNone(classify('untitled', 'hello'))
        self.assertEqual(classify('Visual Studio Code'), 'code')
        self.assertEqual(classify('视频播放', '美食 菜谱 食谱 烹饪 做菜'), 'food')
