"""Import workflow preserves the open drawing and handles cancellation/errors."""
import json
import os
from pathlib import Path
import sys
import tempfile
import tkinter as tk
import unittest
from unittest.mock import patch
from draft import Draft
from cad_document import Document,COLORS

@unittest.skipUnless(os.environ.get('DISPLAY') or sys.platform=='darwin','A graphical display is required')
class ImportUITests(unittest.TestCase):
    def setUp(self):
        self.root=tk.Tk();self.app=Draft(self.root);self.root.update()
    def tearDown(self):self.root.destroy()
    def test_native_import_is_merge_and_keeps_filename(self):
        app=self.app; app.path='/tmp/current.draft.json'
        app.doc.add([dict(type='circle',center=[0,0],radius=1)]);n=len(app.doc.history)
        source=Document();source.add_layer('Imported');source.add([dict(type='line',a=[0,0],b=[2,2],layer='Imported',color=COLORS['Magenta'])])
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'other.draft.json';path.write_text(json.dumps(source.payload()))
            with patch('draft.filedialog.askopenfilename',return_value=str(path)),patch('draft.messagebox.showinfo') as info:
                app.import_drawing()
        self.assertEqual(app.path,'/tmp/current.draft.json'); self.assertEqual(len(app.doc.objects),2)
        self.assertEqual(len(app.doc.history),n+1);self.assertTrue(info.called)
        app.doc.undo();self.assertEqual(len(app.doc.objects),1)
    def test_cancel_and_parse_error_have_no_side_effects(self):
        app=self.app;before=app.doc.state()
        with patch('draft.filedialog.askopenfilename',return_value=''):app.import_drawing()
        with patch('draft.filedialog.askopenfilename',return_value='/missing.json'),patch.object(app,'error') as error:app.import_drawing()
        self.assertTrue(error.called);self.assertEqual(app.doc.state(),before);self.assertFalse(app.doc.history)
