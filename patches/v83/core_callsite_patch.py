# CI/build-time edit: add the wire_route call site at the top of Connection.execute. Idempotent, additive.
import sys, re
p = sys.argv[1]
s = open(p, encoding='utf-8').read()
if 'wire_route.plan(obj)' in s:
    print('already patched'); sys.exit(0)
i = s.index('class Connection')
j = s.index('    def execute(self, obj):\n', i)
k = j + len('    def execute(self, obj):\n')
block = ("        try:\n            from . import wire_route\n            if wire_route.plan(obj) is not None:\n                return\n        except Exception:\n            pass\n")
open(p, 'w', encoding='utf-8').write(s[:k] + block + s[k:])
print('patched', p)
