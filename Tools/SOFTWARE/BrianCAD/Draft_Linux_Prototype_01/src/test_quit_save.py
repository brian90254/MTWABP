"""Native macOS Quit and window-close save protection."""
import json
import os
from pathlib import Path
import sys
import tempfile
import tkinter as tk
import unittest
from unittest.mock import Mock,patch
from draft import Draft


class QuitRegistrationTests(unittest.TestCase):
    def test_native_quit_routes_to_same_handler_on_mac_only(self):
        for system in ('aqua','x11','win32'):
            a=Draft.__new__(Draft)
            a.root=Mock();a.root.tk.call.return_value=system
            a.install_close_handlers();a.root.protocol.assert_called_once_with('WM_DELETE_WINDOW',a.close)
            if system=='aqua':a.root.createcommand.assert_called_once_with('::tk::mac::Quit',a.close)
            else:a.root.createcommand.assert_not_called()


@unittest.skipUnless(os.environ.get('DISPLAY') or sys.platform=='darwin','A graphical display is required')
class QuitSaveUITests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.prefs=patch.dict(os.environ,{'XDG_CONFIG_HOME':self.temp.name});self.prefs.start()
        self.root=tk.Tk();self.a=Draft(self.root);self.root.update()
        self.a.doc.add([dict(type='line',a=[0,0],b=[2,1])]);self.a.draw()
        self.root.tk.call('namespace','eval','::tk::mac','')
        self.root.createcommand('::tk::mac::Quit',self.a.close)
    def tearDown(self):
        if self.alive():self.root.destroy()
        self.prefs.stop();self.temp.cleanup()
    def alive(self):
        try:return bool(int(self.root.tk.call('winfo','exists','.')))
        except tk.TclError:return False
    def native_quit(self):self.root.tk.call('::tk::mac::Quit')
    def test_cancel_and_save_as_cancel_leave_drawing_open(self):
        before=self.a.doc.state()
        with patch('draft.messagebox.askyesnocancel',return_value=None):self.native_quit()
        self.assertTrue(self.alive());self.assertEqual(self.a.doc.state(),before)
        with patch('draft.messagebox.askyesnocancel',return_value=True),patch('draft.filedialog.asksaveasfilename',return_value=''):self.native_quit()
        self.assertTrue(self.alive());self.assertTrue(self.a.doc.dirty)
    def test_save_then_quit_writes_native_drawing(self):
        path=Path(self.temp.name)/'saved.json';self.a.path=str(path)
        with patch('draft.messagebox.askyesnocancel',return_value=True):self.native_quit()
        self.assertFalse(self.alive());self.assertFalse(self.a.doc.dirty)
        self.assertEqual(len(json.loads(path.read_text())['objects']),1)
    def test_failed_save_does_not_quit(self):
        self.a.path=str(Path(self.temp.name)/'saved.json')
        with patch('draft.messagebox.askyesnocancel',return_value=True),patch('draft.os.replace',side_effect=OSError('disk full')),patch.object(self.a,'error') as error:self.native_quit()
        self.assertTrue(self.alive());self.assertTrue(self.a.doc.dirty);error.assert_called_once()
    def test_dont_save_and_clean_quit(self):
        with patch('draft.messagebox.askyesnocancel',return_value=False):self.native_quit()
        self.assertFalse(self.alive())
    def test_window_close_and_clean_quit_use_same_protection(self):
        command=self.root.protocol('WM_DELETE_WINDOW')
        with patch('draft.messagebox.askyesnocancel',return_value=None) as prompt:self.root.tk.call(command)
        prompt.assert_called_once();self.assertTrue(self.alive())
        self.a.doc.saved=self.a.doc.state()
        with patch('draft.messagebox.askyesnocancel') as prompt:self.native_quit()
        prompt.assert_not_called();self.assertFalse(self.alive())
    def test_reentrant_quit_does_not_open_second_prompt(self):
        def prompt(*args,**kwargs):self.native_quit();return None
        with patch('draft.messagebox.askyesnocancel',side_effect=prompt) as ask:self.native_quit()
        self.assertEqual(ask.call_count,1);self.assertTrue(self.alive())
