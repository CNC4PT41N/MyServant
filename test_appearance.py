import tempfile
import unittest
from pathlib import Path
from simulation import Simulation, HOUR
from storage import load, write


class AppearanceTests(unittest.TestCase):
    def test_purchase_equip_switch_and_remove(self):
        s = Simulation()
        self.assertFalse(s.equip('mint'))
        s.data['money'] = 500
        self.assertTrue(s.buy('mint'))
        self.assertEqual(s.data['appearance']['palette'], 'mint')
        s.buy('graphite')
        s.buy('cap')
        balance = s.data['money']
        self.assertTrue(s.equip('mint'))
        self.assertFalse(s.buy('mint'))
        self.assertEqual(s.data['money'], balance)
        self.assertEqual(s.data['appearance'], {'palette': 'mint', 'accessory': 'cap'})
        self.assertTrue(s.unequip('accessory'))
        self.assertIsNone(s.data['appearance']['accessory'])

    def test_cosmetics_have_no_stat_effect(self):
        plain, decorated = Simulation(), Simulation()
        decorated.data['owned'] = ['mint', 'cap']
        decorated.equip('mint')
        decorated.equip('cap')
        for s in (plain, decorated):
            s.schedule('工作')
            s.advance(s.data['updated'] + HOUR)
        for key in ('money', 'xp', 'hunger', 'energy', 'stress'):
            self.assertAlmostEqual(plain.data[key], decorated.data[key])

    def test_roundtrip_and_invalid_appearance(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'save.json'
            s = Simulation()
            s.data['money'] = 100
            s.buy('glasses')
            write(s.data, path)
            self.assertEqual(load(path)['appearance']['accessory'], 'glasses')
            s.data['appearance']['palette'] = 'glasses'
            write(s.data, path)
            with self.assertRaises(ValueError):
                load(path)

    def test_old_appearance_defaults(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'save.json'
            path.write_text('{"money": 50}', encoding='utf-8')
            self.assertEqual(load(path)['appearance'], {'palette': None, 'accessory': None})
