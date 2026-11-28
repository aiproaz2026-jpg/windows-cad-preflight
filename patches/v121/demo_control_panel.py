# -*- coding: utf-8 -*-
"""Demo sheet: control panel (supply, 24 V control, PLC inputs/outputs, field devices). NEW file; it changes no existing file.

Run headless on the installed app (CI runner, Windows Server 2022, Mesa software OpenGL):
  FreeCADCmd.exe -c "exec(open('C:/demo_control_panel.py',encoding='utf-8').read())"

Writes into C:/seed/demo72cp: control_panel_A3.pdf, control_panel.FCStd, result.json.

Honest scope: symbol shapes come from the program's own symbol library and are illustrative
drawings, not certified IEC 60617 / ANSI 315 symbols. This is a demo sheet, not a design: no
rating, IP/NEMA claim, short-circuit, EMC, earthing or safety check is done or implied.
Terminal designations follow the ABB catalogue marking where the symbol has them.
License: GPL-3.0-or-later.
"""
import sys, json, os, traceback
import FreeCAD as App

sys.path.insert(0, 'C:/DeltaTest/Mod')
sys.path.insert(0, 'C:/DeltaTest/Mod/DeltaEngineering')
sys.path.insert(0, 'C:/DeltaTest/Mod/DeltaEngineering/DeltaEngineering')
OUT = 'C:/seed/demo72cp'
os.makedirs(OUT, exist_ok=True)
PDF = OUT + '/control_panel_A3.pdf'
res = {'done': False, 'sheet': 'control_panel_A3.pdf', 'warnings': []}
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

    K_TERM = ['Terminal (illustr.)', 'Terminal (IEC)', 'Terminal']
    K_BRK1 = ['Breaker 1P (illustr.)', 'Breaker 1P (IEC)', 'Breaker 1P']
    K_TR = ['Transformer (illustr.)', 'Transformer (IEC)', 'Transformer']
    K_FUSE = ['Fuse (illustr.)', 'Fuse (IEC)', 'Fuse']
    K_ESTOP = ['Emergency stop (illustr.)', 'Emergency stop (IEC)', 'Emergency stop']
    K_SEL = ['Selector switch (illustr.)', 'Selector switch (IEC)', 'Selector switch']
    K_PBNO = ['Pushbutton NO (illustr.)', 'Pushbutton NO (IEC)', 'Pushbutton NO']
    K_LAMP = ['Lamp (illustr.)', 'Lamp (IEC)', 'Lamp']
    K_BUZ = ['Buzzer (illustr.)', 'Buzzer (IEC)', 'Buzzer']
    K_PSW = ['Pressure switch (illustr.)', 'Pressure switch (IEC)', 'Pressure switch']
    K_PLC = ['PLC block (illustr.)', 'PLC block (IEC)', 'PLC block']
    K_RCOIL = ['Relay coil (illustr.)', 'Relay coil (IEC)', 'Relay coil']
    K_VALVE = ['Solenoid valve coil (illustr.)', 'Solenoid valve coil (IEC)', 'Solenoid valve coil']
    K_CNO = ['Contact NO (illustr.)', 'Contact NO (IEC)', 'Contact NO']
    K_GND = ['Ground (illustr.)', 'Ground (IEC)', 'Ground']

    d = App.newDocument('CP')
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

    # ---- supply: incoming terminal, main breaker, control transformer, fuses ------
    P = {}
    P['L1'] = mk(K_TERM, 'L1', 4000, 0)
    P['Q1'] = mk(K_BRK1, 'Q1', 4300, 0)
    P['T1'] = mk(K_TR, 'T1', 4600, 0)
    P['N'] = mk(K_TERM, 'N', 4950, 30)
    P['F1'] = mk(K_FUSE, 'F1', 5250, 0)
    P['PE'] = mk(K_TERM, 'PE', 4000, -220)
    P['GND'] = mk(K_GND, 'PE-bar', 4300, -220)
    sides(P['Q1'], {'1': 'Left', '2': 'Right'})
    sides(P['T1'], {'1': 'Left', '2': 'Right', '3': 'Right', '4': 'Left'})
    wire(P['L1'], '1', P['Q1'], '1')
    wire(P['Q1'], '2', P['T1'], '1')
    wire(P['T1'], '2', P['N'], '1')
    wire(P['T1'], '3', P['F1'], '1')
    wire(P['PE'], '1', P['GND'], 'PE')

    # ---- door-mounted controls and indicators --------------------------------------
    F = {}
    F['S0'] = mk(K_ESTOP, 'S0', 4000, -520)
    F['S1'] = mk(K_SEL, 'S1', 4380, -520)
    F['S2'] = mk(K_PBNO, 'S2', 4760, -520)
    F['H1'] = mk(K_LAMP, 'H1', 5140, -520)
    F['B1'] = mk(K_BUZ, 'B1', 5520, -520)

    # ---- logic: PLC, field switch, output relay and valve --------------------------
    G = {}
    G['S3'] = mk(K_PSW, 'S3', 4000, -980)
    G['A1'] = mk(K_PLC, 'A1', 4650, -980)
    G['K1'] = mk(K_RCOIL, 'K1', 5410, -980)
    G['Y1'] = mk(K_VALVE, 'Y1', 5650, -980)
    G['K1C'] = mk(K_CNO, 'K1-13', 5350, -1260)
    sides(G['A1'], {'L+': 'Left', 'M': 'Left', 'I0.0': 'Left', 'I0.1': 'Left',
                    'Q0.0': 'Right', 'Q0.1': 'Right'})

    wire(P['F1'], '2', G['A1'], 'L+')
    wire(P['T1'], '4', G['A1'], 'M')
    # 24 V control: emergency stop in series with the selector, then the start button to I0.0
    wire(P['F1'], '2', F['S0'], '21')
    wire(F['S0'], '22', F['S1'], '1')
    wire(F['S1'], '2', F['S2'], '13')
    wire(F['S2'], '14', G['A1'], 'I0.0')
    # field switch to I0.1
    wire(P['F1'], '2', G['S3'], '1')
    wire(G['S3'], '2', G['A1'], 'I0.1')
    # outputs
    wire(G['A1'], 'Q0.0', G['K1'], 'A1')
    wire(G['K1'], 'A2', G['A1'], 'M')
    wire(G['A1'], 'Q0.1', F['H1'], 'X1')
    wire(F['H1'], 'X2', G['A1'], 'M')
    wire(G['A1'], 'Q0.1', F['B1'], 'X1')
    wire(F['B1'], 'X2', G['A1'], 'M')
    # relay contact switches the valve coil from the 24 V rail
    wire(P['F1'], '2', G['K1C'], '13')
    wire(G['K1C'], '14', G['Y1'], 'A1')
    wire(G['Y1'], 'A2', G['A1'], 'M')

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
    pg.text(frame + 20, ph - 38, 'Control panel: supply, 24 V control, PLC inputs and outputs, field devices (ILLUSTRATIVE demo sheet)', 11)
    pg.text(frame + 20, ph - 52, 'Generated by the Delta Engineering add-on on FreeCAD. Demo sheet only, not a design.', 7)

    # enclosure front outline around the door-mounted controls (illustrative)
    ex0, ex1 = X(3960), X(5660)
    ey0, ey1 = Y(-640), Y(-400)
    pg.rect(ex0, ey0, ex1 - ex0, ey1 - ey0, 1.0)
    pg.text(ex0 + 6, ey1 - 12, 'Enclosure front (illustrative): door-mounted controls and indicators', 7)

    for pts, lw, rgb in segs:
        pg.line([(X(a), Y(b)) for a, b in pts], lw, rgb)
    for t in texts:
        pg.text(X(t[0]), Y(t[1]), t[2], t[3] if len(t) > 3 else 8)
    heads = [(0, 'A. Supply: incoming L1 and N terminals, main breaker Q1, control transformer T1, 24 V fuse F1, PE'),
             (-400, 'B. Panel front: emergency stop S0, selector S1, start S2, indicator H1, buzzer B1'),
             (-980, 'C. Logic: PLC A1 (I0.0 / I0.1 inputs, Q0.0 / Q0.1 outputs), pressure switch S3, relay K1, valve Y1')]
    for hy, ht in heads:
        pg.text(frame + 20, Y(hy + 100), ht, 8)

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
             'A1 is drawn as a PLC block: 24 V supply on L+/M, two inputs (I0.0, I0.1), two outputs',
             '(Q0.0, Q0.1). No program, no input/output rating and no terminal list are shown.',
             'Outputs drive relay K1, lamp H1 and buzzer B1; the K1 contact switches valve coil Y1.',
             'Symbol shapes are illustrative, not certified IEC/ANSI symbols. Not a design: no rating,',
             'IP/NEMA, short-circuit, EMC or safety check.']
    ny = ty - 14
    pg.text(lx + 8, ny, 'Sheet notes', 8.5)
    for line in notes:
        ny -= 11
        pg.text(lx + 8, ny, line, 6)

    pg.rect(pw - 420, 20, 400, 62, 1.0)
    pg.text(pw - 410, 62, 'Control panel: supply, 24 V control, PLC I/O (ILLUSTRATIVE demo sheet)', 8.5)
    pg.text(pw - 410, 48, 'Symbol shapes come from the program symbol library; illustrative, not certified IEC/ANSI symbols.', 6.5)
    pg.text(pw - 410, 36, 'Not a design: no rating, IP/NEMA, short-circuit, EMC or safety check. Terminal marking after ABB catalogue.', 6.5)

    pg.save(PDF)
    res['pdf_bytes'] = os.path.getsize(PDF)
    d.saveAs(OUT + '/control_panel.FCStd')
    res['devices_supply'] = 7
    res['devices_front'] = 5
    res['devices_logic'] = 5
    res['done'] = True
except Exception:
    res['error'] = traceback.format_exc()
json.dump(res, open(OUT + '/result.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False))
