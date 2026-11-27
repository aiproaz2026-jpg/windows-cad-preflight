# -*- coding: utf-8 -*-
"""Put the terminal of two-terminal library symbols at the end of the symbol's own lead (horizontal leads only: first terminal left, second right). Other symbols keep the stock layout. GPL-3.0-or-later."""
import sys
import FreeCAD as App


def _leads(prims):
    pts = []
    for p in prims:
        if p[0] == 'L':
            q = p[1]
            pts += [tuple(q[0]), tuple(q[-1])]
    h = [x for x, y in pts if abs(y) < 1e-6]
    if h and max(h) - min(h) >= 60 and abs(max(h) + min(h)) < 1e-6:
        return ((min(h), 0.0), (max(h), 0.0))
    return None


_TABLE = {}


def build_table():
    from . import symbols as S
    _TABLE.clear()
    for k, (lab, term, pr) in S.V60_LIB.items():
        if len(term) == 2:
            r = _leads(pr)
            if r:
                _TABLE[k] = r
    return len(_TABLE)


_orig = {}


def terminal_position(device, name):
    kind = getattr(device, 'SymbolTemplate', None)
    if kind in _TABLE and not getattr(device, 'TerminalSides', None):
        terms = list(getattr(device, 'Terminals', []))
        if name in terms and len(terms) == 2:
            x, y = _TABLE[kind][terms.index(name)]
            return device.Position + App.Vector(x, y, 0)
    return _orig['f'](device, name)


def install():
    from . import core
    n = build_table()
    if 'f' in _orig:
        return n
    _orig['f'] = core.terminal_position
    for m in list(sys.modules.values()):
        try:
            if getattr(m, '__name__', '').startswith('DeltaEngineering') and getattr(m, 'terminal_position', None) is _orig['f']:
                m.terminal_position = terminal_position
        except Exception:
            pass
    return n
