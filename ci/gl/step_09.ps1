$iscc = 'C:/Program Files (x86)/Inno Setup 6/ISCC.exe'
if (-not (Test-Path $iscc)) { choco install innosetup -y --no-progress | Out-Null }
if (-not (Test-Path $iscc)) { throw 'ISCC not found' }
@'
[Setup]
AppName=برنامج CAD للمهندس محمود زهير
AppVersion=20
AppPublisher=برنامج CAD للمهندس محمود زهير (نسخة غير موقّعة)
DefaultDirName={localappdata}\Programs\DeltaEngineering
DefaultGroupName=برنامج CAD للمهندس محمود زهير
PrivilegesRequired=lowest
Compression=lzma2/fast
SolidCompression=yes
OutputDir=C:\out
OutputBaseFilename=CAD-Mahmoud-Zuhair-Setup-v20g
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
DisableProgramGroupPage=yes
UninstallDisplayName=برنامج CAD للمهندس محمود زهير
[Messages]
SetupAppTitle=تثبيت
SetupWindowTitle=تثبيت - %1
WelcomeLabel1=مرحباً بك في معالج تثبيت [name]
WelcomeLabel2=سيتم تثبيت [name/ver] على جهازك. البرنامج تجريبي وغير موقّع رقمياً وغير معتمد للاستخدام الهندسي.
ButtonBack=< &السابق
ButtonNext=&التالي >
ButtonInstall=&تثبيت
ButtonCancel=إلغاء
ButtonFinish=&إنهاء
FinishedHeadingLabel=اكتمل تثبيت [name]
FinishedLabelNoIcons=تم تثبيت [name] على جهازك.
FinishedLabel=تم تثبيت [name] على جهازك. يمكنك تشغيله من الاختصار.
[Files]
Source: "C:\stage\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "C:\stage\DeltaDefaults\user.cfg"; DestDir: "{userappdata}\FreeCAD\v1-1"; Flags: onlyifdoesntexist uninsneveruninstall
[Icons]
Name: "{autoprograms}\برنامج CAD للمهندس محمود زهير"; Filename: "{app}\bin\FreeCAD.exe"; Parameters: """{app}\LaunchDelta.FCMacro"""; WorkingDir: "{app}"
Name: "{autodesktop}\برنامج CAD للمهندس محمود زهير"; Filename: "{app}\bin\FreeCAD.exe"; Parameters: """{app}\LaunchDelta.FCMacro"""; WorkingDir: "{app}"
[Run]
Filename: "{app}\bin\FreeCAD.exe"; Parameters: """{app}\LaunchDelta.FCMacro"""; Description: "تشغيل برنامج CAD للمهندس محمود زهير"; Flags: postinstall nowait skipifsilent unchecked

'@ | Set-Content C:/delta.iss -Encoding utf8BOM
& $iscc C:/delta.iss 2>&1 | Select-Object -Last 15
Get-Item C:/out/CAD-Mahmoud-Zuhair-Setup-v20g.exe | Select-Object Name,Length
(Get-FileHash C:/out/CAD-Mahmoud-Zuhair-Setup-v20g.exe -Algorithm SHA256).Hash
