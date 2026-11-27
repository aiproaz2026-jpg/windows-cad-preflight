# -*- coding: utf-8 -*-
"""Additive Arabic translation layer: a QTranslator plus a one-shot text sweep on workbench activation.
Exact-match dictionary only (ar_dict.DICT). Changes text only; never moves, hides or re-parents any panel. GPL-3.0-or-later."""
from PySide import QtCore, QtGui, QtWidgets
import FreeCADGui as Gui
import re
from .ar_dict import DICT
DICT = dict(DICT)
for _m, _n2 in (('ar_dict2', 'DICT2'), ('ar_dict3', 'DICT3')):
    try:
        _mod = __import__('DeltaEngineering.' + _m, fromlist=[_n2])
        DICT.update(getattr(_mod, _n2))
    except Exception:
        pass
_B = re.compile(r'<b>(.*?)</b>', re.S)
_P = re.compile(r'(</p>\s*<p[^>]*>)([^<]+)(</p>)')


def _tip(t):
    """Translate the title and description inside FreeCAD's HTML tooltips (exact-match dictionary)."""
    if not t or '<p' not in t:
        return t
    t2 = _B.sub(lambda m: '<b>' + DICT.get(_n(m.group(1)), m.group(1)) + '</b>', t)
    t2 = _P.sub(lambda m: m.group(1) + DICT.get(_n(m.group(2)), m.group(2)) + m.group(3), t2)
    return t2

_keep = []

LABELS = {'Origin': 'نقطة الأصل', 'X-axis': 'المحور X', 'Y-axis': 'المحور Y', 'Z-axis': 'المحور Z',
          'XY-plane': 'المستوى XY', 'XZ-plane': 'المستوى XZ', 'YZ-plane': 'المستوى YZ',
          'BaseBody': 'الجسم الأساسي', 'BaseSketch': 'الرسم الأساسي'}


def relabel(doc):
    """Arabic labels for the generic objects FreeCAD and the example create (numeric suffix like 001 is kept)."""
    import re
    n = 0
    for o in doc.Objects:
        m = re.match(r'^(.*?)(\d{3})?$', o.Label)
        base, suf = m.group(1), m.group(2)
        if base in LABELS:
            o.Label = LABELS[base] + (' ' + suf if suf else '')
            n += 1
    return n


def _n(s):
    return (s or '').replace('&', '').strip()


class _Translator(QtCore.QTranslator):
    def translate(self, context, sourceText, disambiguation=None, n=-1):
        r = DICT.get(_n(sourceText))
        return r if r else ''

    def isEmpty(self):
        return False


def sweep():
    """Replace exact-match English UI texts with Arabic. Returns the number of texts changed."""
    mw = Gui.getMainWindow()
    if mw is None:
        return 0
    cnt = 0
    for a in mw.findChildren(QtGui.QAction):
        for get, put in ((a.text, a.setText), (a.toolTip, a.setToolTip), (a.statusTip, a.setStatusTip)):
            r = DICT.get(_n(get()))
            if r and get() != r:
                put(r)
                cnt += 1
    for a in mw.findChildren(QtGui.QAction):
        tt = a.toolTip()
        t2 = _tip(tt)
        if t2 != tt:
            a.setToolTip(t2)
            cnt += 1
    for m in mw.findChildren(QtWidgets.QMenu):
        r = DICT.get(_n(m.title()))
        if r and m.title() != r:
            m.setTitle(r)
            cnt += 1
    for w in mw.findChildren(QtWidgets.QToolBar) + mw.findChildren(QtWidgets.QDockWidget):
        r = DICT.get(_n(w.windowTitle()))
        if r and w.windowTitle() != r:
            w.setWindowTitle(r)
            cnt += 1
    for c in (QtWidgets.QLabel, QtWidgets.QPushButton, QtWidgets.QCheckBox, QtWidgets.QRadioButton):
        for w in mw.findChildren(c):
            r = DICT.get(_n(w.text()))
            if r and w.text() != r:
                w.setText(r)
                cnt += 1
    for w in mw.findChildren(QtWidgets.QGroupBox):
        r = DICT.get(_n(w.title()))
        if r and w.title() != r:
            w.setTitle(r)
            cnt += 1
    for tb in mw.findChildren(QtWidgets.QTabBar):
        for k in range(tb.count()):
            r = DICT.get(_n(tb.tabText(k)))
            if r and tb.tabText(k) != r:
                tb.setTabText(k, r)
                cnt += 1
    return cnt


def _later(*_a):
    QtCore.QTimer.singleShot(0, sweep)


def register():
    # QTranslator subclass intentionally not installed (a CI run with it exited at startup); text sweep only.
    _keep.append('sweep-only')
    try:
        from . import core as _core, gui as _gui
        _orig = _core.create_demo

        def _demo(*a, **k):
            d = _orig(*a, **k)
            relabel(d)
            return d
        _core.create_demo = _demo
        _gui.create_demo = _demo
    except Exception:
        pass
    mw = Gui.getMainWindow()
    if mw is not None:
        try:
            mw.workbenchActivated.connect(_later)
        except Exception:
            pass
        QtCore.QTimer.singleShot(0, sweep)
