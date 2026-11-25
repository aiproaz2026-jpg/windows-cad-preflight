"""Delta Engineering v7 patch: applies v6, then adds the generic fittings library and its Arabic panel tab."""
import sys, os, subprocess, shutil
root = sys.argv[1]
here = os.path.dirname(os.path.abspath(__file__))
subprocess.check_call([sys.executable, os.path.join(here, '..', 'v6', 'apply_v6.py'), root])
bases = [root + '/DeltaEngineering', root + '/package/Mod/DeltaEngineering/DeltaEngineering']
for base in bases:
    if os.path.isdir(base):
        for f in ('fittings.py', 'fittings_panel.py'):
            shutil.copyfile(os.path.join(here, f), os.path.join(base, f))
        p = os.path.join(base, 'drafting_panel.py')
        s = open(p, encoding='utf-8', newline='').read()
        old = "self.tubes=TubeLibraryPanel(self);tabs.addTab(self.tubes,'مقاسات مواسير')"
        assert s.count(old) == 1, (p, s.count(old))
        new = old + ";from .fittings_panel import FittingsPanel;self.fittings=FittingsPanel(self);_fs=QtWidgets.QScrollArea();_fs.setWidgetResizable(True);_fs.setFrameShape(QtWidgets.QFrame.NoFrame);_fs.setWidget(self.fittings);tabs.addTab(_fs,'وصلات ومحطة')"
        s = s.replace(old, new)
        old2 = "panel.raise_();Gui.getMainWindow().resizeDocks"
        assert s.count(old2) == 1, (p, s.count(old2))
        s = s.replace(old2, "panel.raise_();from .fittings_panel import hide_empty_tasks;hide_empty_tasks();Gui.getMainWindow().resizeDocks")
        open(p, 'w', encoding='utf-8', newline='').write(s)
for base in bases:
    sp = os.path.join(base, 'symbols.py')
    if os.path.isfile(sp):
        s = open(sp, encoding='utf-8', newline='').read()
        assert 'v7 additions' not in s
        add = open(os.path.join(here, 'symbols_append.py'), encoding='utf-8', newline='').read()
        open(sp, 'w', encoding='utf-8', newline='').write(s.rstrip('\n') + '\n' + add)
sys.path.insert(0, here)
import core_patches
for base in bases:
    if os.path.isfile(os.path.join(base, 'core.py')):
        print('core patches', base, core_patches.apply(base))
print('v7 patch applied')
