import tempfile
import unittest
from pathlib import Path
from simulation import Simulation, HOUR
from storage import load, write


class ProgressionTests(unittest.TestCase):
    def test_job_requires_matching_skill(self):
        s = Simulation()
        self.assertFalse(s.choose_job('tester'))
        s.data['skills']['office'] = 1000
        self.assertFalse(s.choose_job('tester'))
        s.data['skills']['tech'] = 60
        self.assertTrue(s.choose_job('tester'))

    def test_study_unlocks_job_without_affecting_current_plan(self):
        s = Simulation()
        s.data.update(study='tech', hunger=0, energy=100, stress=0)
        s.data['skills']['tech'] = 30
        s.schedule('学习')
        s.data['study'] = 'design'
        s.advance(s.data['updated'] + 10 * HOUR)
        self.assertGreater(s.data['skills']['tech'], 60)
        self.assertEqual(s.data['skills']['design'], 0)
        self.assertTrue(s.choose_job('tester'))

    def test_purchase_is_single_and_does_not_overdraw(self):
        s = Simulation()
        self.assertFalse(s.buy('books'))
        s.data['money'] = 200
        self.assertTrue(s.buy('books'))
        self.assertFalse(s.buy('books'))
        self.assertEqual(s.data['money'], 80)
        self.assertEqual(s.data['owned'], ['books'])

    def test_equipment_and_profession_increase_rewards(self):
        base, upgraded = Simulation(), Simulation()
        for s in (base, upgraded):
            s.data.update(hunger=0, energy=100, stress=0)
        upgraded.data['owned'] = ['books', 'computer']
        for s in (base, upgraded):
            s.schedule('学习')
            s.advance(s.data['updated'] + HOUR)
        self.assertGreater(upgraded.data['xp'], base.data['xp'])
        upgraded.data['skills']['office'] = 180
        upgraded.choose_job('admin')
        for s in (base, upgraded):
            s.schedule('工作')
            s.advance(s.data['updated'] + HOUR)
        self.assertGreater(upgraded.data['money'], base.data['money'] * 2)

    def test_old_save_migrates_and_new_fields_roundtrip(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'save.json'
            path.write_text('{"xp": 123, "activity": "自主管理"}', encoding='utf-8')
            data = load(path)
            self.assertEqual(data['skills']['office'], 123)
            self.assertEqual(data['activity'], '自由活动')
            s = Simulation(data)
            s.choose_job('clerk')
            s.data['money'] = 500
            s.buy('computer')
            write(s.data, path)
            restored = load(path)
            self.assertEqual(restored['job'], 'clerk')
            self.assertEqual(restored['owned'], ['computer'])

    def test_recovery_equipment_has_effect(self):
        base, upgraded = Simulation(), Simulation()
        upgraded.data['owned'] = ['bed', 'headphones']
        for s in (base, upgraded):
            s.data.update(energy=20, stress=90)
            s.schedule('睡眠')
            s.advance(s.data['updated'] + HOUR)
        self.assertGreater(upgraded.data['energy'], base.data['energy'])
        for s in (base, upgraded):
            s.schedule('休闲')
            s.advance(s.data['updated'] + HOUR)
        self.assertLess(upgraded.data['stress'], base.data['stress'])
