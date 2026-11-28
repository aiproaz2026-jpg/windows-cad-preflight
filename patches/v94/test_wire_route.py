# -*- coding: utf-8 -*-
"""Unit tests for wire_route.route(). Plain Python, no FreeCAD, no dependencies.
Run: python test_wire_route.py     (exit 0 = all passed) GPL-3.0-or-later."""
import sys
import wire_route as W

FAILS = []
CHECKS = [0]


def check(name, cond, detail=''):
    CHECKS[0] += 1
    if cond:
        print('PASS %s' % name)
    else:
        print('FAIL %s %s' % (name, detail))
        FAILS.append(name)


def orthogonal(pts):
    for p, q in zip(pts, pts[1:]):
        if abs(p[0] - q[0]) > 1e-9 and abs(p[1] - q[1]) > 1e-9:
            return False
    return True


def enters(pts, boxes, skip):
    for p, q in zip(pts, pts[1:]):
        for i, r in enumerate(boxes):
            if i in skip:
                continue
            if W._hits_rect(p, q, r):
                return i
    return None


def overlaps_any(pts, used):
    for p, q in zip(pts, pts[1:]):
        for s in used:
            rel = W._relation(p, q, s)
            if rel is not None and rel[0] == 'overlap':
                return True
    return False


# 1. a clear straight run stays straight
A = (0.0, 0.0, 100.0, 60.0)
B = (400.0, 0.0, 500.0, 60.0)
pts = W.route((100, 30), (400, 30), (1, 0), (-1, 0), [A, B], [])
check('straight stays straight', pts == [(100, 30), (400, 30)], str(pts))

# 2. a box between the two terminals is avoided
C = (200.0, -40.0, 300.0, 40.0)
pts = W.route((100, 30), (400, 30), (1, 0), (-1, 0), [A, C, B], [])
check('avoids the body box', orthogonal(pts) and enters(pts, [A, C, B], (0, 2)) is None, str(pts))
check('avoids: first and last point', pts[0] == (100, 30) and pts[-1] == (400, 30), str(pts))
check('avoids: more than the L', len(pts) >= 4, str(pts))

# 3. a wire already routed on the same line is not overlapped
used = [((150, 30), (250, 30))]
pts = W.route((100, 30), (400, 30), (1, 0), (-1, 0), [A, B], used)
check('no overlap with a used wire', orthogonal(pts) and not overlaps_any(pts, used), str(pts))
check('no overlap: endpoints kept', pts[0] == (100, 30) and pts[-1] == (400, 30), str(pts))

# 4. two parallel wires between the same pair of boxes end up on different lines
first = W.route((100, 30), (400, 30), (1, 0), (-1, 0), [A, B], [])
second = W.route((100, 45), (400, 45), (1, 0), (-1, 0), [A, B], [((p, q) for p, q in [])] and [])
used1 = list(zip(first, first[1:]))
second = W.route((100, 45), (400, 45), (1, 0), (-1, 0), [A, B], used1)
check('second parallel wire clears the first', orthogonal(second) and not overlaps_any(second, used1), str(second))

# 5. nothing reachable -> the old L shape and the flag
# the target is sealed in a ring of walls that are not its own symbol
walls = [(250.0, 150.0, 350.0, 160.0), (250.0, 240.0, 350.0, 250.0),
         (250.0, 160.0, 260.0, 240.0), (340.0, 160.0, 350.0, 240.0)]
pts = W.route((0, 0), (300, 200), (1, 0), (-1, 0), walls, [])
check('fallback returns the L shape', pts == [(0, 0), (300, 0), (300, 200)], str(pts))
check('fallback is flagged', W.LAST['ok'] is False, str(W.LAST))

# 6. a wire from a bottom terminal leaves downward and comes back around a circle
circ = (-35.0, -35.0, 35.0, 35.0)
other = (300.0, -300.0, 420.0, -200.0)
pts = W.route((0, -35), (300, -250), (0, -1), (-1, 0), [circ, other], [])
check('bottom terminal leaves downward', pts[1] == (0, -49), str(pts))
check('bottom route clears both boxes', orthogonal(pts) and enters(pts, [circ, other], (0, 1)) is None, str(pts))

# 7. determinism: same input twice gives the same path
p1 = W.route((100, 30), (400, 30), (1, 0), (-1, 0), [A, C, B], [])
p2 = W.route((100, 30), (400, 30), (1, 0), (-1, 0), [A, C, B], [])
check('deterministic', p1 == p2, str((p1, p2)))

# 8. the installed hook must accept whatever plan() returns and write the shape.
#    plan() returns a 3-tuple (points, ok, reason); a wrapper that unpacks two of them raises
#    ValueError on every wire and FreeCAD silently keeps the old shape.
try:
    from DeltaEngineering import wire_route as WP
    from DeltaEngineering import core as CORE
except Exception:
    WP = None
    CORE = None
if WP is None:
    print('SKIP hook test: DeltaEngineering package not importable here')
else:
    class FakeWire(object):
        Shape = None
        Validation = None

    saved_plan = WP.plan
    try:
        WP.plan = lambda obj, doc=None: ([(0.0, 0.0), (50.0, 0.0), (50.0, 30.0)], True, 'routed')
        installed = WP.install()
        obj = FakeWire()
        raised = None
        try:
            CORE.Connection.execute(None, obj)
        except Exception as exc:
            raised = exc
        check('hook runs without raising on a 3-tuple plan', raised is None, repr(raised))
        check('hook writes the shape', obj.Shape is not None, str(obj.Shape))
        check('hook sets Validation', obj.Validation == 'Logical connection only', str(obj.Validation))
        check('install is idempotent', WP.install() == 0, 'second install returned 1')
        check('uninstall restores', WP.uninstall() == 1, 'uninstall returned 0')
    finally:
        WP.plan = saved_plan

# 8b. crossing another wire's stub is what makes a fan look stacked: a straight run through it
#     gives way, while a plain crossing is still allowed
stub_seg = ((250.0, 10.0), (250.0, 100.0))
plain = W.route((100, 30), (400, 30), (1, 0), (-1, 0), [A, B], [stub_seg])
check('a plain crossing keeps the straight run', plain == [(100, 30), (400, 30)], str(plain))
guarded = W.route((100, 30), (400, 30), (1, 0), (-1, 0), [A, B], [(stub_seg, 'stub')])
cuts = [s for s in zip(guarded, guarded[1:])
        if (W._relation(s[0], s[1], stub_seg) or ('',))[0] == 'cross']
check('a straight run does not cut across a stub', not cuts, str(guarded))
check('going round the stub still reaches both ends',
      guarded[0] == (100, 30) and guarded[-1] == (400, 30) and orthogonal(guarded), str(guarded))

# 8c. a short pass-by is not a trunk: a straight run shadowing a wire for less than SHADOW_MIN
#     stays straight, which is the crossings the last revision paid for nothing
short_shadow = [((150.0, 32.0), (150.0 + W.SHADOW_MIN - 10.0, 32.0))]
pts = W.route((100, 30), (400, 30), (1, 0), (-1, 0), [A, B], short_shadow)
check('a short shadow keeps the straight run', pts == [(100, 30), (400, 30)], str(pts))
long_shadow = [((150.0, 32.0), (150.0 + W.SHADOW_MIN + 20.0, 32.0))]
pts = W.route((100, 30), (400, 30), (1, 0), (-1, 0), [A, B], long_shadow)
check('a long shadow still gives way', pts != [(100, 30), (400, 30)] and orthogonal(pts), str(pts))

# 9. fan-out: a face with many terminals fans even when its DeviceType is unknown, and the
#    stub lengths follow the order the block lists its terminals, not their geometric order.
class FakeTerm(object):
    def __init__(self, x, y):
        self.x, self.y = x, y


class FakeDevice(object):
    def __init__(self, names, positions, kind='Generic schematic symbol', fan=None):
        self.Terminals = list(names)
        self.DeviceType = kind
        self._pos = dict(zip(names, positions))
        if fan is not None:
            self.FanStubs = fan


saved_pos = W._terminal_pos
W._terminal_pos = lambda device, name: FakeTerm(*device._pos[name])
try:
    rect = (0.0, -45.0, 60.0, 45.0)
    names = ['T%d' % i for i in range(1, 7)]
    # terminals sit in reverse geometric order: T1 is the lowest, so ranking by y would hand
    # the longest stub to the wrong end of the block
    ys = [40.0 - 12.0 * i for i in range(6)]
    dev = FakeDevice(names, [(200.0, y) for y in ys])
    got = W.fan_lengths(dev, rect)
    check('fan: 6 terminals on one face fan with an unknown DeviceType', len(got) == 6, str(got))
    seq = [got[n] for n in names]
    check('fan: lengths follow terminal order, not geometry',
          seq == sorted(seq) and len(set(seq)) == 6 and seq[0] == W.STUB, str(seq))
    steps = {round(seq[i + 1] - seq[i], 6) for i in range(len(seq) - 1)}
    check('fan: one constant step, at least LANE, distinct for every terminal',
          len(steps) == 1 and min(steps) >= W.LANE, str(seq))

    few = FakeDevice(names[:5], [(200.0, ys[i]) for i in range(5)])
    check('fan: 5 terminals of an unknown type stay unfanned',
          W.fan_lengths(few, rect) == {}, str(W.fan_lengths(few, rect)))

    plc = FakeDevice(names[:2], [(200.0, 20.0), (200.0, -20.0)], kind='PLC block (illustr.)')
    check('fan: a PLC type fans a two-terminal face',
          len(W.fan_lengths(plc, rect)) == 2, str(W.fan_lengths(plc, rect)))

    # the count rule is per side: 6 terminals spread 3/3 over two faces stay stock, because they
    # already leave in different directions and fanning every 8-terminal contactor hurt the
    # reversing demo
    split = FakeDevice(names, [(200.0, 30.0), (200.0, 0.0), (200.0, -30.0),
                              (-200.0, 30.0), (-200.0, 0.0), (-200.0, -30.0)])
    check('fan: 6 terminals spread 3/3 over two faces stay unfanned',
          W.fan_lengths(split, rect) == {}, str(W.fan_lengths(split, rect)))

    # a dense face gets a step as wide as its pitch; a loose face keeps LANE
    dense = FakeDevice(names[:3], [(200.0, 0.0), (200.0, -10.0), (200.0, -20.0)],
                       kind='PLC block (illustr.)')
    gd = W.fan_lengths(dense, rect)
    check('fan: a 10 mm pitch face gets a 12 mm step',
          [gd[n] for n in names[:3]] == [14.0, 26.0, 38.0], str([gd[n] for n in names[:3]]))
    mid = FakeDevice(names[:3], [(200.0, 0.0), (200.0, -14.0), (200.0, -28.0)],
                     kind='PLC block (illustr.)')
    gm = W.fan_lengths(mid, rect)
    check('fan: a 14 mm pitch face is dense and steps 14 mm',
          [gm[n] for n in names[:3]] == [14.0, 28.0, 42.0], str([gm[n] for n in names[:3]]))
    loose = FakeDevice(names[:3], [(200.0, 0.0), (200.0, -18.0), (200.0, -36.0)],
                       kind='PLC block (illustr.)')
    gl = W.fan_lengths(loose, rect)
    check('fan: an 18 mm pitch face keeps the 8 mm step',
          [gl[n] for n in names[:3]] == [14.0, 22.0, 30.0], str([gl[n] for n in names[:3]]))

    saved_whole = W.FAN_COUNT_WHOLE_DEVICE
    W.FAN_COUNT_WHOLE_DEVICE = True
    try:
        check('fan: counting the whole device fans the split 3/3 block',
              len(W.fan_lengths(split, rect)) == 6, str(W.fan_lengths(split, rect)))
    finally:
        W.FAN_COUNT_WHOLE_DEVICE = saved_whole

    off = FakeDevice(names, [(200.0, y) for y in ys], fan=False)
    check('fan: FanStubs False wins over the terminal count',
          W.fan_lengths(off, rect) == {}, str(W.fan_lengths(off, rect)))

    on = FakeDevice(names[:2], [(200.0, 20.0), (200.0, -20.0)], fan=True)
    check('fan: FanStubs True fans a two-terminal face',
          len(W.fan_lengths(on, rect)) == 2, str(W.fan_lengths(on, rect)))
finally:
    W._terminal_pos = saved_pos

print('')
print('%d checks, %d failed' % (CHECKS[0], len(FAILS)))
sys.exit(1 if FAILS else 0)
