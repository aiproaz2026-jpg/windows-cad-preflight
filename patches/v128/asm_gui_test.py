# -*- coding: utf-8 -*-
"""Delta v128: drive the two assembly commands through the real GUI command dispatch and the real Qt input dialogs.
FCMacro run on the installed app (CI Windows Server 2022, Mesa software GL). Result: $DELTA_OUT/asmgui-result.json. GPL-3.0-or-later."""
import os, json, time, traceback
OUT = os.environ.get('DELTA_OUT', 'C:/seed/asmgui')
os.makedirs(OUT, exist_ok=True)
res = {'steps': {}, 'done': False}


def save():
    open(OUT + '/asmgui-result.json', 'w', encoding='utf-8').write(json.dumps(res, ensure_ascii=False, indent=1, default=str))


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

    seen = []

    def answer(plan):
        """Poll for modal dialogs; answer QInputDialogs from plan (list of values), record titles/labels/items. Close message boxes."""
        state = {'i': 0}
        timer = QtCore.QTimer()

        def tick():
            w = QtWidgets.QApplication.activeModalWidget()
            if w is None:
                return
            if isinstance(w, QtWidgets.QInputDialog):
                items = list(w.comboBoxItems()) if w.comboBoxItems() else []
                seen.append({'title': w.windowTitle(), 'label': w.labelText(), 'items': items})
                if state['i'] < len(plan):
                    v = plan[state['i']]; state['i'] += 1
                    if items:
                        w.setTextValue(v)
                    else:
                        w.setDoubleValue(float(v))
                    w.accept()
                else:
                    w.reject()
            else:
                seen.append({'msgbox': w.windowTitle(), 'text': w.findChild(QtWidgets.QLabel).text() if w.findChild(QtWidgets.QLabel) else ''})
                w.close()
        timer.timeout.connect(tick)
        timer.start(250)
        return timer, state

    def yaw(o):
        return o.Placement.Rotation.toEuler()[0]

    def step():
        from DeltaEngineering.gui import register as wb_register
        from DeltaEngineering import assembly_simple as AS
        if 'DeltaWorkbench' not in Gui.listWorkbenches():
            wb_register()
        Gui.activateWorkbench('DeltaWorkbench')
        pump(20)

        def mk(name):
            d = App.newDocument(name)
            a = d.addObject('Part::Box', 'BoxA'); b = d.addObject('Part::Box', 'BoxB')
            for o in (a, b):
                o.Length = 100; o.Width = 20; o.Height = 20
            b.Placement.Base = App.Vector(100, 0, 0)
            d.recompute()
            return d, a, b

        def s_registered():
            mw = Gui.getMainWindow()
            out = {'make': Gui.Command.get('Delta_Asm_Make') is not None, 'move': Gui.Command.get('Delta_Asm_Move') is not None}
            tbs = [t for t in mw.findChildren(QtWidgets.QToolBar) if t.windowTitle() == 'التجميع']
            out['toolbar_count'] = len(tbs)
            out['toolbar_actions'] = [a.text() for a in tbs[0].actions()] if tbs else []
            assert out['make'] and out['move'] and len(tbs) == 1, out
            return out
        run('commands_and_toolbar', s_registered)

        st = {}

        def s_make_revolute():
            d, a, b = mk('AsmGui1'); st['d'], st['a'], st['b'] = d, a, b
            Gui.ActiveDocument = Gui.getDocument(d.Name)
            Gui.Selection.clearSelection(); Gui.Selection.addSelection(a); Gui.Selection.addSelection(b)
            seen.clear()
            tm, state = answer(['مفصل دوران', 'Z', 30])
            Gui.runCommand('Delta_Asm_Make', 0)
            tm.stop(); pump(10)
            out = {'dialogs': list(seen), 'answered': state['i'], 'b_yaw': yaw(b), 'a_base': str(a.Placement.Base),
                   'assembly_objs': [o.TypeId for o in d.Objects if o.TypeId.startswith('Assembly::')],
                   'joint_types': [o.JointType for o in d.Objects if hasattr(o, 'JointType')]}
            assert state['answered'] == 3, out
            assert abs(yaw(b) - 30) < 1e-6, out
            return out
        run('make_revolute_30deg_via_dialogs', s_make_revolute)

        def s_move():
            d, a, b = st['d'], st['a'], st['b']
            j = [o for o in d.Objects if hasattr(o, 'JointType') and o.JointType == 'Revolute'][0]
            Gui.Selection.clearSelection(); Gui.Selection.addSelection(j)
            seen.clear()
            tm, state = answer([60])
            Gui.runCommand('Delta_Asm_Move', 0)
            tm.stop(); pump(10)
            pt = min((v.Point for v in b.Shape.Vertexes), key=lambda p: (p - App.Vector(100, 0, 0)).Length)
            out = {'dialogs': list(seen), 'answered': state['i'], 'b_yaw': yaw(b), 'pivot_dev': (pt - App.Vector(100, 0, 0)).Length}
            assert state['answered'] == 1 and abs(yaw(b) - 60) < 1e-6 and out['pivot_dev'] < 1e-3, out
            return out
        run('move_joint_to_60deg_via_dialog', s_move)

        def s_wrong_selection():
            d, a, b = st['d'], st['a'], st['b']
            Gui.Selection.clearSelection(); Gui.Selection.addSelection(a)
            seen.clear()
            tm, state = answer([])
            Gui.runCommand('Delta_Asm_Make', 0)
            tm.stop(); pump(10)
            out = {'seen': list(seen)}
            assert any('msgbox' in s for s in seen), out
            return out
        run('one_part_selected_shows_message', s_wrong_selection)

        def s_slider():
            d, c, e = mk('AsmGui2')
            Gui.ActiveDocument = Gui.getDocument(d.Name)
            Gui.Selection.clearSelection(); Gui.Selection.addSelection(c); Gui.Selection.addSelection(e)
            seen.clear()
            tm, state = answer(['منزلق', 'X', 25])
            Gui.runCommand('Delta_Asm_Make', 0)
            tm.stop(); pump(10)
            mx = min(v.Point.x for v in e.Shape.Vertexes)
            out = {'dialogs': list(seen), 'answered': state['i'], 'd_min_x': mx}
            assert state['answered'] == 3 and abs(mx - 125) < 1e-6, out
            return out
        run('make_slider_25mm_via_dialogs', s_slider)

        def s_save_reopen():
            d = st['d']
            p = OUT + '/asm_gui.FCStd'
            d.saveAs(p); App.closeDocument(d.Name)
            d2 = App.openDocument(p); d2.recompute()
            b = d2.getObject('BoxB')
            return {'b_yaw_after_reopen': yaw(b), 'size': os.path.getsize(p)}
        run('save_reopen_keeps_pose', s_save_reopen)
        res['done'] = True
        save()
        QtCore.QTimer.singleShot(1500, lambda: os._exit(0))

    QtCore.QTimer.singleShot(6000, step)
except Exception:
    res['error'] = traceback.format_exc()
    res['done'] = True
    save()
