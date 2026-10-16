import unittest
from simulation import Simulation, HOUR
from activity_content import abilities, process
from content_config import CONTENT


class ActivityContentTests(unittest.TestCase):
    def test_completed_study_creates_specific_work_once(self):
        sim = Simulation()
        sim.data['study'] = 'tech'
        sim.schedule('学习', 10)
        sim.advance(sim.data['updated'] + 24 * HOUR)
        result = CONTENT['routes']['tech']['results'][0]
        self.assertEqual(sim.data['works'], {result: 1})
        self.assertIn(result + ' +1', sim.data['last_result'])
        sim.advance(sim.data['updated'] + HOUR)
        self.assertEqual(sim.data['works'][result], 1)

    def test_switching_cannot_farm_results(self):
        sim = Simulation()
        sim.schedule('学习', 10)
        sim.advance(sim.data['updated'] + 5 * HOUR)
        sim.schedule('工作')
        self.assertEqual(sim.data['works'], {})

    def test_work_has_occupation_result(self):
        sim = Simulation()
        sim.data['skills']['design'] = 180
        sim.choose_job('designer')
        sim.schedule('工作', 10)
        sim.advance(sim.data['updated'] + 24 * HOUR)
        self.assertEqual(sim.data['works'], {CONTENT['jobs']['designer']['result']: 1})
        self.assertIn(CONTENT['routes']['design']['abilities'][0], abilities(sim.data))

    def test_process_differs_by_route_and_job(self):
        sim = Simulation()
        sim.schedule('学习')
        modes = CONTENT['routes']['office']['animations']
        self.assertEqual([process(sim.data, t) for t in (0, 12, 24)], [modes[i % len(modes)] for i in range(3)])
        sim.data['study'] = 'tech'
        sim.schedule('学习')
        modes = CONTENT['routes']['tech']['animations']
        self.assertEqual(process(sim.data, 24), modes[2 % len(modes)])
        sim.data['skills']['design'] = 180
        sim.choose_job('designer')
        sim.schedule('工作')
        modes = CONTENT['jobs']['designer']['animations']
        self.assertEqual([process(sim.data, t) for t in (0, 12, 24)], [modes[i % len(modes)] for i in range(3)])
