import os, json, time, traceback, ctypes
from ctypes import wintypes
OUT = os.environ.get('DELTA_OUT','C:/fit12')
os.makedirs(OUT, exist_ok=True)
res = {'steps': {}, 'dialogs': [], 'done': False}
def save():
    open(OUT + '/gui-result12.json', 'w', encoding='utf-8').write(json.dumps(res, ensure_ascii=False, indent=1, default=str))
def rss_mb():
    ctypes.windll.kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    ctypes.windll.psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD]
    class PMC(ctypes.Structure):
        _fields_ = [('cb', wintypes.DWORD), ('PageFaultCount', wintypes.DWORD), ('PeakWorkingSetSize', ctypes.c_size_t), ('WorkingSetSize', ctypes.c_size_t), ('QuotaPeakPagedPoolUsage', ctypes.c_size_t), ('QuotaPagedPoolUsage', ctypes.c_size_t), ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t), ('QuotaNonPagedPoolUsage', ctypes.c_size_t), ('PagefileUsage', ctypes.c_size_t), ('PeakPagefileUsage', ctypes.c_size_t)]
    c = PMC(); c.cb = ctypes.sizeof(c)
    ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.windll.kernel32.GetCurrentProcess(), ctypes.byref(c), c.cb)
    return round(c.WorkingSetSize / 1048576), round(c.PeakWorkingSetSize / 1048576)
try:
    import FreeCAD as App, FreeCADGui as Gui
    from PySide import QtCore, QtWidgets
    from PySide6 import QtTest
    import importlib.util
    _spec = importlib.util.find_spec('DeltaEngineering'); _pkg = list(_spec.submodule_search_locations)[0]
    _ns = {}; exec(open(_pkg + '/core_patches.py', encoding='utf-8-sig').read(), _ns); res['core_patches'] = _ns['apply'](_pkg)
    import DeltaEngineering.core, DeltaEngineering.domain
    from DeltaEngineering.gui import register
    if 'DeltaWorkbench' not in Gui.listWorkbenches(): register()
    Gui.activateWorkbench('DeltaWorkbench')
    mw = Gui.getMainWindow()
    counter = [0]
    def handle():
        w = QtWidgets.QApplication.activeModalWidget()
        if not w: return
        counter[0] += 1
        info = {'n': counter[0], 'cls': type(w).__name__, 'title': w.windowTitle()}
        try:
            w.grab().save(OUT + '/dlg9-%02d.png' % counter[0])
            if isinstance(w, QtWidgets.QInputDialog):
                info['label'] = w.labelText(); w.setTextValue('2 mm'); w.accept()
            elif isinstance(w, QtWidgets.QMessageBox):
                info['text'] = w.text()
                yes = [b for b in w.findChildren(QtWidgets.QPushButton) if b.text() in ('نعم', 'Yes', '&Yes')]
                if yes: yes[0].click()
                else: w.accept()
            elif isinstance(w, QtWidgets.QFileDialog):
                info['filedialog'] = True; w.reject()
            else:
                w.accept()
        except Exception:
            info['err'] = traceback.format_exc()
        res['dialogs'].append(info); save()
    t = QtCore.QTimer(); t.setInterval(400); t.timeout.connect(handle); t.start()
    def shot(name):
        try: mw.grab().save(OUT + '/' + name + '.png')
        except Exception: res['steps'][name + '_shot_err'] = traceback.format_exc()
    def run(name, fn):
        t0 = time.time()
        try:
            out = fn(); res['steps'][name] = {'ok': True, 'secs': round(time.time() - t0, 2), 'detail': out}
        except Exception:
            res['steps'][name] = {'ok': False, 'secs': round(time.time() - t0, 2), 'detail': traceback.format_exc()}
        save()
    def pump(n=5):
        for _ in range(n): QtWidgets.QApplication.processEvents()
    def step():
        from DeltaEngineering.drafting_panel import show_panel
        S = {}
        W = QtWidgets
        def sel(*objs):
            Gui.Selection.clearSelection()
            for o in objs: Gui.Selection.addSelection(o)
        def click(panel, text):
            b = [x for x in panel.findChildren(W.QPushButton) if x.text() == text]
            assert b, 'button not found: ' + text
            b[0].click(); pump()
        def viewport():
            mdi = mw.findChild(W.QMdiArea); sub = mdi.activeSubWindow()
            cand = [w for w in sub.findChildren(W.QWidget) if 'GLWidget' in w.metaObject().className() and w.isVisible()]
            return cand[-1]
        def layout_state(tag):
            vw = viewport()
            docks = [{'name': d.objectName(), 'w': d.width(), 'h': d.height(), 'floating': d.isFloating()} for d in mw.findChildren(W.QDockWidget) if d.isVisible()]
            scr = mw.screen().geometry()
            mh = mw.minimumSizeHint(); return {'screen': [scr.width(), scr.height()], 'window': [mw.width(), mw.height()], 'window_min_hint': [mh.width(), mh.height()], 'window_fits_screen': mw.height() <= scr.height() and mw.width() <= scr.width(), 'window_top_left': [mw.x(), mw.y()], 'viewport_px': [vw.width(), vw.height()], 'docks': docks}
        def metrics(root):
            bad = []; n = 0; overlaps = []
            for w in root.findChildren(W.QWidget):
                if not w.isVisible() or not isinstance(w, (W.QPushButton, W.QLabel, W.QLineEdit, W.QComboBox, W.QCheckBox, W.QSpinBox, W.QDoubleSpinBox)): continue
                n += 1
                h = w.height(); wd = w.width(); txt = getattr(w, 'text', lambda: '')() if hasattr(w, 'text') else ''
                if isinstance(w, W.QLabel) and w.wordWrap():
                    need = w.heightForWidth(wd) if w.hasHeightForWidth() else w.sizeHint().height()
                else:
                    need = w.sizeHint().height()
                tw = w.fontMetrics().horizontalAdvance(txt) if (txt and not (isinstance(w, W.QLabel) and w.wordWrap())) else 0
                short = h < need - 1
                narrow = isinstance(w, W.QPushButton) and tw + 12 > wd
                if short or narrow: bad.append({'cls': type(w).__name__, 'text': txt[:40], 'h': h, 'need_h': need, 'w': wd, 'text_w': tw, 'short': short, 'narrow': narrow})
            for par in root.findChildren(W.QWidget):
                kids = [k for k in par.children() if isinstance(k, W.QPushButton) and k.isVisible()]
                for i in range(len(kids)):
                    for j in range(i + 1, len(kids)):
                        if kids[i].geometry().intersects(kids[j].geometry()):
                            overlaps.append([kids[i].text()[:25], kids[j].text()[:25]])
            return {'checked_widgets': n, 'clipped_count': len(bad), 'clipped_first': bad[:14], 'overlapping_buttons': overlaps[:10], 'overlap_count': len(overlaps)}
        def s_panel_tab():
            Gui.runCommand('Delta_NewProject'); pump(10)
            td = mw.findChild(W.QDockWidget, 'Tasks')
            out = {'tasks_dock_before_panel': {'exists': td is not None, 'visible': bool(td and td.isVisible()), 'size': [td.width(), td.height()] if td else None,
                   'child_widgets': sorted(set(type(c).__name__ for c in td.findChildren(W.QWidget)))[:12] if td else None, 'active_dialog': bool(Gui.Control.activeDialog())},
                   'viewport_before': [viewport().width(), viewport().height()]}
            p = show_panel(); S['p'] = p; pump(25)
            td = mw.findChild(W.QDockWidget, 'Tasks')
            out['tasks_dock_after_panel_visible'] = bool(td and td.isVisible()); out['viewport_after'] = [viewport().width(), viewport().height()]
            idx = [i for i in range(p.tabs.count()) if p.tabs.tabText(i) == 'وصلات ومحطة']
            assert idx, 'fittings tab missing: ' + str([p.tabs.tabText(i) for i in range(p.tabs.count())])
            p.tabs.setCurrentIndex(idx[0]); pump(15)
            sa = p.tabs.currentWidget(); hb = sa.horizontalScrollBar(); vb = sa.verticalScrollBar()
            out.update({'tab_index': idx[0], 'metrics': metrics(p), 'layout': layout_state('fit'),
                        'horizontal_scroll_needed': hb.maximum() > 0, 'hbar_max': hb.maximum(), 'content_w': sa.widget().width(), 'viewport_w': sa.viewport().width(), 'vbar_max': vb.maximum()})
            shot('fit12-A-tab')
            class TaskStub:
                def __init__(self):
                    self.form = W.QLabel('Test task panel')
                def getStandardButtons(self): return int(W.QDialogButtonBox.Close)
                def reject(self): Gui.Control.closeDialog()
            Gui.Control.showDialog(TaskStub()); pump(30)
            td = mw.findChild(W.QDockWidget, 'Tasks')
            out['tasks_dock_visible_when_task_dialog_opens'] = bool(td and td.isVisible()); shot('fit12-A2-task-dialog')
            Gui.Control.closeDialog(); pump(20)
            return out
        run('fittings_tab_present_and_layout', s_panel_tab)
        import DeltaEngineering.fittings as F
        def s_station_ui():
            p = S['p']; fp = p.fittings; d = App.ActiveDocument; out = {}
            def make(kind, n1, n2=None):
                fp.kind.setCurrentIndex(fp.kind.findData(kind)); fp.size1.setCurrentIndex(fp.size1.findText(n1))
                if n2: fp.size2.setCurrentIndex(fp.size2.findText(n2))
                fp.length.setText(''); before = set(o.Name for o in d.Objects)
                click(fp, 'إنشاء القطعة')
                new = [o for o in d.Objects if o.Name not in before and hasattr(o, 'FittingKind')]
                assert len(new) == 1, ('create via UI failed', kind, p.status.text())
                return new[0]
            def join(moving, mp, fixed, fp_):
                fp.port_move.setCurrentIndex(mp); fp.port_fixed.setCurrentIndex(fp_); sel(moving, fixed)
                click(fp, 'وصل المنفذ بالمنفذ')
            pump_o = make('pump', '3', '2')
            pump_o.Placement = App.Placement(App.Vector(1000, -400, 250), App.Rotation(App.Vector(1, 2, 3), 37)); d.recompute()
            f1 = make('flange', '2'); join(f1, 0, pump_o, 1)
            v1 = make('gate_valve', '2'); join(v1, 0, f1, 1)
            f2 = make('flange', '2'); join(f2, 0, v1, 1)
            rd = make('reducer', '2', '4'); join(rd, 0, f2, 1)
            bv = make('ball_valve', '4'); join(bv, 0, rd, 1)
            s1 = make('flange', '3'); join(s1, 0, pump_o, 0)
            cv = make('check_valve', '3'); join(cv, 0, s1, 1)
            S['objs'] = [pump_o, f1, v1, f2, rd, bv, s1, cv]
            rep = F.check_continuity(d)
            click(fp, 'فحص الاستمرارية والتداخل'); out['report_text'] = fp.report.toPlainText()
            out['connected'] = len(rep['connected']); out['open_ports'] = rep['open_ports']; out['errors'] = rep['errors']
            assert rep['ok'] and len(rep['connected']) == 7 and len(rep['open_ports']) == 2, rep
            v = Gui.ActiveDocument.ActiveView; v.viewAxonometric(); v.fitAll(); pump(40); shot('fit12-B-station')
            out['metrics_after'] = metrics(p); return out
        run('station_built_through_panel_buttons', s_station_ui)
        def s_mismatch_ui():
            p = S['p']; fp = p.fittings; d = App.ActiveDocument
            fp.kind.setCurrentIndex(fp.kind.findData('flange')); fp.size1.setCurrentIndex(fp.size1.findText('4'))
            before = set(o.Name for o in d.Objects); click(fp, 'إنشاء القطعة')
            fl4 = [o for o in d.Objects if o.Name not in before][0]; pl0 = App.Placement(fl4.Placement)
            fp.port_move.setCurrentIndex(0); fp.port_fixed.setCurrentIndex(1); sel(fl4, S['objs'][1]); n0 = len(res['dialogs'])
            click(fp, 'وصل المنفذ بالمنفذ'); pump(30); time.sleep(1.0); pump(30)
            same = fl4.Placement.isSame(pl0, 1e-9)
            assert same
            d.removeObject(fl4.Name); d.recompute()
            return {'placement_unchanged': same, 'status': p.status.text(), 'new_dialogs': res['dialogs'][n0:]}
        run('mismatch_refused_through_ui', s_mismatch_ui)
        def s_csv_ui():
            p = S['p']; fp = p.fittings; d = App.ActiveDocument
            path = 'C:/Users/Public/اختبار/الكميات.csv'; os.makedirs(os.path.dirname(path), exist_ok=True)
            rows = fp.export_csv(path); text = open(path, encoding='utf-8-sig').read()
            assert sum(r['qty'] for r in rows if r['kind'] != 'tube') == 8, rows
            assert 'continuity only' in text
            fp.report.setPlainText(fp.report.toPlainText()); pump(10); shot('fit12-C-after-export')
            return {'rows': rows, 'csv_bytes': os.path.getsize(path)}
        run('quantity_csv_through_panel', s_csv_ui)
        def s_save_reopen_gui():
            d = App.ActiveDocument; path = 'C:/Users/Public/اختبار/محطة.FCStd'
            vols = {o.Name: o.Shape.Volume for o in d.Objects if hasattr(o, 'FittingKind')}
            d.saveAs(path); App.closeDocument(d.Name); d2 = App.openDocument(path); d2.recompute(); pump(30)
            diff = max(abs(d2.getObject(n).Shape.Volume - v) for n, v in vols.items())
            rep = F.check_continuity(d2); assert rep['ok'] and len(rep['connected']) == 7 and diff < 1e-6, (rep, diff)
            return {'objects': len(vols), 'max_volume_diff': diff, 'connections': len(rep['connected'])}
        run('save_reopen_arabic_path', s_save_reopen_gui)
        def s_station2():
            import math as M
            Gui.runCommand('Delta_NewProject'); pump(15)
            p = S['p']; fp = p.fittings; d = App.ActiveDocument; out = {}
            from DeltaEngineering.tube_library import PRESETS as PR
            def make(kind, n1, n2=None, ln=None):
                fp.kind.setCurrentIndex(fp.kind.findData(kind)); fp.size1.setCurrentIndex(fp.size1.findText(n1))
                if n2: fp.size2.setCurrentIndex(fp.size2.findText(n2))
                fp.length.setText(('%g mm' % ln) if ln else ''); before = set(o.Name for o in d.Objects)
                click(fp, 'إنشاء القطعة')
                new = [o for o in d.Objects if o.Name not in before and hasattr(o, 'FittingKind')]
                assert len(new) == 1, ('create failed', kind, p.status.text()); return new[0]
            def join(a, ap, b, bp):
                fp.port_move.setCurrentIndex(ap); fp.port_fixed.setCurrentIndex(bp); sel(a, b); click(fp, 'وصل المنفذ بالمنفذ')
            pm = make('pump', '3', '2')
            chain = []
            def run_from(start, sp, items):
                prev, pp_ = start, sp
                for kind, n1, n2, ln in items:
                    o = make(kind, n1, n2, ln); join(o, 0, prev, pp_); chain.append(o); prev, pp_ = o, 1
                return prev
            run_from(pm, 0, [('flange', '3', None, None), ('pipe', '3', None, 1200), ('check_valve', '3', None, None), ('pipe', '3', None, 600)])
            last = run_from(pm, 1, [('flange', '2', None, None), ('gate_valve', '2', None, None), ('flange', '2', None, None), ('pipe', '2', None, 800),
                                    ('elbow90', '2', None, None), ('pipe', '2', None, 600), ('reducer', '2', '4', None), ('ball_valve', '4', None, None), ('pipe', '4', None, 1500)])
            elbows = [o for o in d.Objects if getattr(o, 'FittingKind', '') == 'elbow90']
            e = elbows[0]; R = e.Length.Value; ro = e.OuterDiameter.Value / 2; ri = ro - e.WallThickness.Value
            exp = M.pi * (ro * ro - ri * ri) * (M.pi * R / 2)
            out['elbow_volume'] = e.Shape.Volume; out['elbow_expected_pappus'] = exp
            assert abs(e.Shape.Volume - exp) / exp < 1e-6, (e.Shape.Volume, exp)
            rep = F.check_continuity(d); click(fp, 'فحص الاستمرارية والتداخل')
            out['report_text'] = fp.report.toPlainText(); out['connected'] = len(rep['connected']); out['open_ports'] = rep['open_ports']; out['errors'] = rep['errors']
            n_fit = len([o for o in d.Objects if hasattr(o, 'FittingKind')])
            assert rep['ok'] and len(rep['connected']) == n_fit - 1 and len(rep['open_ports']) == 2, (rep, n_fit)
            bom = F.takeoff(d); out['takeoff'] = bom
            tubes = {r['size']: r['qty'] for r in bom if r['kind'] == 'tube'}
            exp_t = {'OD 88.9 x 5.49 mm': 1.8, 'OD 60.3 x 3.91 mm': 1.4, 'OD 114.3 x 6.02 mm': 1.5}
            assert {k: round(v, 6) for k, v in tubes.items()} == exp_t, (tubes, exp_t)
            v = Gui.ActiveDocument.ActiveView; v.viewAxonometric(); v.fitAll(); pump(40); shot('fit12-D-station2'); out['model_extent_mm'] = [round(x) for x in (lambda bb: (bb.XLength, bb.YLength, bb.ZLength))(__import__('functools').reduce(lambda a, o: (a.add(o.Shape.BoundBox), a)[1], [o for o in d.Objects if hasattr(o, 'FittingKind')], App.BoundBox()))]
            return out
        run('station_with_pipes_elbow_through_panel', s_station2)
        def s_pdf():
            from DeltaEngineering.scaled_output import export_scaled
            d = App.ActiveDocument; out = {}; base = 'C:/Users/Public/اختبار'
            for view in ('Top', 'Front'):
                done = None
                for den in (10, 15, 20, 30, 50):
                    path = base + '/محطة-' + view + '.pdf'
                    try:
                        r = export_scaled(d, path, den, view_name=view); done = (den, r); break
                    except ValueError as e:
                        out[view + '_denominator_%d_rejected' % den] = str(e)[:80]
                assert done, 'no scale fit'
                out[view] = {'denominator': done[0], 'bytes': os.path.getsize(path), 'result': done[1]}
                import shutil; shutil.copy(path, OUT + '/station-' + view + '.pdf')
            return out
        run('station_scaled_pdf', s_pdf)
        def s_starter():
            from DeltaEngineering.symbols import create, TEMPLATES
            from DeltaEngineering.domain import add_terminal_wire, netlist
            from DeltaEngineering import connectivity
            from DeltaEngineering.export import export_current
            from DeltaEngineering.panel import show_panel as show_el
            d = App.ActiveDocument; out = {}
            e = show_el(); pump(20); out['template_combo_items'] = e.template.count(); out['template_keys'] = list(TEMPLATES)
            from DeltaEngineering.electrical import terminal_layout, wire_offset
            bb = d.getObject('ElectricalSystem'); X0 = 4000
            doc_visible_others = [o for o in d.Objects if hasattr(o, 'ViewObject') and o.ViewObject is not None and hasattr(o, 'Shape') and not hasattr(o, 'DeviceType') and not hasattr(o, 'SourceTerminal') and o.ViewObject.Visibility]
            for o in doc_visible_others: o.ViewObject.Visibility = False
            Q = create(d, 'Breaker concept', 'Q1', App.Vector(X0, 0, 0)); K = create(d, 'Contactor concept', 'KM1', App.Vector(X0 + 400, 0, 0))
            O = create(d, 'Overload concept', 'F1', App.Vector(X0 + 400, -300, 0)); M = create(d, 'Motor concept', 'M1', App.Vector(X0 + 400, -600, 0))
            for dev in (K, O, M): terminal_layout(d, dev, list(dev.Terminals), 'Left')
            n = 0; wires = []
            for a, b, pairs in ((Q, K, [('2', '1'), ('4', '3'), ('6', '5')]), (K, O, [('2', '1'), ('4', '3'), ('6', '5')]), (O, M, [('2', 'U'), ('4', 'V'), ('6', 'W')])):
                for sa, sb in pairs:
                    n += 1; wires.append(add_terminal_wire(d, a, sa, b, sb, 'W%d' % n))
            for i, w in enumerate(wires[3:6]): wire_offset(d, w, -(15 + 12 * i))
            for i, w in enumerate(wires[6:9]): wire_offset(d, w, -(15 + 12 * i))
            d.recompute(); rows = netlist(d); out['wires'] = len(rows)
            assert len(rows) == 9
            rep = connectivity.inspect(d); out['connectivity'] = json.loads(json.dumps(rep, default=str))
            shape_ok = all(not o.Shape.isNull() and o.Shape.isValid() for o in (Q, K, O, M)); out['symbol_shapes_valid'] = shape_ok; assert shape_ok
            base = 'C:/Users/Public/اختبار'
            r = export_current(d, base + '/ميكانيكا.pdf', base + '/كهرباء.pdf'); out['export'] = r
            import shutil; shutil.copy(base + '/ميكانيكا.pdf', OUT + '/station-starter-mech.pdf'); shutil.copy(base + '/كهرباء.pdf', OUT + '/station-starter-elec.pdf')
            Gui.Selection.clearSelection()
            for o in (Q, K, O, M): Gui.Selection.addSelection(o)
            Gui.activeDocument().activeView().viewTop(); Gui.SendMsgToActiveView('ViewSelection'); pump(30); Gui.Selection.clearSelection(); pump(10)
            shot('fit12-F-electrical-view')
            out['bboxes'] = {o.Label: [round(v, 1) for v in (o.Shape.BoundBox.XMin, o.Shape.BoundBox.YMin, o.Shape.BoundBox.XMax, o.Shape.BoundBox.YMax)] for o in (Q, K, O, M)}
            out['wire_shape_lengths'] = [round(w.Shape.Length, 1) for w in wires]
            out['vis'] = {o.Label: bool(o.ViewObject.Visibility) for o in (Q, K, O, M)}
            diag = {}
            vo = Q.ViewObject
            diag['display_modes'] = list(vo.listDisplayModes()); diag['display_mode'] = vo.DisplayMode; diag['shape_type'] = Q.Shape.ShapeType; diag['edges'] = len(Q.Shape.Edges)
            diag['type_id'] = Q.TypeId; diag['vo_type'] = type(vo).__name__; diag['vo_visible'] = bool(vo.Visibility)
            diag['camera'] = Gui.activeDocument().activeView().getCameraType()
            import Part
            ctl = d.addObject('Part::Feature', 'CtlLine'); ctl.Shape = Part.makeLine(App.Vector(X0, 100, 0), App.Vector(X0 + 400, 100, 0)); d.recompute()
            diag['ctl_edges'] = len(ctl.Shape.Edges)
            Gui.Selection.clearSelection()
            for o in (Q, K, O, M, ctl): Gui.Selection.addSelection(o)
            Gui.SendMsgToActiveView('ViewSelection'); pump(30); Gui.Selection.clearSelection(); pump(10); shot('fit12-G1-with-control-line')
            for mode in ('Wireframe', 'Flat Lines'):
                try:
                    for o in (Q, K, O, M): o.ViewObject.DisplayMode = mode
                    pump(20); shot('fit12-G2-' + mode.replace(' ', ''))
                except Exception as ex: diag['mode_err_' + mode] = str(ex)
            Gui.activeDocument().activeView().viewIsometric(); Gui.SendMsgToActiveView('ViewFit'); pump(30); shot('fit12-G3-iso-fit-all')
            out['diag'] = diag
            out['overlay_titles_visible_after_view_steps'] = [w.isVisible() for w in mw.findChildren(W.QWidget, 'OverlayTitle') if w.parentWidget() is not None and w.parentWidget().objectName() == 'OverlayRight']
            _td = mw.findChild(W.QDockWidget, 'Tasks'); out['tasks_dock_visible_after_view_steps'] = bool(_td and _td.isVisible())
            d.removeObject(ctl.Name)

            for o in doc_visible_others: o.ViewObject.Visibility = True
            return_note = 'electrical view fitted on the 4 starter devices'
            return out
        run('motor_starter_circuit_symbols_and_pdf', s_starter)
        def s_strip_probe():
            W_ = W; out = []
            for w in mw.findChildren(W_.QWidget):
                if not w.isVisible(): continue
                g = w.mapTo(mw, W_.QWidget().rect().topLeft()) if False else w.mapTo(mw, w.rect().topLeft())
                r = [g.x(), g.y(), w.width(), w.height()]
                if r[1] < 330 and r[1] + r[3] > 250 and r[0] > 500 and r[0] < 980 and r[2] > 20 and r[3] < 60:
                    chain = []; q = w
                    while q is not None and len(chain) < 6: chain.append(type(q).__name__ + ':' + q.objectName()); q = q.parentWidget()
                    out.append({'rect': r, 'cls': type(w).__name__, 'name': w.objectName(), 'title': getattr(w, 'windowTitle', lambda: '')(), 'chain': chain})
            docks = [{'name': dk.objectName(), 'title': dk.windowTitle(), 'visible': dk.isVisible(), 'floating': dk.isFloating(), 'geom': [dk.x(), dk.y(), dk.width(), dk.height()]} for dk in mw.findChildren(W_.QDockWidget)]
            return {'widgets_near_strip': out[:15], 'docks': docks}
        run('strip_probe', s_strip_probe)
        def s_tasks_after_dialog():
            class TaskStub:
                def __init__(self): self.form = W.QLabel('Test task panel')
                def getStandardButtons(self): return int(W.QDialogButtonBox.Close)
                def reject(self): Gui.Control.closeDialog()
            Gui.Control.showDialog(TaskStub()); pump(20); td = mw.findChild(W.QDockWidget, 'Tasks'); vis_open = bool(td and td.isVisible())
            Gui.Control.closeDialog(); t0 = time.time()
            while time.time() - t0 < 4: pump(5); time.sleep(0.1)
            vis_after = bool(td and td.isVisible()); strips = [w for w in mw.findChildren(W.QWidget, 'OverlayTitle')]; shot('fit12-E-after-task-closed')
            Gui.Control.showDialog(TaskStub()); pump(20); strips_open = [w.isVisible() for w in strips]; Gui.Control.closeDialog()
            return {'visible_while_task_open': vis_open, 'visible_after_close_and_4s': vis_after, 'overlay_title_visible_after_close': [w.isVisible() for w in strips], 'overlay_title_visible_while_task_open_2nd': strips_open}
        run('tasks_dock_hidden_again_after_task_closes', s_tasks_after_dialog)
        res['done'] = True; save()
        QtCore.QTimer.singleShot(1500, lambda: os._exit(0))
    QtCore.QTimer.singleShot(6000, step)
except Exception:
    res['error'] = traceback.format_exc(); res['done'] = True; save()

