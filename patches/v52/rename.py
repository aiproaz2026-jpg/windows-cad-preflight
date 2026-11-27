import sys, io
M = sys.argv[1]
BR = 'برنامج CAD للمهندس محمود زهير'
def sub(fn, old, new, count=None):
    p = M + '/' + fn
    s = io.open(p, encoding='utf-8').read()
    n = s.count(old)
    if n < 1 or (count is not None and n != count):
        raise SystemExit('rename: %r found %d times in %s' % (old, n, fn))
    io.open(p, 'w', encoding='utf-8', newline='').write(s.replace(old, new))
    print('ok', fn, n)
sub('gui.py', "MenuText='دلتا | ميكانيكا ومواسير وكهرباء'", "MenuText='%s'" % BR, 1)
sub('gui.py', "self.appendMenu('دلتا',commands)", "self.appendMenu('%s',commands)" % BR, 1)
sub('export.py', 'writer.setTitle(title)', "writer.setTitle(title+' | %s');writer.setCreator('%s')" % (BR, BR), 1)
sub('export.py', "        if single:\n            rectangles=[", "        painter.drawText(QtCore.QRectF(45,h-100,w*0.45,60),int(QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter),'%s')\n        if single:\n            rectangles=[" % BR, 1)
