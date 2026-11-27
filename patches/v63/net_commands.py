# -*- coding: utf-8 -*-
"""Arabic commands for the pipe network builder. GPL-3.0-or-later."""
from . import network as N
import FreeCAD as App

DEMO_NODES = {'A': (0, 0, 0), 'B': (2000, 0, 0), 'C': (4000, 0, 0), 'D': (6000, 0, 0), 'B2': (2000, 1500, 0), 'C2': (4000, 1500, 0), 'E': (6000, 2000, 0), 'F': (7000, 3000, 0)}
DEMO_EDGES = [('A', 'B'), ('B', 'C'), ('C', 'D'), ('B', 'B2'), ('C', 'C2'), ('D', 'E'), ('E', 'F')]
HELP = ('العقد: سطر لكل عقدة بالشكل  اسم س ص ع (مم)\nالوصلات: سطر لكل ماسورة بالشكل  أ-ب\nمثال:\nA 0 0 0\nB 2000 0 0\nC 2000 1500 0\nA-B\nB-C')


def parse(text):
    nodes = {}; edges = []
    for ln in text.replace('\u060c', ' ').splitlines():
        ln = ln.strip()
        if not ln:
            continue
        if '-' in ln and len(ln.split()) == 1:
            a, b = ln.split('-', 1)
            edges.append((a.strip(), b.strip()))
        else:
            p = ln.split()
            if len(p) != 4:
                raise ValueError('سطر غير مفهوم: ' + ln)
            nodes[p[0]] = App.Vector(float(p[1]), float(p[2]), float(p[3]))
    if not nodes or not edges:
        raise ValueError('أدخل عقدة واحدة ووصلة واحدة على الأقل')
    return nodes, edges


def _run(nodes, edges, nps, sch):
    import FreeCADGui as Gui
    from PySide import QtWidgets
    from .gui import active
    doc = active()
    try:
        res = N.build(doc, nodes, edges, nps, sch)
        chk = N.check(doc, res, nodes)
    except Exception as e:
        QtWidgets.QMessageBox.warning(None, 'تعذر إنشاء الشبكة', str(e))
        return
    rows, cnt, tot = N.schedule_rows(res, nps, sch)
    msg = 'ماسورة: %d | وصلات: %s | الطول الكلي %.1f مم | أكبر فجوة وصلة %.2f مم' % (len(rows), ', '.join('%s=%d' % kv for kv in cnt.items()) or '-', tot, chk['max_joint_gap_mm'])
    if chk['bad']:
        msg += '\nتنبيه: ' + '; '.join(chk['bad'])
    QtWidgets.QMessageBox.information(None, 'شبكة المواسير', msg)
    Gui.SendMsgToActiveView('ViewFit')


class _Demo:
    def GetResources(self):
        return {'MenuText': 'شبكة مواسير نموذجية (تيهات وكيعان)', 'ToolTip': 'تنشئ شبكة مواسير متفرعة نموذجية مقاس ٤ بوصة: تيهات وكوع ٩٠° وكوع ٤٥° ومواسير مستقيمة، قابلة للتعديل'}

    def IsActive(self):
        return True

    def Activated(self):
        nodes = {k: App.Vector(*v) for k, v in DEMO_NODES.items()}
        _run(nodes, DEMO_EDGES, '4', 'SCH 40')


class _Text:
    def GetResources(self):
        return {'MenuText': 'شبكة مواسير من نقاط ووصلات', 'ToolTip': 'أدخل عقد الشبكة وإحداثياتها ووصلاتها وسيُنشئ البرنامج المواسير والتيهات والكيعان تلقائياً (٩٠° و٤٥° فقط)'}

    def IsActive(self):
        return True

    def Activated(self):
        from PySide import QtWidgets
        text, ok = QtWidgets.QInputDialog.getMultiLineText(None, 'شبكة مواسير', HELP, '')
        if not ok:
            return
        try:
            nodes, edges = parse(text)
        except Exception as e:
            QtWidgets.QMessageBox.warning(None, 'إدخال غير صحيح', str(e))
            return
        from . import fittings3d as F3
        nps, ok = QtWidgets.QInputDialog.getItem(None, 'شبكة مواسير', 'المقاس (NPS بالبوصة)', F3.presets('elbow90lr'), 0, False)
        if not ok:
            return
        sch, ok = QtWidgets.QInputDialog.getItem(None, 'شبكة مواسير', 'السماكة (SCH)', F3.SCHEDULES, 1, False)
        if not ok:
            return
        _run(nodes, edges, nps, sch)


def command_keys():
    return ['Delta_Net_Demo', 'Delta_Net_Text']


def register():
    import FreeCADGui as Gui
    Gui.addCommand('Delta_Net_Demo', _Demo())
    Gui.addCommand('Delta_Net_Text', _Text())
    from .gui import DeltaWorkbench
    if getattr(DeltaWorkbench, '_net_patched', False):
        return
    orig = DeltaWorkbench.Initialize

    def Initialize(self):
        orig(self)
        self.appendToolbar('شبكات المواسير', command_keys())
        self.appendMenu('شبكات المواسير', command_keys())
    DeltaWorkbench._net_patched = True
    DeltaWorkbench.Initialize = Initialize
