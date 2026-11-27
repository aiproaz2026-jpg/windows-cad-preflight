New-Item -ItemType Directory -Force C:/fit12 | Out-Null
$exe = Get-ChildItem C:/DeltaTest -Recurse -Filter FreeCAD.exe | Where-Object { $_.Directory.Name -eq 'bin' } | Select-Object -First 1
$root = $exe.Directory.Parent.FullName
Copy-Item "$env:GITHUB_WORKSPACE/patches/v7/macro_gui_test.py" "$root\DeltaGuiTest12.FCMacro" -Force
$env:DELTA_OUT = 'C:/fit12'; $env:GALLIUM_DRIVER = 'llvmpipe'; $env:MESA_GL_VERSION_OVERRIDE = '4.5'
Start-Process $exe.FullName -ArgumentList "`"$root\DeltaGuiTest12.FCMacro`"" -RedirectStandardOutput C:/fit12/fc-out.txt -RedirectStandardError C:/fit12/fc-err.txt
$t = 0
while ($t -lt 420) { Start-Sleep 5; $t += 5; if ((Test-Path C:/fit12/gui-result12.json) -and (Select-String -Path C:/fit12/gui-result12.json -Pattern '"done": true' -Quiet)) { break } }
if (-not (Test-Path C:/fit12/gui-result12.json) -or -not (Select-String -Path C:/fit12/gui-result12.json -Pattern '"done": true' -Quiet)) {
  try { Add-Type -AssemblyName System.Windows.Forms,System.Drawing; $b=[System.Windows.Forms.SystemInformation]::VirtualScreen; $bmp=New-Object System.Drawing.Bitmap $b.Width,$b.Height; $g=[System.Drawing.Graphics]::FromImage($bmp); $g.CopyFromScreen($b.Location,[System.Drawing.Point]::Empty,$b.Size); $bmp.Save('C:/fit12/fit12-hang.png') } catch { "screenshot failed: $_" | Out-File C:/fit12/diag.txt -Append }
  Get-Process | Where-Object { $_.MainWindowTitle } | ForEach-Object { "$($_.ProcessName) | $($_.MainWindowTitle)" } | Out-File C:/fit12/diag.txt -Append
}
Start-Sleep 4; Get-Process FreeCAD -ErrorAction SilentlyContinue | Stop-Process -Force
exit 0
