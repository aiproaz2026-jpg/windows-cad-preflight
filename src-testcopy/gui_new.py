from .arabic import message,level
from .arabic_qt import Messages,Inputs
"""Arabic workbench commands. GPL-3.0-or-later."""
import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtWidgets
from .core import create_demo, PipeRoute, Device, Connection, quantities


def active():
    from .documents import new_project,ensure_project
    d=App.ActiveDocument or new_project()
    ensure_project(d)
    return d


class Demo:
    def GetResources(self):
        return {'MenuText':'مشروع اختبار متكامل','ToolTip':'إنشاء مثال اختباري قابل للتعديل، وليس مشروع تنفيذ'}
    def Activated(self):
        from .project import create_project
        create_project()
        Gui.activeDocument().activeView().viewAxonometric()
        Gui.activeDocument().activeView().fitAll()
    def IsActive(self): return True


class NewPipe:
    def GetResources(self):
        return {'MenuText':'إضافة ماسورة','ToolTip':'ماسورة مستقيمة قابلة للتعديل بوحدات مم'}
    def Activated(self):
        length,ok=Inputs.getDouble(Gui.getMainWindow(),'إضافة ماسورة','الطول (مم)',1000,1,1000000,2)
        if not ok: return
        diameter,ok=Inputs.getDouble(Gui.getMainWindow(),'إضافة ماسورة','القطر الخارجي (مم)',100,1,10000,2)
        if not ok: return
        wall,ok=Inputs.getDouble(Gui.getMainWindow(),'إضافة ماسورة','سمك الجدار (مم)',5,0.1,diameter/2-0.01,2)
        if not ok: return
        d=active()
        d.openTransaction('Add parametric pipe')
        o=d.addObject('PartDesign::FeaturePython','PipeRoute')
        o.Label='ماسورة'
        PipeRoute(o,[App.Vector(0,0,0),App.Vector(length,0,0)],diameter,wall)
        d.recompute()
        d.commitTransaction()
        o.ViewObject.ShapeColor=(0.05,0.68,0.64)
        Gui.activeDocument().activeView().fitAll()
    def IsActive(self): return True


class NewDevice:
    def GetResources(self): return {'MenuText':'رمز كهربائي','ToolTip':'إضافة رمز عام مع معرّف قابل للتعديل'}
    def Activated(self):
        tag,ok=Inputs.getText(Gui.getMainWindow(),'رمز كهربائي','المعرّف')
        if not ok or not tag.strip(): return
        d=active()
        d.openTransaction('Add electrical device')
        o=d.addObject('PartDesign::FeaturePython','ElectricalDevice')
        o.Label=tag
        existing=[v for v in d.Objects if hasattr(v,'DeviceType') and v!=o]
        if any(v.Tag==tag for v in existing):
            d.abortTransaction()
            Messages.warning(Gui.getMainWindow(),'معرّف مكرر','استخدم معرّفاً مختلفاً لكل رمز')
            return
        Device(o,tag,App.Vector(len(existing)*300,0,0))
        if existing:o.TerminalSide='Left'
        from .domain import add_terminal
        add_terminal(o,'1')
        add_terminal(o,'2')
        d.recompute()
        d.commitTransaction()
        Gui.activeDocument().activeView().fitAll()
    def IsActive(self): return True


class Connect:
    def GetResources(self): return {'MenuText':'توصيل رمزين','ToolTip':'حدد رمزين ثم أنشئ وصلة منطقية، بدون حسابات كهربائية'}
    def Activated(self):
        sel=Gui.Selection.getSelection()
        if len(sel)!=2 or any(not hasattr(o,'DeviceType') for o in sel):
            Messages.information(Gui.getMainWindow(),'توصيل','حدد رمزين كهربائيين أولاً')
            return
        from .domain import add_terminal_wire
        for device in sel:
            if not getattr(device,'Terminals',[]):
                Messages.warning(Gui.getMainWindow(),'توصيل','أضف أطرافاً للرمز أولاً من خصائصه')
                return
        source,ok=Inputs.getItem(Gui.getMainWindow(),'طرف البداية',sel[0].Label,list(sel[0].Terminals),0,False)
        if not ok:return
        target,ok=Inputs.getItem(Gui.getMainWindow(),'طرف النهاية',sel[1].Label,list(sel[1].Terminals),0,False)
        if not ok:return
        d=active()
        ids={getattr(o,'WireId','') for o in d.Objects}
        number=1
        while 'W'+str(number) in ids:number+=1
        d.openTransaction('Add terminal wire')
        try:
            o=add_terminal_wire(d,sel[0],source,sel[1],target,'W'+str(number))
            d.recompute()
            d.commitTransaction()
        except ValueError as exc:
            d.abortTransaction()
            Messages.warning(Gui.getMainWindow(),'خطأ في التوصيل',message(exc))
    def IsActive(self): return bool(App.ActiveDocument)


class Quantities:
    def GetResources(self): return {'MenuText':'حصر أطوال المواسير','ToolTip':'أطوال خط المركز فقط، بدون وصلات أو هالك'}
    def Activated(self):
        rows=quantities(active())
        text='\n'.join(r['label']+': '+str(round(r['length_mm'],2))+' mm' for r in rows) or 'لا توجد مواسير'
        Messages.information(Gui.getMainWindow(),'حصر الأطوال',text)
    def IsActive(self): return bool(App.ActiveDocument)



class NewElbow:
    def GetResources(self): return {'MenuText':'كوع هندسي ٩٠°','ToolTip':'شكل هندسي مجوف بدون تصنيف ضغط أو اعتماد كتالوج'}
    def Activated(self):
        from .domain import QuarterElbow
        d=active()
        d.openTransaction('Add quarter elbow')
        o=d.addObject('PartDesign::FeaturePython','Elbow')
        o.Label='كوع هندسي تجريبي'
        QuarterElbow(o)
        d.recompute()
        d.commitTransaction()
        o.ViewObject.ShapeColor=(0.05,0.68,0.64)
        Gui.activeDocument().activeView().fitAll()
    def IsActive(self): return True

class ExportNetlist:
    def GetResources(self): return {'MenuText':'تصدير قائمة التوصيل','ToolTip':'JSON لاتصالات الأطراف، مع فحص المراجع'}
    def Activated(self):
        import json
        from .domain import netlist
        try: rows=netlist(active())
        except ValueError as exc:
            Messages.warning(Gui.getMainWindow(),'خطأ في التوصيل',message(exc))
            return
        path,_=QtWidgets.QFileDialog.getSaveFileName(Gui.getMainWindow(),'حفظ قائمة التوصيل','','JSON (*.json)')
        if path:
            with open(path.encode('utf-8') if __import__('sys').getfilesystemencoding()=='ascii' else path,'w',encoding='utf-8') as f: json.dump(rows,f,ensure_ascii=False,indent=2)
    def IsActive(self): return bool(App.ActiveDocument)


class AssemblyExample:
    def GetResources(self): return {'MenuText':'تجميع ميكانيكي','ToolTip':'إنشاء تجميع تجريبي بروابط ومكوّن مثبت، بدون ادعاء اختبار قيود الحركة'}
    def Activated(self):
        from .mechanical import make_assembly_example
        d=App.newDocument('AssemblyExample')
        d.UndoMode=1
        make_assembly_example(d)
        Gui.activeDocument().activeView().viewAxonometric()
        Gui.activeDocument().activeView().fitAll()
    def IsActive(self): return True


class UpdatePiping:
    def GetResources(self): return {'MenuText':'تعديل مسار المشروع','ToolTip':'تعديل الأطوال والكوع مع الحفاظ على اتصال المسار التجريبي'}
    def Activated(self):
        from .project import update_piping
        d=App.ActiveDocument
        values=[]
        for label,default in [('طول الدخول (مم)',d.InletPipe.CenterlineLength.Value),('طول الخروج (مم)',d.OutletPipe.CenterlineLength.Value),('نصف قطر الكوع (مم)',d.RouteElbow.BendRadius.Value),('القطر الخارجي (مم)',d.InletPipe.OuterDiameter.Value),('سمك الجدار (مم)',d.InletPipe.WallThickness.Value)]:
            value,ok=Inputs.getDouble(Gui.getMainWindow(),'تعديل مسار المشروع',label,default,0.1,1000000,2)
            if not ok:return
            values.append(value)
        try:update_piping(d,*values)
        except ValueError as exc:
            Messages.warning(Gui.getMainWindow(),'أبعاد غير صالحة',message(exc))
            return
        Gui.activeDocument().activeView().fitAll()
    def IsActive(self):
        d=App.ActiveDocument
        return bool(d and d.getObject('InletPipe') and d.getObject('RouteElbow') and d.getObject('OutletPipe'))


class ExportSheets:
    def GetResources(self): return {'MenuText':'إخراج لوحات PDF','ToolTip':'إنشاء أو تحديث لوحات المشروع التجريبي وتصدير ملفين PDF'}
    def Activated(self):
        import os
        from .project import validate_project
        from .drawing import add_drawing,add_electrical_drawing,refresh_sheets
        d=App.ActiveDocument
        path,_=QtWidgets.QFileDialog.getSaveFileName(Gui.getMainWindow(),'اختر اسم ملف اللوحة الميكانيكية','','PDF (*.pdf)')
        if not path:return
        base=os.path.splitext(path)[0]
        electrical_path=base+'-electrical.pdf'
        if os.path.exists(path) or os.path.exists(electrical_path):
            answer=Messages.question(Gui.getMainWindow(),'ملفات موجودة','استبدال ملفات PDF الموجودة؟',Messages.Yes|Messages.No)
            if answer!=Messages.Yes:return
        try:
            from .export import export_current
            export_current(d,path,electrical_path)
        except Exception as exc:
            Messages.critical(Gui.getMainWindow(),'تعذر إخراج اللوحات',message(exc))
            return
        Messages.information(Gui.getMainWindow(),'اكتمل الإخراج','تم حفظ اللوحتين من هندسة المشروع الحالية')
    def IsActive(self):
        d=App.ActiveDocument
        return bool(d)


class RouteFromPath:
    def GetResources(self): return {'MenuText':'مواسير من مسار','ToolTip':'حدد مساراً مفتوحاً بزوايا قائمة، ثم أنشئ مواسير بأكواع هندسية'}
    def Activated(self):
        from .routing import RoutedSystem
        sel=Gui.Selection.getSelection()
        if len(sel)!=1 or not hasattr(sel[0],'Shape'):
            Messages.information(Gui.getMainWindow(),'مسار المواسير','حدد مساراً مفتوحاً واحداً مرسوماً بخطوط مستقيمة')
            return
        values=[]
        for label,default in [('نصف قطر الكوع (مم)',150),('القطر الخارجي (مم)',100),('سمك الجدار (مم)',5)]:
            value,ok=Inputs.getDouble(Gui.getMainWindow(),'مواسير من مسار',label,default,0.1,1000000,2)
            if not ok:return
            values.append(value)
        d=App.ActiveDocument
        d.openTransaction('Piping from selected path')
        o=d.addObject('PartDesign::FeaturePython','RoundedRoute')
        RoutedSystem(o,[],*values)
        o.SourcePath=sel[0]
        from .documents import add_to
        add_to(d,'PipingSystem',o)
        d.recompute()
        if o.Shape.isNull():
            reason=o.Validation
            d.abortTransaction()
            Messages.warning(Gui.getMainWindow(),'المسار غير صالح',reason)
            return
        d.commitTransaction()
        o.ViewObject.ShapeColor=(0.05,0.68,0.64)
        Gui.activeDocument().activeView().fitAll()
    def IsActive(self):return bool(App.ActiveDocument)


class ElectricalEditor:
    def GetResources(self):return {'MenuText':'محرر الكهرباء','ToolTip':'إدارة الرموز والأطراف والتوصيلات مع فحص المراجع'}
    def Activated(self):
        from .panel import show_panel
        show_panel()
    def IsActive(self):return True

class DraftingEditor:
    def GetResources(self):return {'MenuText':'الرسم والأبعاد','ToolTip':'رسم مسارات وأبعاد مرتبطة ثم تحويل المسار لمواسير'}
    def Activated(self):
        from .drafting_panel import show_panel
        show_panel()
    def IsActive(self):return True

class NewProject:
    def GetResources(self):return {'MenuText':'مشروع فارغ جديد','ToolTip':'بدء مشروع رسم وميكانيكا ومواسير وكهرباء بدون نموذج جاهز'}
    def Activated(self):
        from .documents import new_project
        new_project()
    def IsActive(self):return True

class ProjectCheck:
    def GetResources(self):return {'MenuText':'فحص تقني للمشروع','ToolTip':'قائمة أخطاء تقنية محدودة، ليست مراجعة تصميم أو اعتماداً هندسياً'}
    def Activated(self):
        from .project_check import inspect
        report=inspect(App.ActiveDocument);dialog=QtWidgets.QDialog(Gui.getMainWindow());dialog.setLayoutDirection(QtCore.Qt.RightToLeft);dialog.setWindowTitle('فحص تقني محدود، ليس اعتماداً هندسياً')
        box=QtWidgets.QVBoxLayout(dialog);note=QtWidgets.QLabel('هذا فحص تقني محدود. لا يتحقق من التصادم أو الضغط أو الإجهاد أو الأمان الكهربائي أو مطابقة المعايير أو جاهزية ويندوز. عدم وجود خطأ هنا لا يعني اعتماد التصميم.')
        note.setTextFormat(QtCore.Qt.PlainText);note.setWordWrap(True);box.addWidget(note)
        summary=QtWidgets.QLabel('أخطاء تقنية: '+str(report['error_count'])+' | عناصر نموذج مرئية: '+str(report['visible_model_objects']));box.addWidget(summary)
        table=QtWidgets.QTableWidget(len(report['issues']),3);table.setHorizontalHeaderLabels(['النوع','العنصر','التفصيل']);table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        for row,item in enumerate(report['issues']):
            for col,key in enumerate(('level','label','message')):table.setItem(row,col,QtWidgets.QTableWidgetItem(level(item[key]) if key=='level' else message(item[key]) if key=='message' else item[key]))
        table.horizontalHeader().setSectionResizeMode(0,QtWidgets.QHeaderView.ResizeToContents);table.horizontalHeader().setSectionResizeMode(1,QtWidgets.QHeaderView.ResizeToContents);table.horizontalHeader().setSectionResizeMode(2,QtWidgets.QHeaderView.Stretch);table.setWordWrap(True);table.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents);box.addWidget(table)
        def choose(row,col):
            name=report['issues'][row]['object'];obj=App.ActiveDocument.getObject(name) if name else None
            if obj:Gui.Selection.clearSelection();Gui.Selection.addSelection(obj)
        table.cellClicked.connect(choose)
        close=QtWidgets.QPushButton('إغلاق');close.clicked.connect(dialog.accept);box.addWidget(close);dialog.resize(940,500);QtCore.QTimer.singleShot(0,table.resizeRowsToContents);dialog.exec_()
    def IsActive(self):return bool(App.ActiveDocument)


class MeasureSelection:
    def GetResources(self):return {'MenuText':'قياس التحديد','ToolTip':'طول ومساحة وحجم وأقصر مسافة، قراءة فقط دون إنشاء أبعاد بالرسم'}
    def Activated(self):
        from .measurement import inspect
        try:report=inspect(Gui.Selection.getSelectionEx())
        except Exception as exc:Messages.warning(Gui.getMainWindow(),'تعذر القياس',message(exc));return
        dialog=QtWidgets.QDialog(Gui.getMainWindow());dialog.setLayoutDirection(QtCore.Qt.RightToLeft);dialog.setWindowTitle('قياس هندسي للقراءة فقط')
        box=QtWidgets.QVBoxLayout(dialog);note=QtWidgets.QLabel('يمكن اختيار عنصرين فرعيين من نفس الجسم. المسافة هي أقصر فاصل بين الشكلين، وليست مسافة المراكز أو سمكاً أو سماحية تصنيع. الزاوية الحادة غير موجهة لخطين مستقيمين أو سطحين مستويين فقط. لا ينشئ هذا القياس بعداً محفوظاً أو اعتماداً هندسياً.')
        note.setTextFormat(QtCore.Qt.PlainText);note.setWordWrap(True);box.addWidget(note)
        values=[]
        for item in report['items']:
            title=item['label']+' / '+({'Whole':'الجسم كاملاً','whole':'الجسم كاملاً','Object':'الجسم كاملاً'}.get(item['selection'],item['selection']))
            values.extend([(title,'طول الحواف (mm)',item['length_mm']),(title,'مساحة السطح (mm²)',item['area_mm2']),(title,'حجم المصمتات (mm³)',item['volume_mm3'])])
            if 'radius_mm' in item:values.append((title,'نصف قطر الحافة الدائرية (mm)',item['radius_mm']))
            if 'point_mm' in item:
                for axis,value in zip(('X','Y','Z'),item['point_mm']):values.append((title,axis+' العالمي (mm)',value))
        if report['minimum_distance_mm'] is not None:values.append(('التحديدان','أقصر مسافة (mm)',report['minimum_distance_mm']))
        if report['unoriented_line_angle_degrees'] is not None:values.append(('الحافتان','زاوية حادة غير موجهة (°)',report['unoriented_line_angle_degrees']))
        if report['unoriented_planar_face_angle_degrees'] is not None:values.append(('السطحان','زاوية حادة غير موجهة (°)',report['unoriented_planar_face_angle_degrees']))
        table=QtWidgets.QTableWidget(len(values),3);table.setHorizontalHeaderLabels(['العنصر','الكمية الهندسية','القيمة']);table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        for row,items in enumerate(values):
            for col,value in enumerate(items):
                cell=QtWidgets.QTableWidgetItem(format(value,'.10g') if col==2 else value)
                if col==2:cell.setTextAlignment(int(QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter))
                table.setItem(row,col,cell)
        table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch);box.addWidget(table)
        close=QtWidgets.QPushButton('إغلاق');close.clicked.connect(dialog.accept);box.addWidget(close);dialog.resize(760,min(700,150+len(values)*30));dialog.exec_()
    def IsActive(self):return bool(App.ActiveDocument and Gui.Selection.getSelection())


def _repair_menu_titles():
    """Undo UTF-8-read-as-Latin-1 corruption of main-window menu titles (seen after an Assembly document is created)."""
    try:
        for action in Gui.getMainWindow().menuBar().actions():
            text=action.text()
            try:fixed=text.encode('latin-1').decode('utf-8')
            except (UnicodeEncodeError,UnicodeDecodeError):continue
            if fixed!=text and any('\u0600'<=c<='\u06ff' for c in fixed):action.setText(fixed)
    except Exception:pass


class _MenuRepair(QtCore.QObject):
    def eventFilter(self,obj,event):
        if event.type() in (QtCore.QEvent.ActionChanged,QtCore.QEvent.ActionAdded):_repair_menu_titles()
        return False


def install_menu_repair():
    bar=Gui.getMainWindow().menuBar()
    if getattr(bar,'_delta_menu_repair',None) is None:
        bar._delta_menu_repair=_MenuRepair(bar);bar.installEventFilter(bar._delta_menu_repair)
    _repair_menu_titles()


class DeltaWorkbench(Gui.Workbench):
    MenuText='دلتا | ميكانيكا ومواسير وكهرباء'
    ToolTip='مرحلة تطوير تجريبية، ليست إصداراً نهائياً'
    def Initialize(self):
        commands=[]
        for name,cls in [('Demo',Demo),('Pipe',NewPipe),('Device',NewDevice),('Connect',Connect),('Quantities',Quantities),('Elbow',NewElbow),('Netlist',ExportNetlist),('Assembly',AssemblyExample),('UpdatePiping',UpdatePiping),('Sheets',ExportSheets),('RouteFromPath',RouteFromPath),('ElectricalEditor',ElectricalEditor),('DraftingEditor',DraftingEditor),('NewProject',NewProject),('ProjectCheck',ProjectCheck),('MeasureSelection',MeasureSelection)]:
            key='Delta_'+name
            Gui.addCommand(key,cls())
            commands.append(key)
        self.appendToolbar('الرسم',['Delta_DraftingEditor','Delta_MeasureSelection'])
        self.appendToolbar('المشروع',['Delta_NewProject','Delta_ProjectCheck','Delta_Demo','Delta_UpdatePiping','Delta_Sheets'])
        self.appendToolbar('المواسير',['Delta_Pipe','Delta_Elbow','Delta_RouteFromPath','Delta_Quantities'])
        self.appendToolbar('الكهرباء',['Delta_ElectricalEditor','Delta_Device','Delta_Connect','Delta_Netlist'])
        self.appendToolbar('الميكانيكا',['Delta_Assembly'])
        self.appendMenu('دلتا',commands)
    def Activated(self):install_menu_repair()
    def GetClassName(self): return 'Gui::PythonWorkbench'


def register():
    Gui.addWorkbench(DeltaWorkbench())
