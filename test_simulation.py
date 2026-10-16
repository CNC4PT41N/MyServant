import unittest
from simulation import Simulation, HOUR


class SimulationTests(unittest.TestCase):
    def test_offline_work_completes_and_preserves_rewards(self):
        s = Simulation()
        s.schedule('工作')
        s.advance(s.data['updated'] + 24 * HOUR)
        self.assertEqual(s.data['activity'], '自由活动')
        self.assertGreater(s.data['money'], 0)
        self.assertTrue(all(0 <= s.data[k] <= 100 for k in ('hunger', 'energy', 'stress')))

    def test_preparation_before_work(self):
        s = Simulation()
        s.data.update(hunger=95, energy=10)
        s.schedule('工作')
        self.assertEqual(s.data['activity'], '进食')
        s.advance(s.data['updated'] + 24 * HOUR)
        self.assertGreater(s.data['money'], 0)
        self.assertEqual(s.data['activity'], '自由活动')

    def test_backward_clock_does_not_remove_progress(self):
        s = Simulation()
        s.schedule('学习')
        s.advance(s.data['updated'] - HOUR)
        self.assertEqual(s.data['remaining'], 10 * HOUR)


if __name__ == '__main__':
    unittest.main()
