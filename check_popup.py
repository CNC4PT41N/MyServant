"""Manual GUI smoke check using isolated saves, at several font scales."""
import tempfile
from pathlib import Path
from unittest.mock import patch
import main

with tempfile.TemporaryDirectory() as folder:
    with patch.object(main, 'SAVE', Path(folder) / 'save.json'), patch.object(main, 'LEGACY_SAVE', Path(folder) / 'save.json'), patch('character_config.CHARACTER', Path(folder) / 'character.json'):
        app = main.App()
        assert app.panel.state() == 'withdrawn'
        for scale in (1.33, 2.0, 2.67):
            app.root.tk.call('tk', 'scaling', scale)
            app.show_panel()
            app.root.update()
            right = app.panel.winfo_rootx() + app.panel.winfo_width()
            bottom = app.panel.winfo_rooty() + app.panel.winfo_height()
            for button in app.action_buttons:
                assert button.winfo_viewable()
                assert button.winfo_rootx() + button.winfo_width() <= right
                assert button.winfo_rooty() + button.winfo_height() <= bottom
            assert app.panel.overrideredirect()
            for page in ('成长', '商店', '活动'):
                app.switch_page(page)
                app.root.update()
                bottom = app.panel.winfo_rooty() + app.panel.winfo_height()
                controls = list(app.job_buttons.values()) if page == '成长' else list(app.shop_buttons.values()) if page == '商店' else app.action_buttons
                for button in controls:
                    assert button.winfo_viewable()
                    assert button.winfo_rooty() + button.winfo_height() <= bottom
                if page == '商店':
                    for category in ('外观', '设备'):
                        app.change_category(category)
                        app.root.update()
                        bottom = app.panel.winfo_rooty() + app.panel.winfo_height()
                        for button in app.shop_buttons.values():
                            assert button.winfo_viewable()
                            assert button.winfo_rooty() + button.winfo_height() <= bottom
        app.sim.data['money'] = 500
        app.switch_page('商店')
        app.purchase('books')
        assert app.shop_buttons['books'].cget('text') == '已拥有'
        app.choose_route('tech')
        assert app.sim.data['study'] == 'tech'
        assert app.job_buttons['tester'].cget('state') == 'disabled'
        app.assign('学习')
        assert app.panel.state() == 'withdrawn'
        app.sim.data['money'] = 500
        app.switch_page('商店')
        app.change_category('外观')
        app.purchase('mint')
        assert app.shop_buttons['mint'].cget('text') == '使用中'
        app.reset_slot('palette')
        assert app.shop_buttons['mint'].cget('text') == '使用'
        app.purchase('mint')
        app.purchase('glasses')
        from character import draw_character
        data = app.sim.data
        data['session'] = None  # Rendering checks below set activities directly.
        for activity, prop in [('工作', 'laptop'), ('学习', 'book'), ('进食', 'bowl'), ('睡眠', 'bed'), ('休闲', 'chair'), ('自由活动', 'body')]:
            data.update(activity=activity, hunger=20, energy=80)
            draw_character(app.canvas, data, 0, main.ACTIVITY_NAMES)
            assert app.canvas.find_withtag(prop)
            if activity == '工作':
                assert app.canvas.find_withtag('profile')
            assert app.canvas.find_withtag('accessory')
            initial = [app.canvas.coords(i) for i in app.canvas.find_all()]
            draw_character(app.canvas, data, 1, main.ACTIVITY_NAMES)
            assert initial != [app.canvas.coords(i) for i in app.canvas.find_all()]
            for item in app.canvas.find_all():
                bounds = app.canvas.bbox(item)
                assert bounds[0] >= 0 and bounds[1] >= 0 and bounds[2] <= 220 and bounds[3] <= 240
        for edge in ('left', 'right', 'top', 'bottom'):
            for activity in main.ACTIVITY_NAMES:
                data.update(activity=activity, hunger=20, energy=80)
                draw_character(app.canvas, data, 0, main.ACTIVITY_NAMES, '#e7edf3', edge)
                assert app.canvas.find_withtag(f'edge_{edge}')
                assert not app.canvas.find_withtag('chair')
                assert not app.canvas.find_withtag('caption')
                prop = {'工作': 'laptop', '学习': 'book', '进食': 'bowl', '睡眠': 'sleep'}.get(activity)
                if prop:
                    assert app.canvas.find_withtag(prop)
                positions = [app.canvas.coords(i) for i in app.canvas.find_all()]
                draw_character(app.canvas, data, 1, main.ACTIVITY_NAMES, '#e7edf3', edge)
                assert positions != [app.canvas.coords(i) for i in app.canvas.find_all()]
                for item in app.canvas.find_all():
                    bounds = app.canvas.bbox(item)
                    assert bounds[0] >= 0 and bounds[1] >= 0 and bounds[2] <= 220 and bounds[3] <= 240, (edge, bounds)
            data['appearance']['accessory'] = 'cap'
            data['owned'] = list(set(data['owned'] + ['cap', 'headphones', 'bed']))
            for activity in main.ACTIVITY_NAMES:
                data['activity'] = activity
                draw_character(app.canvas, data, 1, main.ACTIVITY_NAMES, '#e7edf3', edge)
                for item in app.canvas.find_all():
                    bounds = app.canvas.bbox(item)
                    assert bounds[0] >= 0 and bounds[1] >= 0 and bounds[2] <= 220 and bounds[3] <= 240, (edge, activity, bounds)
            data['activity'] = '工作'
            draw_character(app.canvas, data, 0, main.ACTIVITY_NAMES, '#e7edf3', edge)
            assert app.canvas.find_withtag('laptop')
        area = app.desktop.work_area(100, 200)
        x0, y0, x1, y1 = area
        mid_x, mid_y = (x0 + x1 - 220) // 2, (y0 + y1 - 240) // 2
        for edge, x, y in [('left', x0+10, mid_y), ('right', x1-230, mid_y), ('top', mid_x, y0+10), ('bottom', mid_x, y1-250)]:
            app.edge_pose = None
            app.desktop.move(app.root, x, y)
            app.root.update()
            app.snap_character()
            app.root.update()
            assert app.edge_pose == edge, (edge, app.edge_pose)
            app.show_panel()
            app.root.update()
            assert x0 <= app.panel.winfo_rootx() <= x1 - app.panel.winfo_width()
            assert y0 <= app.panel.winfo_rooty() <= y1 - app.panel.winfo_height()
        app.desktop.move(app.root, mid_x, mid_y)
        app.root.update()
        app.snap_character()
        assert app.edge_pose is None
        assert set(app.pages) == {'活动', '成长', '商店'}
        assert app.character_config['renderer'] == 'stickman'
        import json
        import tkinter as tk
        from character_config import CharacterFile
        cf = app.character_file
        for name, color in [('one.png', '#557788'), ('two.png', '#88bb99')]:
            image = tk.PhotoImage(master=app.root, width=120, height=150)
            image.put(color, to=(0, 0, 120, 150))
            image.write(str(Path(folder) / name), format='png')
        config = cf.default()
        config.update(renderer='images', name='测试角色', fps=2, states={'idle': ['one.png', 'two.png']})
        cf.write(config)
        app.reload_character()
        assert app.character_config['name'] == '测试角色'
        for activity in main.ACTIVITY_NAMES:
            data.update(activity=activity, hunger=20, energy=80)
            app.draw()
            assert app.canvas.find_withtag('custom_character')
        app.image_renderer.draw(app.canvas, data, 0, main.ACTIVITY_NAMES)
        first = app.image_renderer.last_surface.tobytes()
        app.image_renderer.draw(app.canvas, data, app.image_renderer.animation_started+.51, main.ACTIVITY_NAMES)
        assert first != app.image_renderer.last_surface.tobytes()
        with patch.object(main.simpledialog, 'askstring', return_value='新名称'):
            app.rename_character()
        assert cf.read()['name'] == '新名称'
        assert cf.read()['renderer'] == 'images'
        assert 'character' not in app.sim.data
        cf.path.write_text('{broken', encoding='utf-8')
        app.reload_character()
        assert app.character_config['name'] == '新名称'
        assert cf.path.read_text(encoding='utf-8') == '{broken'
        config = cf.default()
        config.update(color='#55aa88', name='火柴人')
        cf.write(config)
        app.reload_character()
        app.draw()
        assert app.image_renderer.config is None
        assert app.canvas.find_withtag('body')
        area = app.desktop.work_area(app.root.winfo_x(), app.root.winfo_y())
        app.desktop.move(app.root, area[0], area[1] + 150)
        app.root.update()
        app.snap_character()
        app.toggle_click_through()
        assert app.desktop.is_click_through(app.root)
        assert main.load(main.SAVE)['desktop']['click_through']
        app.hide_character()
        saved_position = main.load(main.SAVE)['desktop'].copy()
        assert saved_position['edge'] == 'left'
        app.close()
        restored = main.App()
        restored.root.update()
        assert restored.tray.hidden
        assert restored.root.state() == 'withdrawn'
        assert restored.edge_pose == 'left'
        assert restored.tray.click_through
        assert restored.desktop.is_click_through(restored.root)
        restored.show_character()
        restored.root.update()
        assert restored.desktop.position(restored.root) == (saved_position['x'], saved_position['y']), (restored.desktop.position(restored.root), saved_position)
        assert not restored.tray.hidden
        assert not restored.tray.click_through
        assert not restored.desktop.is_click_through(restored.root)
        assert not main.load(main.SAVE)['desktop']['click_through']
        restored.close()
print('Popup, character files, four edge animations and native snapping passed')
