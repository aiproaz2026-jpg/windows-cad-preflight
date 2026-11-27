New-Item -ItemType Directory -Force C:/ocr | Out-Null
choco install tesseract -y --no-progress 2>&1 | Select-Object -Last 3
$tess = 'C:/Program Files/Tesseract-OCR/tesseract.exe'
if (-not (Test-Path $tess)) { 'tesseract missing' | Out-File C:/ocr/ocr-gate.txt; exit 0 }
$td = 'C:/Program Files/Tesseract-OCR/tessdata'
Invoke-WebRequest -Uri 'https://github.com/tesseract-ocr/tessdata_fast/raw/main/ara.traineddata' -OutFile C:/ocr/ara.traineddata
Invoke-WebRequest -Uri 'https://github.com/tesseract-ocr/tessdata_fast/raw/main/eng.traineddata' -OutFile C:/ocr/eng.traineddata
$img = 'C:/seed/g50/delta_ar_ui.png'
if (-not (Test-Path $img)) { 'image missing' | Out-File C:/ocr/ocr-gate.txt; exit 0 }
& $tess $img C:/ocr/ocr-ara -l ara --tessdata-dir C:/ocr 2>&1 | Out-File C:/ocr/ocr-log.txt
$txt = Get-Content C:/ocr/ocr-ara.txt -Raw -Encoding utf8
$nar = ([regex]::Matches($txt, '[\u0600-\u06FF]')).Count
$hit = $txt.Contains([string]::new([char[]]@(0x0628,0x0631,0x0646,0x0627,0x0645,0x062C)))
"arabic_chars=$nar contains_barnamaj=$hit" | Out-File C:/ocr/ocr-gate.txt
Get-Content C:/ocr/ocr-gate.txt
Copy-Item C:/ocr/ocr-gate.txt,C:/ocr/ocr-ara.txt,C:/ocr/ocr-log.txt C:/seed/ -ErrorAction SilentlyContinue
