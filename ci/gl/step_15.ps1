New-Item -ItemType Directory -Force C:/seed/libs,C:/seed/g50 | Out-Null
$app = 'C:\DeltaTest'; $bin = "$app\bin"
$mt = Get-Content "$env:GITHUB_WORKSPACE/patches/v48/libs48.py" -Raw -Encoding utf8
[IO.File]::WriteAllText('C:/seed/libs48.py', $mt.Replace('@@OUT@@', 'C:/seed/libs'), (New-Object Text.UTF8Encoding $false))
$env:PYTHONUTF8 = '1'
$pr = Start-Process "$bin\FreeCADCmd.exe" -ArgumentList "C:\seed\libs48.py" -WorkingDirectory $app -PassThru -RedirectStandardError "C:/seed/libs-err.txt" -RedirectStandardOutput "C:/seed/libs-out.txt"
$pr.WaitForExit(240000) | Out-Null
"libs exited=$($pr.HasExited)" | Tee-Object C:/seed/v17-checks.txt
$mt = Get-Content "$env:GITHUB_WORKSPACE/patches/v57/g58.py" -Raw -Encoding utf8
[IO.File]::WriteAllText('C:/seed/gui50.FCMacro', $mt.Replace('@@OUT@@', 'C:/seed/g50'), (New-Object Text.UTF8Encoding $false))
$env:GALLIUM_DRIVER = 'llvmpipe'; $env:MESA_GL_VERSION_OVERRIDE = '4.5'
$gp = Start-Process "$bin\FreeCAD.exe" -ArgumentList "C:\seed\gui50.FCMacro" -WorkingDirectory $app -PassThru -RedirectStandardError "C:/seed/gui-err.txt" -RedirectStandardOutput "C:/seed/gui-out.txt"
$t = 0; while ($t -lt 300) { Start-Sleep 3; $t += 3; if ((Test-Path C:/seed/g50/gui-result.json) -and (Select-String -Path C:/seed/g50/gui-result.json -Pattern '"done": true' -Quiet)) { break }; if ($gp.HasExited) { break } }
"gui exited=$($gp.HasExited) waited=$t" | Tee-Object -Append C:/seed/v17-checks.txt
Start-Sleep 3; Stop-Process -Id $gp.Id -Force -ErrorAction SilentlyContinue
