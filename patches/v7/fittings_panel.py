# SPDX-License-Identifier: GPL-3.0-or-later
"""Arabic panel for generic illustrative pump-station fittings."""
from PySide import QtWidgets, QtCore
import FreeCADGui as Gui
from . import fittings as F
from . import tube_library as library
from .precision import length


class FittingsPanel(QtWidgets.QWidget):
    def __init__(self, panel):
        super().__init__()
        self.panel = panel
        form = QtWidgets.QFormLayout(self)
        form.setAlignment(QtCore.Qt.AlignTop)
        form.setRowWrapPolicy(QtWidgets.QFormLayout.WrapAllRows)
        form.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
        note = QtWidgets.QLabel(F.SCOPE_AR)
        note.setWordWrap(True)
        form.addRow(note)
        self.kind = QtWidgets.QComboBox()
        for key, label in F.KINDS.items():
            self.kind.addItem(label, key)
        self.size1 = QtWidgets.QComboBox()
        self.size1.addItems(list(library.PRESETS))
        self.size2 = QtWidgets.QComboBox()
        self.size2.addItems(list(library.PRESETS))
        self.size2.setCurrentIndex(max(0, self.size2.count() - 1))
        self.length = QtWidgets.QLineEdit('')
        self.length.setPlaceholderText('اتركه فارغاً للطول الافتراضي')
        self.length.setLayoutDirection(QtCore.Qt.LeftToRight)
        for c in (self.kind, self.size1, self.size2, self.port_move if hasattr(self, 'port_move') else self.kind):
            c.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToMinimumContentsLengthWithIcon)
            c.setMinimumContentsLength(8)
        form.addRow('نوع القطعة', self.kind)
        form.addRow('المقاس الاسمي (المنفذ 1)', self.size1)
        form.addRow('المقاس الثاني (للمخفّض والمضخة)', self.size2)
        form.addRow('الطول، أو نصف قطر الكوع (اختياري)', self.length)
        b = QtWidgets.QPushButton('إنشاء القطعة')
        b.clicked.connect(lambda checked=False: panel.safe(self.create))
        form.addRow(b)
        self.port_move = QtWidgets.QComboBox()
        self.port_move.addItems(['1', '2'])
        self.port_fixed = QtWidgets.QComboBox()
        self.port_fixed.addItems(['1', '2'])
        form.addRow('منفذ القطعة المتحركة', self.port_move)
        form.addRow('منفذ القطعة الثابتة', self.port_fixed)
        hint = QtWidgets.QLabel('حدد القطعة المراد تحريكها أولاً ثم القطعة الثابتة. يُرفض اختلاف قطر المنفذين.')
        hint.setWordWrap(True)
        form.addRow(hint)
        for text, fn in [('وصل المنفذ بالمنفذ', self.snap), ('فحص الاستمرارية والتداخل', self.check),
                         ('حصر الكميات وتصدير CSV', self.export_csv)]:
            b = QtWidgets.QPushButton(text)
            b.clicked.connect(lambda checked=False, f=fn: panel.safe(f))
            form.addRow(b)
        self._tasks_timer = QtCore.QTimer(self)
        self._tasks_timer.setInterval(1500)
        self._tasks_timer.timeout.connect(hide_empty_tasks)
        self._tasks_timer.start()
        self.report = QtWidgets.QPlainTextEdit()
        self.report.setReadOnly(True)
        self.report.setMinimumHeight(120)
        form.addRow(self.report)

    def create(self):
        kind = self.kind.currentData()
        two = kind in ('reducer', 'pump')
        n1 = self.size1.currentText()
        n2 = self.size2.currentText() if two else None
        text = self.length.text().strip()
        obj = F.create_fitting(self.panel.doc(), kind, n1, n2, length(text) if text else None)
        self.panel.profiles.select(obj)
        self.panel.status.setText('تم إنشاء ' + F.KINDS[kind] + '. ' + F.SCOPE_AR)
        return obj

    def snap(self):
        sel = Gui.Selection.getSelection()
        if len(sel) != 2:
            raise ValueError('Select exactly two objects: first the one to move, then the fixed one')
        F.snap(self.panel.doc(), sel[0], self.port_move.currentIndex(), sel[1], self.port_fixed.currentIndex())
        self.panel.status.setText('تم وصل المنفذين هندسياً. لا يعني ذلك توافق الضغط أو المعيار.')

    def check(self):
        rep = F.check_continuity(self.panel.doc())
        lines = ['وصلات متطابقة: %d' % len(rep['connected']), 'منافذ مفتوحة: %d' % len(rep['open_ports'])]
        lines += ['  ' + p for p in rep['open_ports']]
        if rep['errors']:
            lines.append('أخطاء: %d' % len(rep['errors']))
            lines += ['  ' + e for e in rep['errors']]
        else:
            lines.append('لا أخطاء هندسية في الاستمرارية أو التداخل.')
        lines.append(F.SCOPE_AR)
        self.report.setPlainText('\n'.join(lines))
        self.panel.status.setText('فحص هندسي للاستمرارية والتداخل فقط، ليس اعتماداً هندسياً.')
        return rep

    def export_csv(self, path=None):
        rows = F.takeoff(self.panel.doc())
        if path is None:
            path, _ = QtWidgets.QFileDialog.getSaveFileName(self, 'حفظ جدول الكميات', 'الكميات.csv', 'CSV (*.csv)')
            if not path:
                return rows
        F.takeoff_csv(self.panel.doc(), path)
        self.report.setPlainText('\n'.join('%s | %s | %s %s' % (r['item'], r['size'], r['qty'], r['unit']) for r in rows) + '\n' + F.SCOPE_AR)
        self.panel.status.setText('تم حفظ جدول الكميات: ' + path)
        return rows


def hide_empty_tasks():
    """Hide the empty Tasks dock only while no task dialog is active; FreeCAD shows it again when a task starts."""
    mw = Gui.getMainWindow()
    dock = mw.findChild(QtWidgets.QDockWidget, 'Tasks')
    if dock is None or not dock.isVisible():
        return False
    try:
        active = Gui.Control.activeDialog()
    except Exception:
        return False
    if active:
        return False
    dock.hide()
    return True
