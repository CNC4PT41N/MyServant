import json
from pathlib import Path
import tempfile
import unittest
from character_config import CharacterFile
from storage import load


class CharacterConfigTests(unittest.TestCase):
    def test_first_app_launch_uses_current_knight(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder)/'character.json'
            with patch('character_config.CHARACTER', target):
                CharacterFile()
            config = json.loads(target.read_text(encoding='utf-8'))
            self.assertEqual(config['renderer'], 'images')
            self.assertEqual(config['animation_style'], 'knight-frames-v3')
            self.assertTrue(config['micro_motion'])
            self.assertIn('process_shell_top', config['states'])

    def test_default_and_rename_preserves_shape(self):
        with tempfile.TemporaryDirectory() as folder:
            cf = CharacterFile(Path(folder) / 'character.json')
            config = cf.default()
            config['color'] = '#556677'
            cf.write(config)
            cf.rename(' Alex ')
            self.assertEqual(cf.read()['name'], 'Alex')
            self.assertEqual(cf.read()['color'], '#556677')

    def test_invalid_file_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            cf = CharacterFile(Path(folder) / 'character.json')
            cf.path.write_text('{broken', encoding='utf-8')
            with self.assertRaises(ValueError):
                cf.rename('Alex')
            self.assertEqual(cf.path.read_text(encoding='utf-8'), '{broken')

    def test_image_paths_and_missing_states(self):
        with tempfile.TemporaryDirectory() as folder:
            cf = CharacterFile(Path(folder) / 'character.json')
            config = cf.default()
            config.update(renderer='images', states={'idle': ['avatar.png']})
            (Path(folder) / 'avatar.png').write_bytes(b'image')
            cf.write(config)
            self.assertEqual(list(cf.read()['files']), ['idle'])
            config['states'] = {'idle': ['../outside.png']}
            cf.write(config)
            with self.assertRaises(ValueError):
                cf.read()

    def test_legacy_selection_removed_without_losing_progress(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'save.json'
            path.write_text(json.dumps({'character': 'sample', 'money': 345}), encoding='utf-8')
            data = load(path)
            self.assertNotIn('character', data)
            self.assertEqual(data['money'], 345)

    def test_name_validation(self):
        with tempfile.TemporaryDirectory() as folder:
            cf = CharacterFile(Path(folder) / 'character.json')
            for name in ('', '  ', 'a'*21, 'A\nB'):
                with self.assertRaises(ValueError):
                    cf.rename(name)
