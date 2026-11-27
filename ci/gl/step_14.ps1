New-Item -ItemType Directory -Force C:/seed/elec | Out-Null
$cmd = Get-ChildItem C:/DeltaTest -Recurse -Filter FreeCADCmd.exe | Select-Object -First 1
$env:PYTHONUTF8 = '1'
Copy-Item patches/v12/elec_test.py C:/elec_test.py -Force
$o = & $cmd.FullName -c "exec(open('C:/elec_test.py',encoding='utf-8').read())" 2>&1 | Out-String
$o | Set-Content C:/seed/elec/out.txt -Encoding utf8
$o
