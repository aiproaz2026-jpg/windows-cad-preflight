"""Arabic commands and toolbar for the 3D pipe fittings. GPL-3.0-or-later."""
from . import fittings3d as F3


def _cmd(kind):
    title = F3.NAMES[kind]
    prompt = 'اختر المقاس (NPS بالبوصة)' if kind != 'reducer' else 'اختر الزوج (كبير x صغير)'

    class _C:
        def GetResources(self):
            return {'MenuText': title, 'ToolTip': 'قطعة ثلاثية الأبعاد قابلة للتعديل بأبعاد من جداول منشورة، وكل بُعد يمكن تغييره'}

        def IsActive(self):
            return True

        def Activated(self):
            import FreeCADGui as Gui
            from PySide import QtWidgets
            from .gui import active
            doc = active()
            sz, ok = QtWidgets.QInputDialog.getItem(None, title, prompt, F3.presets(kind), 0, False)
            if not ok:
                return
            F3.create(doc, kind, sz)
            Gui.SendMsgToActiveView('ViewFit')
    return _C


def command_keys():
    return ['Delta_Fit_' + k for k in F3.KINDS]


def register():
    import FreeCADGui as Gui
    for k in F3.KINDS:
        Gui.addCommand('Delta_Fit_' + k, _cmd(k)())
    from .gui import DeltaWorkbench
    if getattr(DeltaWorkbench, '_fit_patched', False):
        return
    orig = DeltaWorkbench.Initialize

    def Initialize(self):
        orig(self)
        self.appendToolbar('وصلات ثلاثية الأبعاد', command_keys())
        self.appendMenu('وصلات ثلاثية الأبعاد', command_keys())
    DeltaWorkbench.Initialize = Initialize
    DeltaWorkbench._fit_patched = True
