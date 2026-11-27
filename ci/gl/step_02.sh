mkdir -p /c/delta /c/out
unzip -q src/*DeltaEngineering-development-source-v58-10539385.zip -d /c/delta
python patches/v12/apply_v12.py C:/delta/DeltaEngineering
git rev-parse HEAD | tee /c/out/source-revision.txt
sha256sum src/*DeltaEngineering-development-source-v58-10539385.zip patches/v7/*.py patches/v6/*.py patches/v4/*.py patches/v3/*.py | tee -a /c/out/source-revision.txt
