import tempfile
from pathlib import Path
from unittest.mock import patch
import main
from character_config import CharacterFile

with tempfile.TemporaryDirectory() as folder:
    path = Path(folder) / 'save.json'
    with patch.object(main, 'SAVE', path), patch.object(main, 'LEGACY_SAVE', path):
        app = main.App()
        app.root.update()
        assert not app.character_error, app.character_error
        assert app.character_config['name'] == '小骑士'
        assert app.image_renderer.config is not None
        expected_count = 81 if app.character_config.get('animation_style') == 'knight-frames-v3' else 88
        assert len(app.image_renderer.frames) == expected_count
        app.toggle_click_through()
        app.draw()
        assert app.desktop.is_click_through(app.root)
        app.show_character()
        app.draw()
        assert not app.desktop.is_click_through(app.root)
        assert len(app.image_renderer.frame_cache) <= 2
        for state, frames in app.image_renderer.frames.items():
            for index in range(len(frames)):
                frame = app.image_renderer.get_frame(state, index)
                assert 0 < frame.width <= 200 and 0 < frame.height <= 200
                assert frame.getchannel('A').getextrema()[0] == 0, state
        assert len(app.image_renderer.frame_cache) <= 24
        assert len(app.image_renderer.source_cache) <= 1
        for activity in main.ACTIVITY_NAMES:
            app.sim.data.update(activity=activity, hunger=20, energy=80)
            for edge in (None, 'left', 'right', 'top', 'bottom'):
                app.edge_pose = edge
                app.draw()
                item = app.canvas.find_withtag('custom_character')[0]
                bounds = app.canvas.bbox(item)
                # Tk's invisible rectangle includes a one-pixel hit-test margin,
                # even though the RGBA frame itself contacts the screen at 0.
                assert bounds[0] >= -1 and bounds[1] >= -1 and bounds[2] <= 221 and bounds[3] <= 241, (activity, edge, bounds)
                assert not app.canvas.find_withtag('caption')
                expected = main.ACTIVITY_NAMES  # Verify the internal activity selects its own frame.
                from character_config import STATES
                if edge:
                    from activity_content import process
                    mode = process(app.sim.data, app.motion_clock.phase)
                    candidate = f'process_{mode}_{edge}'
                    expected_state = candidate if candidate in app.image_renderer.frames else STATES[activity] + '_' + edge
                    assert app.image_renderer.current_state == expected_state
                else:
                    from activity_content import process
                    mode = process(app.sim.data, app.motion_clock.phase)
                    mode = {'draw': 'sketch', 'type': 'code'}.get(mode, mode)
                    expected_state = f'process_{mode}' if f'process_{mode}' in app.image_renderer.frames else STATES[activity]
                    assert app.image_renderer.current_state == expected_state
                surface = app.image_renderer.last_surface
                assert surface.mode == 'RGBA'
                assert surface.getpixel((0, 0))[3] == 0
                start = app.image_renderer.animation_started
                snapshots = set()
                for elapsed in (0., 1.3, 3.1, 12.1, 14.1, 17.5, 19.5, 21.5, 25.1, 28.5):
                    app.image_renderer.draw(app.canvas, app.sim.data, start+elapsed, main.ACTIVITY_NAMES, edge)
                    snapshots.add(app.image_renderer.last_surface.tobytes())
                assert len(snapshots) > 1, (activity, edge, 'no pose changes')
        assert len(app.image_renderer.motion_cache) <= 32
        assert app.image_renderer.alpha_window.buffer is not None
        app.close()
        assert app.image_renderer.alpha_window.buffer is None
print('Knight per-pixel alpha, activity loops, complete flying poses and edge selection passed')
