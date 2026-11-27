import os, json, re, traceback
OUT = os.environ.get('DELTA_OUT', 'C:/fit73'); os.makedirs(OUT, exist_ok=True)
res = {'done': False, 'misses': {}, 'seen': 0}
def save():
    open(OUT + '/ui-sweep-result.json', 'w', encoding='utf-8').write(json.dumps(res, ensure_ascii=False, indent=1, default=str))
try:
    import FreeCAD as App, FreeCADGui as Gui
    from PySide import QtCore, QtWidgets, QtGui
    from PySide6 import QtTest
    import importlib.util
    _spec = importlib.util.find_spec('DeltaEngineering'); _pkg = list(_spec.submodule_search_locations)[0]
    import os as _os
    if _os.path.exists(_pkg + '/core_patches.py'):
        _ns = {}; exec(open(_pkg + '/core_patches.py', encoding='utf-8-sig').read(), _ns); _ns['apply'](_pkg)
    import DeltaEngineering.core, DeltaEngineering.domain
    from DeltaEngineering.gui import register
    if 'DeltaWorkbench' not in Gui.listWorkbenches(): register()
    from DeltaEngineering import ar_layer as L
    mw = Gui.getMainWindow()
    LAT = re.compile(r'[A-Za-z]{3,}')
    def check(kind, s, wb):
        if not s: return
        s = str(s)
        for line in re.sub(r'<[^>]+>', '\n', s).split('\n'):
            t = ' '.join(line.replace('&', '').split())
            if len(t) < 3 or not LAT.search(t) or re.search(r'[\u0600-\u06FF]', t): continue
            res['seen'] += 1
            if L._lk(L._n(t)): continue
            res['misses'].setdefault(t, set()).add(kind + ':' + wb)
    def walk(wb):
        for a in mw.findChildren(QtGui.QAction):
            check('action', a.text(), wb); check('tip', a.toolTip(), wb); check('status', a.statusTip(), wb)
            m = a.menu()
            if m is not None: check('menu', m.title(), wb)
        for w in mw.findChildren(QtWidgets.QWidget):
            for fn in ('windowTitle', 'text', 'title', 'toolTip', 'placeholderText'):
                f = getattr(w, fn, None)
                if f is None: continue
                try: v = f()
                except Exception: continue
                if isinstance(v, str): check(fn + ':' + w.__class__.__name__, v, wb)
            if isinstance(w, QtWidgets.QTabBar):
                for i in range(w.count()): check('tab', w.tabText(i), wb)
            if isinstance(w, QtWidgets.QComboBox):
                for i in range(w.count()): check('combo', w.itemText(i), wb)
    def pump(n=10):
        for _ in range(n):
            QtWidgets.QApplication.processEvents(); QtTest.QTest.qWait(100)
    def step():
        try:
            for wb in ['DeltaWorkbench', 'PartDesignWorkbench', 'SketcherWorkbench', 'PartWorkbench', 'DraftWorkbench', 'StartWorkbench']:
                try:
                    Gui.activateWorkbench(wb); pump(25)
                    try: L.sweep()
                    except Exception: pass
                    pump(5); walk(wb)
                except Exception as e:
                    res.setdefault('wb_errors', {})[wb] = str(e)[:200]
            # open every top-level menu so lazily built entries exist
            for mb in mw.findChildren(QtWidgets.QMenuBar):
                for a in mb.actions():
                    m = a.menu()
                    if m is not None:
                        try: m.aboutToShow.emit()
                        except Exception: pass
                        for x in m.actions():
                            check('menuitem', x.text(), 'menubar'); check('menutip', x.toolTip(), 'menubar')
            # dialogs: Delta command dialogs are covered by the macro gate; list the Preferences dialog only if it opens quickly
            res['misses'] = {k: sorted(v) for k, v in sorted(res['misses'].items())}
            res['miss_count'] = len(res['misses']); res['done'] = True
        except Exception:
            res['error'] = traceback.format_exc(); res['misses'] = {k: sorted(v) for k, v in res['misses'].items()}; res['done'] = True
        save()
    QtCore.QTimer.singleShot(3000, step)
except Exception:
    res['error'] = traceback.format_exc(); res['done'] = True; save()
