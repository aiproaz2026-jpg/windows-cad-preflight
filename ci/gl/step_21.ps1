$f = 'C:/seed/libs/libs-result.json'
if (-not (Test-Path $f)) { throw 'V19 GATE FAIL: no libs result' }
$r = Get-Content $f -Raw -Encoding utf8 | ConvertFrom-Json
if (-not $r.done -or $r.error) { throw 'V19 GATE FAIL: libs macro did not finish cleanly' }
foreach ($k in $r.libs.parts.PSObject.Properties) { if ($k.Value.bad.Count -gt 0) { throw "V19 GATE FAIL: $($k.Name) failures" } }
$exp = @{hex_bolt=19;hex_nut=13;washer=13;bearing=21;ipe=15;gear=5}
foreach ($k in $exp.Keys) { if ($r.libs.parts.$k.ok -ne $exp[$k]) { throw "V19 GATE FAIL: $k count $($r.libs.parts.$k.ok) expected $($exp[$k])" } }
if (-not $r.libs.edit_test.nut_edited_valid -or -not $r.libs.edit_test.gear_teeth_edited_valid) { throw 'V19 GATE FAIL: edit test' }
$g = Get-Content 'C:/seed/g50/gui-result.json' -Raw -Encoding utf8 | ConvertFrom-Json
if (-not $g.done -or $g.error) { throw 'V19 GATE FAIL: gui macro' }
foreach ($k in $g.layouts_default.PSObject.Properties) { if ($k.Value.crossings_path -ne 0) { throw "V19 GATE FAIL: $($k.Name) path crossings" }; if ($k.Name -ne 'Z' -and $k.Value.crossings_dim -ne 0) { throw "V19 GATE FAIL: $($k.Name) dim crossings" }; if ($k.Name -eq 'Z' -and $k.Value.crossings_dim -gt 1) { throw 'V19 GATE FAIL: Z dim crossings > 1' } }
if ($g.lib_cmd_error -or @($g.lib_cmds).Count -ne 6) { throw 'V19 GATE FAIL: library commands not registered (6 expected)' }
foreach ($k in $g.lib_cmd_make.PSObject.Properties) { if (-not $k.Value) { throw "V19 GATE FAIL: library command part $($k.Name) invalid" } }
if ($g.ar_layer_error -or -not $g.ar_translator_installed) { throw 'V19 GATE FAIL: Arabic layer not installed' }
foreach ($n in 'Z','L_rot45','L') { if (-not $g.layouts_default.$n.pdf_mm) { throw "V19 GATE FAIL: no pdf for $n" } }
if ($g.fit3d_error -or $g.fit3d_count -ne 64 -or @($g.fit3d_bad).Count -gt 0 -or @($g.fit_cmds).Count -ne 6) { throw 'V19 GATE FAIL: 3D fittings (valid solids, analytic volumes, 6 commands)' }
if (-not $g.fit3d_edit_od_changes_volume -or -not $g.fit3d_tee_bbox_ok) { throw 'V19 GATE FAIL: 3D fitting edit or tee bbox' }
if ($g.window_title -notlike '*محمود زهير*') { throw 'V19 GATE FAIL: window title not renamed' }
if ($g.eq3d_error -or $g.eq3d_count -ne 61 -or @($g.eq3d_bad).Count -gt 0 -or @($g.eq_cmds).Count -ne 7) { throw 'V19 GATE FAIL: equipment solids/commands' }
if ($g.route_bad.Count -gt 0 -or $g.route_bad) { throw 'V19 GATE FAIL: route insertion' }
if ($g.thread_error -or @($g.thread_bad).Count -gt 0 -or -not $g.threads) { throw 'V19 GATE FAIL: thread option (valid single solid, modeled, bbox, volume)' }
if ($g.sched_wall_80 -ne 5.54 -or -not $g.sched_vol_changes -or $g.sched_3half_160_ignored -ne 5.74) { throw 'V19 GATE FAIL: wall schedules' }
'V19 GATE PASS: library counts 19/13/13/21/15/5, edits valid, layouts 0 path crossings (Z 1 dim crossing accepted), 3 PDFs exported, 6 Arabic library commands registered and creating valid parts'
