# -*- coding: utf-8 -*-
"""Additive 'IEC-style' variants of a few electrical symbols (contacts and pushbuttons). Original geometry coded from the widely used drawing conventions (stationary contact, hinged blade, hooked end for break contact, dashed actuator link with an E-shaped push head). NOT a certified copy of IEC 60617. GPL-3.0-or-later."""


def _dash(x0, x1, y, n=4):
    seg = (x1 - x0) / float(2 * n - 1)
    return [('L', [(x0 + 2 * i * seg, y), (x0 + (2 * i + 1) * seg, y)]) for i in range(n)]


def _e(x, y):
    return [('L', [(x, y + 7), (x, y - 7)]), ('L', [(x, y + 7), (x + 7, y + 7)]), ('L', [(x, y), (x + 7, y)]), ('L', [(x, y - 7), (x + 7, y - 7)])]


def _no():
    return [('L', [(0, 40), (0, 14)]), ('L', [(0, -40), (0, -12)]), ('L', [(0, -12), (-12, 12)])]


def _nc():
    return [('L', [(0, 40), (0, 16)]), ('L', [(0, 16), (-9, 16)]), ('L', [(0, -40), (0, -12)]), ('L', [(0, -12), (-9, 14)])]


def build():
    out = {}
    out['Contact NO (IEC-style)'] = ('ملامس NO بنمط IEC (تقريبي)', ('13', '14'), _no())
    out['Contact NC (IEC-style)'] = ('ملامس NC بنمط IEC (تقريبي)', ('21', '22'), _nc())
    out['Pushbutton NO (IEC-style)'] = ('ضاغط NO بنمط IEC (تقريبي)', ('13', '14'), _no() + _dash(-6, -24, 0, 3) + _e(-34, 0))
    out['Pushbutton NC (IEC-style)'] = ('ضاغط NC بنمط IEC (تقريبي)', ('21', '22'), _nc() + _dash(-5, -24, 0, 3) + _e(-34, 0))
    return out


def install():
    from . import symbols as S
    n = 0
    for k, (lab, term, pr) in build().items():
        S.V60_LIB[k] = (lab, tuple(term), pr)
        S.TEMPLATES[k] = (lab, tuple(term))
        n += 1
    try:
        from . import term_ends
        term_ends.build_table()
    except Exception:
        pass
    return n
