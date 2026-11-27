# -*- coding: utf-8 -*-
"""Electrical symbol library editor (add or replace a user symbol). Symbols are original illustrative shapes. GPL-3.0-or-later."""
import os, json
import FreeCAD as App

EXAMPLE = '''{
 "Symbol_Mine": {
  "label": "رمزي الخاص (توضيحي)",
  "terminals": ["1", "2"],
  "prims": [["L", [[-40, 0], [-15, 0]]], ["L", [[15, 0], [40, 0]]], ["C", 0, 0, 15]]
 }
}
مفتاح "L" خط أو مضلع بنقاط [س,ص]، "C" دائرة (س,ص,نق)، "A" قوس (س,ص,نق,زاوية بداية,زاوية نهاية). الوحدات مم.'''


def user_file():
    try:
        d = App.getUserAppDataDir()
    except Exception:
        d = os.path.expanduser('~')
    return os.path.join(d, 'elec_symbols.json')


def _num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def validate(data):
    """Return a list of error strings (empty list means the data is a valid symbol dictionary)."""
    err = []
    if not isinstance(data, dict) or not data:
        return ['يجب أن يكون المحتوى قاموساً فيه رمز واحد على الأقل']
    for name, e in data.items():
        if not isinstance(e, dict) or not {'label', 'terminals', 'prims'} <= set(e):
            err.append('%s: يلزم label و terminals و prims' % name); continue
        t = e['terminals']
        if not isinstance(t, list) or not t or len(set(map(str, t))) != len(t):
            err.append('%s: الأطراف مطلوبة وأسماؤها لا تتكرر' % name)
        if not isinstance(e['prims'], list) or not e['prims']:
            err.append('%s: لا توجد عناصر رسم' % name); continue
        for p in e['prims']:
            try:
                k = p[0]
                if k == 'L':
                    ok = len(p[1]) >= 2 and all(len(q) == 2 and _num(q[0]) and _num(q[1]) for q in p[1])
                elif k == 'C':
                    ok = len(p) == 4 and all(_num(v) for v in p[1:]) and p[3] > 0
                elif k == 'A':
                    ok = len(p) == 6 and all(_num(v) for v in p[1:]) and p[3] > 0
                else:
                    ok = False
            except Exception:
                ok = False
            if not ok:
                err.append('%s: عنصر رسم غير صحيح %s' % (name, str(p)[:40]))
    return err


def save(data, path=None):
    """Merge validated entries into the user file (existing other symbols are kept). Returns the path."""
    errs = validate(data)
    if errs:
        raise ValueError('\n'.join(errs))
    path = path or user_file()
    cur = {}
    if os.path.isfile(path):
        cur = json.load(open(path, encoding='utf-8'))
    cur.update(data)
    tmp = path + '.tmp'
    json.dump(cur, open(tmp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    os.replace(tmp, path)
    return path


def reload_library():
    from . import symbols as S
    lib = S._v60_load()
    S.V60_LIB.clear(); S.V60_LIB.update(lib)
    for k, (lab, term, pr) in lib.items():
        S.TEMPLATES[k] = (lab, tuple(term))
    return len(lib)


class _Cmd:
    def GetResources(self):
        return {'MenuText': 'تحرير مكتبة الرموز الكهربائية', 'ToolTip': 'أضف رمزاً كهربائياً جديداً أو عدّل رمزاً موجوداً (JSON)، ويظهر مباشرة في قائمة الأجهزة'}

    def IsActive(self):
        return True

    def Activated(self):
        from PySide import QtWidgets
        text, ok = QtWidgets.QInputDialog.getMultiLineText(None, 'مكتبة الرموز الكهربائية', 'أدخل رمزاً بصيغة JSON:', EXAMPLE.split('\n}')[0] + '\n}')
        if not ok:
            return
        try:
            data = json.loads(text)
            p = save(data)
            n = reload_library()
        except Exception as e:
            QtWidgets.QMessageBox.warning(None, 'تعذر حفظ الرمز', str(e))
            return
        QtWidgets.QMessageBox.information(None, 'تم', 'حُفظ الرمز في الملف:\n%s\nعدد رموز المكتبة الآن: %d' % (p, n))


def register():
    import FreeCADGui as Gui
    Gui.addCommand('Delta_Elec_LibEdit', _Cmd())
    from .gui import DeltaWorkbench
    if getattr(DeltaWorkbench, '_libedit_patched', False):
        return
    orig = DeltaWorkbench.Initialize

    def Initialize(self):
        orig(self)
        self.appendToolbar('مكتبة الرموز', ['Delta_Elec_LibEdit'])
        self.appendMenu('مكتبة الرموز', ['Delta_Elec_LibEdit'])
    DeltaWorkbench._libedit_patched = True
    DeltaWorkbench.Initialize = Initialize
