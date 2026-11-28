# -*- coding: utf-8 -*-
"""CI metrics for wire_route across the demo gallery. Headless FreeCAD, CI only.

Every gallery sheet is a demo script that builds one wired schematic. For each one this script
builds the sheet twice - once with the wire_route call site off, once with it on - and reports
the wiring numbers before and after wire_route.reroute(doc):

    wires, overlapping pairs and mm, junction overlaps, crossings, segments through foreign
    device boxes, minimum clearance, plan_matches_shape

It writes one A3 PDF per sheet (the state after reroute) and one result.json.

The gallery scripts are run as they are (exec of the file), so this file carries no copy of
their layouts and cannot drift from them. Nothing in them is edited.

Call site off = wire_route.apply() returns False while the sheet is built, so the wires keep the
stock straight / L / Z path. Call site on = apply() is live while the sheet is built, so every
wire is routed by the router as its Connection executes. If the installed core.py does not carry
the wire_route.apply() call site, the on pass installs the hook itself (wire_route.install())
and records call_site_present: false.

UNTESTED until a CI run executes it. Written by a code-only writer: no CI run, no FreeCAD, no
real-hardware test. Not a design and not checked for rating or safety. GPL-3.0-or-later.
"""
import sys, os, io, json, math, glob, inspect, traceback, contextlib
import FreeCAD as App

sys.path.insert(0, 'C:/DeltaTest/Mod')
sys.path.insert(0, 'C:/DeltaTest/Mod/DeltaEngineering')
sys.path.insert(0, 'C:/DeltaTest/Mod/DeltaEngineering/DeltaEngineering')

OUT = os.environ.get('GALLERY_METRICS_OUT', 'C:/seed/gallerymetrics')
SRC = os.environ.get('GALLERY_SCRIPTS', 'C:/gallery_src')
PASSES = [p.strip() for p in os.environ.get('GALLERY_PASSES', 'off,on').split(',') if p.strip()]
PLAN_CHECK = os.environ.get('GALLERY_PLAN_CHECK', '1') != '0'
os.makedirs(OUT, exist_ok=True)

res = {'done': False, 'note': 'UNTESTED: written by a code-only writer; CI has not run this file.',
       'out': OUT, 'scripts_dir': SRC, 'passes': PASSES,
       'sheets_measured': 0, 'sheets_failed': 0, 'skipped': [], 'pass_failures': [],
       'summary': [], 'sheets': {}}
try:
    from DeltaEngineering import wire_route as R
    from DeltaEngineering import minipdf
    from DeltaEngineering import core as CORE

    terminal_position = CORE.terminal_position
    REAL_APPLY = R.apply
    try:
        res['freecad'] = '.'.join(str(x) for x in App.Version()[:3])
    except Exception:
        res['freecad'] = 'unknown'
    res['preset_name'] = os.environ.get('WIRE_ROUTE_PRESET', 'balanced')
    try:
        res['preset'] = R.preset(res['preset_name'])
    except Exception as _e:
        res['preset'] = 'preset() not present in this wire_route: %s' % _e

    def call_site_present():
        """True when core.Connection.execute already calls wire_route.apply (build-time patch)."""
        try:
            return 'wire_route.apply' in inspect.getsource(CORE.Connection.execute)
        except Exception:
            return False

    CALL_SITE = call_site_present()
    res['call_site_present'] = CALL_SITE

    def off(obj, doc=None):
        return False

    def doc_names():
        try:
            return list(App.listDocuments().keys())
        except Exception:
            return []

    def close_all():
        for n in doc_names():
            try:
                App.closeDocument(n)
            except Exception:
                pass

    # ------------------------------------------------------------ measurement

    def gap(seg, r):
        (x1, y1), (x2, y2) = seg
        ax0, ax1 = min(x1, x2), max(x1, x2)
        ay0, ay1 = min(y1, y2), max(y1, y2)
        dx = max(r[0] - ax1, ax0 - r[2], 0.0)
        dy = max(r[1] - ay1, ay0 - r[3], 0.0)
        return math.hypot(dx, dy)

    def own_boxes(obj, index):
        own = set()
        for name in ('SourceDevice', 'TargetDevice'):
            dev = getattr(obj, name, None)
            if dev is not None and id(dev) in index:
                own.add(index[id(dev)])
        return own

    def wire_objects(doc):
        out = []
        for o in doc.Objects:
            shape = getattr(o, 'Shape', None)
            if hasattr(o, 'SourceTerminal') and shape is not None and not shape.isNull():
                out.append(o)
        return out

    def min_clearance(doc):
        found = R.boxes(doc)
        rects = [r for _o, r in found]
        index = {id(o): i for i, (o, _r) in enumerate(found)}
        worst = None
        for o in wire_objects(doc):
            own = own_boxes(o, index)
            for seg in R.segments(o.Shape):
                for i, r in enumerate(rects):
                    if i in own:
                        continue
                    g = gap(seg, r)
                    worst = g if worst is None else min(worst, g)
        return None if worst is None else round(worst, 2)

    def foreign_box_segments(doc):
        """Wire segments that pass through a device box that is not one of the wire's own two."""
        found = R.boxes(doc)
        rects = [r for _o, r in found]
        index = {id(o): i for i, (o, _r) in enumerate(found)}
        n = 0
        for o in wire_objects(doc):
            own = own_boxes(o, index)
            for seg in R.segments(o.Shape):
                for i, r in enumerate(rects):
                    if i in own:
                        continue
                    if R._hits_rect(seg[0], seg[1], r):
                        n += 1
        return n

    def wire_paths(doc):
        out = {}
        for o in wire_objects(doc):
            sg = R.segments(o.Shape)
            if not sg:
                continue
            pts = [[round(sg[0][0][0], 1), round(sg[0][0][1], 1)]]
            pts += [[round(s[1][0], 1), round(s[1][1], 1)] for s in sg]
            out[o.WireId] = pts
        return out

    def shape_points(obj):
        sg = R.segments(obj.Shape)
        if not sg:
            return None
        pts = [[round(sg[0][0][0], 1), round(sg[0][0][1], 1)]]
        pts += [[round(s[1][0], 1), round(s[1][1], 1)] for s in sg]
        return pts

    def plan_matches_shape(doc):
        """How many wires already carry exactly the path the router would plan for them."""
        ok = 0
        total = 0
        if not PLAN_CHECK:
            return None, None
        for o in wire_objects(doc):
            total += 1
            try:
                planned = R.plan(o, doc)
            except Exception:
                planned = None
            if planned is None:
                continue
            cur = [[round(x, 1), round(y, 1)] for x, y in R.clean(planned[0])]
            if cur == shape_points(o):
                ok += 1
        return ok, total

    def measure(doc):
        hits = R.overlaps(doc)
        junction = [h for h in hits if h[3]]
        plain = [h for h in hits if not h[3]]
        cross = R.crossings(doc)
        pm, pm_total = plan_matches_shape(doc)
        return {'wires': len(wire_objects(doc)),
                'overlap_pairs': len(plain),
                'overlap_mm': round(sum(h[2] for h in plain), 1),
                'junction_overlaps': len(junction),
                'junction_mm': round(sum(h[2] for h in junction), 1),
                'crossings': len(cross),
                'segments_in_foreign_box': foreign_box_segments(doc),
                'min_clearance_mm': min_clearance(doc),
                'plan_matches_shape': pm,
                'plan_checked': pm_total,
                'device_boxes': len(R.boxes(doc)),
                'label_boxes': len(R.text_boxes(doc))}

    # ------------------------------------------------------------ A3 sheet

    def sheet(doc, path, title, before, after):
        segs = []
        texts = []
        xs = []
        ys = []

        def add(shape, w, rgb):
            for e in shape.Edges:
                if e.Curve.__class__.__name__ != 'Line':
                    pp = [e.valueAt(e.FirstParameter + (e.LastParameter - e.FirstParameter) * j / 20.0)
                          for j in range(21)]
                else:
                    pp = [e.Vertexes[0].Point, e.Vertexes[-1].Point]
                segs.append(([(p.x, p.y) for p in pp], w, rgb))
                for p in pp:
                    xs.append(p.x)
                    ys.append(p.y)

        for o in doc.Objects:
            if hasattr(o, 'DeviceType') and not o.Shape.isNull():
                add(o.Shape, 0.9, (0.08, 0.2, 0.35))
                texts.append((o.Position.x - 30, o.Position.y + 50, o.Tag))
                for t in list(getattr(o, 'Terminals', None) or []):
                    try:
                        p = terminal_position(o, t)
                    except Exception:
                        continue
                    texts.append((p.x + 4, p.y + 3, t, 5))
        for o in doc.Objects:
            if hasattr(o, 'SourceTerminal') and not o.Shape.isNull():
                add(o.Shape, 1.1, (0.75, 0.22, 0.17))
        if not xs or not ys:
            raise RuntimeError('nothing to draw')
        pw, ph = 1190.55, 841.89
        x0, x1, y0, y1 = min(xs) - 60, max(xs) + 60, min(ys) - 80, max(ys) + 120
        mx, top, bot = 40, 70, 90
        sc = min((pw - 2 * mx) / max(x1 - x0, 1.0), (ph - top - bot) / max(y1 - y0, 1.0))
        X = lambda x: mx + (x - x0) * sc
        Y = lambda y: bot + (y - y0) * sc
        pg = minipdf.Page(pw, ph)
        pg.rect(20, 20, pw - 40, ph - 40, 1.5)
        for pts, w, rgb in segs:
            pg.line([(X(a), Y(b)) for a, b in pts], w, rgb)
        for t in texts:
            pg.text(X(t[0]), Y(t[1]), t[2], t[3] if len(t) > 3 else 8)
        pg.rect(pw - 620, 20, 600, 78, 1.0)
        pg.text(pw - 610, 76, title, 9)
        pg.text(pw - 610, 63, 'Before reroute: %s' % line(before), 6.5)
        pg.text(pw - 610, 52, 'After reroute:  %s' % line(after), 6.5)
        pg.text(pw - 610, 41, 'Generated by the CAD program in CI. Wires routed by wire_route; '
                              'not a design, not checked for rating or safety.', 6.5)
        pg.text(pw - 610, 30, 'CI only, software OpenGL. Not a real-hardware test.', 6.5)
        pg.save(path)
        return os.path.getsize(path)

    def line(m):
        if not m:
            return 'not measured'
        return ('%d wires, %d overlap pairs / %.1f mm, %d junction overlaps, %d crossings, '
                '%d foreign-box segments, min clearance %s mm, plan matches %d/%d'
                % (m['wires'], m['overlap_pairs'], m['overlap_mm'], m['junction_overlaps'],
                   m['crossings'], m['segments_in_foreign_box'],
                   'n/a' if m['min_clearance_mm'] is None else ('%.1f' % m['min_clearance_mm']),
                   -1 if m['plan_matches_shape'] is None else m['plan_matches_shape'],
                   -1 if m['plan_checked'] is None else m['plan_checked']))

    # ------------------------------------------------------------ run a demo script

    def build(script, call_site_on):
        """Run one gallery script; return (document, demo info)."""
        close_all()
        R.uninstall()
        if call_site_on:
            R.apply = REAL_APPLY
            if not CALL_SITE:
                R.install()
        else:
            R.apply = off
        before = doc_names()
        ns = {'__name__': '__gallery_demo__', '__file__': script}
        buf = io.StringIO()
        err = None
        try:
            src = open(script, encoding='utf-8').read()
            with contextlib.redirect_stdout(buf):
                exec(compile(src, script, 'exec'), ns)
        except Exception:
            err = traceback.format_exc()
        finally:
            R.apply = REAL_APPLY
            R.uninstall()
        new = [n for n in doc_names() if n not in before]
        doc = None
        for n in new:
            try:
                doc = App.getDocument(n)
            except Exception:
                doc = None
        if doc is None:
            try:
                doc = App.ActiveDocument
            except Exception:
                doc = None
        demo = ns.get('res') or {}
        info = {'error': err,
                'demo_done': bool(demo.get('done')),
                'demo_error': demo.get('error'),
                'demo_sheet': demo.get('sheet'),
                'demo_route_findings': demo.get('route'),
                'stdout_tail': buf.getvalue()[-1200:]}
        return doc, info

    def run_sheet(path):
        stem = os.path.splitext(os.path.basename(path))[0]
        entry = {'script': path, 'doc': None, 'passes': {}, 'pdf': None, 'pdf_bytes': None}
        for pname in PASSES:
            on = (pname == 'on')
            doc, demo = build(path, on)
            entry.setdefault('demo', demo)
            if doc is None:
                entry['passes'][pname] = {'error': 'the demo script left no document'}
                continue
            entry['doc'] = doc.Name
            m_before = measure(doc)
            block = {'before': m_before}
            if m_before['wires'] == 0:
                block['note'] = 'this sheet has no wires; nothing to reroute'
                entry['passes'][pname] = block
                continue
            paths_before = wire_paths(doc)
            rows = R.reroute(doc)
            m_after = measure(doc)
            paths_after = wire_paths(doc)
            block.update({'after': m_after,
                          'wires_changed_by_reroute': sum(1 for w in paths_before
                                                          if paths_after.get(w) != paths_before[w]),
                          'routed': sum(1 for r in rows if r['routed']),
                          'fallback': [r['wire'] for r in rows if not r['routed']],
                          'reroute_plan_matches_shape': sum(
                              1 for r in rows
                              if [list(q) for q in r['path']] == paths_after.get(r['wire'])),
                          'hook_installed_at_build': bool(on),
                          'per_wire': rows})
            entry['passes'][pname] = block
            try:                     # rewritten by each pass, so the file holds the last good state
                entry['pdf'] = OUT + '/%s_A3.pdf' % stem
                entry['pdf_bytes'] = sheet(doc, entry['pdf'],
                                           '%s - gallery demo, after wire_route.reroute() (%s)' % (stem, pname),
                                           m_before, m_after)
            except Exception:
                entry['pdf_error'] = traceback.format_exc()
        close_all()
        return stem, entry

    # ------------------------------------------------------------ main

    scripts = sorted(glob.glob(os.path.join(SRC, '*.py')))
    res['scripts_seen'] = [os.path.basename(p) for p in scripts]
    if not scripts:
        res['error'] = 'no gallery scripts found in %s' % SRC
    for path in scripts:
        try:
            stem, entry = run_sheet(path)
        except Exception:
            res['sheets_failed'] += 1
            res['sheets'][os.path.splitext(os.path.basename(path))[0]] = {'error': traceback.format_exc()}
            continue
        wired = any('after' in b for b in entry['passes'].values())
        crashed = any('error' in b for b in entry['passes'].values())
        if wired:
            res['sheets_measured'] += 1
            if crashed:
                res['pass_failures'].append({'sheet': stem, 'reason': 'one pass of this sheet did not run'})
        elif crashed:
            res['sheets_failed'] += 1
            res['skipped'].append({'sheet': stem, 'reason': 'the demo script failed before building a wired sheet'})
        else:
            res['skipped'].append({'sheet': stem, 'reason': 'no wires were built'})
        res['sheets'][stem] = entry
        for pname in PASSES:
            block = entry['passes'].get(pname, {})
            if 'before' in block and 'after' in block:
                res['summary'].append({'sheet': stem, 'pass': pname,
                                       'before': block['before'], 'after': block['after'],
                                       'reroute_rows': block['routed'] + len(block['fallback']),
                                       'reroute_plan_matches_shape': block['reroute_plan_matches_shape'],
                                       'wires_changed_by_reroute': block['wires_changed_by_reroute'],
                                       'pdf': entry.get('pdf')})
    crashed_sheets = sum(1 for s in res['sheets'].values() if s.get('error'))
    failed_demos = sum(1 for s in res['skipped']
                       if str(s.get('reason', '')).startswith('the demo script failed'))
    res['sheets_failed'] = crashed_sheets + failed_demos
    res['done'] = True
except Exception:
    res['error'] = traceback.format_exc()

json.dump(res, open(OUT + '/result.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1,
          default=str)
print(json.dumps({'done': res.get('done'), 'sheets_measured': res.get('sheets_measured'),
                  'sheets_failed': res.get('sheets_failed'), 'skipped': res.get('skipped'),
                  'pass_failures': res.get('pass_failures'),
                  'call_site_present': res.get('call_site_present'),
                  'summary': res.get('summary'), 'error': res.get('error')},
                 ensure_ascii=False, default=str))
