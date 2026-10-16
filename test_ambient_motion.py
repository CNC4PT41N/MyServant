import copy
import unittest
from ambient_motion import MotionClock, gesture, speed
from simulation import Simulation


class AmbientMotionTests(unittest.TestCase):
    def test_fatigue_slows_clock_without_phase_jump(self):
        data = Simulation().data
        clock = MotionClock()
        self.assertEqual(clock.step(1000, data), 0)
        self.assertEqual(clock.step(1001, data), 1)
        data['energy'] = 0
        self.assertAlmostEqual(clock.step(1002, data), 1.45)
        self.assertAlmostEqual(clock.step(900, data), 1.45)

    def test_gestures_are_short_and_state_specific(self):
        cases = [({'energy': 20}, 'drowsy'), ({'hunger': 80}, 'stomach'),
                 ({'stress': 90}, 'release'), ({}, 'stretch')]
        for changes, expected in cases:
            data = Simulation().data
            data.update(changes)
            self.assertEqual(gesture(17, data)[0], expected)
            self.assertEqual(gesture(5, data), (None, 0))
            self.assertEqual(gesture(22, data), (None, 0))

    def test_no_rewards_or_interruptions(self):
        data = Simulation().data
        data.update(activity='工作', energy=20, hunger=80, stress=90)
        original = copy.deepcopy(data)
        self.assertEqual(gesture(17, data), (None, 0))
        speed(data)
        self.assertEqual(data, original)
