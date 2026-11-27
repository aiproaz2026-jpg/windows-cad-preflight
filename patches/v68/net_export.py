# -*- coding: utf-8 -*-
"""Export of the last built pipe network: A3 plan PDF (Latin text, vector) and CSV schedule (Arabic headers, UTF-8 with BOM). GPL-3.0-or-later."""
import math, csv, os
import FreeCAD as App

LAST = {}


def remember(nodes, edges, res, nps, sch):
    LAST.clear(); LAST.update(nodes=nodes, edges=edges, res=res, nps=nps, sch=sch)


def _label_offset(nodes, edges, n):
    dirs = []
    for a, b in edges:
        if n in (a, b):
            o = b if a == n else a
            dirs.append(math.atan2(nodes[o].y - nodes[n].y, nodes[o].x - nodes[n].x))
    best, bs = (6, 6), -1
    for ox, oy in ((6, 6), (-30, 6), (6, -12), (-30, -12), (6, 0), (-30, 0)):
        ang = math.atan2(oy + 4, ox + 12)
        s = min([abs(math.atan2(math.sin(ang - d), math.cos(ang - d))) for d in dirs] or [3.0])
        if s > bs + 1e-9:
            bs, best = s, (ox, oy)
    return best


def plan_pdf(path, nodes, edges, res, nps, sch, rows, cnt, tot, title='Pipe network plan'):
    from . import minipdf
    pw, ph = 1190.55, 841.89
    xs = [v.x for v in nodes.values()]; ys = [v.y for v in nodes.values()]
    x0, x1, y0, y1 = min(xs) - 500, max(xs) + 500, min(ys) - 500, max(ys) + 500
    sc = min((pw - 440) / (x1 - x0), (ph - 140) / (y1 - y0)); ox, oy = 40, 80
    X = lambda x: ox + (x - x0) * sc
    Y = lambda y: oy + (y - y0) * sc
    pg = minipdf.Page(pw, ph); pg.rect(20, 20, pw - 40, ph - 40, 1.5)
    for s in res['plan']['segments']:
        a = s['start']; b = a + s['dir'] * s['length']
        pg.line([(X(a.x), Y(a.y)), (X(b.x), Y(b.y))], 2.2, (0.1, 0.25, 0.5))
    for n in res['plan']['fittings']:
        p = nodes[n]
        pg.line([(X(p.x) - 4, Y(p.y) - 4), (X(p.x) + 4, Y(p.y) + 4)], 1.5, (0.8, 0.2, 0.1))
        pg.line([(X(p.x) - 4, Y(p.y) + 4), (X(p.x) + 4, Y(p.y) - 4)], 1.5, (0.8, 0.2, 0.1))
    for n, p in nodes.items():
        o = _label_offset(nodes, edges, n)
        k = res['plan']['fittings'].get(n)
        pg.text(X(p.x) + o[0], Y(p.y) + o[1], n + (' [' + k['kind'] + ']' if k else ''), 8)
    tx = pw - 400; ty = ph - 60
    pg.text(tx, ty, '%s, NPS %s, %s (ILLUSTRATIVE, generic)' % (title, nps, sch), 9); ty -= 16
    for r in rows:
        pg.text(tx, ty, '%s  %s  %s  %.1f mm' % r, 8); ty -= 12
    ty -= 8; pg.text(tx, ty, 'Fittings: ' + (', '.join('%s x%d' % kv for kv in cnt.items()) or '-'), 8); ty -= 12
    pg.text(tx, ty, 'Total straight pipe: %.1f mm' % tot, 8); ty -= 12
    pg.text(tx, ty, 'Fitting dims: ASME B16.9 tables as published (see fittings library).', 6.5)
    pg.save(path)
    return os.path.getsize(path)


def schedule_csv(path, rows, cnt, tot):
    with open(path, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['رقم', 'من-إلى', 'الوصف', 'الطول (مم)'])
        for r in rows:
            w.writerow(list(r))
        w.writerow([])
        w.writerow(['الوصلات', 'العدد'])
        for k, v in cnt.items():
            w.writerow([k, v])
        w.writerow(['إجمالي طول المواسير المستقيمة (مم)', tot])
    return os.path.getsize(path)


def export_last(stem):
    from . import network as N
    if not LAST:
        raise ValueError('لا توجد شبكة منشأة في هذه الجلسة')
    rows, cnt, tot = N.schedule_rows(LAST['res'], LAST['nps'], LAST['sch'])
    a = plan_pdf(stem + '_plan_A3.pdf', LAST['nodes'], LAST['edges'], LAST['res'], LAST['nps'], LAST['sch'], rows, cnt, tot)
    b = schedule_csv(stem + '_schedule.csv', rows, cnt, tot)
    return stem + '_plan_A3.pdf', stem + '_schedule.csv', a, b


class _Cmd:
    def GetResources(self):
        return {'MenuText': 'تصدير مخطط الشبكة وجدولها', 'ToolTip': 'يصدّر آخر شبكة مواسير تم إنشاؤها إلى ملف PDF بمقاس A3 وجدول CSV'}

    def IsActive(self):
        return True

    def Activated(self):
        from PySide import QtWidgets
        if not LAST:
            QtWidgets.QMessageBox.warning(None, 'تصدير الشبكة', 'أنشئ شبكة مواسير أولاً')
            return
        p, _ = QtWidgets.QFileDialog.getSaveFileName(None, 'اسم الملف (بدون امتداد)', os.path.expanduser('~/network'), 'PDF (*.pdf)')
        if not p:
            return
        stem = p[:-4] if p.lower().endswith('.pdf') else p
        try:
            r = export_last(stem)
        except Exception as e:
            QtWidgets.QMessageBox.warning(None, 'تعذر التصدير', str(e))
            return
        QtWidgets.QMessageBox.information(None, 'تم التصدير', '%s\n%s' % (r[0], r[1]))


def register():
    import FreeCADGui as Gui
    from . import net_commands as NC, network as N
    Gui.addCommand('Delta_Net_Export', _Cmd())
    if not getattr(N, '_remember_patched', False):
        orig = N.build

        def build(doc, nodes, edges, nps, schedule='SCH 40'):
            r = orig(doc, nodes, edges, nps, schedule)
            remember(nodes, edges, r, nps, schedule)
            return r
        N.build = build
        N._remember_patched = True
    from .gui import DeltaWorkbench
    if getattr(DeltaWorkbench, '_netexp_patched', False):
        return
    o = DeltaWorkbench.Initialize

    def Initialize(self):
        o(self)
        self.appendToolbar('تصدير الشبكة', ['Delta_Net_Export'])
        self.appendMenu('تصدير الشبكة', ['Delta_Net_Export'])
    DeltaWorkbench._netexp_patched = True
    DeltaWorkbench.Initialize = Initialize
