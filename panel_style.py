"""Replaceable UI style, separate from game and character data."""
import json
from pathlib import Path
import re

from app_paths import ROOT
DEFAULT = {
    'name': '简洁浅色', 'font': 'Microsoft YaHei UI', 'font_size': 9,
    'title_font': 'Segoe UI', 'padding': 14, 'show_header': False,
    'header_text': 'MYSERVANT',
    'layout': 'classic',
    'colors': {
        'background': '#eef2f5', 'surface': '#ffffff', 'text': '#253346',
        'muted': '#65768a', 'subtle': '#708095', 'border': '#ccd6df',
        'button': '#edf2f6', 'hover': '#e0e9f1', 'pressed': '#d1dce7',
        'selected': '#bfe5dc', 'accent': '#65bba9', 'accent_text': '#123a32',
        'track': '#e8edf2', 'hunger': '#c89f56', 'energy': '#65bba9',
        'stress': '#9690c8', 'disabled': '#9aa7b6',
        'header': '#253346', 'header_text': '#eef2f5',
        'bubble': '#f4f7f8', 'bubble_text': '#344657',
    },
}


def read_style(path=None):
    path = path or ROOT / 'panel.json'
    raw = json.loads(path.read_text(encoding='utf-8-sig'))
    if not isinstance(raw, dict):
        raise ValueError('面板配置必须为JSON对象')
    data = dict(DEFAULT)
    data.update(raw)
    if not isinstance(raw.get('colors', {}), dict):
        raise ValueError('colors 必须为颜色对象')
    data['colors'] = dict(DEFAULT['colors'], **raw.get('colors', {}))
    for color in data['colors'].values():
        if not isinstance(color, str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', color):
            raise ValueError('颜色必须为六位十六进制值')
    for key in ('name', 'font', 'title_font', 'header_text'):
        if not isinstance(data[key], str) or not data[key].strip() or len(data[key]) > 40:
            raise ValueError('面板名称或字体无效')
    if type(data['font_size']) is not int or not 8 <= data['font_size'] <= 12:
        raise ValueError('字号应为8～12')
    if type(data['padding']) is not int or not 6 <= data['padding'] <= 24:
        raise ValueError('留白应为6～24')
    if type(data['show_header']) is not bool:
        raise ValueError('show_header 必须为布尔值')
    if data['layout'] not in ('classic', 'hollow'):
        raise ValueError('layout 必须为 classic 或 hollow')
    return data


def load_style():
    try:
        return read_style(), ''
    except (OSError, ValueError, TypeError) as error:
        return DEFAULT, str(error)
