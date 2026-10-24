"""Persistent non-modal Edit inspector, live selection and bulk property changes."""
import copy
import os
import sys
import tkinter as tk
import unittest
from unittest.mock import patch
from draft import Draft


@unittest.skipUnless(os.environ.get('DISPLAY') or sys.platform=='darwin','A graphical display is required')
class EditInspectorTests(unittest.TestCase):
    def setUp(self):
        self.root=tk.Tk(); self.app=Draft(self.root); self.root.update()
        self.errors=[]; self.callbacks=[]
        self.root.report_callback_exception=lambda *args:self.callbacks.append(args)
        self.dialogs=patch('draft.messagebox.showerror',side_effect=lambda *a,**k:self.errors.append(a[1]))
        self.dialogs.start(); self.app.error=self.errors.append
        a=self.app; a.scale=100; a.origin=[300,350]
        a.doc.add_layer('Ramps')
        a.doc.add([{'type':'line','a':[0,0],'b':[2,0]},
                   {'type':'circle','center':[4,2],'radius':1,'layer':'Ramps','color':'#2465d8','pattern':'Dashed','weight':.03}])
        a.doc.objects[0]['layer']='Layer1'; a.doc.clear_selection(); a.draw()

    def tearDown(self):
        self.root.destroy(); self.dialogs.stop()
        self.assertFalse(self.callbacks,repr(self.callbacks))
        self.assertFalse(self.errors,repr(self.errors))

    def select(self,ids):
        self.app.selected=set(ids); self.app.doc.point_selection={}; self.app.draw(); self.root.update()

    def click(self,p,shift=False,time=10000):
        x,y=self.app.screen(p)
        for event in ('<ButtonPress-1>','<ButtonRelease-1>'):
            self.app.canvas.event_generate(event,x=round(x),y=round(y),state=1 if shift else 0,time=time)
        self.root.update()

    def test_open_empty_and_follow_real_mouse_selection_without_grab(self):
        a=self.app; a.edit_dialog(); self.root.update(); window=a.edit_window
        self.assertIsNone(self.root.grab_current()); self.assertEqual(a.edit_fields,{})
        self.assertTrue(a.edit_apply.instate(['disabled']))
        self.click([1,0]); self.assertEqual(a.selected,{0}); self.assertIn('bx',a.edit_fields)
        self.click([5,2],shift=True,time=12000)
        self.assertEqual(a.selected,{0,1}); self.assertIs(a.edit_window,window)
        self.assertNotIn('bx',a.edit_fields); self.assertNotIn('diameter',a.edit_fields)
        self.assertEqual(a.edit_fields['layer'].get(),''); self.assertEqual(a.edit_fields['color'].get(),'')
        self.assertEqual(a.edit_fields['pattern'].get(),''); self.assertEqual(a.edit_fields['weight'].get(),'')
        self.assertFalse(a.edit_apply.instate(['disabled']))

    def test_bulk_layers_styles_sparse_changes_and_undo_live(self):
        a=self.app; self.select({0,1}); a.edit_dialog(); window=a.edit_window
        before=a.doc.state(); history=len(a.doc.history)
        a.edit_widgets['layer'].set('Layer1'); a.edit_apply.invoke()
        self.assertEqual(len(a.doc.history),history+1)
        for i,o in enumerate(a.objects):
            expected=copy.deepcopy(before['objects'][i]); expected['layer']='Layer1'
            self.assertEqual(o,expected)
        self.assertEqual(a.edit_fields['color'].get(),'')
        a.edit_widgets['color'].set('Green'); a.edit_widgets['pattern'].set('Dotted'); a.edit_apply.invoke()
        self.assertTrue(all(o['color']=='#198548' and o['pattern']=='Dotted' for o in a.objects))
        self.assertEqual(len(a.doc.history),history+2)
        a.undo(); self.assertEqual(a.edit_fields,{})
        self.select({0,1}); self.assertEqual(a.edit_fields['color'].get(),'')
        a.undo(); self.assertEqual(a.doc.state(),before)
        self.select({0,1}); self.assertEqual(a.edit_fields['layer'].get(),'')
        a.redo(); self.select({0,1}); self.assertEqual(a.edit_fields['layer'].get(),'Layer1')
        self.assertIs(a.edit_window,window); self.assertIsNone(self.root.grab_current())

    def test_pending_fields_survive_mouse_motion_but_not_selection_change(self):
        a=self.app; self.select({0}); a.edit_dialog()
        a.edit_fields['bx'].set('7')
        for p in [(20,20),(40,40),(60,60)]: a.canvas.event_generate('<Motion>',x=p[0],y=p[1])
        self.root.update(); self.assertEqual(a.edit_fields['bx'].get(),'7')
        a.doc.add_layer('New Layer'); a.draw()
        self.assertEqual(a.edit_fields['bx'].get(),'7')
        self.assertIn('New Layer',a.edit_widgets['layer'].cget('values'))
        self.select({1}); self.assertNotIn('bx',a.edit_fields)
        a.edit_widgets['color'].set('Red'); a.edit_apply.invoke()
        self.assertEqual(a.objects[0]['b'],[2,0]); self.assertEqual(a.objects[1]['color'],'#c44236')

    def test_mixed_blank_is_unchanged_invalid_is_atomic_and_noop_has_no_history(self):
        a=self.app; self.select({0,1}); a.edit_dialog(); before=a.doc.state(); n=len(a.doc.history)
        a.edit_apply.invoke(); self.assertEqual(len(a.doc.history),n)
        a.edit_fields['weight'].set('-1'); a.edit_apply.invoke()
        self.assertTrue(self.errors); self.errors.clear()
        self.assertEqual(a.doc.state(),before); self.assertEqual(len(a.doc.history),n)
        a.edit_fields['weight'].set(''); a.edit_widgets['pattern'].set('Dotted'); a.edit_apply.invoke()
        self.assertEqual([o['weight'] for o in a.objects],[.01,.03])
        self.assertTrue(all(o['pattern']=='Dotted' for o in a.objects))

    def test_layers_window_and_editor_work_together_and_close_reopens(self):
        a=self.app; self.select({0,1}); a.edit_dialog(); a.layers_dialog(); self.root.update()
        self.assertIsNone(self.root.grab_current())
        self.assertTrue(a.layer_window.winfo_exists()); self.assertTrue(a.edit_window.winfo_exists())
        a.edit_widgets['color'].set('Green')
        frame=a.layer_tree.master
        entry=next(w for w in frame.winfo_children() if w.winfo_class()=='TEntry')
        entry.delete(0,'end'); entry.insert(0,'New Group')
        new=next(w for w in frame.winfo_children() if w.winfo_class()=='TButton' and w.cget('text')=='New')
        new.invoke(); self.root.update()
        self.assertEqual(a.edit_fields['color'].get(),'Green')
        self.assertIn('New Group',a.edit_widgets['layer'].cget('values'))
        a.edit_widgets['color'].set(''); a.edit_apply.invoke()
        self.assertEqual([o['color'] for o in a.objects],['#202b36','#2465d8'])
        a.close_edit(); self.assertIsNone(a.edit_window); self.assertIsNone(a._edit_doc)
        a.edit_dialog(); self.assertEqual(a.edit_fields['color'].get(),'')
        self.assertIsNone(self.root.grab_current())

    def test_shared_circle_arc_geometry_and_current_total_length(self):
        import cad_geometry as g
        a=self.app
        a.doc.add([{'type':'arc','center':[6,1],'radius':2,'start':0,'sweep':1}])
        self.select({1,2}); a.edit_dialog()
        self.assertIn('diameter',a.edit_fields); self.assertNotIn('sweep',a.edit_fields)
        self.assertEqual(a.edit_fields['diameter'].get(),'')
        self.assertEqual(a.edit_fields['cx'].get(),'')
        a.edit_fields['diameter'].set('6')
        self.assertIn('Selected total length',a.edit_length.get())
        self.assertNotIn('check entered',a.edit_length.get())
        before=a.doc.state(); history=len(a.doc.history); a.edit_apply.invoke()
        self.assertEqual(a.objects[1]['radius'],3); self.assertEqual(a.objects[2]['radius'],3)
        self.assertEqual(a.objects[1]['center'],[4,2]); self.assertEqual(a.objects[2]['center'],[6,1])
        self.assertEqual(len(a.doc.history),history+1)
        total=sum(g.length(a.objects[i]) for i in (1,2))
        self.assertIn(f'{total:.6g} in',a.edit_length.get())
        a.undo(); self.assertEqual(a.doc.state(),before)

    def test_partial_owner_selection_hidden_layers_and_stale_apply(self):
        a=self.app; a.selected=set(); a.doc.point_selection={0:{'a'}}; a.edit_dialog()
        self.assertIn('ax',a.edit_fields)
        a.doc.toggle_layer('Ramps'); a.draw()
        a.edit_widgets['layer'].set('Ramps'); a.edit_apply.invoke()
        self.assertEqual(a.edit_fields,{}); self.assertTrue(a.edit_apply.instate(['disabled']))
        a.doc.toggle_layer('Ramps'); self.select({1})
        a.edit_fields['diameter'].set('10')
        a.doc.delete_selected()  # mutation before the next draw must not reuse the old index
        before=a.doc.state(); a.apply_edit()
        self.assertEqual(a.doc.state(),before); self.assertEqual(a.edit_fields,{})


if __name__=='__main__': unittest.main()
