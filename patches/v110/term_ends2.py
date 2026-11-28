# -*- coding: utf-8 -*-
"""Terminal dots at the end of each symbol's own lead, for the whole electrical library.
GPL-3.0-or-later.

Covers what term_ends.py (v71) did not: vertical two-terminal symbols (contacts, coils,
1P breaker), single-terminal symbols, and multi-terminal blocks (3P breaker, contactor,
overload relay, motors, transformer, VFD, PLC). Blocks get their dots on the block edge
at the pole positions; every other symbol gets its dots where its own lead stops.

HONEST SCOPE: the positions are schematic drawing positions only. They say nothing about
terminal order, rating or wiring correctness. Symbols stay original illustrative shapes,
not IEC/ANSI. Terminal names follow the library data (ABB-style markings, see
elec_lib_data.py). UNTESTED until a CI run executes it.
"""
import sys

TOL = 1e-6
MIN_SPAN = 30.0      # a lead pair shorter than this is not treated as a lead
MAX_OFFSET = 0.5     # a lead pair must be centred on the symbol origin within this


# Explicit terminal coordinates in mm, relative to the device origin, for symbols whose
# terminals are not at the end of a drawn two-terminal lead: one-terminal symbols and
# multi-terminal blocks. Keyed by symbol name, then by terminal name as in elec_lib_data.py.
EXPLICIT = {
    'Ground (illustr.)': {'PE': (0.0, 28.0)},
    'Terminal (illustr.)': {'1': (0.0, 25.0)},
    'Selector switch (illustr.)': {'1': (-35.0, 0.0), '2': (35.0, 22.0), '3': (35.0, -22.0)},
    'Breaker 3P (illustr.)': {'1': (-30.0, 35.0), '2': (-30.0, -35.0),
                              '3': (0.0, 35.0), '4': (0.0, -35.0),
                              '5': (30.0, 35.0), '6': (30.0, -35.0)},
    'Contactor 3P (illustr.)': {'1L1': (-30.0, 35.0), '2T1': (-30.0, -35.0),
                                '3L2': (0.0, 35.0), '4T2': (0.0, -35.0),
                                '5L3': (30.0, 35.0), '6T3': (30.0, -35.0),
                                'A1': (45.0, 20.0), 'A2': (45.0, -20.0)},
    'Overload relay (illustr.)': {'1L1': (-30.0, 35.0), '2T1': (-30.0, -35.0),
                                  '3L2': (0.0, 35.0), '4T2': (0.0, -35.0),
                                  '5L3': (30.0, 35.0), '6T3': (30.0, -35.0),
                                  '95': (45.0, 10.0), '96': (45.0, -10.0)},
    'Motor 3-phase (illustr.)': {'U1': (-17.5, -30.31), 'V1': (0.0, -35.0),
                                 'W1': (17.5, -30.31), 'PE': (0.0, 35.0)},
    'Motor 1-phase (illustr.)': {'U1': (-15.0, -25.98), 'U2': (15.0, -25.98), 'PE': (0.0, 30.0)},
    'Transformer (illustr.)': {'1': (-8.0, 27.0), '2': (-8.0, -27.0),
                               '3': (8.0, 27.0), '4': (8.0, -27.0)},
    'VFD block (illustr.)': {'L1': (-55.0, 24.0), 'L2': (-55.0, 0.0), 'L3': (-55.0, -24.0),
                             'U': (55.0, 24.0), 'V': (55.0, 0.0), 'W': (55.0, -24.0),
                             'PE': (0.0, -40.0)},
    'PLC block (illustr.)': {'L+': (-60.0, 25.0), 'M': (-60.0, -25.0),
                             'I0.0': (-20.0, 45.0), 'I0.1': (20.0, 45.0),
                             'Q0.0': (-20.0, -45.0), 'Q0.1': (20.0, -45.0)},
    # v101: the '(IEC-style)' and '(IEC)' multi-terminal blocks had no explicit table, so their terminals
    # fell back to one column on the right edge with overlapping labels. Same edge layout as the
    # '(illustr.)' set, taken from each symbol's own drawn box (bounding boxes read from the library
    # primitives: blocks 90 x 70 mm, VFD 110 x 80, PLC 120 x 90, motor circle r35 / r30, transformer
    # circles r16 at x = -9 and +9). Illustrative positions, not a standard.
    'Breaker 3P (IEC-style)': {'1': (-30.0, 35.0), '2': (-30.0, -35.0),
                               '3': (0.0, 35.0), '4': (0.0, -35.0),
                               '5': (30.0, 35.0), '6': (30.0, -35.0)},
    'Contactor 3P (IEC-style)': {'1L1': (-30.0, 35.0), '2T1': (-30.0, -35.0),
                                 '3L2': (0.0, 35.0), '4T2': (0.0, -35.0),
                                 '5L3': (30.0, 35.0), '6T3': (30.0, -35.0),
                                 'A1': (45.0, 20.0), 'A2': (45.0, -20.0)},
    'Overload relay (IEC-style)': {'1L1': (-30.0, 35.0), '2T1': (-30.0, -35.0),
                                   '3L2': (0.0, 35.0), '4T2': (0.0, -35.0),
                                   '5L3': (30.0, 35.0), '6T3': (30.0, -35.0),
                                   '95': (45.0, 10.0), '96': (45.0, -10.0)},
    'Breaker 3P (IEC)': {'1': (-28.0, 35.0), '2': (-28.0, -35.0),
                         '3': (0.0, 35.0), '4': (0.0, -35.0),
                         '5': (28.0, 35.0), '6': (28.0, -35.0)},
    'Contactor 3P (IEC)': {'1L1': (-28.0, 35.0), '2T1': (-28.0, -35.0),
                           '3L2': (0.0, 35.0), '4T2': (0.0, -35.0),
                           '5L3': (28.0, 35.0), '6T3': (28.0, -35.0),
                           'A1': (45.0, 20.0), 'A2': (45.0, -20.0)},
    'Motor 3-phase (IEC-style)': {'U1': (-17.5, -30.31), 'V1': (0.0, -35.0),
                                  'W1': (17.5, -30.31), 'PE': (0.0, 35.0)},
    'Motor 1-phase (IEC-style)': {'U1': (-15.0, -25.98), 'U2': (15.0, -25.98), 'PE': (0.0, 30.0)},
    'Transformer (IEC-style)': {'1': (-9.0, 16.0), '2': (-9.0, -16.0),
                                '3': (9.0, 16.0), '4': (9.0, -16.0)},
    'VFD block (IEC-style)': {'L1': (-55.0, 24.0), 'L2': (-55.0, 0.0), 'L3': (-55.0, -24.0),
                              'U': (55.0, 24.0), 'V': (55.0, 0.0), 'W': (55.0, -24.0),
                              'PE': (0.0, -40.0)},
    'PLC block (IEC-style)': {'L+': (-60.0, 25.0), 'M': (-60.0, -25.0),
                              'I0.0': (-20.0, 45.0), 'I0.1': (20.0, 45.0),
                              'Q0.0': (-20.0, -45.0), 'Q0.1': (20.0, -45.0)},
    # v110: single-terminal and meter symbols of the IEC-style set had no entry, so their dots sat 60 mm to the
    # right of the drawing. Placed on the drawn lead ends (illustrative, not a standard).
    'Ground (IEC-style)': {'PE': (0.0, 28.0)},
    'Terminal (IEC-style)': {'1': (0.0, 25.0)},
    'Selector switch (IEC-style)': {'1': (-35.0, 0.0), '2': (35.0, 22.0), '3': (35.0, -22.0)},
    'Energy meter kWh (IEC-style)': {'1': (-40.0, 0.0), '2': (40.0, 0.0), '3': (-10.0, -17.32), '4': (10.0, -17.32)},
    # legacy templates from the first symbol set, still selectable
    'Motor concept': {'U': (-17.5, -30.31), 'V': (0.0, -35.0), 'W': (17.5, -30.31), 'PE': (0.0, 35.0)},
    'Switch concept': {'1': (-35.0, 0.0), '2': (35.0, 0.0)},
    'Earth concept': {'PE': (0.0, 28.0)},
}

TABLE = {}
_orig = {}
_orig_exec = {}
_last = {'pt': None, 'leader': False}


def _polylines(prims):
    out = []
    for pr in prims:
        if pr[0] == 'L' and len(pr[1]) >= 2:
            out.append([(float(x), float(y)) for x, y in pr[1]])
    return out


def _loose_ends(polys):
    """Points that belong to exactly one polyline end, so a drawn lead stops there."""
    count = {}
    for pts in polys:
        for q in (pts[0], pts[-1]):
            count[q] = count.get(q, 0) + 1
    return [q for q, n in count.items() if n == 1]


def lead_pair(prims):
    """The two lead ends of a two-terminal symbol, or None. Vertical leads first, then horizontal."""
    ends = _loose_ends(_polylines(prims))
    for vertical in (True, False):
        same = [q for q in ends if abs(q[0] if vertical else q[1]) <= TOL]
        if len(same) < 2:
            continue
        vals = [q[1] if vertical else q[0] for q in same]
        lo, hi = min(vals), max(vals)
        if hi - lo < MIN_SPAN or abs(hi + lo) > MAX_OFFSET:
            continue
        if vertical:
            return ((0.0, hi), (0.0, lo))
        return ((lo, 0.0), (hi, 0.0))
    return None


def table_from(lib):
    """Build {symbol: {terminal: (x, y)}} from a symbol library dictionary."""
    table = {}
    for kind, (_label, terminals, prims) in lib.items():
        terminals = [str(t) for t in terminals]
        if kind in EXPLICIT and set(EXPLICIT[kind]) == set(terminals):
            table[kind] = dict(EXPLICIT[kind])
            continue
        pair = lead_pair(prims) if len(terminals) == 2 else None
        if pair:
            table[kind] = {terminals[0]: pair[0], terminals[1]: pair[1]}
    return table


def build_table(lib=None):
    if lib is None:
        from . import symbols as S
        lib = S.V60_LIB
    fresh = table_from(lib)
    for kind, pos in EXPLICIT.items():
        if kind not in fresh and kind not in lib:
            fresh[kind] = dict(pos)
    TABLE.clear()
    TABLE.update(fresh)
    return len(TABLE)


def _pinned(device, name):
    """A terminal the user pinned to a side with set_terminal_sides keeps the stock position."""
    for item in list(getattr(device, 'TerminalSides', []) or []):
        key, _, val = str(item).rpartition('=')
        if key == name and val in ('Left', 'Right'):
            return True
    return False


def terminal_position(device, name):
    import FreeCAD as App
    _last['pt'] = None
    kind = getattr(device, 'SymbolTemplate', None)
    pos = TABLE.get(kind)
    if pos and name in pos and not _pinned(device, name):
        x, y = pos[name]
        point = device.Position + App.Vector(x, y, 0)
        _last['pt'] = point
        return point
    return _orig['f'](device, name)


class _PartShim(object):
    """The core draws a leader from +/-35 mm to every terminal. Where the terminal already
    sits on the symbol's own lead that leader is redundant or crosses the symbol, so it is
    replaced by a 0.01 mm stub (an identical start and end point makes Part.makeLine fail)."""

    def __init__(self, real):
        self._real = real

    def __getattr__(self, name):
        return getattr(self._real, name)

    def makeLine(self, a, b):
        import FreeCAD as App
        p = _last['pt']
        # only the leader drawn inside Device.execute is replaced; wires between devices
        # also end on a terminal point and must stay full length
        if _last['leader'] and p is not None and (b - p).Length < 1e-9:
            return self._real.makeLine(b, b + App.Vector(0.01, 0, 0))
        return self._real.makeLine(a, b)


def install():
    """Patch core.terminal_position and the leader drawing. Returns the symbol count."""
    from . import core
    n = build_table()
    if 'f' in _orig:
        return n
    _orig['f'] = core.terminal_position
    # unwrap a Part shim left by an earlier terminal patch so shims never nest
    prev = core.Part
    while hasattr(prev, '_real'):
        prev = prev._real
    if not isinstance(prev, _PartShim):
        core.Part = _PartShim(prev)
    old = sys.modules.get(__name__.rsplit('.', 1)[0] + '.term_ends')
    if old is not None and hasattr(old, 'install') and not getattr(old, '_v72_disabled', False):
        old.install = lambda: 0          # v71 must not re-patch over this one
        old._v72_disabled = True
    if 'execute' not in _orig_exec and hasattr(core, 'Device'):
        _orig_exec['execute'] = core.Device.execute

        def _execute(self, obj):
            _last['leader'] = True
            try:
                return _orig_exec['execute'](self, obj)
            finally:
                _last['leader'] = False

        core.Device.execute = _execute
    for m in list(sys.modules.values()):
        try:
            if getattr(m, 'terminal_position', None) is _orig['f']:
                m.terminal_position = terminal_position
        except Exception:
            pass
    return n


def positions(device):
    """{terminal: (x, y)} actually used for this device."""
    out = {}
    for name in list(getattr(device, 'Terminals', [])):
        p = terminal_position(device, name)
        out[name] = (round(p.x - device.Position.x, 3), round(p.y - device.Position.y, 3))
    return out
