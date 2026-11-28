# wire_route — orthogonal wire router for schematic connections

Status: **untested inside FreeCAD.** This revision has only run in a stand-in harness (fake
`FreeCAD`/`Part` modules) on a Linux box. GPL-3.0-or-later, same as the project.

What this revision adds:

* **A nudge pass after routing (`spread_paths`).** Search-based respacing failed three times, so
  this revision stops asking the search for a wider lane and widens the lane it already has. Each
  run is one segment of an orthogonal polyline; moving it sideways only lengthens or shortens its
  two neighbours, so the bend count, the topology and every crossing stay exactly as they were.
  `reroute()` collects the routed paths and, after the last wire, groups parallel segments within
  `LANE` of each other that overlap along their length (`SPREAD_SHARE` 25 mm) into channels,
  chained so a wide bundle is one channel, and respaces each channel to `LANE` pitch about its own
  middle, widest move first. The pitch falls back to 6 mm and then to `SPACE_MIN` when the sheet
  has no room for a full lane, and a channel that cannot move at any pitch is not retried.
* **Every nudge is checked before it is taken.** A move is refused when it changes the wire's
  ends, collapses a neighbour to nothing (`fold`), is not orthogonal, adds a crossing, overlaps
  another wire, enters or hugs a foreign box, or makes the wire cross itself. Refusals are counted
  per wire and reported by reason (`spread_refused`, and the pass prints `spread: moves=.. mm=..
  refused=.. ms=.. why=overlap=25`). Only accepted moves are written back, so a wire that is not
  moved is not touched.
* **Each wire says what it is hemmed against.** When the clean search returns `none`, the tier
  string is annotated with the nearest thing in the way: `8=none@8001 by wire W12:2.0` or
  `4=none@8001 by K1:2.0`. It reports the nearer of the nearest foreign box and the nearest
  already-routed wire, because on a crowded sheet the thing in the way is as often a wire as a
  symbol - naming only boxes once put `K1:397.0` on a wire that was 2 mm from its neighbour. The
  gap is the room that side had, so a small number reads as a real block and a large one reads as
  "nothing here is stopping it". A `0.0` means the two wires touch: on the harness every `none`
  tier is blocked by a wire at 0.0 mm - a shared terminal approach or a run already on top of the
  other - and never by a symbol.
* **The clean search may not leave the neighbourhood of the tight path.** `CLEAN_PAD` (40 mm):
  the clean A* is refused any edge outside the tight path's bounding box grown by that pad, which
  is enforced in `blocked()`. A wide lane is a local move - shift the run by a lane - and a search
  over the whole sheet spent its budget going nowhere. On the five harness sheets this took the
  clean pass from about 200 000 pops to 85 000 and the whole run from 9.3 s back to 5.0 s.
* **The budget is shared out before it is spent.** `reroute()` gives each wire its share of what
  is left over the wires still to come, floored at `CLEAN_MIN` (4 000 pops), and `CLEAN_TOTAL` is
  400 000 pops per document. On the last CI run the document cap was gone before W11, W12, W15,
  W17, W18, W19, W20 and W22, which all reported `no-budget`; with the share-out no wire can be
  starved by the ones before it, and the total is still capped.
* **A clean lane may not be bought by hugging a symbol.** The candidate is refused if it runs
  within `EDGE_PAD` of a box for longer than the tight path did (`<tier>=hugs`), on top of the
  existing no-extra-crossings and `WRAP_MAX` guards. One CI sheet came back at 0.0 mm clearance
  from a box, which reads as a wire touching the symbol.
* Every wire reports `clean_allow` as well as `clean_pops`, so a run shows how much budget the
  wire was given and how much it used.

Kept from v16: the narrow-run trigger (`NARROW_MIN` 60 mm) instead of the 4 mm crowding trigger,
the shared-terminal approach exempt from crowding (`la`/`lb`, the terminal's fan stub), `LAST`
cleared per wire, and the per-tier report `clean_tiers` (`8=taken`, `8=none@8001`, `8=no-gain`,
`8=too-long`, `8=crossings`, `8=hugs`, `8=no-budget`).

Kept from v15: the two-tier clean pass (8 mm, then 4 mm), `WRAP_MAX` 1.35, `_corridor()` /
`_face_pitch()` for a genuinely narrow gap, `_corner_exit()` off by default, and the fifth demo
sheet `crowd`.

The rule kept from v12, unchanged: a shared run into one terminal is a node however long it is
(geometric, no tolerance), and a wire may join its own terminal stub anywhere along it. Overlap is
refused, not priced: the strict pass will not draw along a wire already routed, the loose pass is
only a backstop, and every wire reports which pass it took.

## Harness numbers for this revision

Five sheets, balanced preset, one run each. `overlaps` counts wire pairs lying on each other, `j`
junction pairs, `cr` crossings, `<2` wire pairs closer than 2 mm, `ms` mean milliseconds per wire.
Wall-clock milliseconds move with the load on the harness box, so compare them within a run.

| sheet | overlaps | j | crossings | <2 mm | <4 mm | mean ms | nudged wires | nudged mm |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| DOL, 18 wires | 0 | 2 | 1 | 0 | 0 | 56 | 2 | 2.0 |
| reversing, 23 wires | 0 | 8 | 12 | 0 | 1 | 49 | 0 (25 refusals, all `overlap`) | 0.0 |
| PLC, 12 wires | 0 | 0 | 7 | 0 | 0 | 144 | 4 | 8.0 |
| dense face, 6 wires | 0 | 0 | 2 | 0 | 0 | 10 | 0 | 0.0 |
| crowded gap, 6 wires | 0 | 0 | 2 | 0 | 0 | 138 | 10 | 13.2 |

Crossings 24 across the five sheets (v12 26, v16 24, v17 24), overlaps 0, every wire on the
strict pass. The nudge pass moves 16 wires across three sheets, by 1 to 2 mm each, and costs 1 to
3 ms per sheet. Reversing moves nothing: every channel there is a 2 mm run with a wire on both
sides, so every move is refused as an `overlap`. The five-sheet run is 5.0 s, the same as v17
within the noise of the harness box.

What this pass does **not** do: it does not fix the control panel. It cannot move a wire into
space that is not there, and on this harness the sheets have almost no 2 mm band to spread - the
routed geometry already sits at 4 mm or wider on most wires, which is why `pairs_under_4mm` is 0
or 1. `bundle.py` (eight wires through a 24 mm doorway) does not show a spread either: eight wires
cannot pass a 24 mm doorway at 8 mm pitch, so most of its pairs are at 0.0 mm and every nudge is
refused. The proof of work for the pass is the unit test - a synthetic 2 mm band in open space is
nudged to 4 mm or wider, and a band facing a symbol box, a crossing or an overlap is left alone -
not the demo sheets.

## Files

| file | what it is |
| --- | --- |
| `wire_route.py` | the module: pure router + FreeCAD glue |
| `test_wire_route.py` | 92 checks, no FreeCAD needed (the hook test needs the package) |
| `route_demos.py` | CI script: builds the DOL, reversing, PLC, dense-face and crowded-gap sheets, measures stock, installs, reroutes, measures again, writes five A3 PDFs |
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
* `used`: `((x1, y1), (x2, y2))` axis-aligned segments of wires already routed. An item may also
  be `(segment, flag)` with `flag == 'stub'`, which marks the short run out of a fanned terminal.
* `LAST` holds `{'ok', 'reason'}`; reasons `'straight'`, `'routed'`, `'no path'`, `'detour'`.
  `route_ex(...)` returns `(points, ok, reason)`; `ok=False` means the old L-shape.

## How it decides

1. **Straight stays straight** when no box is within `margin` of the two ends, no used wire runs
   along it, it does not cut across a fan stub, and it does not run parallel within `LANE` of a
   routed wire for more than `SHADOW_MIN`: a straight line that shadows a routed wire is what put
   two runs on one trunk, but a brief pass-by is not a trunk. The first and last `margin` mm are
   the terminal itself and are not tested.
2. **Stubs**: `STUB` = 14 mm = `margin + LANE` out along each exit direction, so the stub end
   lands on the first lane. A stub that cannot get outside its own symbol box may stay inside it,
   and only then is that box enterable.
3. **Coordinate set**: `a`, `b`, both stub ends, lanes at `margin + k*LANE` for `k = 0..3` beside
   every box, lanes at `±LANE` and `±2 * LANE` beside every wire already routed near this wire,
   and the two ends of every fan stub near this wire (plus `±LANE`), which is what a wire goes
   round instead of cutting across. No snapping. Candidates are clipped to the span of the two
   terminals plus 300 mm.
4. **A\*** over `(x, y, heading)`. Step cost = length; bend 20; crossing 120; running along a used
   wire 250 per mm; running parallel within 5 mm of one 12 per mm.
5. **Junctions**: sharing a run is free where the other wire ends on the same terminal this wire
   ends on and the shared run holds that terminal - the two wires are then one approach into it -
   or where the shared part sits wholly inside that terminal's stub zone. A run that starts at a
   terminal and leaves it is an overlap.
6. **Loop cap**: a path longer than `1.9 ×` manhattan `+ 150 mm` is refused, L-shape, `'detour'`.
7. Deterministic tie-break `(f, cost, state)`. No path → L-shape, `Validation = 'Route fallback'`.

## Presets

`wire_route.preset(name)` sets `NEAR`, `LANE`, `CROSS`, `OVERLAP` and the matching `STUB`:

| preset | NEAR | LANE | CROSS | reversing overlaps | reversing crossings |
| --- | --- | --- | --- | --- | --- |
| `balanced` (default) | 12 | 8 | 120 | 2 pairs / 2.5 mm | 23 |
| `fewer-crossings` | 0 | 6 | 200 | 2 pairs / 2 mm | 21 |

`route_demos.py` reads `WIRE_ROUTE_PRESET` from the environment and records what it set in
`result.json` under `preset`. **Crossings do not respond to the cost.** With `NEAR = 0` and
`CROSS = 1000` the reversing still had 22 crossings: they come from the topology, not the tuning.

## Stub fan-out

A block with many terminals on one face stacks its stubs on top of each other: every wire leaves
along the same direction for the same 14 mm, so the turns all happen in one place. `fan_lengths()`
gives each terminal its own stub length:

* terminals are grouped by exit direction, so the top face and the bottom face fan separately;
* inside a group they are ranked **by terminal order** (their index in `device.Terminals`), and
  the stub length is `STUB + rank * step`, capped at `FAN_MAX` (12) steps;
* `step` is `LANE` on a face whose terminals are more than `FAN_DENSE_PITCH` (16 mm) apart, and
  `max(FAN_STEP_MIN, min(FAN_STEP_MAX, pitch))` on a dense one, so 14 mm terminals step 14 mm and
  8.6 mm terminals step 12 mm, while 18 mm terminals keep the 8 mm step;
* where the document knows each terminal's wire, the face is ordered by the far end of that wire:
  the lowest far end gets the longest stub (see "A fan is ordered" below);
* the fan applies to any face with `FAN_MIN_TERMS` (6) or more terminals, to devices whose
  `DeviceType` contains one of `FAN_TYPES` (`'plc'`, `'vfd'`, `'block'`), or to any device
  carrying a boolean `FanStubs` property, which wins over both. `FAN = False` turns it off.

The count is **per side**, as asked ("6 or more terminals on one side"). Counting the whole
device instead fans every 8-terminal contactor and overload relay, and on the reversing demo that
costs more than it saves: overlaps went from 2 pairs / 2.5 mm to 2 pairs / 60 mm and crossings
from 23 to 27, because the longer stubs eat the space between the two contactors. Terminals
spread around a symbol's own leads already leave in different directions, so the type rule is
what covers a block there. If a block on the CI sheet still stacks its stubs and its type is not
in `FAN_TYPES`, set `FAN_COUNT_WHOLE_DEVICE = True` and the count rule applies to the whole
device instead of one side; that is the switch to flip first, and the reversing cost above is
what it buys.

`_ends()` looks the two lengths up and hands them to `route_ex(a_stub=..., b_stub=...)`. Stub ends
of neighbouring terminals on the same face end up one `step` apart along the exit direction and at
least their terminal spacing across it. Each fanned stub is then marked in the used list, so the
next wire pays `STUB_CROSS` to cut across it.

**A fan is ordered by arrival.** Ordering by terminal index alone put the wire that arrives from
below on a short stub, so it turned in close to the block and cut across the longer stubs of the
terminals below it. `_ctx` now builds an arrival map (terminal -> far end of its wire) and
`fan_lengths()` sorts the face by it, lowest far end last, which gives the arriving-from-below
wire the longest stub and the outermost lane. Ordering the other way round was measured: the
reversing demo went from 2 overlap pairs / 2.5 mm to 6 pairs / 20.5 mm.

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

Measured in the harness (not FreeCAD), `balanced` preset, this run (per-wire times move by about a third between runs on the same
machine, so read them as a scale, not a measurement):

| demo | wires | overlaps before | overlaps after | junction overlaps after | crossings before → after | min clearance | segments through labels | min stub gap after | ms per wire |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| DOL starter | 18 | 1 pair, 40 mm | 0 | 2 pairs, 19 mm | 0 → 1 | none under 2 mm | 3 → 0 | 17.5 mm | 31 |
| reversing starter | 23 | 19 pairs, 4030 mm (14 non-junction) | 0 | 8 pairs, 77 mm | 0 → 26 | none under 2 mm | 9 → 0 | 17.5 mm | 53 |
| PLC block | 12 | 5 pairs, 800 mm | 0 | 0 | 3 → 7 | none under 2 mm | 6 → 0 | 17.5 mm | 90 |
| dense face | 6 | 4 pairs, 213 mm | 0 | 0 | 0 → 2 | 28 → 3 mm | 0 → 0 | 12.0 mm | 9 |

`min_stub_gap_mm` is the closest two stub ends leaving the same device, skipping pairs that end
on the same terminal (a junction, not a stacked stub). All 59 wires routed, no fallbacks,
`plan_matches_shape` equal to the wire count on every sheet, no segment enters a non-endpoint
box. The reversing sheet now routes every wire on the strict pass, so it has no residual
overlaps at all; the two 1.0 and 1.5 mm slivers it used to carry were loose-pass wires converging
on the same overload terminals, and they are gone with the stub-join change.

Crossings went up as overlaps went down: separating parallel runs costs crossings. That is the
trade this revision makes, and it is why the DOL went from 0 to 1 crossing and the reversing from
0 to 26. The reversing moved 25 to 26 with the stub-join change: more direct approaches into a
terminal cross one more run on the way in.

## Known limits

* **Most crossings are structural here.** 23 on the reversing, and the earlier 22 did not respond
  to `NEAR = 0`, `CROSS = 1000` or `LANE = 6`. Both contactors feed the same overload terminals,
  so K1R's runs must cross K1F's verticals, and the two wires from one breaker pin to the two
  contactors cross each other. `crossing_detail` lists every pair.
* **The fan is gated by type and by terminal count.** I do not have the CI PLC sheet, so
  `route_demos.py` builds its own: two PLC blocks with six terminals each. If your block is not
  matched by `FAN_TYPES` and has fewer than six terminals on the crowded side, set a `FanStubs`
  property on it; nothing else needs changing.
* **A terminal with several wires on it cannot be fanned apart.** All of them share that
  terminal's stub end by definition; the separation has to come from the router's lanes after the
  stub. On the DOL the coil terminal A1 carries two wires and their last approach sits 6 mm apart,
  which is a junction, not a defect.
* **The nudge pass only moves interior runs.** A terminal stub (the first and last segment of a
  wire) is never moved, because its far end is the pin. A run with a wire on both sides is refused
  as an `overlap`, so a band that is hemmed in cannot be widened from the middle - only its outer
  wires can move, and the inner ones follow in later rounds if room opens up. It also cannot move
  a run into a symbol box or past another wire, which is why reversing reports 25 refusals.
* **Label boxes are estimates**, not the renderer's own geometry.
* **Wires pass close to symbols**: lanes are `margin` (6 mm) out, so 5 mm is the real minimum.
  Nothing enters a box.
* **Motor.** No symbol change: the bottom terminals send the wires down and around the circle, in
  the innermost lanes.
* **Schematic-offset wires are untouched.**
* **Speed**: 0.02 to 0.2 s per wire in the harness, 8 s for all four sheets (was 48 s for three).
  Three things did it: routed wires and boxes live in grid indexes (`_SegIndex`, `_RectIndex`) so
  the A* looks at the wires near an edge instead of all of them; the document is scanned once per
  pass for boxes, label boxes and fan lengths (`_ctx`) instead of once per wire; and the coordinate
  set is clipped. The slowest single wire is on the reversing sheet, 3.0 s to 4.2 s depending on the run. FreeCAD's shape reads
  will add to this, but they are not in the A* loop. If a sheet is still too slow, set
  `FAN_COUNT_WHOLE_DEVICE` aside and drop the `±2 * LANE` used-wire lanes first.
* **A shared stub is only free at a terminal of this wire.** Riding some other wire's stub that
  does not end on one of this wire's own terminals counts as an overlap. The length bound lives in
  `_stub_share_ok()` and follows the terminal's real stub length: a fanned 30 mm stub gets a
  60 mm zone, a plain 14 mm stub keeps 28 mm.
* **The strict overlap pass can run out of paths.** On the reversing demo the three wires into
  the motor terminals have no overlap-free route at all: their stub ends already sit on a wire
  drawn earlier, so the strict pass fails and the loose one runs. Those wires report
  `strict: false` in `result.json`, and they are where the two residual 1.0 and 1.5 mm overlaps
  are. Raising `OVERLAP` does not help - there is no path to find, not a price to raise.
* **Clearance costs crossings.** Keeping 1.4 mm from every symbol moved the reversing demo from
  23 crossings to 25 and left two wire-wire pairs at 1.0 mm. Setting `CLEAR_COST = 0` gives the
  crossings back and reports the pairs instead; `CLEAR_AT` sets where the cost starts.
* **The per-document cache assumes symbols do not move mid-pass.** It rebuilds when the object list
  or a device position changes; call `wire_route.clear_cache()` after moving symbols by other means.
* `boxes(doc)` is rescanned per wire: O(n²) document scans on a large sheet.
* The FreeCAD half has only run against the stand-in modules for this revision.

## Test

```
python3 test_wire_route.py     # 92 checks; the hook test runs when the package is importable
```
