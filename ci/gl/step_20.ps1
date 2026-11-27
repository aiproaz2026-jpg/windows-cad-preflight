$f = 'C:/fit12/gui-result12.json'
if (-not (Test-Path $f)) { throw 'GATE FAIL: no result file written' }
$r = Get-Content $f -Raw -Encoding utf8 | ConvertFrom-Json
if (-not $r.done) { throw 'GATE FAIL: macro did not finish' }
if ($r.error) { throw 'GATE FAIL: macro error recorded' }
$bad = @($r.steps.PSObject.Properties | Where-Object { $_.Value.PSObject.Properties.Name -contains 'ok' -and -not $_.Value.ok } | ForEach-Object { $_.Name })
if ($bad.Count -gt 0) { throw ('GATE FAIL: failed steps: ' + ($bad -join ', ')) }
$t = $r.steps.tasks_dock_hidden_again_after_task_closes.detail
if (-not ($t.dialog_active_when_open -eq $true -and $t.dialog_active_after_close -eq $false)) { throw 'GATE FAIL: fake task dialog did not open and close' }
"GATE PASS"
