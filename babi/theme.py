from __future__ import annotations

import curses
import functools
import importlib.resources
import json
import os.path
from typing import Any, NamedTuple

from babi.color import Color
from babi.color_manager import ColorManager
from babi.fdict import FDict

A_ITALIC = getattr(curses, 'A_ITALIC', 0x80000000)  # not always present


class Style(NamedTuple):
    fg: Color | None
    bg: Color | None
    b: bool
    i: bool
    u: bool

    def attr(self, color_manager: ColorManager) -> int:
        pair = color_manager.color_pair(self.fg, self.bg)
        return (
            curses.color_pair(pair)
            | self.b * curses.A_BOLD
            | self.i * A_ITALIC
            | self.u * curses.A_UNDERLINE
        )

    @classmethod
    def blank(cls) -> Style:
        return cls(fg=None, bg=None, b=False, i=False, u=False)


class PartialStyle(NamedTuple):
    fg: Color | None = None
    bg: Color | None = None
    b: bool | None = None
    i: bool | None = None
    u: bool | None = None

    def overlay_on(self, dct: dict[str, Any]) -> None:
        for attr in self._fields:
            value = getattr(self, attr)
            if value is not None:
                dct[attr] = value

    @classmethod
    def from_dct(cls, dct: dict[str, Any]) -> PartialStyle:
        kv = cls()._asdict()
        if 'foreground' in dct:
            kv['fg'] = Color.parse(dct['foreground'])
        if 'background' in dct:
            kv['bg'] = Color.parse(dct['background'])
        if dct.get('fontStyle') == 'bold':
            kv['b'] = True
        elif dct.get('fontStyle') == 'italic':
            kv['i'] = True
        elif dct.get('fontStyle') == 'underline':
            kv['u'] = True
        return cls(**kv)


class TrieNode(NamedTuple):
    style: PartialStyle
    children: FDict[str, TrieNode]

    @classmethod
    def from_dct(cls, dct: dict[str, Any]) -> TrieNode:
        children = FDict({k: TrieNode.from_dct(v) for k, v in dct['children'].items()})
        return cls(PartialStyle.from_dct(dct), children)


class Theme:
    def __init__(self, default: Style, rules: TrieNode) -> None:
        self.default = default
        self.rules = rules
        self.select = functools.lru_cache(maxsize=None)(self._select)

    def _select(self, scope: tuple[str, ...]) -> Style:
        if not scope:
            return self.default
        else:
            style = self.select(scope[:-1])._asdict()
            node = self.rules
            for part in scope[-1].split('.'):
                if part not in node.children:
                    break
                else:
                    node = node.children[part]
                    node.style.overlay_on(style)
            return Style(**style)

    @classmethod
    def from_dct(cls, data: dict[str, Any]) -> Theme:
        default = Style.blank()._asdict()

        for k in ('foreground', 'editor.foreground'):
            if k in data.get('colors', {}):
                default['fg'] = Color.parse(data['colors'][k])
                break

        for k in ('background', 'editor.background'):
            if k in data.get('colors', {}):
                default['bg'] = Color.parse(data['colors'][k])
                break

        root: dict[str, Any] = {'children': {}}
        rules = data.get('tokenColors', []) + data.get('settings', [])
        for rule in rules:
            if 'scope' not in rule:
                scopes = ['']
            elif rule['scope'] == '':
                scopes = ['']
            elif isinstance(rule['scope'], str):
                scopes = [
                    s.strip()
                    # some themes have a buggy trailing/leading comma
                    for s in rule['scope'].strip().strip(',').split(',')
                    if s.strip()
                ]
            else:
                scopes = rule['scope']

            for scope in scopes:
                if ' ' in scope:
                    # TODO: implement parent scopes
                    continue
                elif scope == '':
                    PartialStyle.from_dct(rule['settings']).overlay_on(default)
                    continue

                cur = root
                for part in scope.split('.'):
                    cur = cur['children'].setdefault(part, {'children': {}})

                cur.update(rule['settings'])

        return cls(Style(**default), TrieNode.from_dct(root))

    @classmethod
    def from_filename(cls, filename: str) -> Theme:
        if not os.path.exists(filename):
            default_theme = importlib.resources.read_text(
                'babi.resources',
                'default-theme.json',
            )
            return cls.from_dct(json.loads(default_theme))
        else:
            with open(filename, encoding='UTF-8') as f:
                return cls.from_dct(json.load(f))
