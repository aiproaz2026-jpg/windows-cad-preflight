"""Arabic commands for the editable parametric parts library. GPL-3.0-or-later.
Additive: adds commands and a toolbar to the existing Delta workbench."""
import FreeCAD as App

FAMILIES = [
    ('hex_bolt', 'برغي سداسي', 'مقاس البرغي (ISO 4014)'),
    ('hex_nut', 'صامولة سداسية', 'مقاس الصامولة (ISO 4032)'),
    ('washer', 'وردة (حلقة)', 'مقاس الوردة (ISO 7089)'),
    ('bearing', 'رولمان بلي', 'رقم الرولمان (سلسلة 62)'),
    ('ipe', 'مقطع IPE', 'مقاس IPE'),
    ('gear', 'ترس مسنن', None),
]


def sizes(family):
    from . import parts_library as PL
    return {'hex_bolt': list(PL.BOLTS_ISO4014), 'hex_nut': list(PL.NUTS_ISO4032),
            'washer': list(PL.WASHERS_ISO7089), 'bearing': list(PL.BEARINGS_62),
            'ipe': list(PL.IPE)}.get(family, [])


def make_part(doc, family, preset=None, module=None, teeth=None):
    """Create one editable parametric part. Returns the object."""
    from . import parts_library as PL
    obj = PL.create(doc, family, preset)
    if family == 'gear' and (module or teeth):
        if module:
            obj.Module = module
        if teeth:
            obj.Teeth = int(teeth)
        doc.recompute()
    label = [x[1] for x in FAMILIES if x[0] == family][0]
    obj.Label = label + (' ' + str(preset) if preset else '')
    return obj


def _make_command(family, title, prompt):
    class _Cmd:
        def GetResources(self):
            return {'MenuText': title, 'ToolTip': 'إضافة ' + title + ' قابل للتعديل بقيم من جداول منشورة، مع اختيار المقاس'}

        def IsActive(self):
            return True

        def Activated(self):
            import FreeCADGui as Gui
            from PySide import QtWidgets
            from .gui import active
            doc = active()
            if family == 'gear':
                m, ok = QtWidgets.QInputDialog.getDouble(None, title, 'المعامل (module) بالمم', 2.0, 0.5, 20.0, 2)
                if not ok:
                    return
                z, ok = QtWidgets.QInputDialog.getInt(None, title, 'عدد الأسنان', 20, 8, 200)
                if not ok:
                    return
                obj = make_part(doc, family, None, m, z)
            else:
                items = sizes(family)
                sz, ok = QtWidgets.QInputDialog.getItem(None, title, prompt, items, 0, False)
                if not ok:
                    return
                obj = make_part(doc, family, sz)
            Gui.SendMsgToActiveView('ViewFit')
    return _Cmd


def command_keys():
    return ['Delta_Lib_' + f for f, _, _ in FAMILIES]


def register():
    import FreeCADGui as Gui
    for fam, title, prompt in FAMILIES:
        Gui.addCommand('Delta_Lib_' + fam, _make_command(fam, title, prompt)())
    from .gui import DeltaWorkbench
    if getattr(DeltaWorkbench, '_lib_patched', False):
        return
    orig = DeltaWorkbench.Initialize

    def Initialize(self):
        orig(self)
        self.appendToolbar('مكتبة القطع', command_keys())
        self.appendMenu('مكتبة القطع', command_keys())
    DeltaWorkbench.Initialize = Initialize
    DeltaWorkbench._lib_patched = True
