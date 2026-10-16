import json
from pathlib import Path
import tempfile
import unittest
from panel_style import read_style, ROOT


class PanelStyleTests(unittest.TestCase):
    def test_both_styles_and_editable_values(self):
        for name in ('panel-default.json', 'panel-hollow-knight.json'):
            self.assertIn('colors', read_style(ROOT / name))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'panel.json'
            path.write_text(json.dumps({'font_size': 11, 'colors': {'surface': '#abcdef'}}), encoding='utf-8')
            style = read_style(path)
            self.assertEqual(style['colors']['surface'], '#abcdef')
            self.assertEqual(style['font_size'], 11)
            self.assertIn('text', style['colors'])
        self.assertEqual(read_style(ROOT / 'panel-hollow-knight.json')['layout'], 'hollow')

    def test_invalid_color_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'panel.json'
            original = '{"colors":{"surface":"not-a-color"}}'
            path.write_text(original, encoding='utf-8')
            with self.assertRaises(ValueError):
                read_style(path)
            self.assertEqual(path.read_text(encoding='utf-8'), original)
