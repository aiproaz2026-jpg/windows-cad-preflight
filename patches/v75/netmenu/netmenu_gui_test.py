# -*- coding: utf-8 -*-
"""Delta Engineering v69 test: network export MENU COMMAND registration, run as an FCMacro
on the installed app (real FreeCAD GUI, Mesa software GL in CI).

Verifies what the headless net68 test cannot: that InitGui's net_export.register() actually
wired the Delta_Net_Export command into the GUI command manager, the DeltaWorkbench menu bar
and toolbar, that the no-network guard fires through the real command dispatch, and that the
command produces the A3 plan PDF and CSV schedule end to end.

Result JSON: $DELTA_OUT/netmenu-result.json (runner polls for "done": true).
GPL-3.0-or-later. UNTESTED until a CI run executes it (written without build access).
"""
import os, json, time, traceback
OUT = os.environ.get('DELTA_OUT', 'C:/seed/netmenu')
os.makedirs(OUT, exist_ok=True)
os.makedirs(OUT + '/out', exist_ok=True)
res = {'steps': {}, 'done': False}


def save():
    open(OUT + '/netmenu-result.json', 'w', encoding='utf-8').write(json.dumps(res, ensure_ascii=False, indent=1, default=str))


try:
    import FreeCAD as App, FreeCADGui as Gui
    from PySide import QtCore, QtWidgets

    def pump(n=5):
        for _ in range(n):
            QtWidgets.QApplication.processEvents()

    def run(name, fn):
        t0 = time.time()
        try:
            out = fn()
            res['steps'][name] = {'ok': True, 'secs': round(time.time() - t0, 2), 'detail': out}
        except Exception:
            res['steps'][name] = {'ok': False, 'secs': round(time.time() - t0, 2), 'detail': traceback.format_exc()}
        save()

    def step():
        from DeltaEngineering.gui import register as wb_register, DeltaWorkbench
        from DeltaEngineering import net_export as NE, network as N, net_commands as NC
        if 'DeltaWorkbench' not in Gui.listWorkbenches():
            wb_register()
        Gui.activateWorkbench('DeltaWorkbench')
        pump(20)
        mw = Gui.getMainWindow()
        MENU_TITLE = 'تصدير الشبكة'
        CMD = 'Delta_Net_Export'
        CMD_TEXT_PART = 'تصدير مخطط الشبكة'

        def s_registration():
            out = {}
            cmd = Gui.Command.get(CMD)
            out['registered'] = cmd is not None
            assert cmd is not None, CMD + ' not registered with the GUI command manager (InitGui append9 did not run?)'
            out['remember_hook_active'] = bool(getattr(N, '_remember_patched', False))
            out['workbench_patch_active'] = bool(getattr(DeltaWorkbench, '_netexp_patched', False))
            assert out['remember_hook_active'], 'network.build remember hook not patched in (register() did not run)'
            assert out['workbench_patch_active'], 'DeltaWorkbench.Initialize not patched (register() did not run)'
            r = NE._Cmd().GetResources()
            out['menutext'] = r.get('MenuText')
            out['tooltip_nonempty'] = bool(r.get('ToolTip'))
            out['is_active'] = bool(cmd.isActive())
            assert out['menutext'] and CMD_TEXT_PART in out['menutext'], r
            assert out['tooltip_nonempty'], r
            assert out['is_active'], 'command IsActive() is False'
            return out
        run('registration_and_resources', s_registration)

        def s_menu_toolbar():
            out = {}
            pump(20)
            menus = [m for m in mw.findChildren(QtWidgets.QMenu) if m.title() == MENU_TITLE]
            out['menu_count'] = len(menus)
            out['menu_actions'] = [a.text() for a in menus[0].actions()] if menus else []
            out['menu_found'] = len(menus) == 1
            out['menu_has_command'] = any(CMD_TEXT_PART in t for t in out['menu_actions'])
            tbs = [t for t in mw.findChildren(QtWidgets.QToolBar) if t.windowTitle() == MENU_TITLE]
            out['toolbar_count'] = len(tbs)
            out['toolbar_actions'] = [a.text() for a in tbs[0].actions()] if tbs else []
            out['toolbar_found'] = len(tbs) >= 1
            out['toolbar_visible'] = bool(tbs and tbs[0].isVisible())
            out['all_menu_titles'] = sorted(set(m.title() for m in mw.findChildren(QtWidgets.QMenu) if m.title()))
            try:
                mw.grab().save(OUT + '/netmenu-main.png')
            except Exception:
                out['shot_err'] = traceback.format_exc()
            assert out['menu_found'], 'expected exactly one menu titled ' + MENU_TITLE + ': ' + str(out['all_menu_titles'])
            assert out['menu_has_command'], 'menu actions lack the export command: ' + str(out['menu_actions'])
            assert out['toolbar_found'], 'no toolbar titled ' + MENU_TITLE
            return out
        run('menu_and_toolbar_present', s_menu_toolbar)

        def s_guard():
            out = {}
            NE.LAST.clear()
            calls = {'warn': [], 'info': [], 'save_dialog': 0}
            orig_warn = QtWidgets.QMessageBox.warning
            orig_info = QtWidgets.QMessageBox.information
            orig_save = QtWidgets.QFileDialog.getSaveFileName
            def fake_warn(*a, **k):
                calls['warn'].append({'title': str(a[1]) if len(a) > 1 else '', 'text': str(a[2]) if len(a) > 2 else ''})
                return QtWidgets.QMessageBox.Ok
            def fake_info(*a, **k):
                calls['info'].append({'title': str(a[1]) if len(a) > 1 else '', 'text': str(a[2]) if len(a) > 2 else ''})
                return QtWidgets.QMessageBox.Ok
            def fake_save(*a, **k):
                calls['save_dialog'] += 1
                return ('', '')
            try:
                QtWidgets.QMessageBox.warning = staticmethod(fake_warn)
                QtWidgets.QMessageBox.information = staticmethod(fake_info)
                QtWidgets.QFileDialog.getSaveFileName = staticmethod(fake_save)
                Gui.runCommand(CMD)  # real dispatch through the command manager
                pump(10)
            finally:
                QtWidgets.QMessageBox.warning = orig_warn
                QtWidgets.QMessageBox.information = orig_info
                QtWidgets.QFileDialog.getSaveFileName = orig_save
            out['warnings'] = calls['warn']
            out['save_dialog_calls'] = calls['save_dialog']
            out['guard_warning_shown'] = len(calls['warn']) == 1 and 'أنشئ شبكة' in calls['warn'][0]['text']
            out['dialog_not_reached'] = calls['save_dialog'] == 0
            out['dispatched_via'] = 'Gui.runCommand'
            assert out['guard_warning_shown'], 'no-network warning not shown: ' + str(calls)
            assert out['dialog_not_reached'], 'save dialog reached with no network built'
            return out
        run('guard_without_network', s_guard)

        def s_export():
            out = {}
            doc = App.newDocument('NetMenuTest')
            nodes = {k: App.Vector(*v) for k, v in NC.DEMO_NODES.items()}
            N.build(doc, nodes, NC.DEMO_EDGES, '4', 'SCH 40')
            out['last_remembered_after_build'] = bool(NE.LAST)
            assert out['last_remembered_after_build'], 'network.build did not populate net_export.LAST'
            stem = OUT + '/out/demo_export'
            calls = {'warn': [], 'info': [], 'save_dialog': 0}
            orig_warn = QtWidgets.QMessageBox.warning
            orig_info = QtWidgets.QMessageBox.information
            orig_save = QtWidgets.QFileDialog.getSaveFileName
            def fake_warn(*a, **k):
                calls['warn'].append(str(a[2]) if len(a) > 2 else str(a))
                return QtWidgets.QMessageBox.Ok
            def fake_info(*a, **k):
                calls['info'].append({'title': str(a[1]) if len(a) > 1 else '', 'text': str(a[2]) if len(a) > 2 else ''})
                return QtWidgets.QMessageBox.Ok
            def fake_save(*a, **k):
                calls['save_dialog'] += 1
                return (stem, 'PDF (*.pdf)')
            try:
                QtWidgets.QMessageBox.warning = staticmethod(fake_warn)
                QtWidgets.QMessageBox.information = staticmethod(fake_info)
                QtWidgets.QFileDialog.getSaveFileName = staticmethod(fake_save)
                Gui.runCommand(CMD)  # real dispatch, patched only at the Qt dialog boundary
                pump(10)
            finally:
                QtWidgets.QMessageBox.warning = orig_warn
                QtWidgets.QMessageBox.information = orig_info
                QtWidgets.QFileDialog.getSaveFileName = orig_save
            out['save_dialog_calls'] = calls['save_dialog']
            out['warnings'] = calls['warn']
            out['info'] = calls['info']
            pdf = stem + '_plan_A3.pdf'
            csvf = stem + '_schedule.csv'
            out['pdf_exists'] = os.path.exists(pdf)
            out['csv_exists'] = os.path.exists(csvf)
            assert out['pdf_exists'] and out['csv_exists'], 'export artifacts missing: ' + str(calls)
            out['pdf_bytes'] = os.path.getsize(pdf)
            out['csv_bytes'] = os.path.getsize(csvf)
            out['pdf_magic_ok'] = open(pdf, 'rb').read(5) == b'%PDF-'
            txt = open(csvf, encoding='utf-8-sig').read().splitlines()
            out['csv_lines'] = len(txt)
            out['csv_header_ok'] = bool(txt) and txt[0].startswith('رقم')
            out['success_info_shown'] = len(calls['info']) == 1 and 'تم التصدير' in calls['info'][0]['title']
            assert calls['save_dialog'] == 1 and not calls['warn'], str(calls)
            assert out['pdf_bytes'] > 2000, out['pdf_bytes']
            assert out['csv_bytes'] > 200, out['csv_bytes']
            assert out['pdf_magic_ok'] and out['csv_header_ok']
            assert out['success_info_shown'], str(calls['info'])
            App.closeDocument(doc.Name)
            return out
        run('export_with_network_through_command', s_export)

        def s_reregister():
            out = {}
            NE.register()  # must be a no-op for UI duplication
            pump(10)
            menus = [m for m in mw.findChildren(QtWidgets.QMenu) if m.title() == MENU_TITLE]
            tbs = [t for t in mw.findChildren(QtWidgets.QToolBar) if t.windowTitle() == MENU_TITLE]
            out['menu_count_after_reregister'] = len(menus)
            out['toolbar_count_after_reregister'] = len(tbs)
            out['command_still_registered'] = Gui.Command.get(CMD) is not None
            assert out['command_still_registered']
            assert len(menus) == 1, 'duplicate menu after re-register: ' + str(len(menus))
            assert len(tbs) == 1, 'duplicate toolbar after re-register: ' + str(len(tbs))
            return out
        run('reregister_idempotent', s_reregister)

        res['done'] = True
        save()
        QtCore.QTimer.singleShot(1500, lambda: os._exit(0))

    QtCore.QTimer.singleShot(6000, step)
except Exception:
    res['error'] = traceback.format_exc()
    res['done'] = True
    save()
