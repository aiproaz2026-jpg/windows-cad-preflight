$root = 'C:/stage'
$pat = '^(license|licence|copying|notice|notices|copyright|authors|unlicense|patents)([._-].*)?$|^(license|licence|copying)'
$files = Get-ChildItem $root -Recurse -File | Where-Object { $_.Name -match $pat -and $_.Length -lt 2MB }
$out = New-Object System.Collections.Generic.List[string]
$out.Add('THIRD-PARTY NOTICES INDEX / فهرس إشعارات المكوّنات الخارجية')
$out.Add('This program bundles FreeCAD (LGPL-2.1-or-later), OpenCASCADE (LGPL-2.1 with exception), Python, Qt (LGPL-3.0), and other open-source components.')
$out.Add('This file is an automatically generated index of the licence and notice files found inside the installed payload. It is NOT a legal opinion and NOT a complete licence review.')
$out.Add('Each listed file is shipped unchanged in the installation folder at the path shown. Count: ' + $files.Count)
$out.Add('')
foreach ($f in ($files | Sort-Object FullName)) {
  $bs = [string][char]92; $rel = $f.FullName.Substring($root.Length).Replace($bs,'/').TrimStart('/')
  $h = (Get-FileHash $f.FullName -Algorithm SHA256).Hash.Substring(0,16)
  $first = ''
  try { $first = ((Get-Content $f.FullName -TotalCount 3 -ErrorAction Stop) -join ' ').Trim(); if ($first.Length -gt 100) { $first = $first.Substring(0,100) } } catch {}
  $out.Add($rel + ' | ' + $f.Length + ' bytes | sha256:' + $h + ' | ' + $first)
}
$out | Set-Content C:/stage/THIRD-PARTY-NOTICES.txt -Encoding utf8
New-Item -ItemType Directory -Force C:/seed | Out-Null
Copy-Item C:/stage/THIRD-PARTY-NOTICES.txt C:/seed/THIRD-PARTY-NOTICES.txt
"notice files indexed: $($files.Count)"
$total = (Get-ChildItem $root -Recurse -File | Measure-Object).Count
"payload files: $total"
