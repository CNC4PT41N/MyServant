import json
from pathlib import Path
import tempfile
import unittest
from storage import load, write


class DesktopSettingsTests(unittest.TestCase):
    def test_old_desktop_migrates(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'save.json'
            old = {'x': 10, 'y': 20, 'edge': 'left', 'hidden': False, 'topmost': True}
            path.write_text(json.dumps({'desktop': old}), encoding='utf-8')
            data = load(path)
            self.assertFalse(data['desktop']['click_through'])
            data['desktop']['click_through'] = True
            write(data, path)
            self.assertTrue(load(path)['desktop']['click_through'])

    def test_clickthrough_requires_boolean(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'save.json'
            data = load(path)
            data['desktop']['click_through'] = 'yes'
            write(data, path)
            with self.assertRaises(ValueError):
                load(path)
