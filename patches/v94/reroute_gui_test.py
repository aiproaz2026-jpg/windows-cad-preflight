# -*- coding: utf-8 -*-
"""GUI test of the Delta_Wire_Reroute command (installed app, FreeCAD GUI macro, Mesa software GL in CI).
Steps: registration, menu and toolbar present once, command run through Gui.runCommand reroutes a small sheet,
re-register is idempotent. Result: $DELTA_OUT/wirereroute-result.json. GPL-3.0-or-later."""
import os, json, time, traceback
OUT = os.environ.get('DELTA_OUT', 'C:/seed/wr_gui2')
os.makedirs(OUT, exist_ok=True)
res = {'steps': {}, 'done': False}


def save():
    open(OUT + '/wirereroute-result.json', 'w', encoding='utf-8').write(json.dumps(res, ensure_ascii=False, indent=1, default=str))


try:
    import FreeCAD as App, FreeCADGui as Gui
    from PySide import QtCore, QtWidgets

    def pump(n=5):
        for _ in range(n):
            QtWidgets.QApplication.processEvents()

    def run(name, fn):
        t0 = time.time()
        try:
            res['steps'][name] = {'ok': True, 'secs': round(time.time() - t0, 2), 'detail': fn()}
        except Exception:
            res['steps'][name] = {'ok': False, 'secs': round(time.time() - t0, 2), 'detail': traceback.format_exc()}
        save()

    def step():
        from DeltaEngineering.gui import register as wb_register
        from DeltaEngineering import wire_reroute_cmd as WC, wire_route as R
        if 'DeltaWorkbench' not in Gui.listWorkbenches():
            wb_register()
        Gui.activateWorkbench('DeltaWorkbench')
        pump(20)
        mw = Gui.getMainWindow()
        TITLE = 'إعادة توجيه الأسلاك'
        CMD = 'Delta_Wire_Reroute'

        def s_reg():
            cmd = Gui.Command.get(CMD)
            assert cmd is not None, CMD + ' not registered'
            r = WC._Cmd().GetResources()
            assert TITLE in r.get('MenuText', ''), r
            return {'registered': True, 'menutext': r.get('MenuText'), 'patched': bool(getattr(__import__('DeltaEngineering.gui', fromlist=['x']).DeltaWorkbench, '_wr_patched', False))}
        run('registration', s_reg)

        def s_menu():
            pump(20)
            menus = [m for m in mw.findChildren(QtWidgets.QMenu) if m.title() == TITLE]
            tbs = [t for t in mw.findChildren(QtWidgets.QToolBar) if t.windowTitle() == TITLE]
            out = {'menus': len(menus), 'toolbars': len(tbs), 'menu_actions': [a.text() for a in menus[0].actions()] if menus else []}
            try:
                mw.grab().save(OUT + '/wr-main.png')
            except Exception:
                out['shot_err'] = traceback.format_exc()
            assert len(menus) == 1 and len(tbs) >= 1, out
            return out
        run('menu_toolbar', s_menu)

        def s_cmd():
            from DeltaEngineering.symbols import create
            from DeltaEngineering.domain import add_terminal_wire
            try:
                from DeltaEngineering import term_ends2 as TE
                TE.install()
            except Exception:
                pass
            V = App.Vector
            R.apply_orig = R.apply
            R.apply = lambda obj, doc=None: False      # stock wires: call site off while building
            doc = App.newDocument('WRTest')
            Q = create(doc, 'Breaker 3P (illustr.)', 'Q1', V(0, 0, 0))
            K = create(doc, 'Contactor 3P (illustr.)', 'K1', V(60, -200, 0))
            for i, (a, b) in enumerate((('2', '1L1'), ('4', '3L2'), ('6', '5L3'))):
                add_terminal_wire(doc, Q, a, K, b, 'W%d' % (i + 1))
            doc.recompute()
            doc.recompute()
            wires = [o for o in doc.Objects if hasattr(o, 'SourceTerminal')]
            assert len(wires) == 3, len(wires)
            before = [round(o.Shape.Length, 1) for o in wires if not o.Shape.isNull()]
            before_valid = [o.Validation for o in wires]
            before_ov, before_cr = len(R.overlaps(doc)), len(R.crossings(doc))
            before_edges = [len(o.Shape.Edges) for o in wires]
            R.apply = R.apply_orig                 # call site back on, then run the command on the stock sheet
            calls = {'info': [], 'warn': []}
            oi, ow = QtWidgets.QMessageBox.information, QtWidgets.QMessageBox.warning

            def fi(*a, **k):
                calls['info'].append(str(a[2]) if len(a) > 2 else str(a))
                return QtWidgets.QMessageBox.Ok

            def fw(*a, **k):
                calls['warn'].append(str(a[2]) if len(a) > 2 else str(a))
                return QtWidgets.QMessageBox.Ok
            try:
                QtWidgets.QMessageBox.information = staticmethod(fi)
                QtWidgets.QMessageBox.warning = staticmethod(fw)
                Gui.runCommand(CMD)
                pump(10)
            finally:
                QtWidgets.QMessageBox.information, QtWidgets.QMessageBox.warning = oi, ow
            after = [round(o.Shape.Length, 1) for o in wires if not o.Shape.isNull()]
            valid = [o.Validation for o in wires]
            out = {'before_edges': before_edges, 'after_edges': [len(o.Shape.Edges) for o in wires], 'before_validation': before_valid, 'before_overlaps': before_ov, 'before_crossings': before_cr, 'before_lengths': before, 'after_lengths': after, 'validation': valid, 'info': calls['info'], 'warn': calls['warn'], 'overlaps': len(R.overlaps(doc)), 'crossings': len(R.crossings(doc))}
            assert not calls['warn'], calls
            assert len(calls['info']) == 1 and '3' in calls['info'][0], calls
            assert len(after) == 3 and all(l > 0 for l in after), out
            App.closeDocument(doc.Name)
            return out
        run('command_reroutes_sheet', s_cmd)

        def s_rereg():
            WC.register()
            pump(10)
            menus = [m for m in mw.findChildren(QtWidgets.QMenu) if m.title() == TITLE]
            tbs = [t for t in mw.findChildren(QtWidgets.QToolBar) if t.windowTitle() == TITLE]
            out = {'menus': len(menus), 'toolbars': len(tbs)}
            assert len(menus) == 1 and len(tbs) == 1, out
            return out
        run('reregister_idempotent', s_rereg)
        res['done'] = True
        save()
        QtCore.QTimer.singleShot(1500, lambda: os._exit(0))

    QtCore.QTimer.singleShot(6000, step)
except Exception:
    res['error'] = traceback.format_exc()
    res['done'] = True
    save()
