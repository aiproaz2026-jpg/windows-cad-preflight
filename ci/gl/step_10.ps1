$rel = Invoke-RestMethod https://api.github.com/repos/pal1000/mesa-dist-win/releases/latest
$a = $rel.assets | Where-Object { $_.name -match 'release-msvc\.7z$' } | Select-Object -First 1
Invoke-WebRequest $a.browser_download_url -OutFile C:/mesa.7z
7z x C:/mesa.7z -oC:/mesa -y | Out-Null
