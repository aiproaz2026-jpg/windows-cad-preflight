Adopted router for the repo: wire_route v12 = patches/v99/wire_route.py (CI evidence: dist/v21bj, run 46123819349).
Decision date 2026-11-28. Reason: 0 overlap pairs on the control panel and on every routed gallery sheet, W19 and W22 routed strictly, unit test 42/42.
Known tradeoffs: a few more crossings on small sheets than v10 (PLC 3, elec2 1, elec6 9, elec8 4), 2 mm minimum lane clearance reads as crowded at A3 scale.
Not covered: blocks_A3 and gallery_terms were not routed in v21bj (checked in v21bk). CI is Windows Server 2022 with Mesa software GL, not real hardware.
