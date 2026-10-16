"""Native tray integration smoke check, using an isolated save."""
import ctypes as c
import tempfile
from pathlib import Path
from unittest.mock import patch
import main

with tempfile.TemporaryDirectory() as folder:
    path = Path(folder) / 'save.json'
    with patch.object(main, 'SAVE', path), patch.object(main, 'LEGACY_SAVE', path), patch('character_config.CHARACTER', Path(folder) / 'character.json'):
        app = main.App()
        app.root.update()
        assert app.tray.window and app.tray.icon
        app.assign('工作')
        app.hide_character()
        assert app.root.state() == 'withdrawn'
        app.sim.advance(app.sim.data['updated'] + 3600)
        assert app.sim.data['money'] > 0
        app.save()
        assert main.load(path)['money'] > 0
        # Exercise the actual native callback through the Windows message pump.
        app.tray.user.PostMessageW(app.tray.window, 0x8001, 1, 0x202)
        app.root.update()
        app.handle_tray_events()
        assert app.root.state() == 'normal'
        for ident, action in [(1, 'hide'), (2, 'panel'), (3, 'quit')]:
            with patch.object(app.tray.user, 'TrackPopupMenu', return_value=ident):
                app.tray.popup()
            app.handle_tray_events()
            if action == 'hide':
                assert app.tray.hidden
            elif action == 'panel':
                assert not app.tray.hidden
                app.root.update()
                assert app.panel.state() == 'normal'
            else:
                assert app.closed and app.tray.window is None and app.tray.icon is None
print('Native icon, click callback, tray menu, hidden progress and cleanup passed')
