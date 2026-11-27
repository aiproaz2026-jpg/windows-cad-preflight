New-Item -ItemType Directory -Force C:/flaui | Out-Null
cd C:/flaui
dotnet new console -n FlaUiGate --framework net8.0 --force 2>&1 | Select-Object -Last 2
cd FlaUiGate
dotnet add package FlaUI.UIA3 2>&1 | Select-Object -Last 3
dotnet add package System.Drawing.Common 2>&1 | Select-Object -Last 2
@'
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Threading;
using FlaUI.Core;
using FlaUI.Core.AutomationElements;
using FlaUI.Core.Definitions;
using FlaUI.UIA3;
var res = new Dictionary<string, object>();
try {
  var psi = new ProcessStartInfo(args[0], "\"" + args[1] + "\"") { UseShellExecute = false };
  var app = Application.Launch(psi);
  using var auto = new UIA3Automation();
  Window w = null;
  for (int i = 0; i < 45; i++) {
    Thread.Sleep(2000);
    try { w = app.GetMainWindow(auto, TimeSpan.FromSeconds(1)); if (w != null && !string.IsNullOrEmpty(w.Title) && w.Title.Contains("CAD")) break; } catch { }
  }
  res["window_found"] = w != null;
  if (w != null) {
    res["title"] = w.Title;
    var items = w.FindAllDescendants(cf => cf.ByControlType(ControlType.MenuItem)).Select(e => e.Name).Where(n => !string.IsNullOrEmpty(n)).Distinct().ToList();
    res["menu_items"] = items;
    res["menu_item_count"] = items.Count;
    res["arabic_menu_items"] = items.Count(n => n.Any(c => c >= 0x0600 && c <= 0x06FF));
    var btns = w.FindAllDescendants(cf => cf.ByControlType(ControlType.Button)).Select(e => e.Name).Where(n => !string.IsNullOrEmpty(n)).Distinct().Count();
    res["button_names"] = btns;
    res["any_element_named_program"] = w.FindAllDescendants().Any(e => (e.Name ?? "").Contains("\u0645\u062d\u0645\u0648\u062f"));
    try { w.Capture().Save("C:/flaui/flaui-window.png", System.Drawing.Imaging.ImageFormat.Png); res["capture"] = true; } catch (Exception ce) { res["capture_error"] = ce.Message; }
  }
  try { app.Kill(); } catch { }
} catch (Exception ex) { res["error"] = ex.ToString().Substring(0, Math.Min(600, ex.ToString().Length)); }
File.WriteAllText("C:/flaui/flaui-result.json", JsonSerializer.Serialize(res, new JsonSerializerOptions { WriteIndented = true, Encoder = System.Text.Encodings.Web.JavaScriptEncoder.UnsafeRelaxedJsonEscaping }));
'@ | Set-Content Program.cs -Encoding utf8
dotnet build -c Release 2>&1 | Select-String "error|Build succeeded" | Select-Object -First 6
$exe = Get-ChildItem C:/DeltaTest -Recurse -Filter FreeCAD.exe | Where-Object { $_.Directory.Name -eq 'bin' } | Select-Object -First 1
$root = $exe.Directory.Parent.FullName
$env:GALLIUM_DRIVER = 'llvmpipe'; $env:MESA_GL_VERSION_OVERRIDE = '4.5'
$m = "$root\LaunchDelta.FCMacro"
Get-Process FreeCAD -ErrorAction SilentlyContinue | Stop-Process -Force
$p = Start-Process dotnet -ArgumentList "bin/Release/net8.0/FlaUiGate.dll","`"$($exe.FullName)`"","`"$m`"" -PassThru -NoNewWindow
if (-not $p.WaitForExit(240000)) { 'FlaUI harness timeout, killing'; try { $p.Kill() } catch {} }
Get-Process FreeCAD -ErrorAction SilentlyContinue | Stop-Process -Force
if (Test-Path C:/flaui/flaui-result.json) { Get-Content C:/flaui/flaui-result.json -Raw -Encoding utf8 | Select-Object -First 1 }
New-Item -ItemType Directory -Force C:/seed | Out-Null
Copy-Item C:/flaui/flaui-result.json,C:/flaui/flaui-window.png C:/seed/ -ErrorAction SilentlyContinue
