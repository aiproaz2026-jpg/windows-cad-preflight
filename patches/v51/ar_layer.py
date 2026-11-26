# -*- coding: utf-8 -*-
"""Additive Arabic translation layer: a QTranslator plus a one-shot text sweep on workbench activation.
Exact-match dictionary only (ar_dict.DICT). Changes text only; never moves, hides or re-parents any panel. GPL-3.0-or-later."""
from PySide import QtCore, QtGui, QtWidgets
import FreeCADGui as Gui
from .ar_dict import DICT

_keep = []


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
    mw = Gui.getMainWindow()
    if mw is not None:
        try:
            mw.workbenchActivated.connect(_later)
        except Exception:
            pass
        QtCore.QTimer.singleShot(0, sweep)
