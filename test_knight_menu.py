import copy
import json
from pathlib import Path
import tempfile
import unittest

from activity_content import process
from knight_collection import KEEPSAKES
from progression import TRAINING, learning_title
from simulation import Simulation, HOUR
from storage import load, write


class KnightMenuTests(unittest.TestCase):
    def test_training_choice_is_snapshotted_for_running_session(self):
        sim = Simulation()
        self.assertTrue(sim.choose_training('office', 2))
        sim.schedule('学习', 4)
        self.assertEqual(sim.data['session']['title'], '强力劈砍')
        sim.choose_training('design', 1)
        self.assertEqual(learning_title(sim.data, planned=True), '强力劈砍')
        self.assertEqual(process(sim.data, 0), 'nail')
        sim.schedule('学习', 4)
        self.assertEqual(sim.data['session']['title'], '荒芜俯冲')
        self.assertEqual(process(sim.data, 0), 'soul')

    def test_selected_spell_and_results_survive_restart(self):
        sim = Simulation()
        sim.choose_training('design', 2)
        sim.schedule('学习', 8)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'save.json'
            write(sim.data, path)
            restored = Simulation(load(path))
            self.assertEqual(learning_title(restored.data, planned=True), '嚎叫幽灵')
            restored.advance(restored.data['updated'] + 24*HOUR)
            self.assertEqual(restored.data['works'], {'嚎叫幽灵心得': 1})

    def test_invalid_training_does_not_change_selection(self):
        sim = Simulation()
        before = copy.deepcopy(sim.data)
        for route, value in [('bad', 0), ('office', -1), ('design', 3), ('tech', True)]:
            self.assertFalse(sim.choose_training(route, value))
            self.assertEqual(sim.data, before)

    def test_collection_purchase_is_atomic_and_separate_from_equipment(self):
        sim = Simulation()
        self.assertFalse(sim.collect_keepsake('folded_map'))
        self.assertFalse(sim.collect_keepsake('unknown'))
        sim.data['money'] = 100
        self.assertTrue(sim.collect_keepsake('folded_map'))
        self.assertFalse(sim.collect_keepsake('folded_map'))
        self.assertEqual(sim.data['money'], 40)
        self.assertEqual(sim.data['owned'], [])
        self.assertEqual(sim.data['keepsakes'], ['folded_map'])
        self.assertEqual(sim.data['appearance'], {'palette': None, 'accessory': None})
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'save.json'
            write(sim.data, path)
            self.assertEqual(load(path)['keepsakes'], ['folded_map'])

    def test_legacy_save_preserves_items_and_running_course(self):
        sim = Simulation()
        sim.data['owned'] = ['books', 'bed', 'mint']
        sim.data['appearance']['palette'] = 'mint'
        sim.schedule('学习')
        original = sim.data['session']['title']
        for key in ('training_choice', 'plan_training', 'keepsakes'):
            del sim.data[key]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'save.json'
            write(sim.data, path)
            restored = load(path)
            self.assertEqual(restored['owned'], ['books', 'bed', 'mint'])
            self.assertEqual(restored['appearance']['palette'], 'mint')
            self.assertEqual(restored['session']['title'], original)
            self.assertIsNone(restored['plan_training'])
            self.assertEqual(restored['keepsakes'], [])

    def test_invalid_new_save_fields_are_rejected_without_overwriting(self):
        for key, value in [('keepsakes', ['folded_map', 'folded_map']),
                           ('keepsakes', [{}]), ('plan_training', 3),
                           ('training_choice', {'office': True, 'tech': None, 'design': None})]:
            sim = Simulation()
            sim.data[key] = value
            with tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / 'save.json'
                write(sim.data, path)
                before = path.read_bytes()
                with self.assertRaises(ValueError):
                    load(path)
                self.assertEqual(path.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
