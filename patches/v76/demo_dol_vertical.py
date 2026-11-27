# -*- coding: utf-8 -*-
"""Demo sheet: motor starter variants (direct-on-line and reversing). NEW file; it changes no existing file.

Run headless on the installed app (CI runner, Windows Server 2022, Mesa software OpenGL):
  FreeCADCmd.exe -c "exec(open('C:/demo_motor_starters.py',encoding='utf-8').read())"

Writes into C:/seed/demo76dol: dol_vertical_A3.pdf, dol_vertical.FCStd, result.json.

Honest scope: symbol shapes come from the program's own symbol library and are illustrative
drawings, not certified IEC 60617 / ANSI 315 symbols. This is a demo sheet, not a design: no
rating, selectivity, short-circuit, coordination or safety check is done or implied.
Terminal designations follow the ABB catalogue marking (contactors, overload relays).
License: GPL-3.0-or-later.
"""
import sys, json, os, traceback
import FreeCAD as App

sys.path.insert(0, 'C:/DeltaTest/Mod')
sys.path.insert(0, 'C:/DeltaTest/Mod/DeltaEngineering')
sys.path.insert(0, 'C:/DeltaTest/Mod/DeltaEngineering/DeltaEngineering')
OUT = 'C:/seed/demo76dol'
os.makedirs(OUT, exist_ok=True)
PDF = OUT + '/dol_vertical_A3.pdf'
res = {'done': False, 'sheet': 'dol_vertical_A3.pdf', 'warnings': []}
try:
    from DeltaEngineering.symbols import create
    from DeltaEngineering import symbols as S
    from DeltaEngineering.domain import add_terminal_wire, netlist
    from DeltaEngineering.core import terminal_position
    from DeltaEngineering import routecheck
    from DeltaEngineering import minipdf
    try:
        from DeltaEngineering.electrical import terminal_layout, set_terminal_sides
    except Exception:
        from DeltaEngineering.electrical import terminal_layout

        def set_terminal_sides(doc, dev, mapping):
            for name, side in mapping.items():
                terminal_layout(doc, dev, [name], side)
    try:
        from DeltaEngineering import term_ends2 as term_ends
        res['term_ends_table'] = term_ends.install()
        terminal_position = term_ends.terminal_position
    except Exception as _e:
        res['term_ends_table'] = None
        res['warnings'].append('terminal ends not installed: %s' % _e)

    # symbol names: prefer the shipped illustrative keys, fall back to IEC-style keys if a later
    # patch renames the library. Only names that exist in the library are used.
    K_TERM = ['Terminal (illustr.)', 'Terminal (IEC)', 'Terminal']
    K_BRK3 = ['Breaker 3P (illustr.)', 'Breaker 3P (IEC)', 'Breaker 3P']
    K_CON3 = ['Contactor 3P (illustr.)', 'Contactor 3P (IEC)', 'Contactor 3P']
    K_OL = ['Overload relay (illustr.)', 'Overload relay (IEC)', 'Overload relay']
    K_M3 = ['Motor 3-phase (illustr.)', 'Motor 3-phase (IEC)', 'Motor 3-phase']
    K_COIL = ['Contactor coil (illustr.)', 'Contactor coil (IEC)', 'Contactor coil']
    K_PBNO = ['Pushbutton NO (illustr.)', 'Pushbutton NO (IEC)', 'Pushbutton NO']
    K_PBNC = ['Pushbutton NC (illustr.)', 'Pushbutton NC (IEC)', 'Pushbutton NC']
    K_CNC = ['Contact NC (illustr.)', 'Contact NC (IEC)', 'Contact NC']

    d = App.newDocument('MSV')
    V = App.Vector
    devs = []
    counters = {'wires': 0}

    def pick(*cands):
        lib = getattr(S, 'V60_LIB', None) or {}
        tmpl = getattr(S, 'TEMPLATES', None) or {}
        for c in cands:
            if c in lib or c in tmpl:
                return c
        raise RuntimeError('no such symbol: ' + ' | '.join(cands))

    def mk(cands, tag, x, y):
        o = create(d, pick(*cands), tag, V(x, y, 0))
        devs.append(o)
        return o

    def T(o, name):
        names = [str(t) for t in o.Terminals]
        if name not in names:
            raise RuntimeError('terminal %s not on %s [%s]; has: %s' % (name, o.Tag, o.SymbolTemplate, ', '.join(names)))
        return name

    def wire(a, sa, b, sb):
        counters['wires'] += 1
        add_terminal_wire(d, a, T(a, sa), b, T(b, sb), 'W%d' % counters['wires'])

    def sides(o, mapping):
        names = set(str(t) for t in o.Terminals)
        m = dict((k, v) for k, v in mapping.items() if k in names)
        if m:
            try:
                set_terminal_sides(d, o, m)
            except Exception as e:
                res['warnings'].append('terminal sides %s: %s' % (o.Tag, e))

    def allleft(o):
        try:
            terminal_layout(d, o, list(o.Terminals), 'Left')
        except Exception as e:
            res['warnings'].append('terminal layout %s: %s' % (o.Tag, e))

    # ---- vertical DOL power chain: Q1 above KM1 above F1, wires are straight verticals ---------
    X0 = 4400
    Q1 = mk(K_BRK3, 'Q1', X0, 0)
    KM1 = mk(K_CON3, 'KM1', X0, -180)
    F1 = mk(K_OL, 'F1', X0, -360)
    for a, b, pairs in ((Q1, KM1, (('2', '1L1'), ('4', '3L2'), ('6', '5L3'))), (KM1, F1, (('2T1', '1L1'), ('4T2', '3L2'), ('6T3', '5L3')))):
        for ta, tb in pairs:
            wire(a, ta, b, tb)
    res['straight_check'] = []

    d.recompute()
    res['netlist'] = len(netlist(d))
    for o in d.Objects:
        if hasattr(o, 'SourceTerminal') and not o.Shape.isNull():
            res['straight_check'].append([o.WireId, len(o.Shape.Edges), round(o.Shape.Length, 3)])
    res['route'] = routecheck.check(d)['count']

    # ---- render --------------------------------------------------------------------
    segs = []
    texts = []
    xs = []
    ys = []

    def add_shape(shape, lw, rgb):
        for e in shape.Edges:
            if e.Curve.__class__.__name__ == 'Line':
                pts = [e.Vertexes[0].Point, e.Vertexes[-1].Point]
            else:
                pts = e.discretize(24)
            segs.append(([(p.x, p.y) for p in pts], lw, rgb))
            for p in pts:
                xs.append(p.x)
                ys.append(p.y)

    ndev = 0
    for o in d.Objects:
        if hasattr(o, 'DeviceType') and not o.Shape.isNull():
            add_shape(o.Shape, 0.9, (0.08, 0.2, 0.35))
            ndev += 1
            texts.append((o.Position.x - 30, o.Position.y + 50, o.Tag))
            for t in o.Terminals:
                p = terminal_position(o, t)
                texts.append((p.x + 4, p.y + 3, t, 5))
    nwire = 0
    for o in d.Objects:
        if hasattr(o, 'SourceTerminal') and not o.Shape.isNull():
            add_shape(o.Shape, 1.0, (0.75, 0.22, 0.17))
            nwire += 1
    res['devices'] = ndev
    res['wires'] = nwire
    if not xs or not ys:
        raise RuntimeError('nothing to draw: no device geometry was produced')

    pw, ph = 1190.55, 841.89
    frame = 20.0
    draw_w = 720.0
    x0, x1 = min(xs) - 70, max(xs) + 60
    y0, y1 = min(ys) - 70, max(ys) + 110
    bot, top = 95.0, ph - 62.0
    sc = min(draw_w / (x1 - x0), (top - bot) / (y1 - y0))
    X = lambda x: frame + 20 + (x - x0) * sc
    Y = lambda y: bot + (y - y0) * sc

    pg = minipdf.Page(pw, ph)
    pg.rect(frame, frame, pw - 2 * frame, ph - 2 * frame, 1.5)
    pg.text(frame + 20, ph - 38, 'Direct-on-line power chain, vertical layout (ILLUSTRATIVE demo sheet)', 11)
    pg.text(frame + 20, ph - 52, 'Generated by the Delta Engineering add-on on FreeCAD. Demo sheet only, not a design.', 7)
    for pts, lw, rgb in segs:
        pg.line([(X(a), Y(b)) for a, b in pts], lw, rgb)
    for t in texts:
        pg.text(X(t[0]), Y(t[1]), t[2], t[3] if len(t) > 3 else 8)
    pg.text(X(X0 - 30) - 30, Y(120), 'L1', 8); pg.text(X(X0) - 4, Y(120), 'L2', 8); pg.text(X(X0 + 30) - 4, Y(120), 'L3', 8)
    pg.text(frame + 20, ph - 66, 'Vertical power chain: supply L1/L2/L3 above Q1, outputs continue below F1 to the motor (motor not drawn here).', 7)

    # device list panel
    lx = 790.0
    lwid = pw - 30.0 - lx
    pg.rect(lx, 100, lwid, ph - 62 - 100, 1.0)
    pg.text(lx + 8, ph - 74, 'Device list (tag / symbol / terminals)', 8.5)
    ty = ph - 90
    for o in devs:
        if ty < 110:
            break
        pg.text(lx + 8, ty, '%s  %s' % (o.Tag, str(o.SymbolTemplate).replace(' (illustr.)', '')), 6.5)
        pg.text(lx + 8, ty - 7, 'terminals: ' + ', '.join(str(t) for t in o.Terminals), 5.5)
        ty -= 17.0

    notes = ['Wires drawn: %d, nets: %d.' % (nwire, res['netlist']),
             'Terminals on the 3-pole blocks line up in x, so each wire is a straight vertical line.',
             'The motor is left out: its terminals sit on the bottom edge of the symbol.',
             'Symbol shapes are illustrative, not certified IEC/ANSI symbols. Not a design: no rating,',
             'selectivity or safety check. Terminal marking after the ABB catalogue.']
    ny = ty - 14
    pg.text(lx + 8, ny, 'Sheet notes', 8.5)
    for line in notes:
        ny -= 11
        pg.text(lx + 8, ny, line, 6)

    pg.rect(pw - 420, 20, 400, 62, 1.0)
    pg.text(pw - 410, 62, 'DOL power chain, vertical (ILLUSTRATIVE demo sheet)', 8.5)
    pg.text(pw - 410, 48, 'Symbol shapes come from the program symbol library; illustrative, not certified IEC/ANSI symbols.', 6.5)
    pg.text(pw - 410, 36, 'Not a design: no rating, selectivity, short-circuit or safety check. Terminal marking after ABB catalogue.', 6.5)

    pg.save(PDF)
    res['pdf_bytes'] = os.path.getsize(PDF)
    d.saveAs(OUT + '/dol_vertical.FCStd')
    res['done'] = True
except Exception:
    res['error'] = traceback.format_exc()
json.dump(res, open(OUT + '/result.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False))
