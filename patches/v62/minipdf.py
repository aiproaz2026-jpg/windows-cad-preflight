# -*- coding: utf-8 -*-
"""Tiny dependency-free vector PDF writer (lines, rectangles, Latin text with Helvetica). GPL-3.0-or-later."""
def _esc(s):
    return s.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')


class Page:
    def __init__(self, w, h):
        self.w, self.h, self.ops = w, h, []

    def line(self, pts, width=0.8, rgb=(0, 0, 0)):
        if len(pts) < 2:
            return
        o = ['%.3f %.3f %.3f RG %.2f w' % (rgb + (width,)), '%.2f %.2f m' % pts[0]]
        o += ['%.2f %.2f l' % p for p in pts[1:]]
        o.append('S')
        self.ops.append(' '.join(o))

    def rect(self, x, y, w, h, width=1.0):
        self.ops.append('0 0 0 RG %.2f w %.2f %.2f %.2f %.2f re S' % (width, x, y, w, h))

    def text(self, x, y, s, size=8, rgb=(0, 0, 0)):
        s = s.encode('latin-1', 'replace').decode('latin-1')
        self.ops.append('BT %.3f %.3f %.3f rg /F1 %.1f Tf %.2f %.2f Td (%s) Tj ET' % (rgb + (size, x, y, _esc(s))))

    def save(self, path):
        content = '\n'.join(self.ops).encode('latin-1')
        objs = [b'<< /Type /Catalog /Pages 2 0 R >>', b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
                ('<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %.2f %.2f] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>' % (self.w, self.h)).encode(),
                b'<< /Length %d >>\nstream\n' % len(content) + content + b'\nendstream',
                b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
        out = bytearray(b'%PDF-1.4\n'); offs = []
        for i, o in enumerate(objs, 1):
            offs.append(len(out)); out += b'%d 0 obj\n' % i + o + b'\nendobj\n'
        x = len(out); out += b'xref\n0 %d\n0000000000 65535 f \n' % (len(objs) + 1)
        for o in offs:
            out += b'%010d 00000 n \n' % o
        out += b'trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n' % (len(objs) + 1, x)
        open(path, 'wb').write(bytes(out))
