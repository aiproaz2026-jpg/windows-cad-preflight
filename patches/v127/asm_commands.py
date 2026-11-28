"""Arabic commands for the simple assembly (two parts, one joint, solve, move). GPL-3.0-or-later."""
from . import assembly_simple as AS


def _assembly_of(joint):
    for o in joint.Document.Objects:
        if o.TypeId == 'Assembly::AssemblyObject':
            for g in o.Group:
                if g.TypeId == 'Assembly::JointGroup' and joint in g.Group:
                    return o
    return None


class _Make:
    def GetResources(self):
        return {'MenuText': 'تجميع بسيط: قطعتان ومفصل', 'ToolTip': 'حدد قطعتين (الأولى تُثبَّت) ثم اختر نوع المفصل والمحور وقيمة الحركة. تحديد مواضع فقط: بدون ديناميكا أو تصادم أو تحقق هندسي'}

    def IsActive(self):
        return True

    def Activated(self):
        import FreeCADGui as Gui
        from PySide import QtWidgets
        from .gui import active
        doc = active()
        sel = [o for o in Gui.Selection.getSelection() if hasattr(o, 'Shape')]
        if len(sel) != 2:
            QtWidgets.QMessageBox.information(None, 'تجميع بسيط', 'حدد قطعتين بالضبط. الأولى تُثبَّت والثانية تتحرك.')
            return
        names = list(AS.JOINTS.values())
        lab, ok = QtWidgets.QInputDialog.getItem(None, 'تجميع بسيط', 'نوع المفصل', names, 0, False)
        if not ok:
            return
        jt = [k for k, v in AS.JOINTS.items() if v == lab][0]
        ax, ok = QtWidgets.QInputDialog.getItem(None, 'تجميع بسيط', 'محور المفصل', list(AS.AXES), 0, False)
        if not ok:
            return
        try:
            info = AS.make_assembly(doc, sel[0], sel[1], jt, ax)
            if jt != 'Fixed':
                unit = 'درجة' if jt == 'Revolute' else 'مم'
                v, ok = QtWidgets.QInputDialog.getDouble(None, 'تجميع بسيط', 'قيمة الحركة (%s)' % unit, 0.0, -100000.0, 100000.0, 2)
                if ok:
                    AS.move(info, v)
        except Exception as e:
            QtWidgets.QMessageBox.warning(None, 'تعذر التجميع', str(e))
            return
        Gui.SendMsgToActiveView('ViewFit')


class _Move:
    def GetResources(self):
        return {'MenuText': 'تحريك مفصل التجميع', 'ToolTip': 'حدد مفصلاً داخل التجميع ثم أدخل القيمة (درجة أو مم) لإعادة الحل'}

    def IsActive(self):
        return True

    def Activated(self):
        import FreeCADGui as Gui
        from PySide import QtWidgets
        sel = Gui.Selection.getSelection()
        if not sel or not hasattr(sel[0], 'JointType'):
            QtWidgets.QMessageBox.information(None, 'تحريك مفصل', 'حدد مفصلاً أولاً من شجرة التجميع.')
            return
        j = sel[0]
        asm = _assembly_of(j)
        if asm is None:
            QtWidgets.QMessageBox.warning(None, 'تحريك مفصل', 'لم أجد التجميع الذي يحوي هذا المفصل.')
            return
        v, ok = QtWidgets.QInputDialog.getDouble(None, 'تحريك مفصل', 'القيمة (درجة أو مم)', 0.0, -100000.0, 100000.0, 2)
        if ok:
            AS.move({'joint': j, 'assembly': asm}, v)


def command_keys():
    return ['Delta_Asm_Make', 'Delta_Asm_Move']


def register():
    import FreeCADGui as Gui
    Gui.addCommand('Delta_Asm_Make', _Make())
    Gui.addCommand('Delta_Asm_Move', _Move())
    from .gui import DeltaWorkbench
    if getattr(DeltaWorkbench, '_asm_patched', False):
        return
    orig = DeltaWorkbench.Initialize

    def Initialize(self):
        orig(self)
        self.appendToolbar('التجميع', command_keys())
        self.appendMenu('التجميع', command_keys())
    DeltaWorkbench._asm_patched = True
    DeltaWorkbench.Initialize = Initialize
