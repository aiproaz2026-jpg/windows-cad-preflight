$base = 'https://github.com/FreeCAD/FreeCAD/releases/download/1.1.4'
$name = 'FreeCAD_1.1.4-Windows-x86_64-py311-installer.exe'
Invoke-WebRequest "$base/$name" -OutFile C:/fc.exe -UseBasicParsing
$want = (([string](Invoke-RestMethod "$base/$name-SHA256.txt")) -split '\s+')[0]
$got = (Get-FileHash C:/fc.exe -Algorithm SHA256).Hash
if ($got -ine $want) { throw "SHA256 mismatch" }
"FreeCAD installer SHA256 verified: $got"
$p = Start-Process C:/fc.exe -ArgumentList '/S','/D=C:\stagebase' -Wait -PassThru
"official installer exit $($p.ExitCode)"
$exe = Get-ChildItem C:/stagebase -Recurse -Filter FreeCAD.exe | Where-Object { $_.Directory.Name -eq 'bin' } | Select-Object -First 1
$root = $exe.Directory.Parent.FullName
New-Item -ItemType Directory C:/stage -Force | Out-Null
Copy-Item "$root/*" C:/stage -Recurse -Force
Get-ChildItem C:/stage -Filter 'Uninstall*' -ErrorAction SilentlyContinue | Remove-Item -Force
New-Item -ItemType Directory C:/stage/Mod -Force | Out-Null
Copy-Item C:/delta/DeltaEngineering/package/Mod/DeltaEngineering C:/stage/Mod/DeltaEngineering -Recurse -Force
Copy-Item C:/delta/DeltaEngineering/LaunchDelta.FCMacro C:/stage/LaunchDelta.FCMacro -Force
Copy-Item C:/out/source-revision.txt C:/stage/DELTA-SOURCE-REVISION.txt -Force
@'
Delta Engineering v16 offline installer (unsigned, experimental, NOT certified for engineering use).
Contains: FreeCAD 1.1.4 (LGPL-2.1-or-later, https://github.com/FreeCAD/FreeCAD/releases/tag/1.1.4 , source at the same tag),
and the Delta Engineering Python addon (GPL-3.0-or-later).
Generic fittings and electrical symbols are illustrative geometry. Drawings are geometric drafts.
Full license inventory is NOT complete yet.

'@ | Set-Content C:/stage/DELTA-NOTICE.txt -Encoding utf8
@'
# Delta Engineering launcher: activates the Delta workbench and closes FreeCAD's stock Start tab. It never hides or moves any panel.
import FreeCAD as App
import FreeCADGui as Gui
import DeltaEngineering.core
import DeltaEngineering.domain
from DeltaEngineering.gui import register
if 'DeltaWorkbench' not in Gui.listWorkbenches(): register()
Gui.activateWorkbench('DeltaWorkbench')
try:
    try:
        from PySide6 import QtWidgets, QtCore
    except Exception:
        from PySide import QtWidgets, QtCore
    def _close_start():
        for sw in Gui.getMainWindow().findChildren(QtWidgets.QMdiSubWindow):
            w = sw.widget()
            cn = w.metaObject().className() if w is not None else ''
            if 'StartView' in cn or (sw.windowTitle().strip() == 'Start' and not App.listDocuments()):
                sw.close()
    for ms in (1500, 4000, 8000):
        QtCore.QTimer.singleShot(ms, _close_start)
except Exception as e:
    App.Console.PrintWarning('Delta launcher: ' + str(e) + '\n')
'@ | Set-Content C:/stage/LaunchDelta.FCMacro -Encoding utf8
New-Item -ItemType Directory C:/stage/DeltaDefaults -Force | Out-Null
@'
<?xml version="1.0" encoding="UTF-8" standalone="no" ?>
<FCParameters>
  <FCParamGroup Name="Root">
    <FCParamGroup Name="BaseApp">
      <FCParamGroup Name="Preferences">
        <FCParamGroup Name="General">
          <FCText Name="Language">Arabic</FCText>
        </FCParamGroup>
      </FCParamGroup>
    </FCParamGroup>
  </FCParamGroup>
</FCParameters>
'@ | Set-Content C:/stage/DeltaDefaults/user.cfg -Encoding utf8
$sz = (Get-ChildItem C:/stage -Recurse -File | Measure-Object Length -Sum).Sum
"staged size MB $([math]::Round($sz/1MB))"
