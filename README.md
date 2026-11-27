# Windows CAD build and test workspace (Arabic CAD program, "Delta Engineering" add-on on FreeCAD)

This repository holds the build recipes, patches, and CI evidence for a free Windows CAD installer
(piping and pump stations, 3D mechanical parts, electrical drawing, Arabic interface).
It is a work in progress and is public only while the program is being finished.

- The installer bundles FreeCAD (LGPL-2.1-or-later and many other open-source components) and the
  Delta Engineering Python add-on (GPL-3.0-or-later, see LICENSE).
- A third-party notices index for every shipped file is generated at build time:
  see `dist/<build>/checks/THIRD-PARTY-NOTICES.txt` (an index, not a legal opinion).
- `src/` holds the add-on development source (GPL-3.0-or-later). `patches/` holds the patches applied on top of it.
- `dist/` holds CI evidence (logs, JSON results, screenshots as base64, hashes). CI is Windows Server 2022 with
  Mesa software OpenGL. It is not a real-hardware test.
- Installers are unsigned and experimental. Library values (pipes, flanges, threads) come from cited public
  sources and are editable; they are not certified for engineering use without review by a qualified engineer.
- Arabic translations were written by the build agent and are not professionally reviewed.
