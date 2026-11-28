# -*- coding: utf-8 -*-
"""Reproduce the control-panel 30 mm run from the CI diag on the stand-in harness.

Geometry copied from /downloads/v21bi_cp_30mm_run-b8ad4a86.txt:
  W7  T1.4 (4540,-18)  -> A1.M (4590,-959)
  W19 B1.X2 (5560,-520) -> A1.M (4590,-959)
  W22 Y1.A2 (5650,-1020) -> A1.M (4590,-959)
Three wires into one terminal; the last 30 mm of the approach (y=-959, x 4560..4590) is shared.
"""
import sys
import wire_route as W

# device boxes: the terminal sits on the face the wire leaves from
BOXES = [
    (4540.0, -40.0, 4562.0, 0.0),        # T1.4, terminal on the left face
    (5540.0, -540.0, 5560.0, -500.0),    # B1.X2, right face
    (5630.0, -1042.0, 5670.0, -1020.0),  # Y1.A2, bottom face
    (4590.0, -1060.0, 4760.0, -880.0),   # A1 block, A1.M on the left face
]

WIRES = [
    ('W7', (4540, -18), (-1, 0), (4590, -959), (-1, 0)),
    ('W19', (5560, -520), (1, 0), (4590, -959), (-1, 0)),
    ('W22', (5650, -1020), (0, -1), (4590, -959), (-1, 0)),
]


class _P(object):
    def __init__(self, x, y):
        self.x, self.y = x, y


class _V(object):
    def __init__(self, pt):
        self.Point = _P(pt[0], pt[1])


class _E(object):
    def __init__(self, p, q):
        self.Vertexes = [_V(p), _V(q)]


class _Shape(object):
    def __init__(self, pts):
        self.Edges = [_E(p, q) for p, q in zip(pts, pts[1:])]

    def isNull(self):
        return False


class _Wire(object):
    def __init__(self, wid, pts):
        self.WireId, self.Shape, self.SourceTerminal = wid, _Shape(pts), True


class _Doc(object):
    def __init__(self, wires):
        self.Objects = wires


# A1.M carries three wires, so its fan stub is 30 mm: that is where all three wires turn, and
# the 30 mm run the CI diag found is exactly that shared stub
A1_STUB = 30.0

paths = []
used = []
for wid, a, da, b, db in WIRES:
    pts = W.route(a, b, da, db, BOXES, list(used), b_stub=A1_STUB)
    paths.append((wid, pts))
    used.extend(zip(pts, pts[1:]))
    print('%s  %d points  %s' % (wid, len(pts), pts))

doc = _Doc([_Wire(wid, pts) for wid, pts in paths])
hits = W.overlaps(doc)
print('')
print('overlap pairs: %d' % len(hits))
for h in hits:
    print('  %s/%s %.1f mm junction=%s' % h)
print('non-junction: %d' % len([h for h in hits if not h[3]]))
print('crossings: %d' % len(W.crossings(doc)))
