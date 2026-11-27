"""Arabic commands: valves, pump, pipe, weld-neck flange, and automatic fitting insertion on a selected route. GPL-3.0-or-later."""
from . import equipment3d as E3
from . import fittings3d as F3


def _eq_cmd(kind):
    title = E3.NAMES[kind]
    prompt = 'اختر المقاس (NPS بالبوصة)' if kind != 'pump' else 'اختر الزوج (السحب x الطرد)'

    class _C:
        def GetResources(self):
            tip = 'قطعة ثلاثية الأبعاد قابلة للتعديل'
            if kind in ('gate_valve', 'ball_valve', 'check_valve', 'pump'):
                tip += '، شكل عام توضيحي: الأبعاد الخارجية من جداول والباقي تقريبي ويمكن تعديله'
            return {'MenuText': title, 'ToolTip': tip}

        def IsActive(self):
            return True

        def Activated(self):
            import FreeCADGui as Gui
            from PySide import QtWidgets
            from .gui import active
            doc = active()
            sz, ok = QtWidgets.QInputDialog.getItem(None, title, prompt, E3.presets(kind), 0, False)
            if not ok:
                return
            E3.create(doc, kind, sz)
            Gui.SendMsgToActiveView('ViewFit')
    return _C


class _Route:
    def GetResources(self):
        return {'MenuText': 'إدراج وصلات ومواسير على مسار', 'ToolTip': 'حدد مساراً (خطوط متصلة) ثم اختر المقاس والسماكة: تُوضع كيعان ٩٠° و٤٥° ومواسير مستقيمة تلقائياً'}

    def IsActive(self):
        return True

    def Activated(self):
        import FreeCADGui as Gui
        from PySide import QtWidgets
        from .gui import active
        doc = active()
        sel = Gui.Selection.getSelection()
        if not sel or not hasattr(sel[0], 'Shape'):
            QtWidgets.QMessageBox.information(None, 'إدراج وصلات', 'حدد مساراً أولاً (عنصر خطوط متصلة).')
            return
        pts = E3.ordered_points(sel[0].Shape)
        nps, ok = QtWidgets.QInputDialog.getItem(None, 'إدراج وصلات', 'المقاس (NPS بالبوصة)', F3.presets('elbow90lr'), 0, False)
        if not ok:
            return
        sch, ok = QtWidgets.QInputDialog.getItem(None, 'إدراج وصلات', 'السماكة (SCH)', F3.SCHEDULES, 1, False)
        if not ok:
            return
        try:
            E3.route_fittings(doc, pts, nps, sch)
        except Exception as e:
            QtWidgets.QMessageBox.warning(None, 'تعذر الإدراج', str(e))
            return
        Gui.SendMsgToActiveView('ViewFit')


def command_keys():
    return ['Delta_Eq_' + k for k in E3.KINDS] + ['Delta_Fit_Route']


def register():
    import FreeCADGui as Gui
    for k in E3.KINDS:
        Gui.addCommand('Delta_Eq_' + k, _eq_cmd(k)())
    Gui.addCommand('Delta_Fit_Route', _Route())
    from .gui import DeltaWorkbench
    if getattr(DeltaWorkbench, '_eq_patched', False):
        return
    orig = DeltaWorkbench.Initialize

    def Initialize(self):
        orig(self)
        self.appendToolbar('المعدات والمسارات', command_keys())
        self.appendMenu('المعدات والمسارات', command_keys())
    DeltaWorkbench._eq_patched = True
    DeltaWorkbench.Initialize = Initialize
