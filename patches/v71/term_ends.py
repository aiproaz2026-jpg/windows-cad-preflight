# -*- coding: utf-8 -*-
"""Put the terminal of two-terminal library symbols at the end of the symbol's own lead (horizontal leads only: first terminal left, second right). Other symbols keep the stock layout. GPL-3.0-or-later."""
import sys
import FreeCAD as App


def _vleads(prims):
    ys = []
    for p in prims:
        if p[0] == 'L':
            for q in (p[1][0], p[1][-1]):
                if abs(q[0]) < 1e-6:
                    ys.append(q[1])
    if ys and max(ys) - min(ys) >= 60 and abs(max(ys) + min(ys)) < 1e-6:
        return ((0.0, max(ys)), (0.0, min(ys)))
    return None


def _leads(prims):
    pts = []
    for p in prims:
        if p[0] == 'L':
            q = p[1]
            pts += [tuple(q[0]), tuple(q[-1])]
    h = [x for x, y in pts if abs(y) < 1e-6]
    if h and max(h) - min(h) >= 60 and abs(max(h) + min(h)) < 1e-6:
        lo, hi = min(h), max(h)
        # core draws a leader from x=+/-35 to the terminal; an identical point makes Part.makeLine fail and the symbol vanish, so stay 0.01 mm inside.
        if abs(abs(hi) - 35.0) < 1e-6:
            lo, hi = lo + 0.01, hi - 0.01
        return ((lo, 0.0), (hi, 0.0))
    return None


_TABLE = {}


def build_table():
    from . import symbols as S
    _TABLE.clear()
    for k, (lab, term, pr) in S.V60_LIB.items():
        if len(term) == 2:
            r = _leads(pr) or _vleads(pr)
            if r:
                _TABLE[k] = r
    return len(_TABLE)


_orig = {}


_last = {'pt': None}


def terminal_position(device, name):
    _last['pt'] = None
    kind = getattr(device, 'SymbolTemplate', None)
    if kind in _TABLE and not getattr(device, 'TerminalSides', None):
        terms = list(getattr(device, 'Terminals', []))
        if name in terms and len(terms) == 2:
            x, y = _TABLE[kind][terms.index(name)]
            _last['pt'] = device.Position + App.Vector(x, y, 0)
            return _last['pt']
    return _orig['f'](device, name)


class _PartShim(object):
    # core draws a leader from x=+/-35 to each terminal; where the terminal already sits on the symbol's own lead, replace that leader by a 0.01 mm stub.
    def __init__(self, real):
        self._real = real

    def __getattr__(self, name):
        return getattr(self._real, name)

    def makeLine(self, a, b):
        p = _last['pt']
        if p is not None and (b - p).Length < 1e-9:
            return self._real.makeLine(b, b + App.Vector(0.01, 0, 0))
        return self._real.makeLine(a, b)


def install():
    from . import core
    n = build_table()
    if 'f' in _orig:
        return n
    _orig['f'] = core.terminal_position
    if not isinstance(core.Part, _PartShim):
        core.Part = _PartShim(core.Part)
    for m in list(sys.modules.values()):
        try:
            if getattr(m, '__name__', '').startswith('DeltaEngineering') and getattr(m, 'terminal_position', None) is _orig['f']:
                m.terminal_position = terminal_position
        except Exception:
            pass
    return n
