# gallery_metrics.py - wiring numbers for the demo gallery, before and after wire_route

**Status: UNTESTED.** Written by a code-only writer. No CI run has executed it, no FreeCAD has
opened it, and nothing here is a real-hardware test. It is a measurement script for CI evidence,
not a design check and not a safety check.

Patch v86, three files:

| file | what it is |
| --- | --- |
| `gallery_metrics.py` | the FreeCADCmd script. Copy to `C:/gallery_metrics.py` and run with `FreeCADCmd -c "exec(open('C:/gallery_metrics.py',encoding='utf-8').read())"` |
| `gallery_ci_steps.yml.txt` | two workflow steps (run + gate) plus the publish line, in the same style as the existing build workflow |
| `README-gallery-metrics.md` | this note |

## What it measures

For every gallery sheet it reports, for the state before rerouting and the state after
`wire_route.reroute(doc)`:

- `wires` - number of `Connection` objects with a computed shape (`SourceTerminal` present)
- `overlap_pairs`, `overlap_mm` - collinear overlapping segment pairs between different wires,
  and their total shared length in mm, excluding junctions
- `junction_overlaps`, `junction_mm` - the same, for overlaps that sit at a terminal both wires
  end on (a node, not a drafting defect). `wire_route.overlaps()` decides this with its
  `shared_terminal` rule; this script only splits the list
- `crossings` - perpendicular crossings between different wires (`wire_route.crossings()`)
- `segments_in_foreign_box` - wire segments that pass through a device box that is not one of
  the wire's own two devices. Measured from the shapes in every state, so the before number
  comes from the drawing, not from the router's own report
- `min_clearance_mm` - the smallest distance between any wire segment and any device box other
  than its own two, in mm. `null` when a sheet has no wires
- `plan_matches_shape` - how many wires already carry exactly the path `wire_route.plan()` would
  plan for them, out of `plan_checked`. Stock drawings should be near 0; a routed drawing should
  be all of them
- `device_boxes`, `label_boxes` - how many obstacle boxes the router saw

After a reroute it also records `routed`, `fallback` (wire ids the router refused),
`wires_changed_by_reroute`, and `reroute_plan_matches_shape` - how many wires carry exactly the
path `reroute()` reported for them.

## The two passes: call site off, then on

Each sheet is built twice.

- **off** - `wire_route.apply()` returns `False` while the sheet is built, so every wire keeps the
  stock straight / L / Z path. That is the real "before" drawing. Then `reroute(doc)` runs.
- **on** - `apply()` is live while the sheet is built, so every wire is routed as its
  `Connection.execute` runs. If the installed `core.py` carries the build-time call site
  (`core_callsite_patch.py`), that call site does the work. If it does not, the script calls
  `wire_route.install()` for the build and records `call_site_present: false` in `result.json`.
  Then `reroute(doc)` runs again, which also shows whether a second reroute is a no-op.

`WIRE_ROUTE_PRESET` (default `balanced`) is applied once at start through `wire_route.preset()`
when that function exists, so the whole gallery is measured under one preset.

## The gallery

The gallery is the demo scripts that build a wired sheet. The script runs them as they are -
`exec` of the file - so it carries no copy of their layouts and cannot drift from them. It does
not edit them. The step stages these files into `C:/gallery_src/` and the script measures every
`*.py` it finds there, in name order:

| sheet | repo path | builds |
| --- | --- | --- |
| gallery_elec2 | patches/v64/gallery_elec2.py | single-phase pump control (PC) |
| gallery_elec3 | patches/v64/gallery_elec3.py | level / timer control (LT) |
| v70_elec4 | patches/v70_elec4.py | control panel (CP) |
| elec5 | patches/v71/elec5.py | vent / thermostat (VT) |
| gallery_elec6 | patches/v75/demos/gallery_elec6.py | VFD feeder (VF) |
| gallery_elec7 | patches/v75/demos/gallery_elec7.py | PLC panel (PL) |
| gallery_elec8 | patches/v75/demos/gallery_elec8.py | transformer (TR) |
| gallery_terms | patches/v75/term2/gallery_terms.py | terminal chain (TR) |
| demo_control_panel | patches/v76/demo_control_panel.py | control panel demo |
| demo_motor_starters | patches/v76/demo_motor_starters.py | motor starter variants |
| demo_dol_vertical | patches/v76/demo_dol_vertical.py | DOL starter, vertical layout |

`gallery_sym.py` and `gallery_iec.py` build symbol grids with no wires, so they are not in the
list. If one is added anyway it lands in `skipped` with reason `no wires were built`, not in the
numbers.

If the gallery set is different from this list, change the `$scripts` array in the CI step.
Nothing in `gallery_metrics.py` is per-sheet.

## Output

Written to `C:/seed/gallerymetrics/` (override with `GALLERY_METRICS_OUT`):

- `result.json` - `done`, `call_site_present`, `preset`, `scripts_seen`, `sheets_measured`,
  `sheets_failed`, `skipped`, `pass_failures`, a flat `summary` (one row per sheet and pass, with
  `before` and `after` metrics, `reroute_rows`, `reroute_plan_matches_shape`) and the full
  per-sheet detail under `sheets` including `per_wire` rows from `reroute()`
- `<sheet>_A3.pdf` - one A3 sheet per measured sheet, drawn from the document after the reroute,
  with the before and after numbers in the title block

The demo scripts also write their own `result.json`, PDF and FCStd into their own seed folders
(`C:/seed/gallery64e`, `C:/seed/gallery72`, `C:/seed/demo72cp`, ...), exactly as they do when the
workflow runs them on their own.

## Knobs

| env var | default | effect |
| --- | --- | --- |
| `GALLERY_SCRIPTS` | `C:/gallery_src` | folder of demo scripts to measure |
| `GALLERY_METRICS_OUT` | `C:/seed/gallerymetrics` | where `result.json` and the PDFs go |
| `GALLERY_PASSES` | `off,on` | which passes to run. `off` alone roughly halves the run |
| `GALLERY_PLAN_CHECK` | `1` | `0` skips the `plan_matches_shape` measurement, which plans every wire once more and is the most expensive number |
| `WIRE_ROUTE_PRESET` | `balanced` | `wire_route.preset()` name |

## Gate

The gate step fails only on things that are wrong with this measurement, not on another sheet's
bug:

- no `result.json`, a timeout, `done` not true, a top-level `error`
- `sheets_measured` is 0
- for any sheet and pass: the reroute changed the wire count
- for any sheet and pass: `reroute_plan_matches_shape` is not equal to the number of wires
  `reroute()` reported (the router wrote something other than the path it reported)

A demo script that does not build is printed as a `GALLERY NOTE` and listed in `skipped` or
`pass_failures`. That is that sheet's problem, not this script's, and it should be visible in the
evidence rather than fail the build here.

## What I could not check

- **It has never run in FreeCAD.** Syntax is checked (`ast.parse`, `py_compile`), and the file was
  run once against stub `FreeCAD`, `wire_route`, `core`, `Part` and `minipdf` modules to exercise
  its own plumbing (the two passes, `exec` of a demo script, document discovery, the summary,
  `result.json`, the PDF call, the skip and crash paths). That proves nothing about the real
  FreeCAD API, the real router or a real drawing. No CI run has touched it.
- **Runtime is an estimate.** Eleven sheets, two builds each, and each build is a full demo sheet
  with its own PDF and FCStd write. If a build takes 20-60 s on Mesa, the step lands around
  7-22 minutes; the step timeout is 45 minutes. `GALLERY_PASSES=off` halves it.
- **It depends on the demo scripts' own shape**: one document per script, a `res` dict, and a
  module-level `OUT`. All eleven do that today. A script that builds two documents, closes its
  document, or raises before creating one is handled (the last document is measured; a missing
  document is recorded as an error) but not measured properly.
- **`plan_matches_shape` compares rounded points.** It rounds to 0.1 mm on both sides, so a
  sub-0.1 mm difference reads as a match.
- **The call site may not be there.** If the workflow does not run `core_callsite_patch.py`, the
  `on` pass routes through `wire_route.install()` instead and `call_site_present` says `false`.
  That is a different mechanism than the shipped call site; the numbers are comparable but the
  path is not identical.
- **The PDF is a CI drawing, not a deliverable.** Software OpenGL, CI only, no rating or safety
  claim. Same caveat as every other sheet in this repo.

## Reference

The measurement helpers (`measure`, `min_clearance`, `wire_paths`, the A3 `sheet()` drawing) are
taken from `patches/v84/route_demos.py` and adapted: the per-wire state diagnostics are dropped,
`segments_in_foreign_box` is measured from the geometry in every state rather than only from the
reroute report, and `plan_matches_shape` is measured against the shapes rather than only against
the reroute rows.
