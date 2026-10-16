import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock
from PIL import Image
from character_config import CharacterFile
from character_images import ImageRenderer
from knight_animation import frame_index, motion_kind, static_offset, rig_phase
from simulation import Simulation
from knight_rig import deform, joint_offsets


class KnightAnimationTests(unittest.TestCase):
    def test_v3_held_poses_have_visible_motion_at_desktop_size(self):
        config = CharacterFile().read()
        if config.get('animation_style') != 'knight-frames-v3':
            self.skipTest('Custom external character')
        from PIL import ImageChops
        for state, specs in config['files'].items():
            edge = next((side for side in ('left', 'right', 'top', 'bottom') if state.endswith('_'+side)), None)
            with Image.open(specs[0]['image']) as source:
                image = source.convert('RGBA')
            frames = []
            for phase in (.25, .75):
                frame = Image.new('RGBA', image.size, '#e1e5e9')
                frame.alpha_composite(deform(image, 'micro', phase, edge, motion_kind(state)))
                frames.append(frame.convert('RGB'))
            # Count visible differences after alpha composition, rather than
            # tiny byte changes or RGB hidden in fully transparent pixels.
            visible = sum(max(pixel) >= 12 for pixel in ImageChops.difference(*frames).getdata())
            self.assertGreater(visible, 80, (state, visible))

    def test_v3_shell_matches_idle_scale_and_retains_micro_motion(self):
        config = CharacterFile().read()
        if config.get('animation_style') != 'knight-frames-v3':
            self.skipTest('Custom external character')
        from build_knight_v3 import head_geometry
        with Image.open(config['files']['idle'][0]['image']) as standing:
            reference = head_geometry(standing)[1]
        self.assertTrue(config.get('micro_motion'))
        for state in ('relax', 'process_shell', 'process_shell_left', 'process_shell_right', 'process_shell_bottom'):
            for spec in config['files'][state]:
                with Image.open(spec['image']) as frame:
                    self.assertLessEqual(abs(head_geometry(frame)[1]-reference), 2)
        # During the long held keyframe the cloth still changes locally, with
        # no translation or change of contact at any window border.
        with Image.open(config['files']['process_shell'][0]['image']) as source:
            image = source.convert('RGBA')
        for edge in (None, 'left', 'right', 'top', 'bottom'):
            phases = [deform(image, 'micro', n/32, edge) for n in range(32)]
            self.assertGreater(len({frame.tobytes() for frame in phases}), 16)
            for frame in phases:
                self.assertEqual(frame.size, image.size)
                for box in ((0,0,image.width,1), (0,image.height-1,image.width,image.height),
                            (0,0,1,image.height), (image.width-1,0,image.width,image.height)):
                    self.assertEqual(frame.crop(box).tobytes(), phases[0].crop(box).tobytes())

    def test_v3_drag_preserves_standing_character_scale(self):
        config = CharacterFile().read()
        if config.get('animation_style') != 'knight-frames-v3':
            self.skipTest('Custom external character')
        from build_knight_v3 import head_geometry
        with Image.open(config['files']['idle'][0]['image']) as standing:
            reference = head_geometry(standing)[1]
        for spec in config['files']['drag']:
            with Image.open(spec['image']) as frame:
                self.assertLessEqual(abs(head_geometry(frame)[1]-reference), 3)
                self.assertLessEqual(frame.height, 200)

    def test_screen_contacts_follow_visible_pixels_and_drag_ignores_edges(self):
        sim = Simulation()
        renderer = ImageRenderer.__new__(ImageRenderer)
        renderer.config = {'fps': 6, 'screen_contacts': True}
        renderer.frames = {state: [None] for state in ('idle', 'drag', 'idle_left', 'idle_right', 'idle_top', 'idle_bottom')}
        image = Image.new('RGBA', (80, 90))
        from PIL import ImageDraw
        ImageDraw.Draw(image).rectangle((11, 7, 67, 76), fill='white')
        renderer.get_frame = lambda *args: image
        renderer.alpha_window = MagicMock()
        renderer.last_canvas_frame = None
        for edge in ('left', 'right', 'top', 'bottom'):
            renderer.draw(MagicMock(), sim.data, 0, {}, edge)
            bounds = renderer.last_surface.getbbox()
            index, expected = {'left': (0, 0), 'right': (2, 220), 'top': (1, 0), 'bottom': (3, 240)}[edge]
            self.assertEqual(bounds[index], expected)
            renderer.draw(MagicMock(), sim.data, 1, {}, edge, 'look', True)
            self.assertEqual(renderer.current_state, 'drag')
            self.assertEqual(renderer.last_surface.getbbox(), (81, 126, 138, 196))

    def test_quiet_pause_prevents_repetitive_fast_motion(self):
        config = {'fps': 6, 'animation_style': 'knight-frames'}
        self.assertEqual(motion_kind('process_nail_right'), 'nail')
        self.assertEqual(frame_index('process_nail_right', 16.9, 4, config), 0)
        self.assertEqual(frame_index('process_nail_right', 17.1, 4, config), 1)
        self.assertEqual(frame_index('process_nail_right', 18.1, 4, config), 2)
        self.assertEqual(frame_index('process_nail_right', 19.1, 4, config), 3)
        self.assertEqual(frame_index('process_nail_right', 20.21, 4, config), 0)
        config['frame_sequences'] = {'process_nail_right': [0, 1, 3, 0]}
        self.assertEqual(frame_index('process_nail_right', 18.1, 4, config), 3)
        self.assertEqual(rig_phase('nail', 15, config), 0)
        self.assertGreater(rig_phase('nail', 20, config), 0)

    def test_external_frame_timings_are_validated(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            Image.new('RGBA', (40, 50)).save(path / 'sprite.png')
            file = CharacterFile(path / 'character.json')
            config = file.default()
            config.update(renderer='images', states={'idle': ['sprite.png'] * 4},
                          timings={'idle': [2., .3, .4, .5]})
            file.write(config)
            self.assertEqual(file.read()['timings']['idle'], [2., .3, .4, .5])
            for invalid in ([1], [0, 1, 1, 1], [True, 1, 1, 1], [float('inf')] * 4):
                config['timings']['idle'] = invalid
                if invalid[0] == float('inf'):
                    file.path.write_text(json.dumps(config), encoding='utf-8')
                else:
                    file.write(config)
                with self.assertRaises(ValueError):
                    file.read()

    def test_each_pose_starts_at_frame_zero_and_does_not_rotate(self):
        sim = Simulation()
        renderer = ImageRenderer.__new__(ImageRenderer)
        renderer.config = {'fps': 6, 'animation_style': 'knight-frames', 'motion': True}
        renderer.frames = {state: list(range(4)) for state in ('idle', 'sleep', 'drag')}
        image = Image.new('RGBA', (60, 80), 'white')
        calls = []
        def get_frame(state, index):
            calls.append((state, index))
            return image
        renderer.get_frame = get_frame
        renderer.alpha_window = MagicMock()
        renderer.last_canvas_frame = None
        canvas = MagicMock()
        renderer.draw(canvas, sim.data, 100, {})
        self.assertEqual(calls[-1], ('idle', 0))
        initial = renderer.last_surface.getbbox()
        renderer.draw(canvas, sim.data, 118.1, {})
        self.assertEqual(calls[-1], ('idle', 1))
        self.assertEqual(renderer.last_surface.getbbox(), initial)
        sim.data['activity'] = '睡眠'
        renderer.draw(canvas, sim.data, 119, {}, 'top')
        self.assertEqual(calls[-1], ('sleep', 0))
        renderer.draw(canvas, sim.data, 119.1, {}, 'top', dragging=True)
        self.assertEqual(calls[-1], ('drag', 0))

    def test_single_frame_legacy_breath_is_at_most_one_pixel(self):
        self.assertTrue(all(abs(static_offset('idle', i / 10)[1]) <= 1 for i in range(100)))

    def test_rig_changes_local_artwork_without_moving_contact_border(self):
        image = Image.new('RGBA', (180, 184))
        from PIL import ImageDraw
        draw = ImageDraw.Draw(image)
        draw.rectangle((40, 0, 135, 16), fill='white')
        draw.rectangle((42, 35, 55, 165), fill='#5c6c89')
        draw.rectangle((100, 90, 155, 125), fill='white')
        draw.rectangle((50, 170, 120, 183), fill='white')
        first = deform(image, 'battle', 0, 'top')
        second = deform(image, 'battle', .375, 'top')
        self.assertNotEqual(first.tobytes(), second.tobytes())
        self.assertEqual(first.crop((0, 0, 180, 20)).tobytes(), second.crop((0, 0, 180, 20)).tobytes())
        self.assertEqual(first.getpixel((0, 0)), (0, 0, 0, 0))
        self.assertNotEqual(joint_offsets('eat', .25), joint_offsets('sleep', .25))

    def test_active_knight_avoids_extra_arm_assets_and_busy_wing_frames(self):
        config = CharacterFile().read()
        if config.get('animation_style') == 'knight-frames-v3':
            self.assertEqual(len(config['files']), 81)
            self.assertTrue(config['screen_contacts'])
            self.assertFalse(config.get('rigs'))
            self.assertFalse(config.get('flying_states'))
            self.assertNotIn('monarch_wings', config['files'])
            for state in ('process_soul_top', 'process_explore_top', 'process_shell_top', 'process_nail_top', 'process_battle_top', 'eat_top', 'sleep_top'):
                self.assertTrue(all('animation-v3' in str(frame['image']) for frame in config['files'][state]))
                self.assertGreaterEqual(sum(config['timings'][state]), 24)
            return
        if config.get('animation_style') != 'knight-frames':
            self.skipTest('Custom external character')
        for state in ('process_soul_top', 'process_explore_top', 'process_shell_top', 'process_nail_top', 'process_battle_top'):
            self.assertIn(state, config['flying_states'])
            self.assertTrue(all(frame['image'].name == 'normal.png' for frame in config['files'][state]))
        self.assertTrue(all(frame['image'].name == 'top-supported.png' for frame in config['files']['eat_top']))
        self.assertNotIn('eat_top', config['flying_states'])
        self.assertNotIn('sleep_top', config['flying_states'])
        self.assertEqual(config['frame_sequences']['monarch_wings'], [0, 2, 3, 0])
        self.assertGreaterEqual(sum(config['timings']['monarch_wings']), 25)
        self.assertGreaterEqual(min(config['timings']['monarch_wings']), 1.5)
