# -*- coding: utf-8 -*-
"""Arabic display of property-panel NAMES and group headers (column 0 only). Display text only: the real property names,
values, and the Tasks panel are untouched. Hand-written translations, not professionally reviewed. GPL-3.0-or-later."""
from PySide import QtCore, QtWidgets

PROPS = {
 'Placement': 'الموضع', 'Label': 'التسمية', 'Label2': 'التسمية 2', 'Visibility': 'الظهور', 'Shape': 'الشكل',
 'Area': 'المساحة', 'Length': 'الطول', 'Width': 'العرض', 'Height': 'الارتفاع', 'Radius': 'نصف القطر', 'Diameter': 'القطر',
 'Angle': 'الزاوية', 'Base': 'الأساس', 'Draft': 'المسودة', 'Attachment': 'الإرفاق', 'Attacher Engine': 'محرك الإرفاق',
 'Attachment Support': 'دعامة الإرفاق', 'Attachment Offset': 'إزاحة الإرفاق', 'Map Mode': 'نمط الربط', 'Map Path Parameter': 'معامل مسار الربط',
 'Map Reversed': 'ربط معكوس', 'Support': 'الدعامة', 'Closed': 'مغلق', 'Chamfer Size': 'حجم الشطف', 'Fillet Radius': 'نصف قطر التدوير',
 'Face Maker Class': 'صانع الأوجه', 'Make Face': 'إنشاء وجه', 'Points': 'النقاط', 'Start': 'البداية', 'End': 'النهاية',
 'First Angle': 'الزاوية الأولى', 'Last Angle': 'الزاوية الأخيرة', 'Pitch': 'الخطوة', 'Height Left': 'الارتفاع الأيسر',
 'Part': 'الجزء', 'Volume': 'الحجم', 'Mass': 'الكتلة', 'Material': 'المادة', 'Density': 'الكثافة', 'Edges': 'الحواف',
 'Faces': 'الأوجه', 'Vertices': 'الرؤوس', 'Solids': 'المجسمات', 'Thickness': 'السماكة', 'Size': 'الحجم', 'Depth': 'العمق',
 'Offset': 'الإزاحة', 'Reversed': 'معكوس', 'Midplane': 'المستوى الأوسط', 'Type': 'النوع', 'Profile': 'المقطع',
 'Sketch': 'الرسم التخطيطي', 'Group': 'المجموعة', 'Links': 'الروابط', 'Expression Engine': 'محرك التعبيرات',
 'Description': 'الوصف', 'Comment': 'التعليق', 'Tag': 'الوسم', 'Position': 'الإحداثي', 'Direction': 'الاتجاه', 'Axis': 'المحور',
 'Rotation': 'الدوران', 'Scale': 'المقياس', 'Color': 'اللون', 'Line Color': 'لون الخط', 'Line Width': 'سماكة الخط',
 'Point Size': 'حجم النقطة', 'Shape Color': 'لون الشكل', 'Transparency': 'الشفافية', 'Display Mode': 'نمط العرض',
 'Draw Style': 'نمط الرسم', 'Selectable': 'قابل للتحديد', 'Show In Tree': 'إظهار في الشجرة', 'Bounding Box': 'الصندوق المحيط',
 'Deviation': 'الانحراف', 'Angular Deflection': 'الانحراف الزاوي', 'Lighting': 'الإضاءة', 'Line Style': 'نمط الخط',
 'Object Style': 'نمط الكائن', 'Override Material': 'تجاوز المادة', 'Pattern': 'النمط', 'Shape Appearance': 'مظهر الشكل',
 'Shape Material': 'مادة الشكل', 'Display Options': 'خيارات العرض', 'Selection': 'التحديد', 'Base Feature': 'الميزة الأساسية',
 'Refine': 'تنقية', 'Fillet': 'تدوير', 'Chamfer': 'شطف', 'Pad': 'بثق', 'Pocket': 'تجويف', 'Revolution': 'دوران', 'Groove': 'أخدود',
 'Number Of Teeth': 'عدد الأسنان', 'Module': 'المعامل', 'Pressure Angle': 'زاوية الضغط', 'Bore': 'الثقب', 'Bore Diameter': 'قطر الثقب',
 'Outer Diameter': 'القطر الخارجي', 'Inner Diameter': 'القطر الداخلي', 'Nominal Diameter': 'القطر الاسمي', 'Wall Thickness': 'سماكة الجدار',
 'Device Type': 'نوع الجهاز', 'Terminals': 'الأطراف', 'Terminal Side': 'جهة الطرف', 'Terminal Sides': 'جهات الأطراف',
 'Symbol Template': 'قالب الرمز', 'Symbol Scope': 'نطاق الرمز', 'Electrical': 'كهرباء', 'Mechanical': 'ميكانيك', 'Piping': 'مواسير',
 'Wire Id': 'معرّف السلك', 'Source Device': 'جهاز المصدر', 'Target Device': 'جهاز الهدف', 'Source Terminal': 'طرف المصدر',
 'Target Terminal': 'طرف الهدف', 'Path': 'المسار', 'Dimension': 'البعد', 'Measure': 'القياس', 'Text': 'النص', 'Font Size': 'حجم الخط',
 'Font Name': 'اسم الخط', 'Distance': 'المسافة', 'Elevation': 'المنسوب', 'Flow': 'التدفق', 'Head': 'الرأس', 'Power': 'القدرة',
 'Speed': 'السرعة', 'Pressure': 'الضغط', 'Nominal Size': 'المقاس الاسمي', 'Pipe Class': 'فئة الأنابيب', 'Schedule': 'السماكة القياسية (Schedule)',
 'Standard': 'المعيار', 'Thread': 'القلاووظ', 'Thread Pitch': 'خطوة القلاووظ', 'Thread Length': 'طول القلاووظ',
 'Major Diameter': 'القطر الأكبر', 'Minor Diameter': 'القطر الأصغر', 'Pitch Diameter': 'القطر الفعّال', 'Start Point': 'نقطة البداية',
 'End Point': 'نقطة النهاية', 'Center': 'المركز', 'Normal': 'العمودي', 'Base Point': 'نقطة الأساس', 'X': 'س', 'Y': 'ص', 'Z': 'ع',
 'Name': 'الاسم', 'Value': 'القيمة', 'Property': 'الخاصية', 'Visible': 'مرئي', 'Hidden': 'مخفي', 'Id': 'المعرّف', 'Index': 'الفهرس',
 'Document': 'المستند', 'Use Legacy Placement': 'استخدام الموضع القديم', 'Attacher Type': 'نوع المُرفِق',
 'Map Path Parameter ': 'معامل مسار الربط', 'Offset Angle': 'زاوية الإزاحة', 'Line': 'خط', 'Circle': 'دائرة', 'Arc': 'قوس',
}


class _D(QtWidgets.QStyledItemDelegate):
    def displayText(self, value, locale):
        s = value if isinstance(value, str) else str(value)
        k = s.strip()
        return PROPS.get(k) or PROPS.get(k.replace('_', ' ')) or QtWidgets.QStyledItemDelegate.displayText(self, value, locale)


_keep = []


def install(mw):
    """Install on the property editor's name column once. Returns number of editors patched."""
    n = 0
    for w in mw.findChildren(QtWidgets.QTreeView):
        try:
            cn = w.metaObject().className()
        except Exception:
            continue
        if 'PropertyEditor' in cn and not w.property('delta_ar_props'):
            d = _D(w)
            w.setItemDelegateForColumn(0, d)
            w.setProperty('delta_ar_props', True)
            _keep.append(d)
            n += 1
    return n
