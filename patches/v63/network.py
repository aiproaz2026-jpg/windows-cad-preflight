# -*- coding: utf-8 -*-
"""Branching pipe network builder: nodes + edges -> straight pipes, 90/45 elbows and equal tees (B16.9 tables from fittings_library),
with a joint check against the real solids and a schedule. GPL-3.0-or-later.
Rules: degree 1 = free end; degree 2 collinear = plain joint; degree 2 at 90/45 deg = elbow; degree 3 with two collinear legs
(run) and a perpendicular leg (branch) = equal tee. Anything else raises ValueError (no silent guess). Generic model, not a design."""
import math
import FreeCAD as App
from . import fittings_library as FL
from . import equipment3d as E

V = App.Vector
TOL = 0.5  # degrees


def plan(nodes, edges, nps):
    """Pure geometry plan (no document). nodes {name: Vector}, edges [(a, b)]. Returns dict with fittings and pipe segments."""
    if nps not in FL.TEE_EQ_CM or nps not in FL.ELBOW_90_LR_A:
        raise ValueError('NPS %s has no fitting tables' % nps)
    adj = {n: [] for n in nodes}
    for a, b in edges:
        if a not in nodes or b not in nodes or a == b:
            raise ValueError('Bad edge %s-%s' % (a, b))
        if b in adj[a]:
            raise ValueError('Duplicate edge %s-%s' % (a, b))
        adj[a].append(b); adj[b].append(a)
    unit = {}
    for a, b in edges:
        d = nodes[b] - nodes[a]
        if d.Length < 1e-6:
            raise ValueError('Zero-length edge %s-%s' % (a, b))
        d.normalize(); unit[(a, b)] = d; unit[(b, a)] = V(-d.x, -d.y, -d.z)
    fit = {}   # node -> dict(kind, ...)
    setb = {}  # (node, neighbour) -> setback mm
    for n, nb in adj.items():
        if len(nb) == 0:
            raise ValueError('Node %s has no edge' % n)
        if len(nb) == 1:
            setb[(n, nb[0])] = 0.0
        elif len(nb) == 2:
            d1 = unit[(nb[0], n)]; d2 = unit[(n, nb[1])]  # travel nb0 -> n -> nb1
            ang = math.degrees(math.acos(max(-1.0, min(1.0, d1.dot(d2)))))
            if ang < TOL:
                setb[(n, nb[0])] = setb[(n, nb[1])] = 0.0
            elif abs(ang - 90) <= TOL:
                s = float(FL.ELBOW_90_LR_A[nps]); fit[n] = {'kind': 'elbow90lr', 'din': d1, 'dout': d2, 'setback': s}
                setb[(n, nb[0])] = setb[(n, nb[1])] = s
            elif abs(ang - 45) <= TOL:
                s = float(FL.ELBOW_45_LR_B[nps]); fit[n] = {'kind': 'elbow45', 'din': d1, 'dout': d2, 'setback': s}
                setb[(n, nb[0])] = setb[(n, nb[1])] = s
            else:
                raise ValueError('Node %s bend %.1f deg: only 90 and 45 degree bends have fittings' % (n, ang))
        elif len(nb) == 3:
            run = None
            for i in range(3):
                for j in range(i + 1, 3):
                    if unit[(n, nb[i])].dot(unit[(n, nb[j])]) < -1 + 1e-6 + (1 - math.cos(math.radians(TOL))):
                        run = (i, j)
            if run is None:
                raise ValueError('Node %s has three legs but no two are collinear (needs a run)' % n)
            br = ({0, 1, 2} - set(run)).pop()
            dr = unit[(n, nb[run[0]])]; dbr = unit[(n, nb[br])]
            if abs(dr.dot(dbr)) > math.sin(math.radians(TOL)):
                raise ValueError('Node %s branch is not perpendicular to the run' % n)
            c, m = FL.TEE_EQ_CM[nps]
            fit[n] = {'kind': 'tee_eq', 'run': dr, 'branch': dbr, 'c': float(c), 'm': float(m)}
            setb[(n, nb[run[0]])] = setb[(n, nb[run[1]])] = float(c); setb[(n, nb[br])] = float(m)
        else:
            raise ValueError('Node %s has %d legs: not supported' % (n, len(nb)))
    segs = []
    for a, b in edges:
        L = (nodes[b] - nodes[a]).Length - setb[(a, b)] - setb[(b, a)]
        if L <= 1e-6:
            raise ValueError('Edge %s-%s is too short (%.1f mm) for its end fittings' % (a, b, L))
        segs.append({'a': a, 'b': b, 'start': nodes[a] + unit[(a, b)] * setb[(a, b)], 'dir': unit[(a, b)], 'length': L})
    return {'fittings': fit, 'segments': segs, 'adj': adj, 'setb': setb, 'unit': unit}


def build(doc, nodes, edges, nps, schedule='SCH 40'):
    p = plan(nodes, edges, nps)
    out = {'pipes': [], 'fittings': {}, 'plan': p}
    for n, f in p['fittings'].items():
        e = E.F3.create(doc, f['kind'], nps); e.Schedule = schedule; doc.recompute()
        if f['kind'] == 'tee_eq':
            e.Placement = App.Placement(nodes[n], E._frame(f['run'], f['branch']))
        else:
            e.Placement = App.Placement(nodes[n] - f['din'] * f['setback'], E._frame(f['din'], f['dout']))
        e.Label = 'Net_%s_%s' % (f['kind'], n)
        out['fittings'][n] = e
    for s in p['segments']:
        pp = E.create(doc, 'pipe', nps); pp.Schedule = schedule; pp.Length = s['length']; doc.recompute()
        pp.Placement = App.Placement(s['start'], E._frame(s['dir']))
        pp.Label = 'Net_pipe_%s_%s' % (s['a'], s['b'])
        out['pipes'].append(pp)
    doc.recompute()
    return out


def check(doc, res, nodes):
    """Joint check on the real solids: each pipe end that should meet a fitting must touch that fitting's solid (<0.5 mm gap, no overlap);
    free ends need no fitting. Also every solid must be valid with positive volume."""
    p = res['plan']; worst = 0.0; bad = []
    for obj, s in zip(res['pipes'], p['segments']):
        end = s['start'] + s['dir'] * s['length']
        for pt, node in ((s['start'], s['a']), (end, s['b'])):
            f = res['fittings'].get(node)
            if f is None:
                continue
            dist = obj.Shape.distToShape(f.Shape)[0]
            worst = max(worst, dist)
            if dist > 0.5:
                bad.append('%s end at %s: %.2f mm from fitting' % (obj.Label, node, dist))
            else:
                ov = obj.Shape.common(f.Shape).Volume
                if ov > 1.0:
                    bad.append('%s overlaps fitting at %s by %.1f mm3' % (obj.Label, node, ov))
    for o in list(res['pipes']) + list(res['fittings'].values()):
        if o.Shape.isNull() or not o.Shape.isValid() or o.Shape.Volume <= 0:
            bad.append('invalid solid ' + o.Label)
    return {'max_joint_gap_mm': worst, 'bad': bad}


def schedule_rows(res, nps, schedule='SCH 40'):
    rows = []
    cnt = {}
    for f in res['fittings'].values():
        cnt[f.FittingKind] = cnt.get(f.FittingKind, 0) + 1
    tot = sum(s['length'] for s in res['plan']['segments'])
    for i, s in enumerate(res['plan']['segments'], 1):
        rows.append(('P%d' % i, '%s-%s' % (s['a'], s['b']), 'NPS %s %s pipe' % (nps, schedule), round(s['length'], 1)))
    return rows, cnt, round(tot, 1)
