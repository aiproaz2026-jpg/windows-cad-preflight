# SPDX-License-Identifier: GPL-3.0-or-later
"""Synchronous vector-PDF export, independent of asynchronous TechDraw UI caches.
Native sheets remain editable; this output always projects current source solids.
"""
import hashlib,json,os,tempfile
import FreeCAD as App
import Part,TechDraw
from PySide import QtCore,QtGui,QtSvg
from .domain import netlist
from .project import validate_project


def path_for_python(path):
    import sys
    return path.encode('utf-8') if sys.getfilesystemencoding()=='ascii' else path


def projection_svg(shape,direction):
    if shape.isNull() or not shape.isValid():raise ValueError('Invalid source geometry')
    # Both calls finish on the caller thread, not TechDraw view-worker threads.
    geometry=TechDraw.projectEx(shape,direction)
    bounds=App.BoundBox()
    for part in geometry:
        if not part.isNull():bounds.add(part.BoundBox)
    if not bounds.isValid() or max(bounds.XLength,bounds.YLength)<=0:
        raise ValueError('Empty or degenerate projection')
    margin=max(bounds.XLength,bounds.YLength)*0.025
    box=(bounds.XMin-margin,-bounds.YMax-margin,bounds.XLength+2*margin,bounds.YLength+2*margin)
    # Fit-to-page stroke scales with the view extent, not arbitrary model units.
    stroke=max(bounds.XLength,bounds.YLength)*0.0012
    content=TechDraw.projectToSVG(shape,direction).replace('stroke-width="1.0"','stroke-width="'+format(stroke,'.12g')+'"')
    return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="%s">%s</svg>'%(' '.join(str(v) for v in box),content)


def current_snapshot(d):
    from .validation import valid_document
    valid_document(d)
    from .documents import model_objects,electrical_objects,world_shape
    models=model_objects(d);electric=electrical_objects(d)
    for obj in models:
        if not obj.Shape.isValid():raise ValueError('Invalid source geometry: '+obj.Label)
        if hasattr(obj,'Validation') and obj.Shape.isNull():raise ValueError(obj.Validation)
    # Invalid parametric objects must not disappear silently from exports.
    for obj in d.Objects:
        if obj.TypeId in ('Part::Cut','Part::Fuse','Part::Common') and (obj.Shape.isNull() or not obj.Shape.isValid()):raise ValueError('Invalid native solid feature: '+obj.Label)
        if hasattr(obj,'Validation') and hasattr(obj,'Shape') and obj.Shape.isNull():
            raise ValueError('Invalid object: '+obj.Label+' / '+obj.Validation)
    if not models and not electric:raise ValueError('No drawable model or electrical objects')
    mechanical=Part.makeCompound([world_shape(o) for o in models]) if models else None
    electrical=Part.makeCompound([world_shape(o) for o in electric]) if electric else None
    views=[projection_svg(mechanical,App.Vector(0,0,1)) if mechanical else None,
           projection_svg(mechanical,App.Vector(1,-1,1)) if mechanical else None,
           projection_svg(electrical,App.Vector(0,0,1)) if electrical else None]
    report={'centerline_mm':sum(o.CenterlineLength.Value for o in d.Objects if hasattr(o,'CenterlineLength'))}
    rows=netlist(d)
    signature=hashlib.sha256((''.join(v or '' for v in views)+json.dumps(rows,sort_keys=True)).encode('utf-8')).hexdigest()
    return views,rows,signature,report


def _page(path,title,views,rows=None,annotations=None,single=False):
    writer=QtGui.QPdfWriter(path)
    writer.setPageSize(QtGui.QPageSize(QtGui.QPageSize.A3))
    writer.setPageOrientation(QtGui.QPageLayout.Landscape)
    writer.setResolution(100)
    writer.setTitle(title)
    painter=QtGui.QPainter()
    if not painter.begin(writer):raise IOError('Cannot start PDF writer')
    try:
        w,h=writer.width(),writer.height()
        painter.fillRect(0,0,w,h,QtGui.QColor('white'))
        painter.setPen(QtGui.QColor('#16283b'))
        painter.drawRect(20,20,w-40,h-40)
        font=QtGui.QFont('DejaVu Sans',16);painter.setFont(font)
        painter.drawText(QtCore.QRectF(45,35,w-90,70),int(QtCore.Qt.AlignRight|QtCore.Qt.AlignVCenter),title)
        painter.drawLine(20,110,w-20,110)
        painter.setFont(QtGui.QFont('DejaVu Sans',10))
        painter.drawText(QtCore.QRectF(45,h-100,w-90,60),int(QtCore.Qt.AlignRight|QtCore.Qt.AlignVCenter),'نموذج توضيحي للتطوير فقط، غير صالح للتنفيذ. إسقاط ملائم للصفحة، ليس مقياس طباعة معتمداً.')
        if single:
            rectangles=[QtCore.QRectF(100,180,w-200,h-380)]
            labels=['رسم وأبعاد مرتبطة | مليمتر']
        elif rows is None:
            rectangles=[QtCore.QRectF(65,170,w*0.43,h-330),QtCore.QRectF(w*0.52,170,w*0.43,h-330)]
            labels=['المسقط العلوي','منظور ميكانيكي']
        else:
            rectangles=[QtCore.QRectF(65,210,w*0.52,h-430)]
            labels=['توصيلات الأطراف المنطقية']
        for svg,rect,label in zip(views,rectangles,labels):
            if svg is None:
                painter.drawText(rect,int(QtCore.Qt.AlignCenter),'لا توجد عناصر في هذا القسم')
                continue
            renderer=QtSvg.QSvgRenderer(QtCore.QByteArray(svg.encode('utf-8')))
            if not renderer.isValid():raise ValueError('Projection SVG failed to render')
            # Preserve aspect ratio explicitly.
            box=renderer.viewBoxF()
            ratio=min(rect.width()/box.width(),rect.height()/box.height())
            target=QtCore.QRectF(rect.center().x()-box.width()*ratio/2,rect.center().y()-box.height()*ratio/2,box.width()*ratio,box.height()*ratio)
            renderer.render(painter,target)
            if annotations:
                painter.setFont(QtGui.QFont('DejaVu Sans',8))
                for ann in annotations:
                    text,x,y,side=ann[:4]
                    px=target.x()+(x-box.x())*ratio
                    py=target.y()+(-y-box.y())*ratio
                    if side=='normal':
                        nx,ny=ann[4]
                        ax=px+nx*10;ay=py-ny*10
                        if nx>0.3:rx=ax;align=QtCore.Qt.AlignLeft
                        elif nx<-0.3:rx=ax-117;align=QtCore.Qt.AlignRight
                        else:rx=ax-58;align=QtCore.Qt.AlignHCenter
                        if ny>0.3:ry=ay-24
                        elif ny<-0.3:ry=ay
                        else:ry=ay-12
                        painter.drawText(QtCore.QRectF(rx,ry,117,24),int(align|QtCore.Qt.AlignVCenter),text)
                        continue
                    labelrect=QtCore.QRectF(px-125 if side=='left' else px+8,py-12,117,24)
                    painter.drawText(labelrect,int(QtCore.Qt.AlignRight if side=='left' else QtCore.Qt.AlignLeft),text)
                painter.setFont(QtGui.QFont('DejaVu Sans',10))
            painter.drawText(QtCore.QRectF(rect.x(),125,rect.width(),40),int(QtCore.Qt.AlignHCenter),label)
        if rows is not None:
            x=w*0.65
            painter.drawText(QtCore.QRectF(x,190,w*0.30,40),int(QtCore.Qt.AlignRight),'قائمة توصيل الأطراف')
            y=250;page_number=1
            flags=int(QtCore.Qt.AlignLeft|QtCore.Qt.TextWrapAnywhere)
            for row in rows:
                line=row['wire']+' : '+row['source']['device']+':'+row['source']['terminal']+' -> '+row['target']['device']+':'+row['target']['terminal']
                if len(line)>4000:raise ValueError('Connection row exceeds supported 4000-character safety limit')
                width=w*0.30
                required=max(45,painter.fontMetrics().boundingRect(QtCore.QRect(0,0,int(width),100000),flags,line).height()+15)
                if required>h-420:raise ValueError('Connection row is too large for one page')
                if y+required>h-150:
                    if not writer.newPage():raise IOError('Cannot create continuation page')
                    page_number+=1;painter.fillRect(0,0,w,h,QtGui.QColor('white'))
                    painter.drawRect(20,20,w-40,h-40)
                    painter.drawText(QtCore.QRectF(45,35,w-90,70),int(QtCore.Qt.AlignRight),'قائمة توصيل الأطراف | صفحة '+str(page_number))
                    painter.drawLine(20,110,w-20,110)
                    painter.drawText(QtCore.QRectF(45,h-100,w-90,60),int(QtCore.Qt.AlignRight),'توصيلات منطقية فقط، بدون حسابات أو اعتماد هندسي')
                    x=65;y=180
                painter.drawText(QtCore.QRectF(x,y,width,required),flags,line);y+=required
    finally:painter.end()


def export_current(d,mechanical_path,electrical_path):
    if os.path.abspath(mechanical_path)==os.path.abspath(electrical_path):raise ValueError('Choose two different paths')
    views,rows,signature,report=current_snapshot(d)
    targets=[mechanical_path,electrical_path]
    temporary=[]
    previous={}
    replaced=[]
    try:
        for target in targets:
            parent=os.path.dirname(os.path.abspath(target))
            if not os.path.isdir(path_for_python(parent)):raise IOError('Destination directory does not exist')
            directory=path_for_python(parent)
            fd,path=tempfile.mkstemp(suffix=b'.pdf' if isinstance(directory,bytes) else '.pdf',dir=directory)
            os.close(fd)
            temporary.append(path.decode('utf-8') if isinstance(path,bytes) else path)
        _page(temporary[0],'الميكانيكا والمواسير | مشروع تجريبي',views[:2])
        from .core import terminal_position
        from .documents import world_point
        labels=[]
        for device in [o for o in d.Objects if hasattr(o,'DeviceType')]:
            tagpoint=world_point(device,device.Position+App.Vector(-40,65,0))
            labels.append((device.Tag,tagpoint.x,tagpoint.y,'right'))
            for terminal in device.Terminals:
                point=world_point(device,terminal_position(device,terminal))
                side='left' if device.TerminalSide=='Right' else 'right'
                labels.append((terminal,point.x,point.y,side))
        _page(temporary[1],'الكهرباء | توصيلات منطقية تجريبية',[views[2]],rows,labels)
        for path in temporary:
            with open(path_for_python(path),'rb') as f:
                if f.read(5)!=b'%PDF-':raise IOError('PDF export failed validation')
            if os.path.getsize(path_for_python(path))<1000:raise IOError('PDF export unexpectedly empty')
        # Generate both first, then back up existing bytes for rollback if replacement fails.
        for target in targets:
            if os.path.exists(path_for_python(target)):
                with open(path_for_python(target),'rb') as f:previous[target]=f.read()
            else:previous[target]=None
        try:
            for source,target in zip(temporary,targets):
                os.replace(path_for_python(source),path_for_python(target))
                replaced.append(target)
        except Exception:
            for target in replaced:
                if previous[target] is None:os.remove(path_for_python(target))
                else:
                    with open(path_for_python(target),'wb') as f:f.write(previous[target])
            raise
        return {'source_signature':signature,'centerline_mm':report['centerline_mm'],'wire_count':len(rows),'synchronous_projection':True}
    finally:
        for path in temporary:
            if os.path.exists(path_for_python(path)):os.remove(path_for_python(path))
