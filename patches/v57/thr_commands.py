"""Arabic commands for the thread option. GPL-3.0-or-later."""
from . import threads3d as T3


def _cmd(kind):
    title = T3.NAMES[kind]

    class _C:
        def GetResources(self):
            return {'MenuText': title, 'ToolTip': 'قلاووظ بارامتري قابل للتعديل (المقاس، الطول، نمط النمذجة). قياسي تقريبي: انظر خاصية Limits. لا يوجد قلاووظ داخلي'}

        def IsActive(self):
            return True

        def Activated(self):
            import FreeCADGui as Gui
            from PySide import QtWidgets
            from .gui import active
            doc = active()
            sz, ok = QtWidgets.QInputDialog.getItem(None, title, 'اختر المقاس', T3.presets(kind), 0, False)
            if not ok:
                return
            T3.create(doc, kind, sz)
            Gui.SendMsgToActiveView('ViewFit')
    return _C


def command_keys():
    return ['Delta_Thr_' + k for k in T3.KINDS]


def register():
    import FreeCADGui as Gui
    for k in T3.KINDS:
        Gui.addCommand('Delta_Thr_' + k, _cmd(k)())
    from .gui import DeltaWorkbench
    if getattr(DeltaWorkbench, '_thr_patched', False):
        return
    orig = DeltaWorkbench.Initialize

    def Initialize(self):
        orig(self)
        self.appendToolbar('القلاووظ (الأسنان)', command_keys())
        self.appendMenu('القلاووظ (الأسنان)', command_keys())
    DeltaWorkbench._thr_patched = True
    DeltaWorkbench.Initialize = Initialize
