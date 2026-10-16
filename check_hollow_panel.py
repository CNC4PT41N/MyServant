"""Isolated GUI regression: fixed bounds, scrolling, input, saves and screenshots."""
from pathlib import Path
import queue
import tempfile
from unittest.mock import patch
import tkinter as tk
import time

from PIL import ImageGrab
import main
from storage import load


class QuietTray:
    def __init__(self):
        self.events = queue.Queue()

    def close(self):
        pass


def click(view, key):
    target = next(t for t in view.targets if t['key'] == key)
    assert target['enabled'], key
    cv = target['cv']
    if cv is view.body:
        cv.yview_moveto(max(0, target['y']-cv.winfo_height()/2)/(view.content_h*view.scale))
    cv.event_generate('<Button-1>', x=round(target['x']), y=round(target['y']-cv.canvasy(0)))
    view.app.root.update()


def run():
    output = Path('Saved/preview/panel-implemented').resolve()
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as folder:
        save = Path(folder)/'save.json'
        with patch.object(main, 'SAVE', save), patch.object(main, 'LEGACY_SAVE', save), patch.object(main, 'Tray', QuietTray):
            app = main.App()
            try:
                app.hide_character()
                app.show_panel()
                app.root.update()
                view = app.menu_view
                bounds = app.desktop.position(app.panel) + (app.panel.winfo_width(), app.panel.winfo_height())
                for page in ('修行', '收藏', '活动')*3:
                    click(view, 'tab-'+page)
                    assert app.desktop.position(app.panel)+(app.panel.winfo_width(), app.panel.winfo_height()) == bounds
                click(view, 'tab-修行')
                click(view, 'route-design')
                click(view, 'training-2')
                click(view, 'duration-8')
                click(view, 'start-training')
                assert app.sim.data['session']['title'] == '嚎叫幽灵'
                assert app.panel.state() == 'withdrawn'
                assert load(save)['plan_training'] == 2
                app.show_panel()
                click(view, 'tab-收藏')
                app.sim.data['money'] = 300
                view.refresh()
                click(view, 'item-old_bell')
                click(view, 'purchase')
                assert app.sim.data['money'] == 180
                assert load(save)['keepsakes'] == ['old_bell']
                click(view, 'collection-已收藏')
                assert [t['key'] for t in view.targets if t['key'].startswith('item-')] == ['item-old_bell']
                click(view, 'tab-活动')
                click(view, 'activity-探险')
                assert view.content_h > view.body_h
                # Keyboard navigation scrolls focused lower controls into view.
                view.focus_key = 'job-temp'
                view.navigate(type('Event', (), {'state': 0})(), 1)
                assert view.body.canvasy(0) > 0
                app.sim.data['skills']['design'] = 500
                view.refresh()
                click(view, 'job-independent')
                click(view, 'start-exploration')
                assert app.sim.data['plan_job'] == 'independent'
                assert app.sim.data['activity'] == '工作'
                app.show_panel()
                app.sim.data['last_result'] = '很长的成果记录' * 10
                app.refresh_panel()
                app.root.update()
                assert (app.panel.winfo_width(), app.panel.winfo_height()) == bounds[2:]
                app.sim.data['last_result'] = ''
                # Simulate 100%, 150%, 200% DPI and small work areas without
                # changing the user's OS setting. Only scroll viewport changes.
                for dpi in (96, 144, 192):
                    with patch.object(view, 'winfo_fpixels', return_value=dpi):
                        view.fit((0, 0, 1024, 768))
                        app.panel.geometry(f'{view.size[0]}x{view.size[1]}')
                        app.root.update()
                        size = view.size
                        assert size[0] <= 350 and size[1] <= 525, size
                        for page in ('活动', '修行', '收藏'):
                            view.switch_page(page)
                            app.root.update()
                            assert view.size == size
                            assert app.panel.winfo_width() == size[0]
                            assert app.panel.winfo_height() == size[1]
                            assert view.body.winfo_y()+view.body.winfo_height() < size[1]
                        view.switch_page('活动')
                        app.sim.data['last_result'] = ''
                        view.refresh()
                        for target in view.targets:
                            if target['key'].startswith(('activity-', 'duration-')):
                                assert target['y']-target['h']/2 >= 0, target['key']
                                assert target['y']+target['h']/2 <= view.body_h*view.scale, target['key']
                app.sim.free_activity()
                app.sim.data.update(money=240, hunger=30, energy=85, stress=10)
                view.choose_route('office')
                view.collection_tab = '寻觅'
                view.selected_item = 'folded_map'
                app.show_panel()
                width, height = view.size
                app.desktop.move(app.panel, 300, 80, width, height)
                for page, name in [('活动', 'activity'), ('修行', 'training'), ('收藏', 'collection')]:
                    view.switch_page(page)
                    app.panel.lift()
                    app.root.update()
                    time.sleep(.12)
                    ImageGrab.grab(bbox=(300, 80, 300+width, 80+height), all_screens=True).save(output/(name+'.png'))
                print('PASS: geometry, DPI, scrolling, mouse/keyboard, training, purchase and save reload')
                print('Screenshots:', output)
            finally:
                app.close()


if __name__ == '__main__':
    run()
