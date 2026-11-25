"""Delta Engineering v6 patches: applies v4 first, then dock layout fixes (scroll-wrapped panels, tabified editor docks)."""
import sys,os,subprocess
root=sys.argv[1]
here=os.path.dirname(os.path.abspath(__file__))
subprocess.check_call([sys.executable,os.path.join(here,'..','v4','apply_v4.py'),root])
def rep(rel,old,new):
    for base in (root+'/DeltaEngineering', root+'/package/Mod/DeltaEngineering/DeltaEngineering'):
        p=os.path.join(base,rel)
        s=open(p,encoding='utf-8',newline='').read()
        assert s.count(old)==1,(p,old,s.count(old))
        open(p,'w',encoding='utf-8',newline='').write(s.replace(old,new))
SC="_sc=QtWidgets.QScrollArea();_sc.setWidgetResizable(True);_sc.setFrameShape(QtWidgets.QFrame.NoFrame);_sc.setWidget(%s);self.setWidget(_sc)"
rep('drafting_panel.py',"shell=QtWidgets.QWidget();self.setWidget(shell);","shell=QtWidgets.QWidget();"+SC%'shell'+";")
rep('drafting_panel.py',"panel=DraftingPanel();Gui.getMainWindow().addDockWidget(QtCore.Qt.RightDockWidgetArea,panel);panel.show();","panel=DraftingPanel();Gui.getMainWindow().addDockWidget(QtCore.Qt.RightDockWidgetArea,panel);_other=Gui.getMainWindow().findChild(QtWidgets.QDockWidget,'DeltaElectricalPanel');(Gui.getMainWindow().tabifyDockWidget(_other,panel) if _other else None);panel.show();panel.raise_();")
rep('panel.py',"area=QtWidgets.QWidget();self.setWidget(area)","area=QtWidgets.QWidget();"+SC%'area')
rep('panel.py',"Gui.getMainWindow().addDockWidget(QtCore.Qt.RightDockWidgetArea,panel)","Gui.getMainWindow().addDockWidget(QtCore.Qt.RightDockWidgetArea,panel);_other=Gui.getMainWindow().findChild(QtWidgets.QDockWidget,'DeltaDraftingPanel');(Gui.getMainWindow().tabifyDockWidget(_other,panel) if _other else None);panel.raise_()")
print('v6 patch applied')
