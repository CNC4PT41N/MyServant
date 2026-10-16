"""Synthetic OCR and UI verification, no real screen capture."""
import ctypes as c
from ctypes import wintypes as w
from pathlib import Path
import subprocess
import tempfile
import time
from unittest.mock import patch
from PIL import Image, ImageDraw, ImageFont
import main

with tempfile.TemporaryDirectory() as folder:
    path = Path(folder)
    sample = Image.new('RGB', (900, 160), 'white')
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 32)
    ImageDraw.Draw(sample).text((20, 30), 'Python function code programming', font=font, fill='black')
    sample.save(path / 'ocr.png')
    result = subprocess.run(['C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', str(Path('local_ocr.ps1').resolve()), str(path / 'ocr.png')], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=25, creationflags=0x08000000)
    assert result.returncode == 0, result.stderr.decode(errors='replace')
    assert 'python' in result.stdout.decode('utf-8-sig', errors='replace').lower(), result.stdout
    with patch.object(main, 'SAVE', path / 'save.json'), patch.object(main, 'LEGACY_SAVE', path / 'save.json'):
        app = main.App()
        app.root.update()
        app.assign('工作')
        app.sim.data['screen_feedback']['next_at'] = 1
        with patch.object(main, 'observe', return_value='document') as observation:
            app.poll_feedback()
            for _ in range(20):
                app.root.update()
                app.poll_feedback()
                if app.feedback_pose:
                    break
                time.sleep(.02)
            observation.assert_called_once()
        assert app.feedback_pose == 'look'
        assert app.bubble.state() == 'normal'
        assert app.sim.data['screen_feedback']['count'] == 1
        for edge in ('left', 'right', 'top', 'bottom'):
            app.edge_pose = edge
            app.draw()
            from activity_content import process
            mode = process(app.sim.data, app.motion_clock.phase)
            candidate = f'feedback_look_{edge}'
            assert app.image_renderer.current_state == (candidate if candidate in app.image_renderer.frames else 'work_' + edge)
        app.edge_pose = None
        app.draw()
        assert app.image_renderer.current_state == 'feedback_look'
        app.feedback_until = 1
        app.poll_feedback()
        assert app.bubble.state() == 'withdrawn'
        assert app.feedback_pose is None
        app.close()
print('Local Windows OCR, async feedback, bubble expiry and edge precedence passed')
