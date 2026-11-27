$PSVersionTable.PSVersion.ToString()
Get-Command pwsh,bash,git,dotnet,python,choco,winget,7z -ErrorAction SilentlyContinue | Format-Table Name,Source -AutoSize
Get-CimInstance Win32_OperatingSystem | Select-Object Caption,Version | Format-List
Get-CimInstance Win32_Processor | Select-Object Name,NumberOfCores | Format-List
Get-PSDrive C | Select-Object Used,Free | Format-List
Get-ChildItem 'C:\Program Files' -Name | Select-Object -First 60
Get-ChildItem 'C:\Program Files (x86)' -Name | Select-Object -First 60
