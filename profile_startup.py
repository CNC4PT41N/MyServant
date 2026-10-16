"""Measure startup with an isolated copy of the save; no screen observation."""
import sys
import time
started = time.perf_counter()
import main
import tempfile
from pathlib import Path
from unittest.mock import patch
imports = time.perf_counter()-started
measurements = []


def timed(label, function):
    def run(*args, **kwargs):
        start = time.perf_counter()
        try:
            return function(*args, **kwargs)
        finally:
            measurements.append((label, time.perf_counter()-start))
    return run


with tempfile.TemporaryDirectory() as folder:
    path = Path(folder) / 'save.json'
    source = main.SAVE if main.SAVE.exists() else main.LEGACY_SAVE
    main.write(main.load(source), path)
    with patch.object(main, 'SAVE', path), patch.object(main, 'LEGACY_SAVE', path), \
         patch.object(main.ImageRenderer, 'select', timed('image load', main.ImageRenderer.select)), \
         patch.object(main.CharacterFile, 'read', timed('character config', main.CharacterFile.read)), \
         patch.object(main.Simulation, 'advance', timed('offline simulation', main.Simulation.advance)), \
         patch.object(main.Tray, '__init__', timed('tray', main.Tray.__init__)):
        start = time.perf_counter()
        app = main.App()
        app.root.update()
        total = time.perf_counter()-start
        app.close()
print('Python:', sys.executable)
print('imports: %.3fs' % imports)
for label in ('image load', 'character config', 'offline simulation', 'tray'):
    print('%s: %.3fs' % (label, sum(value for name, value in measurements if name == label)))
print('window startup: %.3fs' % total)
print('total including imports: %.3fs' % (total+imports))
