"""Program name in the main window title. Event-driven: reacts to title changes only. GPL-3.0-or-later."""
import re
BRAND = 'برنامج CAD للمهندس محمود زهير'
_keep = []


def retitle(text):
    if BRAND in text:
        return text
    return re.sub(r'FreeCAD(\s+\d+(\.\d+)*)?', BRAND, text)


def register():
    from PySide import QtCore
    import FreeCADGui as Gui

    class _F(QtCore.QObject):
        def eventFilter(self, o, ev):
            if ev.type() == QtCore.QEvent.WindowTitleChange:
                t = o.windowTitle()
                n = retitle(t)
                if n != t:
                    o.setWindowTitle(n)
            return False

    def attach():
        mw = Gui.getMainWindow()
        if mw is None:
            return False
        f = _F(mw)
        mw.installEventFilter(f)
        _keep.append(f)
        t = mw.windowTitle()
        n = retitle(t)
        mw.setWindowTitle(n if n != t else BRAND)
        return True
    if not attach():
        QtCore.QTimer.singleShot(1500, attach)
