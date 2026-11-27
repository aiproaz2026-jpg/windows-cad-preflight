M=C:/delta/DeltaEngineering/package/Mod/DeltaEngineering/DeltaEngineering
ls $M/drafting.py
cp patches/v58/drafting_v11.py $M/drafting.py
cp patches/v49/parts_library.py $M/parts_library.py
cp patches/v48/fittings_library.py $M/fittings_library.py
cp patches/v50/library_commands.py $M/library_commands.py
cat patches/v50/initgui_append.txt >> C:/delta/DeltaEngineering/package/Mod/DeltaEngineering/InitGui.py
tail -8 C:/delta/DeltaEngineering/package/Mod/DeltaEngineering/InitGui.py
cp patches/v51/ar_dict.py $M/ar_dict.py
cp patches/v54/ar_layer.py patches/v54/ar_dict2.py patches/v54/ar_dict3.py $M/
cp patches/v59/ar_layer.py patches/v59/ar_dict4.py $M/
cat patches/v51/initgui_append2.txt >> C:/delta/DeltaEngineering/package/Mod/DeltaEngineering/InitGui.py
sed -i "s/ | Mechanical'/'/; s/ | Piping'/'/; s/ | Electrical'/'/" $M/core.py
cp patches/v52/fittings3d.py patches/v52/fit_commands.py patches/v52/brand.py $M/
cat patches/v52/initgui_append3.txt >> C:/delta/DeltaEngineering/package/Mod/DeltaEngineering/InitGui.py
python patches/v52/rename.py $M
cp patches/v53/fittings3d.py patches/v53/equipment3d.py patches/v53/eq_commands.py $M/
cp patches/v57/threads3d.py patches/v57/thr_commands.py $M/
cat patches/v53/initgui_append4.txt >> C:/delta/DeltaEngineering/package/Mod/DeltaEngineering/InitGui.py
cat patches/v57/initgui_append5.txt >> C:/delta/DeltaEngineering/package/Mod/DeltaEngineering/InitGui.py
grep -n "root.Label\|piping.Label\|electrical.Label" $M/core.py
python -m py_compile $M/drafting.py $M/parts_library.py $M/fittings_library.py $M/library_commands.py $M/ar_dict.py $M/ar_dict2.py $M/ar_dict3.py $M/ar_dict4.py $M/ar_layer.py $M/core.py $M/fittings3d.py $M/fit_commands.py $M/brand.py $M/equipment3d.py $M/eq_commands.py $M/threads3d.py $M/thr_commands.py $M/gui.py $M/export.py && echo v17 patches compile ok
sha256sum $M/drafting.py $M/parts_library.py $M/fittings_library.py | tee -a /c/out/source-revision.txt
