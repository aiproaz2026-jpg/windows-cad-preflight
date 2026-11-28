# -*- coding: utf-8 -*-
"""GUI command: re-route every electrical wire of the active document with wire_route.
Additive module, license GPL-3.0-or-later. Does not delete or change any device; it only rewrites wire shapes."""
import FreeCAD as App


def reroute_active():
    from . import wire_route as R
    doc = App.ActiveDocument
    if doc is None:
        raise RuntimeError('no active document')
    rows = R.reroute(doc)
    n_routed = sum(1 for r in rows if r.get('routed', True))
    return len(rows), n_routed


class _Cmd:
    def GetResources(self):
        return {'MenuText': 'إعادة توجيه الأسلاك', 'ToolTip': 'يعيد رسم كل أسلاك المخطط الكهربائي الحالي بمسارات متعامدة تتجنب الرموز'}

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        from PySide import QtWidgets
        try:
            n, ok = reroute_active()
        except Exception as e:
            QtWidgets.QMessageBox.warning(None, 'إعادة توجيه الأسلاك', str(e))
            return
        QtWidgets.QMessageBox.information(None, 'إعادة توجيه الأسلاك', 'عدد الأسلاك: %d' % n)


def register():
    import FreeCADGui as Gui
    Gui.addCommand('Delta_Wire_Reroute', _Cmd())
    from .gui import DeltaWorkbench
    if getattr(DeltaWorkbench, '_wr_patched', False):
        return
    o = DeltaWorkbench.Initialize

    def Initialize(self):
        o(self)
        self.appendToolbar('إعادة توجيه الأسلاك', ['Delta_Wire_Reroute'])
        self.appendMenu('إعادة توجيه الأسلاك', ['Delta_Wire_Reroute'])
    DeltaWorkbench._wr_patched = True
    DeltaWorkbench.Initialize = Initialize
