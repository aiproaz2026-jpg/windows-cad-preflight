mkdir -p dist/v20g
sha256sum /c/out/CAD-Mahmoud-Zuhair-Setup-v20g.exe | tee dist/v20g/CAD-Mahmoud-Zuhair-Setup-v20g.exe.sha256 || true
cp /c/out/source-revision.txt dist/v20g/ || true
mkdir -p dist/v20g/elec; cp /c/seed/elec/* dist/v20g/elec/ || true
mkdir -p dist/v20g/checks; cp /c/seed/THIRD-PARTY-NOTICES.txt /c/seed/flaui-result.json /c/seed/ocr-gate.txt /c/seed/ocr-ara.txt /c/seed/ocr-log.txt dist/v20g/checks/ || true; [ -f /c/seed/flaui-window.png ] && base64 -w0 /c/seed/flaui-window.png > dist/v20g/checks/flaui-window.png.b64; cp /c/seed/libs/* /c/seed/libs-err.txt /c/seed/libs-out.txt /c/seed/v17-checks.txt /c/seed/g50/gui-result.json /c/seed/g50/ui-strings.json /c/seed/gui-err.txt /c/seed/gui-out.txt dist/v20g/checks/ || true
for f in /c/seed/g50/*.png /c/seed/g50/*.pdf; do [ -f "$f" ] && base64 -w0 "$f" > dist/v20g/checks/$(basename $f).b64; done
cp /c/fit12/*.png /c/fit12/*.pdf /c/fit12/gui-result12.json /c/fit12/fc-err.txt /c/fit12/diag.txt dist/v20g/ || true
for f in dist/v20g/*.png dist/v20g/station-*.pdf; do [ -f "$f" ] && base64 -w0 "$f" > "$f.b64"; done

mkdir -p out; cp /c/out/CAD-Mahmoud-Zuhair-Setup-v20g.exe out/ || true
