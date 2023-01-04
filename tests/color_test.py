from __future__ import annotations

import pytest

from babi.color import Color


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        ('#1e77d3', Color(0x1E, 0x77, 0xD3)),
        ('white', Color(0xFF, 0xFF, 0xFF)),
        ('black', Color(0x00, 0x00, 0x00)),
        ('#ccc', Color(0xCC, 0xCC, 0xCC)),
    ),
)
def test_color_parse(s, expected):
    assert Color.parse(s) == expected
