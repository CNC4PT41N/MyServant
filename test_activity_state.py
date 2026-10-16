import unittest
from unittest.mock import MagicMock
from PIL import Image
from simulation import Simulation
from activity_state import effective_activity
from activity_content import process
from character_images import ImageRenderer


class ActivityStateTests(unittest.TestCase):
    def test_care_does_not_flicker_at_threshold(self):
        sim = Simulation()
        sim.schedule('工作')
        sim.data.update(hunger=81, energy=80)
        sim.tick(1 / 60)
        self.assertLess(sim.data['hunger'], 80)
        self.assertEqual(effective_activity(sim.data), '进食')
        self.assertIsNone(process(sim.data, 0))
        sim.data['hunger'] = 35
        self.assertEqual(effective_activity(sim.data), '工作')
        sim.data.update(care_activity=None, hunger=20, energy=14)
        sim.tick(1 / 60)
        sim.data['energy'] = 16
        self.assertEqual(effective_activity(sim.data), '睡眠')
        sim.data['energy'] = 50
        self.assertEqual(effective_activity(sim.data), '工作')

    def test_all_edge_care_poses_override_process_and_feedback(self):
        sim = Simulation()
        renderer = ImageRenderer.__new__(ImageRenderer)
        renderer.config = {'fps': 6, 'motion': False}
        states = ['idle', 'drag', 'eat', 'sleep', 'feedback_focus']
        for edge in ('left', 'right', 'top', 'bottom'):
            states += [f'eat_{edge}', f'sleep_{edge}', f'feedback_focus_{edge}']
        from content_config import MODES
        for mode in MODES:
            states += [f'process_{mode}'] + [f'process_{mode}_{edge}' for edge in ('left', 'right', 'top', 'bottom')]
        renderer.frames = {state: [None] for state in states}
        renderer.get_frame = lambda *args: Image.new('RGBA', (50, 50))
        renderer.alpha_window = MagicMock()
        renderer.last_canvas_frame = None
        for activity in ('工作', '学习'):
            sim.data.update(hunger=20, energy=80)
            sim.schedule(activity)
            for hunger, energy, base in ((85, 80, 'eat'), (20, 10, 'sleep')):
                sim.data.update(hunger=hunger, energy=energy, care_activity=None)
                for edge in (None, 'left', 'right', 'top', 'bottom'):
                    renderer.draw(MagicMock(), sim.data, 0, {}, edge, 'focus')
                    self.assertEqual(renderer.current_state, base + ('_' + edge if edge else ''))
                    renderer.draw(MagicMock(), sim.data, 0, {}, edge, 'focus', True)
                    self.assertEqual(renderer.current_state, 'drag')
