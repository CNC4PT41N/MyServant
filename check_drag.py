"""Drag precedence test using synthetic events, no real screen reading."""
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
from unittest.mock import patch
import main

with tempfile.TemporaryDirectory() as folder:
    path = Path(folder) / 'save.json'
    with patch.object(main, 'SAVE', path), patch.object(main, 'LEGACY_SAVE', path):
        app = main.App()
        app.root.update()
        app.assign('工作')
        previous_epoch = app.feedback_epoch
        x, y = app.desktop.position(app.root)
        app.sim.data['screen_feedback']['next_at'] = 1
        with patch.object(main, 'observe') as observation:
            app.drag_start(SimpleNamespace(x_root=x+110, y_root=y+100))
            app.poll_feedback()
            observation.assert_not_called()
            assert app.dragging
            assert app.observation_cancel.is_set()
            assert app.image_renderer.current_state == 'drag'
            area = app.desktop.work_area(x, y)
            app.drag(SimpleNamespace(x_root=area[0]+120, y_root=y+100))
            app.root.update()
            before = app.desktop.position(app.root)
            app.snap_character()
            assert app.desktop.position(app.root) == before
            app.poll_feedback()
            observation.assert_not_called()
            app.feedback_queue.put((previous_epoch, '工作', 'document'))
            app.sim.data['screen_feedback']['next_at'] = time.time()+10000
            app.drag_end(SimpleNamespace())
            app.root.update()
            app.poll_feedback()
            assert not app.dragging
            assert app.edge_pose == 'left'
            assert app.desktop.position(app.root)[0] == area[0]
            from activity_content import process
            candidate = 'process_' + process(app.sim.data, app.motion_clock.phase) + '_left'
            assert app.image_renderer.current_state == (candidate if candidate in app.image_renderer.frames else 'work_left')
            assert app.feedback_pose is None
            assert app.bubble.state() == 'withdrawn'
            assert app.sim.data['activity'] == '工作'
        app.image_renderer.config = None
        app.drag_start(SimpleNamespace(x_root=100, y_root=100))
        app.draw()
        assert app.canvas.find_withtag('drag')
        assert not app.canvas.find_withtag('laptop')
        app.drag_end(SimpleNamespace())
        app.close()
print('Drag pose priority, suppressed observation, stale-result discard and release snapping passed')
