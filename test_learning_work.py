import tempfile
import unittest
from pathlib import Path
from progression import course_for, mastery_bonus
from simulation import Simulation, HOUR
from storage import load, write
from content_config import CONTENT


class LearningWorkTests(unittest.TestCase):
    def test_course_progression_and_current_course_stays_fixed(self):
        sim = Simulation()
        sim.data['skills']['tech'] = 59
        sim.data['study'] = 'tech'
        sim.schedule('学习')
        sim.advance(sim.data['updated'] + HOUR)
        self.assertEqual(sim.data['plan_course'], ['tech', 0])
        self.assertEqual(course_for(sim.data), ('tech', 1))
        sim.schedule('学习')
        self.assertEqual(sim.data['plan_course'], ['tech', 1])

    def test_mastery_increases_pay_and_is_capped(self):
        base, trained = Simulation(), Simulation()
        trained.data['job_hours']['temp'] = 100
        for sim in (base, trained):
            sim.schedule('工作')
            sim.advance(sim.data['updated'] + HOUR)
        self.assertGreater(trained.data['money'], base.data['money'])
        trained.data['job_hours']['temp'] = 10000
        self.assertEqual(mastery_bonus(trained.data), .15)

    def test_offline_completion_reports_and_roundtrips(self):
        sim = Simulation()
        sim.schedule('学习')
        sim.advance(sim.data['updated'] + HOUR)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'save.json'
            write(sim.data, path)
            resumed = Simulation(load(path))
            resumed.advance(resumed.data['updated'] + 12 * HOUR)
            self.assertIsNone(resumed.data['session'])
            self.assertIn('经验 +', resumed.data['last_result'])
            self.assertGreater(resumed.data['skills']['office'], 0)

    def test_interrupt_preserves_rewards_without_double_credit(self):
        sim = Simulation()
        sim.schedule('工作')
        sim.advance(sim.data['updated'] + HOUR)
        balance = sim.data['money']
        sim.free_activity()
        self.assertEqual(sim.data['money'], balance)
        self.assertIn(CONTENT['labels']['currency'] + ' +', sim.data['last_result'])
        sim.free_activity()
        self.assertEqual(sim.data['money'], balance)

    def test_protective_rest_does_not_count_as_work(self):
        sim = Simulation()
        sim.schedule('工作')
        sim.data['hunger'] = 90
        sim.tick(5 / 60)
        self.assertEqual(sim.data['session']['hours'], 0)
        self.assertEqual(sim.data['job_hours']['temp'], 0)
