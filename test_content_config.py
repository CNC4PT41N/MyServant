import copy
import json
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest
from content_config import ROOT, read_content


class ContentConfigTests(unittest.TestCase):
    def test_both_versions_load(self):
        standard = read_content(ROOT / 'activities-default.json')
        themed = read_content(ROOT / 'activities-hollow-knight.json')
        self.assertEqual(themed['routes']['office']['name'], '骨钉')
        self.assertEqual(themed['jobs']['tester']['animations'], ['flower'])
        self.assertEqual(set(standard['jobs']), set(themed['jobs']))

    def test_external_values_reach_simulation(self):
        config = read_content(ROOT / 'activities-default.json')
        config['jobs']['temp']['income'] = 75
        config['experience_rates'][0] = 13
        config['routes']['office']['courses'][0] = '外部课程'
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'activities.json'
            path.write_text(json.dumps(config), encoding='utf-8')
            environment = os.environ.copy()
            environment['MYSERVANT_CONTENT_FILE'] = str(path)
            code = "from simulation import Simulation; from progression import COURSES; s=Simulation(); s.schedule('工作'); s.tick(1); assert s.data['money']>70; s.schedule('学习'); s.tick(1); assert s.data['session']['xp']>10; assert COURSES['office'][0]=='外部课程'"
            result = subprocess.run([sys.executable, '-c', code], env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_invalid_config_preserved(self):
        data = read_content(ROOT / 'activities-default.json')
        data['jobs']['temp']['income'] = -100
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'activities.json'
            source = json.dumps(data)
            path.write_text(source, encoding='utf-8')
            with self.assertRaises(ValueError):
                read_content(path)
            self.assertEqual(path.read_text(encoding='utf-8'), source)

    def test_new_jobs_allowed_without_renaming_old_ids(self):
        data = read_content(ROOT / 'activities-default.json')
        data['jobs']['custom'] = copy.deepcopy(data['jobs']['temp'])
        data['jobs']['custom']['name'] = '自定义委托'
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'activities.json'
            path.write_text(json.dumps(data), encoding='utf-8')
            self.assertIn('custom', read_content(path)['jobs'])
