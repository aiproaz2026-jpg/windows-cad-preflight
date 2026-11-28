# wire_route — orthogonal wire router for schematic connections

Status: **untested inside FreeCAD.** This revision has only run in a stand-in harness (fake
`FreeCAD`/`Part` modules) on a Linux box. GPL-3.0-or-later, same as the project.

What this revision adds: **stub fan-out for multi-terminal blocks.** A PLC-style block gets one
stub length per terminal, `LANE` apart, so its terminals leave in a staggered fan instead of a
stack. See "Stub fan-out" below. `route_demos.py` also builds a third sheet, a PLC block with its
terminals fanned on both faces.

What it keeps from the last revision, from the CI diagnostics: `plan()` only planned and returned
`(points, ok, reason)`, and the `install()` wrapper unpacked two values from it, so the hook
raised `ValueError` on every wire and FreeCAD kept the old shapes. There is now one function,
`apply(obj)`, that plans and writes, and the wrapper calls it and never touches the tuple. A unit
test drives the installed wrapper with a three-value plan, so this cannot come back silently.

Also in this revision: lanes are exact multiples of `LANE` (never snapped), `STUB = margin + LANE`
so a stub end lands on a lane, lanes are taken from wires already routed, the junction rule is
precise, and `preset()` switches the tuning.

## Files

| file | what it is |
| --- | --- |
| `wire_route.py` | the module: pure router + FreeCAD glue |
| `test_wire_route.py` | 17 checks, no FreeCAD needed (the hook test needs the package) |
| `route_demos.py` | CI script: builds the DOL, reversing and PLC sheets, measures stock, installs, reroutes, measures again, writes three A3 PDFs |
| `README_wire_route.md` | this file |

## Contract (pure part, no FreeCAD)

```python
route(a, b, a_dir, b_dir, obstacles, used, grid=5.0, margin=6.0,
      a_stub=None, b_stub=None) -> [(x, y), ...]
```

`a_stub` / `b_stub` are optional stub lengths in mm; `None` means the default `STUB`. They exist
for the fan-out below and are the only addition to the agreed signature.

* first point is `a`, last point is `b`; every segment is axis-aligned
* `a_dir`, `b_dir`: unit vector from the symbol bbox centre to the terminal (largest component
  wins). `wire_route.exit_dir(box, point)` computes it.
* `obstacles`: `(xmin, ymin, xmax, ymax)`: every device box plus every label box, both endpoints
  included. A path may leave or enter a box only at its own terminal.
* `used`: `((x1, y1), (x2, y2))` axis-aligned segments of wires already routed.
* `LAST` holds `{'ok', 'reason'}`; reasons `'straight'`, `'routed'`, `'no path'`, `'detour'`.
  `route_ex(...)` returns `(points, ok, reason)`; `ok=False` means the old L-shape.

## How it decides

1. **Straight stays straight** when no box is within `margin` of the two ends and no used wire
   runs along it. The first and last `margin` mm are the terminal itself and are not tested.
2. **Stubs**: `STUB` = 14 mm = `margin + LANE` out along each exit direction, so the stub end
   lands on the first lane. A stub that cannot get outside its own symbol box may stay inside it,
   and only then is that box enterable.
3. **Coordinate set**: `a`, `b`, both stub ends, lanes at `margin + k*LANE` beside every box, and
   one lane `±LANE` beside every wire already routed near this wire. No snapping.
4. **A\*** over `(x, y, heading)`. Step cost = length; bend 20; crossing 120; running along a used
   wire 250 per mm; running parallel within 5 mm of one 12 per mm.
5. **Junctions**: sharing a run is free only where the other wire actually ends on one of this
   wire's terminals and the shared part is inside that terminal's stub zone.
6. **Loop cap**: a path longer than `1.9 ×` manhattan `+ 150 mm` is refused, L-shape, `'detour'`.
7. Deterministic tie-break `(f, cost, state)`. No path → L-shape, `Validation = 'Route fallback'`.

## Presets

`wire_route.preset(name)` sets `NEAR`, `LANE`, `CROSS`, `OVERLAP` and the matching `STUB`:

| preset | NEAR | LANE | CROSS | reversing overlaps | reversing crossings |
| --- | --- | --- | --- | --- | --- |
| `balanced` (default) | 12 | 8 | 120 | 2 pairs / 4 mm | 22 |
| `fewer-crossings` | 0 | 6 | 200 | 2 pairs / 2 mm | 21 |

`route_demos.py` reads `WIRE_ROUTE_PRESET` from the environment and records what it set in
`result.json` under `preset`. **Crossings do not respond to the cost.** With `NEAR = 0` and
`CROSS = 1000` the reversing still had 22 crossings: they come from the topology, not the tuning.

## Stub fan-out

A block with many terminals on one face stacks its stubs on top of each other: every wire leaves
along the same direction for the same 14 mm, so the turns all happen in one place. `fan_lengths()`
gives each terminal its own stub length:

* terminals are grouped by exit direction, so the top face and the bottom face fan separately;
* inside a group they are ranked along the face, and the stub length is `STUB + rank * LANE`
  (14, 22, 30, ... mm), capped at `FAN_MAX` steps;
* the fan applies to devices whose `DeviceType` contains one of `FAN_TYPES`
  (`'plc'`, `'vfd'`, `'block'`), or to any device carrying a boolean `FanStubs` property, which
  wins over the type rule. `FAN = False` turns it off for everything.

`_ends()` looks the two lengths up and hands them to `route_ex(a_stub=..., b_stub=...)`. Stub ends
of neighbouring terminals on the same face end up at least `LANE` apart along the exit direction
and at least their terminal spacing across it, which is the "8 mm apart" requirement as long as the
terminals themselves are 8 mm apart.

## Label boxes

Labels are drawn, not modelled, so `text_boxes(doc)` estimates them: the tag above the symbol's
top-left corner (`TAG_W` per character, min 20 mm wide, 12 mm tall, 2 mm above the box) and a
14 × 10 mm box starting 2 mm right of each terminal dot. Label boxes at either terminal of the
wire being routed are dropped. Point `wire_route.TEXT_BOXES` at your own callable if the drawing
places labels differently.

## Hook point in `core.py`

`core.py`, `class Connection` (line 104), `def execute(self, obj)` (line 117). The stock geometry
is written at the end of that method, in the `SchematicOffset == 0` branch:
`Part.makePolygon([a, (b.x, a.y), b])` or `Part.makeLine(a, b)`, then
`Validation = 'Logical connection only'`.

`wire_route.install()` wraps `Connection.execute` with a function that calls `apply(obj)`:

* `apply()` calls `plan()`, which returns `None` when the wire keeps the stock path
  (`SchematicOffset != 0`, missing device, no device boxes, nothing plannable, any exception).
* `plan()` **only plans**: it returns `(points, ok, reason)` and writes nothing.
* `apply()` cleans the points, writes the shape, sets `Validation` to `'Logical connection only'`
  or `'Route fallback'`, and returns True. Any failure returns False and the stock method runs.
* terminals come from `core.terminal_position`; obstacles from every object with `DeviceType` and
  a non-null `Shape` plus `TEXT_BOXES`; `used` from the wire objects earlier in document order.
* `_wire_route_installed` makes `install()` idempotent (0 when already installed);
  `uninstall()` puts the stock method back.

In `result.json`, `installed: 0` on the second demo means "already installed"; `hook_active` says
whether the wrapper is live; `wires_changed_by_hook` says whether it actually changed anything.

Explicit call site instead of the wrapper, if you prefer, at the top of `Connection.execute`:

```python
        try:
            from . import wire_route
            if wire_route.apply(obj):
                return
        except Exception:
            pass
```

## Integration

1. `wire_route.py` goes into the patch folder next to `term_ends2.py` and is copied to
   `$M/DeltaEngineering/`.
2. Append to `InitGui.py` (same place as `initgui_append10.txt`), after the `term_ends2` install:

```python
try:
    from DeltaEngineering import wire_route as _wr
    _wr.install()
except Exception as _e11:
    import FreeCAD as _A11
    _A11.Console.PrintError("wire route v73 failed: " + str(_e11) + "\n")
```

`route_demos.py` is a separate CI step: it needs `C:/DeltaTest/Mod` on `sys.path` and writes
`C:/seed/route73/{dol,reversing}_A3.pdf` and `result.json`.

## The measurement

For each demo the script runs three phases and reports all three:

1. `uninstall()`, build, `recompute()`, measure → `before`, recording every wire's shape path.
2. `install()`, `touch()` every wire, `recompute()` → measure `hooked`.
   `wires_changed_by_hook` is the direct answer to "did the wrapper run".
3. `reroute(doc)` writes every wire explicitly, no recompute afterwards → measure `after`,
   recording shape paths again.

`result.json` carries `before`, `hooked`, `after`, `paths_after`, `per_wire[].path`,
`wires_changed_by_hook`, `wires_changed_by_reroute` and `plan_matches_shape` (planned points vs
the shape read back from the document). If `plan_matches_shape` is short of the wire count, the
measurement is reading something other than what the router wrote.

Measured in the harness (not FreeCAD), `balanced` preset:

| demo | wires | overlaps before | overlaps after | junction overlaps after | crossings before → after | min clearance | segments through labels | min stub gap after |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| DOL starter | 18 | 1 pair, 40 mm | 0 | 2 pairs, 28 mm | 0 → 1 | 23 → 23 mm | 3 → 0 | 8.0 mm |
| reversing starter | 23 | 19 pairs, 4030 mm | 2 pairs, 4 mm | 9 pairs, 106 mm | 0 → 22 | 0 → 5 mm | 9 → 0 | 17.5 mm |
| PLC block | 12 | 5 pairs, 800 mm | 0 | 0 | 3 → 6 | 2 → 16 mm | 6 → 0 | 17.5 mm |

`min_stub_gap_mm` is the closest two stub ends leaving the same device: the fan-out check. All
53 wires routed, no fallbacks, `plan_matches_shape` equal to the wire count on every sheet, no
segment enters a non-endpoint box.

## Known limits

* **Crossings are structural here.** 22 on the reversing, and unchanged by `NEAR = 0`,
  `CROSS = 1000` or `LANE = 6`. Both contactors feed the same overload terminals, so K1R's runs
  must cross K1F's verticals, and the two wires from one breaker pin to the two contactors cross
  each other. `crossing_detail` lists every pair.
* **The fan is type-gated.** I do not have the CI PLC sheet, so `route_demos.py` builds its own:
  two PLC blocks with six terminals each, one facing each way. If your PLC block is not matched by
  `FAN_TYPES`, set a `FanStubs` property on it or add its type to `FAN_TYPES`; nothing else needs
  changing.
* **Label boxes are estimates**, not the renderer's own geometry.
* **Wires pass close to symbols**: lanes are `margin` (6 mm) out, so 5 mm is the real minimum.
  Nothing enters a box.
* **Motor.** No symbol change: the bottom terminals send the wires down and around the circle, in
  the innermost lanes.
* **Schematic-offset wires are untouched.**
* **Speed**: about 0.5 s per wire in the harness (23 s for 41 wires), because lanes are taken from
  every nearby routed wire. FreeCAD will be slower. Drop the used-wire lanes in `_coords` first if
  that is too slow.
* `boxes(doc)` is rescanned per wire: O(n²) document scans on a large sheet.
* The FreeCAD half has only run against the stand-in modules for this revision.

## Test

```
python3 test_wire_route.py     # 17 checks; the hook test runs when the package is importable
```
