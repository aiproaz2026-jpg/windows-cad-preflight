$exe = Get-ChildItem C:/DeltaTest -Recurse -Filter FreeCAD.exe | Where-Object { $_.Directory.Name -eq 'bin' } | Select-Object -First 1
$bin = $exe.Directory.FullName
Copy-Item C:/mesa/x64/opengl32.dll $bin -Force
foreach ($n in 'libgallium_wgl.dll','libglapi.dll') { if (Test-Path "C:/mesa/x64/$n") { Copy-Item "C:/mesa/x64/$n" $bin -Force } }
