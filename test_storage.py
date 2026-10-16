import tempfile
import unittest
from pathlib import Path
from simulation import Simulation, HOUR
from storage import load, write


class StorageTests(unittest.TestCase):
    def test_edit_replace_and_resume_without_exit_save(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'save.json'
            sim = Simulation()
            sim.schedule('工作')
            write(sim.data, path)
            data = load(path)
            data['money'] = 500
            write(data, path)
            resumed = Simulation(load(path))
            resumed.advance(data['updated'] + 12 * HOUR)
            self.assertGreater(resumed.data['money'], 500)
            self.assertEqual(resumed.data['activity'], '自由活动')
            self.assertFalse(path.with_suffix('.tmp').exists())

    def test_invalid_edit_is_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'save.json'
            original = '{"hunger": 200}'
            path.write_text(original, encoding='utf-8')
            with self.assertRaises(ValueError):
                load(path)
            self.assertEqual(path.read_text(encoding='utf-8'), original)
