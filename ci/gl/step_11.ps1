$sw = [Diagnostics.Stopwatch]::StartNew()
$p = Start-Process C:/out/CAD-Mahmoud-Zuhair-Setup-v20g.exe -ArgumentList '/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/DIR=C:\DeltaTest' -Wait -PassThru
"setup exit $($p.ExitCode) seconds $($sw.Elapsed.TotalSeconds)"
if ($p.ExitCode -ne 0) { throw 'setup failed' }
$sz = (Get-ChildItem C:/DeltaTest -Recurse -File | Measure-Object Length -Sum).Sum
"installed size MB $([math]::Round($sz/1MB))"
"addon present: $(Test-Path C:/DeltaTest/Mod/DeltaEngineering/InitGui.py)"
"fittings module present: $(Test-Path C:/DeltaTest/Mod/DeltaEngineering/DeltaEngineering/fittings.py)"
"shortcut: $(Test-Path "$env:APPDATA/Microsoft/Windows/Start Menu/Programs/برنامج CAD للمهندس محمود زهير.lnk")"
Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*','HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*','HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*' -ErrorAction SilentlyContinue | Where-Object { $_.DisplayName -match 'Delta' } | ForEach-Object { "REGISTRY: $($_.DisplayName) | DisplayVersion=$($_.DisplayVersion) | $($_.InstallLocation)" }
$cmd = Get-ChildItem C:/DeltaTest -Recurse -Filter FreeCADCmd.exe | Select-Object -First 1
$env:PYTHONUTF8 = '1'
$mods = 'core','domain','symbols','export','fittings','documents','scaled_output','tube_library','drafting','electrical','connectivity'
$lines = @('import sys, FreeCAD, importlib','sys.path.insert(0, ''C:/DeltaTest/Mod'')','sys.path.insert(0, ''C:/DeltaTest/Mod/DeltaEngineering'')'); foreach ($m in $mods) { $lines += "try:`n    importlib.import_module('DeltaEngineering.$m'); print('OK $m')`nexcept Exception as e:`n    print('FAIL $m', repr(e))" }
$lines | Set-Content C:/imp.py -Encoding utf8
$o = & $cmd.FullName -c "exec(open('C:/imp.py',encoding='utf-8').read())" 2>&1 | Out-String; $o
$okc = @([regex]::Matches($o, '(?m)^OK (\w+)') | ForEach-Object { $_.Groups[1].Value } | Sort-Object -Unique).Count
"distinct OK imports: $okc"
if ($okc -ne 11) { throw "import check: expected 11 OK, got $okc" }
if ($o -match 'FAIL ') { throw 'import check failed' }
