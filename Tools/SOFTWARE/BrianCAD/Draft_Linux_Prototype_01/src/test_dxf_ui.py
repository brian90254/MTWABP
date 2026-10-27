"""DXF export dialog scope, frozen selection, cancellation and failure feedback."""
import copy
import os
from pathlib import Path
import sys
import tempfile
import tkinter as tk
import unittest
from unittest.mock import patch
try: import ezdxf
except ImportError: ezdxf=None
from draft import Draft
from cad_dxf import DXFDependencyError


@unittest.skipUnless(os.environ.get('DISPLAY') or sys.platform=='darwin','A graphical display is required')
class DXFWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.root=tk.Tk(); self.app=Draft(self.root); self.root.update()
        self.callbacks=[]; self.errors=[]; self.info=[]
        self.root.report_callback_exception=lambda *a:self.callbacks.append(a)
        self.app.error=self.errors.append
        self.error_patch=patch('draft.messagebox.showerror',side_effect=lambda *a,**k:self.errors.append(a[1]))
        self.info_patch=patch('draft.messagebox.showinfo',side_effect=lambda *a,**k:self.info.append(a[1]))
        self.error_patch.start(); self.info_patch.start()
        self.app.doc.add([{'type':'line','a':[0,0],'b':[2,0]},
                          {'type':'circle','center':[3,0],'radius':1},
                          {'type':'ellipse','center':[6,0],'rx':2,'ry':1,'angle':.3}])
        self.app.path='/tmp/playfield.draft.json'; self.app.draw()

    def tearDown(self):
        self.root.destroy(); self.error_patch.stop(); self.info_patch.stop()
        self.assertFalse(self.callbacks,repr(self.callbacks)); self.assertFalse(self.errors,repr(self.errors))

    def find(self,parent,kind,text):
        for w in parent.winfo_children():
            if w.winfo_class()==kind and w.cget('text').startswith(text): return w
            found=self.find(w,kind,text)
            if found is not None: return found
        return None

    @unittest.skipUnless(ezdxf,'Install requirements-dxf.txt')
    def test_selected_scope_is_frozen_and_does_not_change_document_or_path(self):
        a=self.app; a.selected={1}; a.doc.point_selection={0:{'a'}}
        a.export_dxf_dialog(); self.root.update(); a.export_scope.set('selected')
        a.objects[1]['center']=[99,99]; a.selected={2}; a.doc.point_selection={}
        before=a.doc.state(); history=copy.deepcopy(a.doc.history); future=copy.deepcopy(a.doc.future)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'selected.dxf'
            with patch('draft.filedialog.asksaveasfilename',return_value=str(path)) as save:
                self.find(a.export_window,'TButton','Export').invoke()
            entities=list(ezdxf.readfile(path).modelspace())
            self.assertEqual([e.dxftype() for e in entities],['LINE','CIRCLE'])
            self.assertEqual(tuple(entities[1].dxf.center),(3,0,0))
            self.assertEqual(save.call_args.kwargs['initialfile'],'playfield.dxf')
        self.assertEqual(a.doc.state(),before); self.assertEqual(a.doc.history,history); self.assertEqual(a.doc.future,future)
        self.assertEqual(a.selected,{2}); self.assertEqual(a.path,'/tmp/playfield.draft.json')
        self.assertIsNone(self.root.grab_current()); self.assertTrue(self.info)

    @unittest.skipUnless(ezdxf,'Install requirements-dxf.txt')
    def test_whole_drawing_includes_hidden_locked_geometry_and_no_selection_option(self):
        a=self.app; a.doc.clear_selection(); a.doc.layers[-1]['visible']=False; a.objects[0]['locked']=True
        before=a.doc.state(); a.export_dxf_dialog(); self.root.update()
        self.assertEqual(a.export_scope.get(),'all')
        self.assertTrue(self.find(a.export_window,'TRadiobutton','Selected objects').instate(['disabled']))
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'all.dxf'
            with patch('draft.filedialog.asksaveasfilename',return_value=str(path)):
                self.find(a.export_window,'TButton','Export').invoke()
            out=ezdxf.readfile(path)
            self.assertEqual(len(out.modelspace()),3); self.assertTrue(out.layers.get('Layer1').is_off())
        self.assertEqual(a.doc.state(),before)

    @unittest.skipUnless(ezdxf,'Install requirements-dxf.txt')
    def test_save_cancel_and_write_error_keep_dialog_and_drawing(self):
        a=self.app; before=a.doc.state(); n=len(a.doc.history)
        a.export_dxf_dialog(); self.root.update()
        with patch('draft.filedialog.asksaveasfilename',return_value=''):
            self.find(a.export_window,'TButton','Export').invoke()
        self.assertTrue(a.export_window.winfo_exists()); self.assertFalse(self.info)
        with patch('draft.filedialog.asksaveasfilename',return_value='/tmp/export-error.dxf'),patch('draft.cad_dxf.export_dxf',side_effect=OSError('write blocked')):
            self.find(a.export_window,'TButton','Export').invoke()
        self.assertTrue(self.errors); self.errors.clear(); self.assertTrue(a.export_window.winfo_exists())
        self.assertEqual(a.doc.state(),before); self.assertEqual(len(a.doc.history),n)
        self.find(a.export_window,'TButton','Cancel').invoke(); self.assertIsNone(self.root.grab_current())

    def test_missing_optional_dependency_and_empty_drawing(self):
        a=self.app; before=a.doc.state(); a.export_dxf_dialog()
        with patch('draft.cad_dxf.require_ezdxf',side_effect=DXFDependencyError('Install requirements-dxf.txt')),patch('draft.filedialog.asksaveasfilename') as save:
            self.find(a.export_window,'TButton','Export').invoke()
            save.assert_not_called()
        self.assertTrue(self.errors); self.errors.clear(); self.assertEqual(a.doc.state(),before)
        self.find(a.export_window,'TButton','Cancel').invoke()
        a.doc.objects=[]; a.export_dxf_dialog()
        self.assertTrue(self.errors); self.errors.clear(); self.assertIsNone(self.root.grab_current())


if __name__=='__main__': unittest.main()
