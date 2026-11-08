"""Layer header sorting/isolation, undo and existing row double-click behavior."""
import os
import sys
import tkinter as tk
import unittest
from tkinter import ttk
from cad_document import COLORS,Document,layer_sort_key
from draft import Draft

class LayerHeaderTests(unittest.TestCase):
    def test_natural_numeric_first_case_insensitive_sort(self):
        names=['Layer10','Beta','10 Ramps','alpha','Layer2','2 Parts']
        self.assertEqual(sorted(names,key=layer_sort_key),['2 Parts','10 Ramps','alpha','Beta','Layer2','Layer10'])
    def test_bulk_visibility_is_atomic_undoable_and_keeps_active_visible(self):
        d=Document();d.add([dict(type='line',a=[0,0],b=[1,0],layer='Construction')])
        before=d.state();n=len(d.history)
        self.assertTrue(d.toggle_other_layers());self.assertEqual(len(d.history),n+1)
        self.assertEqual([l['name'] for l in d.layers if l['visible']],[d.active]);self.assertFalse(d.selected)
        self.assertTrue(d.toggle_other_layers());self.assertTrue(all(l['visible'] for l in d.layers))
        d.undo();self.assertEqual([l['name'] for l in d.layers if l['visible']],[d.active])
        d.undo();self.assertEqual(d.state(),before)
        d.layers=[{'name':'Only','visible':True}];d.active='Only';n=len(d.history)
        self.assertFalse(d.toggle_other_layers());self.assertEqual(len(d.history),n)
        d.layers[0]['visible']=False;d.toggle_other_layers();self.assertTrue(d.layers[0]['visible'])

@unittest.skipUnless(os.environ.get('DISPLAY') or sys.platform=='darwin','A graphical display is required')
class LayerHeaderUITests(unittest.TestCase):
    def setUp(self):
        self.root=tk.Tk();self.a=Draft(self.root);self.root.update();self.callbacks=[]
        self.root.report_callback_exception=lambda *args:self.callbacks.append(args)
        for name in ('10 Ramps','2 Parts','alpha','Beta','Layer10','Layer2'):self.a.doc.add_layer(name)
        self.a.doc.saved=self.a.doc.state();self.a.layers_dialog();self.root.update();self.tree=self.a.layer_tree;self.clock=10000
    def tearDown(self):self.root.destroy();self.assertFalse(self.callbacks,repr(self.callbacks))
    def names(self):return [self.tree.item(row,'values')[-1] for row in self.tree.get_children()]
    def double(self,x,y):
        self.clock+=2000
        for offset in (0,120):
            self.tree.event_generate('<ButtonPress-1>',x=x,y=y,time=self.clock+offset)
            self.tree.event_generate('<ButtonRelease-1>',x=x,y=y,time=self.clock+offset+20)
        self.root.update()
    def header(self,column):
        x=20 if column=='#0' else self.tree.column('#0','width')+self.tree.column('active','width')+self.tree.column('locked','width')+30
        self.assertEqual(self.tree.identify_column(x),column);self.assertEqual(self.tree.identify_region(x,10),'heading')
        self.double(x,10)
    def test_sort_reverse_selection_and_refresh_without_dirtying_drawing(self):
        a=self.a;before=a.doc.state();n=len(a.doc.history);selected=str(next(i for i,l in enumerate(a.doc.layers) if l['name']=='Beta'))
        self.tree.selection_set(selected);self.header('#3')
        self.assertEqual(self.names(),sorted(self.names(),key=layer_sort_key));self.assertEqual(self.names()[:2],['2 Parts','10 Ramps'])
        self.assertEqual(self.tree.selection(),(selected,));self.assertEqual(a.doc.state(),before);self.assertEqual(len(a.doc.history),n);self.assertFalse(a.doc.dirty)
        self.header('#3');self.assertEqual(self.names(),sorted(self.names(),key=layer_sort_key,reverse=True))
        a.doc.add_layer('1 First');a.refresh_layers();self.assertEqual(self.names(),sorted(self.names(),key=layer_sort_key,reverse=True))
        self.header('#3');self.assertEqual(self.names()[0],'1 First')
    def test_eye_header_isolates_restores_and_row_double_clicks_still_work(self):
        a=self.a;n=len(a.doc.history);self.header('#0')
        self.assertEqual([l['name'] for l in a.doc.layers if l['visible']],[a.doc.active]);self.assertEqual(len(a.doc.history),n+1)
        self.header('#0');self.assertTrue(all(l['visible'] for l in a.doc.layers))
        self.header('#3')
        row=str(next(i for i,l in enumerate(a.doc.layers) if l['name']=='Beta'))
        self.tree.see(row);self.root.update();x,y,w,h=self.tree.bbox(row,'name');self.double(x+20,y+h//2)
        self.assertEqual(a.doc.active,'Beta')
        self.header('#0');self.assertEqual([l['name'] for l in a.doc.layers if l['visible']],['Beta'])
        x,y,w,h=self.tree.bbox(row,'#0');self.double(x+w//2,y+h//2);self.assertFalse(next(l for l in a.doc.layers if l['name']=='Beta')['visible'])
        self.header('#0');self.assertTrue(all(l['visible'] for l in a.doc.layers))

    def test_active_layer_restores_pen_and_native_save_preserves_it(self):
        a=self.a
        def activate(name):
            row=next(row for row in self.tree.get_children() if self.tree.item(row,'values')[-1]==name)
            self.tree.see(row);self.root.update()
            x,y,w,h=self.tree.bbox(row,'name');self.double(x+20,y+h//2)
        def choose(parent,name):
            for widget in parent.winfo_children():
                if isinstance(widget,ttk.Radiobutton) and widget.cget('text')==name:
                    widget.invoke();return True
                if choose(widget,name):return True
            return False
        self.assertTrue(choose(self.root,'Blue'))
        activate('Beta');self.assertEqual(a.color.get(),COLORS['Black'])
        self.assertTrue(choose(self.root,'Red'))
        activate('Layer1');self.assertEqual(a.color.get(),COLORS['Blue'])
        a.family.set('Lines');a.family_changed();a.create_object([[0,0],[1,0]])
        self.assertEqual(a.objects[-1]['color'],COLORS['Blue'])
        loaded=Document.from_payload(a.doc.payload())
        loaded.set_layer('Beta');self.assertEqual(loaded.layer_color(),COLORS['Red'])
