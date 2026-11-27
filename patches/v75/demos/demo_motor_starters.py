# -*- coding: utf-8 -*-
"""Demo sheet: motor starter variants (direct-on-line and reversing). NEW file; it changes no existing file.

Run headless on the installed app (CI runner, Windows Server 2022, Mesa software OpenGL):
  FreeCADCmd.exe -c "exec(open('C:/demo_motor_starters.py',encoding='utf-8').read())"

Writes into C:/seed/demo72ms: motor_starter_variants_A3.pdf, motor_starters.FCStd, result.json.

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
OUT = 'C:/seed/demo72ms'
os.makedirs(OUT, exist_ok=True)
PDF = OUT + '/motor_starter_variants_A3.pdf'
res = {'done': False, 'sheet': 'motor_starter_variants_A3.pdf', 'warnings': []}
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
        from DeltaEngineering import term_ends
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

    # ---- A. direct-on-line starter -------------------------------------------------
    A = {}
    A['L1'] = mk(K_TERM, 'L1', 4000, 0)
    A['L2'] = mk(K_TERM, 'L2', 4000, -150)
    A['L3'] = mk(K_TERM, 'L3', 4000, -300)
    A['Q1'] = mk(K_BRK3, 'Q1', 4400, -150)
    A['KM1'] = mk(K_CON3, 'KM1', 4800, -150)
    A['F1'] = mk(K_OL, 'F1', 5200, -150)
    A['M1'] = mk(K_M3, 'M1', 5600, -150)
    sides(A['Q1'], {'1': 'Left', '3': 'Left', '5': 'Left', '2': 'Right', '4': 'Right', '6': 'Right'})
    sides(A['KM1'], {'1L1': 'Left', '3L2': 'Left', '5L3': 'Left', '2T1': 'Right', '4T2': 'Right',
                     '6T3': 'Right', 'A1': 'Left', 'A2': 'Right'})
    sides(A['F1'], {'1L1': 'Left', '3L2': 'Left', '5L3': 'Left', '2T1': 'Right', '4T2': 'Right',
                    '6T3': 'Right', '95': 'Right', '96': 'Right'})
    allleft(A['M1'])
    wire(A['L1'], '1', A['Q1'], '1')
    wire(A['L2'], '1', A['Q1'], '3')
    wire(A['L3'], '1', A['Q1'], '5')
    wire(A['Q1'], '2', A['KM1'], '1L1')
    wire(A['Q1'], '4', A['KM1'], '3L2')
    wire(A['Q1'], '6', A['KM1'], '5L3')
    wire(A['KM1'], '2T1', A['F1'], '1L1')
    wire(A['KM1'], '4T2', A['F1'], '3L2')
    wire(A['KM1'], '6T3', A['F1'], '5L3')
    wire(A['F1'], '2T1', A['M1'], 'U1')
    wire(A['F1'], '4T2', A['M1'], 'V1')
    wire(A['F1'], '6T3', A['M1'], 'W1')

    # ---- B. reversing starter (power) ----------------------------------------------
    B = {}
    B['L1'] = mk(K_TERM, 'L1-B', 4000, -650)
    B['L2'] = mk(K_TERM, 'L2-B', 4000, -800)
    B['L3'] = mk(K_TERM, 'L3-B', 4000, -950)
    B['Q2'] = mk(K_BRK3, 'Q2', 4400, -800)
    B['KMF'] = mk(K_CON3, 'KM1-F', 4800, -680)
    B['KMR'] = mk(K_CON3, 'KM2-R', 4800, -980)
    B['F2'] = mk(K_OL, 'F2', 5200, -830)
    B['M2'] = mk(K_M3, 'M2', 5600, -830)
    sides(B['Q2'], {'1': 'Left', '3': 'Left', '5': 'Left', '2': 'Right', '4': 'Right', '6': 'Right'})
    sides(B['KMF'], {'1L1': 'Left', '3L2': 'Left', '5L3': 'Left', '2T1': 'Right', '4T2': 'Right',
                     '6T3': 'Right', 'A1': 'Left', 'A2': 'Right'})
    sides(B['KMR'], {'1L1': 'Left', '3L2': 'Left', '5L3': 'Left', '2T1': 'Right', '4T2': 'Right',
                     '6T3': 'Right', 'A1': 'Left', 'A2': 'Right'})
    sides(B['F2'], {'1L1': 'Left', '3L2': 'Left', '5L3': 'Left', '2T1': 'Right', '4T2': 'Right',
                    '6T3': 'Right', '95': 'Right', '96': 'Right'})
    allleft(B['M2'])
    wire(B['L1'], '1', B['Q2'], '1')
    wire(B['L2'], '1', B['Q2'], '3')
    wire(B['L3'], '1', B['Q2'], '5')
    # forward contactor: L1, L2, L3 in order
    wire(B['Q2'], '2', B['KMF'], '1L1')
    wire(B['Q2'], '4', B['KMF'], '3L2')
    wire(B['Q2'], '6', B['KMF'], '5L3')
    # reverse contactor: L1 and L3 swapped at the input, outputs stay in order
    wire(B['Q2'], '2', B['KMR'], '5L3')
    wire(B['Q2'], '4', B['KMR'], '3L2')
    wire(B['Q2'], '6', B['KMR'], '1L1')
    wire(B['KMF'], '2T1', B['F2'], '1L1')
    wire(B['KMF'], '4T2', B['F2'], '3L2')
    wire(B['KMF'], '6T3', B['F2'], '5L3')
    wire(B['KMR'], '2T1', B['F2'], '1L1')
    wire(B['KMR'], '4T2', B['F2'], '3L2')
    wire(B['KMR'], '6T3', B['F2'], '5L3')
    wire(B['F2'], '2T1', B['M2'], 'U1')
    wire(B['F2'], '4T2', B['M2'], 'V1')
    wire(B['F2'], '6T3', B['M2'], 'W1')

    # ---- B control: stop, forward and reverse with NC interlock --------------------
    C = {}
    C['L'] = mk(K_TERM, 'L1c', 4000, -1300)
    C['S1'] = mk(K_PBNC, 'S1-stop', 4300, -1300)
    C['S2'] = mk(K_PBNO, 'S2-fwd', 4600, -1300)
    C['KI2'] = mk(K_CNC, 'KM2-21', 4900, -1300)
    C['KC1'] = mk(K_COIL, 'KM1-F coil', 5200, -1300)
    C['S3'] = mk(K_PBNO, 'S3-rev', 4600, -1500)
    C['KI1'] = mk(K_CNC, 'KM1-21', 4900, -1500)
    C['KC2'] = mk(K_COIL, 'KM2-R coil', 5200, -1500)
    C['N'] = mk(K_TERM, 'Nc', 5500, -1300)
    wire(C['L'], '1', C['S1'], '21')
    wire(C['S1'], '22', C['S2'], '13')
    wire(C['S2'], '14', C['KI2'], '21')
    wire(C['KI2'], '22', C['KC1'], 'A1')
    wire(C['KC1'], 'A2', C['N'], '1')
    wire(C['S1'], '22', C['S3'], '13')
    wire(C['S3'], '14', C['KI1'], '21')
    wire(C['KI1'], '22', C['KC2'], 'A1')
    wire(C['KC2'], 'A2', C['N'], '1')

    d.recompute()
    res['netlist'] = len(netlist(d))
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
    pg.text(frame + 20, ph - 38, 'Motor starter variants: direct-on-line and reversing (ILLUSTRATIVE demo sheet)', 11)
    pg.text(frame + 20, ph - 52, 'Generated by the Delta Engineering add-on on FreeCAD. Demo sheet only, not a design.', 7)
    for pts, lw, rgb in segs:
        pg.line([(X(a), Y(b)) for a, b in pts], lw, rgb)
    for t in texts:
        pg.text(X(t[0]), Y(t[1]), t[2], t[3] if len(t) > 3 else 8)
    heads = [(0, 'A. Direct-on-line starter: breaker Q1, contactor KM1, overload F1, motor M1'),
             (-650, 'B. Reversing starter: KM1-F forward, KM2-R reverse (L1/L3 swapped at the input), shared overload F2'),
             (-1300, 'B control: stop S1, forward S2, reverse S3, NC interlocks KM2-21 / KM1-21, coils A1-A2')]
    for hy, ht in heads:
        pg.text(frame + 20, Y(hy + 120), ht, 8)

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
             'Reversing contactor KM2-R gets L1 and L3 swapped at its input; its outputs stay in order.',
             'NC auxiliary contacts KM2-21 and KM1-21 interlock the two coils; S1 stops both directions.',
             'The control strip is drawn as its own chain so each branch is readable; in the real circuit',
             'the two branches share one stop button S1.',
             'Symbol shapes are illustrative, not certified IEC/ANSI symbols. Not a design: no rating,',
             'selectivity or safety check. Terminal marking after the ABB catalogue.']
    ny = ty - 14
    pg.text(lx + 8, ny, 'Sheet notes', 8.5)
    for line in notes:
        ny -= 11
        pg.text(lx + 8, ny, line, 6)

    pg.rect(pw - 420, 20, 400, 62, 1.0)
    pg.text(pw - 410, 62, 'Motor starter variants: DOL and reversing (ILLUSTRATIVE demo sheet)', 8.5)
    pg.text(pw - 410, 48, 'Symbol shapes come from the program symbol library; illustrative, not certified IEC/ANSI symbols.', 6.5)
    pg.text(pw - 410, 36, 'Not a design: no rating, selectivity, short-circuit or safety check. Terminal marking after ABB catalogue.', 6.5)

    pg.save(PDF)
    res['pdf_bytes'] = os.path.getsize(PDF)
    d.saveAs(OUT + '/motor_starters.FCStd')
    res['devices_a'] = 7
    res['devices_b'] = 8
    res['devices_b_control'] = 9
    res['done'] = True
except Exception:
    res['error'] = traceback.format_exc()
json.dump(res, open(OUT + '/result.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False))
