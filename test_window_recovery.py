from unittest import TestCase
from unittest.mock import MagicMock, patch
import tempfile
from pathlib import Path
from PIL import Image

from alpha_window import LayeredWindowError
from character_config import CharacterFile
from character_images import ImageRenderer
from main import App
from simulation import Simulation


class WindowRecoveryTests(TestCase):
    def make_app(self):
        app = App.__new__(App)
        app.closed = False
        app.instance = None
        app.root = MagicMock()
        app.panel = MagicMock()
        app.panel.winfo_viewable.return_value = False
        app.sim = Simulation()
        app.tray = MagicMock()
        app.tray.hidden = False
        app.dragging = False
        app.desktop = MagicMock()
        app.desktop.ensure_visible.return_value = False
        app.image_renderer = MagicMock()
        app.last_visibility_check = 0
        app.last_disk_check = float('inf')
        app.last_save = float('inf')
        for name in ('handle_tray_events', 'poll_feedback', 'snap_character', 'draw'):
            setattr(app, name, MagicMock())
        return app

    def test_window_checks_never_restore_an_intentionally_hidden_pet(self):
        app = self.make_app()
        app.tray.hidden = True
        app.update()
        app.desktop.ensure_visible.assert_not_called()
        app.draw.assert_not_called()
        app.root.after.assert_called_once_with(1000, app.update)

    def test_unexpected_native_hide_invalidates_pixels_and_draws(self):
        app = self.make_app()
        app.desktop.ensure_visible.return_value = True
        app.update()
        app.image_renderer.alpha_window.invalidate.assert_called_once()
        app.draw.assert_called_once()
        app.root.after.assert_called_once()

    def test_frame_timer_survives_a_failed_monitor_query(self):
        app = self.make_app()
        app.desktop.ensure_visible.side_effect = OSError('monitor temporarily unavailable')
        with patch('main.record_error') as log:
            app.update()
        log.assert_called_once()
        app.root.after.assert_called_once()
        app.desktop.ensure_visible.side_effect = None
        app.update()
        app.draw.assert_called_once()
        self.assertEqual(app.root.after.call_count, 2)

    def test_timer_survives_unexpected_callback_error_too(self):
        app = self.make_app()
        app.poll_feedback.side_effect = RuntimeError('test callback')
        with self.assertRaises(RuntimeError):
            app.update()
        app.root.after.assert_called_once()

    def test_transient_upload_failure_does_not_unload_character(self):
        app = self.make_app()
        app.motion_clock = MagicMock()
        app.edge_pose = None
        app.feedback_pose = None
        app.canvas = MagicMock()
        app.image_renderer.draw.side_effect = LayeredWindowError('test compositor reset')
        with patch('main.record_error'):
            App.draw(app)
        app.image_renderer.unload.assert_not_called()
        app.image_renderer.draw.side_effect = None
        App.draw(app)
        self.assertEqual(app.image_renderer.draw.call_count, 2)


class LazyImageStartupTests(TestCase):
    def test_startup_opens_only_the_first_idle_image_then_checks_later_frames(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            Image.new('RGBA', (80, 100), 'white').save(root / 'idle.png')
            Image.new('RGBA', (90, 110), 'white').save(root / 'study.png')
            file = CharacterFile(root / 'character.json')
            config = file.default()
            config.update(renderer='images', states={'idle': ['idle.png']*4, 'study': ['study.png']*4})
            file.write(config)
            with patch('character_images.AlphaWindow'):
                renderer = ImageRenderer(MagicMock())
            with patch('character_images.Image.open', wraps=Image.open) as opened:
                renderer.select(file.read())
                self.assertEqual(opened.call_count, 1)
                renderer.get_frame('study', 0)
                self.assertEqual(opened.call_count, 2)
            self.assertEqual(renderer.get_frame('study', 0).size, (90, 110))

    def test_invalid_idle_replacement_keeps_the_previous_character(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            Image.new('RGBA', (80, 100), 'white').save(root / 'idle.png')
            file = CharacterFile(root / 'character.json')
            config = file.default()
            config.update(renderer='images', states={'idle': ['idle.png']})
            file.write(config)
            good = file.read()
            with patch('character_images.AlphaWindow'):
                renderer = ImageRenderer(MagicMock())
            renderer.select(good)
            (root / 'broken.png').write_bytes(b'not an image')
            config['states']['idle'] = ['broken.png']
            file.write(config)
            with self.assertRaises(OSError):
                renderer.select(file.read())
            self.assertIs(renderer.config, good)
            self.assertEqual(renderer.get_frame('idle', 0).size, (80, 100))
