"""Tk workflow checks; skip on headless hosts unless a display is supplied."""
import json
import os
from pathlib import Path
import tempfile
import tkinter as tk
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from draft import Draft
from cad_tools import METHODS
from cad_geometry import length


@unittest.skipUnless(os.environ.get('DISPLAY') or __import__('sys').platform=='darwin', 'A graphical display is required')
class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.root=tk.Tk(); self.app=Draft(self.root)
        self.errors=[]; self.callbacks=[]
        self.root.report_callback_exception=lambda *args:self.callbacks.append(args)
        self.app.error=self.errors.append
        self.dialog_errors=patch('draft.messagebox.showerror',side_effect=lambda *a,**k:self.errors.append(a[1]))
        self.dialog_errors.start(); self.root.update()

    def tearDown(self):
        self.root.destroy(); self.dialog_errors.stop()
        self.assertFalse(self.callbacks,repr(self.callbacks))

    def choose(self,family,method=None):
        self.app.family.set(family); self.app.family_changed()
        if method:
            self.app.tool.set(method); self.app.method_changed()
        self.root.update()

    def button(self,widget,text):
        for child in widget.winfo_children():
            if child.winfo_class()=='TButton' and child.cget('text')==text: return child
            found=self.button(child,text)
            if found: return found
        return None

    def right_click(self):
        legacy=(self.root.tk.call('tk','windowingsystem')=='aqua' and
                int(self.root.tk.call('package','vcompare',
                    self.root.tk.call('package','provide','Tk'),'8.7a0'))<0)
        self.app.canvas.event_generate(f'<Button-{2 if legacy else 3}>',x=100,y=100)
        self.root.update()

    def test_right_click_cancels_construction_and_preserves_selection(self):
        a=self.app; self.choose('Lines'); a.pick([0,0]); a.pick([2,0])
        a.selected={0}; before=a.doc.state(); history=len(a.doc.history)
        for family,points in [('Lines',[[3,3]])]:
            self.choose(family)
            for point in points: a.pick(point)
            self.right_click()
            self.assertEqual(a.family.get(),'Select'); self.assertEqual(a.tool.get(),'Select')
            self.assertEqual(a.points,[]); self.assertEqual(a.selected,{0})
            self.assertEqual(a.doc.state(),before); self.assertEqual(len(a.doc.history),history)
        self.choose('Splines')
        for point in [[0,0],[1,2],[2,0]]: a.pick(point)
        a.canvas.focus_force(); self.root.update()
        a.canvas.event_generate('<Return>'); self.root.update()
        self.assertEqual(a.objects[-1]['type'],'spline')
        self.assertFalse(self.errors)

    def test_right_click_finishes_spline_then_returns_to_select(self):
        a=self.app
        for method in ['Through points','Closed through points','Bezier controls']:
            self.choose('Splines',method)
            for p in [[0,0],[1,2],[2,0]]: a.pick(p)
            n=len(a.objects); history=len(a.doc.history)
            self.right_click()
            self.assertEqual(len(a.objects),n+1); self.assertEqual(len(a.doc.history),history+1)
            self.assertEqual(a.family.get(),'Splines'); self.assertEqual(a.points,[])
            self.right_click()
            self.assertEqual(a.family.get(),'Select'); self.assertEqual(len(a.objects),n+1)
        self.choose('Splines'); self.right_click()
        self.assertEqual(a.family.get(),'Select')
        self.assertFalse(self.errors)

    def test_right_click_incomplete_spline_preserves_picks_for_retry(self):
        a=self.app; self.choose('Splines'); a.pick([0,0]); self.right_click()
        self.assertEqual(a.family.get(),'Splines'); self.assertEqual(a.points,[[0,0]])
        self.assertTrue(self.errors); self.errors.clear()
        a.pick([1,1]); self.right_click(); self.assertEqual(len(a.objects),1)
        self.assertEqual(a.family.get(),'Splines')
        self.assertFalse(self.errors)

    def test_trim_tangent_contacts_and_whole_circle_single_contact(self):
        import math
        a=self.app; a.scale=100; a.origin=[400,300]
        a.doc.add([{'type':'circle','center':[0,0],'radius':1},
                   {'type':'line','a':[-2,1],'b':[2,1]},
                   {'type':'line','a':[-2,-1],'b':[2,-1]}])
        a.selected={1,2}; self.choose('Trim'); before=a.doc.state()
        self.trim_mouse([1,0]); self.assertEqual(a.objects[0]['type'],'arc')
        self.assertAlmostEqual(a.objects[0]['sweep'],math.pi)
        a.undo(); self.assertEqual(a.doc.state(),before)
        a.selected={1}; self.choose('Trim'); self.trim_mouse([1,0],14000)
        self.assertEqual(len(a.objects),2); self.assertEqual(a.selected,{0})
        a.undo(); self.assertEqual(a.doc.state(),before)
        self.assertFalse(self.errors)

    def test_tangent_line_mouse_preview_commit_and_connected_start(self):
        import math
        import cad_geometry as g
        a=self.app
        a.doc.add([{'type':'circle','center':[0,0],'radius':1}])
        a.scale=150; a.origin=[400,300]
        self.choose('Lines','Connected points'); a.pick([2,0])
        q=[.5,math.sqrt(3)/2]
        x,y=a.screen([q[0]+.02,q[1]-.01])
        a.canvas.event_generate('<Motion>',x=round(x),y=round(y)); self.root.update()
        self.assertEqual(a.marker,'tangent')
        self.assertAlmostEqual(g.dist(a.mouse,q),0)
        a.canvas.event_generate('<ButtonPress-1>',x=round(x),y=round(y))
        a.canvas.event_generate('<ButtonRelease-1>',x=round(x),y=round(y)); self.root.update()
        line=a.objects[-1]
        self.assertEqual(line['type'],'line')
        self.assertAlmostEqual(g.dist(line['b'],q),0)
        self.assertAlmostEqual(g.dot(g.sub(line['b'],line['a']),line['b']),0)
        self.assertEqual(a.points,[line['b']])
        a.undo(); self.assertEqual(len(a.objects),1)
        self.assertFalse(self.errors)

    def trim_mouse(self,p,time=10000):
        x,y=self.app.screen(p)
        self.app.canvas.event_generate('<ButtonPress-1>',x=round(x),y=round(y),time=time)
        self.app.canvas.event_generate('<ButtonRelease-1>',x=round(x),y=round(y),time=time+10)
        self.root.update()

    def test_trim_circle_with_selected_line_and_right_click_exit(self):
        import math
        a=self.app
        a.doc.add([{'type':'circle','center':[0,0],'radius':1},
                   {'type':'line','a':[0,-2],'b':[0,2]}])
        a.selected={1}; a.scale=100; a.origin=[400,300]
        boundary=a.objects[1]; self.choose('Trim')
        self.assertEqual(a.trim_cutters,[boundary]); self.assertEqual(a.params,{})
        history=len(a.doc.history)
        self.trim_mouse([1,0])
        self.assertEqual(a.objects[0]['type'],'arc')
        self.assertAlmostEqual(a.objects[0]['sweep'],math.pi)
        self.assertIs(a.objects[1],boundary); self.assertEqual(a.selected,{1})
        self.assertEqual(len(a.doc.history),history+1)
        self.trim_mouse([0,-1.5],12000)  # active boundary is protected
        self.assertEqual(len(a.doc.history),history+1)
        self.right_click(); self.assertEqual(a.family.get(),'Select')
        a.undo(); self.assertEqual(a.objects[0]['type'],'circle')
        self.assertFalse(self.errors)

    def test_trim_repeated_targets_reindexes_boundaries_and_undo_exits(self):
        a=self.app; a.scale=100; a.origin=[400,300]
        a.doc.add([{'type':'line','a':[-3,0],'b':[3,0]},
                   {'type':'line','a':[-3,.5],'b':[3,.5]},
                   {'type':'circle','center':[0,0],'radius':1}])
        a.selected={2}; boundary=a.objects[2]; self.choose('Trim')
        before=a.doc.state(); history=len(a.doc.history)
        self.trim_mouse([0,0]); self.assertEqual(len(a.objects),4)
        self.assertEqual(a.selected,{3}); self.assertIs(a.objects[3],boundary)
        self.trim_mouse([0,.5],12000); self.assertEqual(len(a.objects),5)
        self.assertEqual(a.selected,{4}); self.assertIs(a.objects[4],boundary)
        self.assertEqual(a.trim_cutters,[boundary]); self.assertEqual(a.family.get(),'Trim')
        self.assertEqual(len(a.doc.history),history+2)
        a.undo(); self.assertEqual(a.family.get(),'Select'); self.assertEqual(len(a.objects),4)
        a.undo(); self.assertEqual(a.doc.state(),before)
        a.redo(); self.assertEqual(len(a.objects),4)
        self.assertFalse(self.errors)

    def test_trim_promotes_partial_boundary_and_leaves_locked_target(self):
        a=self.app; a.scale=100; a.origin=[400,300]
        a.doc.add([{'type':'line','a':[-3,0],'b':[3,0],'locked':True},
                   {'type':'circle','center':[0,0],'radius':1}])
        a.selected=set(); a.doc.point_selection={1:{'radius'}}
        self.choose('Trim'); self.assertEqual(a.selected,{1}); self.assertFalse(a.doc.point_selection)
        before=a.doc.state(); self.trim_mouse([0,0])
        self.assertEqual(a.doc.state(),before)
        a.root.event_generate('<Escape>'); self.root.update()
        self.assertEqual(a.family.get(),'Select'); self.assertFalse(a.trim_cutters)
        self.assertFalse(self.errors)

    def test_three_click_tangent_arc_preview_and_auto_direction(self):
        import cad_geometry as g
        a=self.app; a.scale=100; a.origin=[400,300]
        a.snap.set(False); a.grid_snap.set(False)
        self.choose('Arcs','Start tangent + end')
        self.assertEqual(list(a.params),['x','y','x2','y2','x3','y3'])
        for p in [[0,0],[2,0]]:
            self.trim_mouse(p)
        self.assertEqual(a.objects,[]); self.assertEqual(len(a.points),2)
        self.assertIn('arc endpoint',a.prompt())
        for end,positive in [([1,1],True),([1,-1],False)]:
            x,y=a.screen(end); a.canvas.event_generate('<Motion>',x=x,y=y); self.root.update()
            preview=a.preview(); self.assertEqual(preview['type'],'arc')
            self.assertEqual(preview['sweep']>0,positive)
            self.assertTrue(a.canvas.find_withtag('tangent-guide'))
        a.clockwise.set(False)  # Third click below the tangent still chooses clockwise.
        self.trim_mouse([1,-1],14000)
        self.assertEqual(len(a.objects),1); self.assertLess(a.objects[0]['sweep'],0)
        self.assertAlmostEqual(g.dist(g.path(a.objects[0])[-1],[1,-1]),0)
        self.assertFalse(a.canvas.find_withtag('tangent-guide'))
        a.undo(); self.assertEqual(a.objects,[])
        self.assertFalse(self.errors)

    def test_tangent_arc_typed_parameters_and_edited_preview(self):
        import cad_geometry as g
        a=self.app; self.choose('Arcs','Start tangent + end')
        a.pick([0,0]); a.pick([1,0])
        a.params['x'].set('3'); a.params['y'].set('-4')
        a.params['x2'].set('3'); a.params['y2'].set('-2')
        a.mouse=[2,-3]
        self.assertAlmostEqual(g.dist(a.preview()['center'],[2,-4]),0)
        a.params['x3'].set('2'); a.params['y3'].set('-3')
        a.apply_parameters()
        self.assertEqual(len(a.objects),1)
        self.assertAlmostEqual(g.dist(a.objects[0]['center'],[2,-4]),0)
        self.assertFalse(self.errors)

    def test_tangent_arc_rejects_degenerate_clicks_and_can_retry(self):
        a=self.app; self.choose('Arcs','Start tangent + end')
        a.snap.set(False); a.grid_snap.set(False); a.scale=100; a.origin=[400,300]
        self.trim_mouse([0,0]); self.trim_mouse([0,0],12000)
        self.assertEqual(a.points,[[0,0]]); self.assertTrue(self.errors); self.errors.clear()
        self.trim_mouse([1,0],14000); self.trim_mouse([2,0],16000)
        self.assertEqual(len(a.points),2); self.assertEqual(a.objects,[])
        self.assertTrue(self.errors); self.errors.clear()
        self.trim_mouse([1,1],18000); self.assertEqual(len(a.objects),1)
        self.assertFalse(self.errors)

    def test_curve_constraint_snaps_commit_exact_line_endpoints(self):
        import math
        import cad_geometry as g
        from cad_document import Document
        a=self.app; a.scale=100; a.origin=[400,300]
        a.grid_snap.set(False)
        cases=[({'type':'ellipse','center':[0,0],'rx':2,'ry':1,'angle':0},
                [3,0],[4/3,math.sqrt(5)/3],'tangent'),
               ({'type':'spline','method':'bezier','closed':False,'points':[[0,0],[1,2],[2,0]]},
                [3,1],[1,1],'tangent'),
               ({'type':'spline','method':'bezier','closed':False,'points':[[0,0],[1,2],[2,0]]},
                [1,3],[1,1],'perpendicular')]
        for obj,start,q,label in cases:
            with self.subTest(kind=obj['type'],mode=label):
                a.doc=Document(); a.doc.add([obj]); self.choose('Lines')
                a.pick(start)
                x,y=a.screen([q[0]+.01,q[1]+.01])
                a.motion(SimpleNamespace(x=x,y=y)); self.assertEqual(a.marker,label)
                self.assertLess(g.dist(a.mouse,q),1e-7)
                a.click(SimpleNamespace(x=x,y=y,state=0))
                self.assertLess(g.dist(a.objects[-1]['b'],q),1e-7)
                self.assertTrue(any(g.dist(p,q)<1e-7 for p in a.snap_history.points))
                a.undo(); self.assertEqual(len(a.objects),1)
        self.assertFalse(self.errors)

    def test_trim_oval_mouse_and_arc_editor(self):
        import math
        from cad_document import Document
        a=self.app; a.doc=Document(); a.scale=100; a.origin=[400,300]
        a.doc.add([{'type':'ellipse','center':[0,0],'rx':2,'ry':1,'angle':0},
                   {'type':'line','a':[0,-3],'b':[0,3]}])
        a.selected={1}; self.choose('Trim'); before=a.doc.state()
        self.trim_mouse([2,0]); self.assertEqual(a.objects[0]['type'],'ellipse')
        self.assertAlmostEqual(a.objects[0]['sweep'],math.pi)
        self.right_click(); a.selected={0}; a.edit_dialog(); self.root.update()
        self.assertIn('start',a.edit_fields); self.assertIn('sweep',a.edit_fields)
        a.edit_fields['sweep'].set('90'); self.button(a.edit_window,'Apply').invoke()
        self.assertAlmostEqual(a.objects[0]['sweep'],math.pi/2)
        self.button(a.edit_window,'Close').invoke()
        a.undo(); a.undo(); self.assertEqual(a.doc.state(),before)
        self.assertFalse(self.errors)

    def test_trim_spline_mouse_split_and_oval_boundary(self):
        from cad_document import Document
        a=self.app; a.doc=Document(); a.scale=100; a.origin=[400,300]
        a.doc.add([{'type':'spline','method':'bezier','closed':False,'points':[[0,0],[1,2],[2,0]]},
                   {'type':'line','a':[.5,-2],'b':[.5,3]},
                   {'type':'line','a':[1.5,-2],'b':[1.5,3]}])
        a.selected={1,2}; self.choose('Trim'); before=a.doc.state(); history=len(a.doc.history)
        self.trim_mouse([1,1]); self.assertEqual(len(a.objects),4)
        self.assertEqual(a.selected,{2,3}); self.assertEqual(len(a.doc.history),history+1)
        self.assertAlmostEqual(a.objects[0]['points'][-1][0],.5)
        self.assertAlmostEqual(a.objects[1]['points'][0][0],1.5)
        a.undo(); self.assertEqual(a.doc.state(),before)
        a.doc=Document()
        a.doc.add([{'type':'line','a':[-3,0],'b':[3,0]},
                   {'type':'ellipse','center':[0,0],'rx':2,'ry':1,'angle':0}])
        a.selected={1}; self.choose('Trim'); self.trim_mouse([0,0],14000)
        self.assertEqual(len(a.objects),3); self.assertEqual(a.selected,{2})
        self.assertAlmostEqual(a.objects[0]['b'][0],-2)
        self.assertAlmostEqual(a.objects[1]['a'][0],2)
        self.assertFalse(self.errors)

    def chamfer_setup(self):
        from cad_document import Document
        a=self.app; a.doc=Document(); a.scale=100; a.origin=[400,300]
        a.doc.add([{'type':'line','a':[0,0],'b':[4,0]},
                   {'type':'line','a':[0,0],'b':[0,4]}])
        self.choose('Chamfer'); return a

    def test_chamfer_single_radius_field_two_clicks_and_undo(self):
        a=self.chamfer_setup(); self.assertEqual(list(a.params),['radius'])
        entries=[w for frame in a.parameter_frame.winfo_children() for w in frame.winfo_children() if w.winfo_class()=='TEntry']
        self.assertEqual(len(entries),1)
        self.assertIsNone(self.button(a.parameter_frame,'Apply / Create'))
        before=a.doc.state(); history=len(a.doc.history)
        self.trim_mouse([2,0]); self.assertEqual(a.doc.state(),before)
        self.assertIsNotNone(a.chamfer_first); self.assertIn('second segment',a.prompt())
        a.params['radius'].set('.5')  # the value at the second pick defines the result
        self.trim_mouse([0,2],12000)
        self.assertEqual(len(a.objects),3); self.assertEqual(a.objects[-1]['type'],'arc')
        self.assertAlmostEqual(a.objects[-1]['radius'],.5)
        self.assertEqual(a.family.get(),'Chamfer'); self.assertIsNone(a.chamfer_first)
        self.assertEqual(len(a.doc.history),history+1)
        self.assertAlmostEqual(a.objects[0]['a'][0],.5)
        self.assertAlmostEqual(a.objects[1]['a'][1],.5)
        a.undo(); self.assertEqual(a.doc.state(),before)
        a.redo(); self.assertEqual(len(a.objects),3)
        self.assertFalse(self.errors)

    def test_chamfer_invalid_radius_retry_and_right_click_cancel(self):
        a=self.chamfer_setup(); before=a.doc.state(); history=len(a.doc.history)
        a.params['radius'].set('0'); self.trim_mouse([2,0])
        self.assertIsNone(a.chamfer_first); self.assertTrue(self.errors); self.errors.clear()
        a.params['radius'].set('.5'); self.trim_mouse([2,0],12000)
        self.trim_mouse([2,0],14000); self.assertTrue(self.errors); self.errors.clear()
        a.params['radius'].set('10'); self.trim_mouse([0,2],16000)
        self.assertTrue(self.errors); self.errors.clear(); self.assertIsNotNone(a.chamfer_first)
        self.assertEqual(a.doc.state(),before); self.assertEqual(len(a.doc.history),history)
        a.params['radius'].set('.5'); self.trim_mouse([0,2],18000)
        self.assertEqual(len(a.objects),3)
        a.undo(); self.trim_mouse([2,0],20000); self.right_click()
        self.assertEqual(a.family.get(),'Select'); self.assertIsNone(a.chamfer_first)
        self.assertEqual(a.doc.state(),before)
        self.assertFalse(self.errors)

    def test_chamfer_curve_mouse_workflow(self):
        from cad_document import Document
        a=self.app; a.doc=Document(); a.scale=100; a.origin=[400,300]
        a.doc.add([{'type':'line','a':[1,-2],'b':[1,2]},
                   {'type':'spline','method':'bezier','closed':False,'points':[[-2,5],[0,-3],[2,5]]}])
        self.choose('Chamfer'); a.params['radius'].set('1')
        self.trim_mouse([1,-.5]); self.trim_mouse([-.4,1.16],12000)
        self.assertEqual(len(a.objects),3); self.assertEqual(a.objects[-1]['type'],'arc')
        self.assertAlmostEqual(a.objects[-1]['radius'],1)
        self.assertAlmostEqual(a.objects[-1]['center'][0],0,places=6)
        self.assertAlmostEqual(a.objects[-1]['center'][1],0,places=6)
        self.assertFalse(self.errors)

    def test_all_tool_controls_and_tab_order(self):
        for family,methods in METHODS.items():
            for method in methods:
                self.choose(family,method)
                self.assertEqual(self.app.tool.get(),method)
                self.assertTrue(self.app.status.get())
        self.choose('Lines')
        entries=[]
        for frame in self.app.parameter_frame.winfo_children():
            entries.extend(w for w in frame.winfo_children() if w.winfo_class()=='TEntry')
        self.assertEqual(len(entries),8)
        for a,b in zip(entries,entries[1:]):
            self.assertEqual(str(a.tk_focusNext()),str(b))
        self.assertLess(self.app.parameter_frame.winfo_reqwidth(),self.root.winfo_width())

    def test_click_and_manual_bottom_parameters(self):
        self.choose('Lines'); a=self.app
        a.pick([2,3]); self.assertEqual(a.params['x'].get(),'2'); self.assertEqual(a.params['y'].get(),'3')
        a.params['x'].set('4')  # amend the clicked start before choosing endpoint
        a.pick([6,3]); self.assertEqual(a.objects[0]['a'],[4,3]); self.assertEqual(a.objects[0]['b'],[6,3])
        a.params['x'].set('0'); a.params['y'].set('0'); a.params['length'].set('2'); a.params['angle'].set('90')
        a.last_parameter='angle'; a.apply_parameters(); self.assertAlmostEqual(a.objects[-1]['b'][1],2)
        self.choose('Circles'); a.params['x'].set('0'); a.params['y'].set('0'); a.params['diameter'].set('1')
        a.apply_parameters(); self.assertEqual(a.objects[-1]['radius'],.5)
        self.assertFalse(self.errors)

    def test_continuous_offset_and_tangent(self):
        a=self.app; self.choose('Lines','Connected points')
        for p in [[0,0],[2,0],[2,2]]: a.pick(p)
        self.assertEqual(len(a.objects),2); self.assertEqual(a.points,[[2,2]])
        a.finish(); self.assertEqual(a.points,[])
        self.choose('Lines','Offset from line'); a.pick([1,0]); a.pick([1,.25])
        self.assertAlmostEqual(a.objects[-1]['a'][1],.25)
        self.choose('Arcs','Start tangent + end'); a.pick([1,0]); a.pick([2,0]); a.pick([2,1])
        self.assertEqual(a.objects[-1]['type'],'arc')
        self.assertFalse(self.errors)

    def test_spline_workflow_and_group_transforms(self):
        a=self.app; self.choose('Splines')
        for p in [[0,0],[1,2],[2,0]]: a.pick(p)
        self.assertEqual(len(a.objects),0); a.finish(); self.assertEqual(a.objects[0]['type'],'spline')
        self.choose('Polygons'); a.pick([3,0]); a.pick([4,1])
        a.selected={0,1}; self.choose('Modify','Move')
        a.params['dx'].set('2'); a.params['dy'].set('3'); a.apply_parameters()
        self.assertEqual(a.objects[0]['points'][0],[2,3]); self.assertEqual(a.objects[1]['points'][0],[5,3])
        a.undo(); self.assertEqual(a.objects[0]['points'][0],[0,0])
        self.assertFalse(self.errors)

    def test_mouse_transform_and_selection(self):
        a=self.app; self.choose('Lines'); a.pick([0,0]); a.pick([2,0])
        self.choose('Modify','Rotate')
        for p in [[0,0],[1,0],[0,1]]: a.pick(p)
        self.assertAlmostEqual(a.objects[0]['b'][1],2)
        self.choose('Select'); a.fit(); self.root.update()
        px,py=a.screen([0,1])
        a.click(SimpleNamespace(x=px,y=py,state=0)); self.assertEqual(a.selected,{0})
        a.click(SimpleNamespace(x=px,y=py,state=1)); self.assertFalse(a.selected)
        self.assertFalse(self.errors)

    def test_layer_highlight_double_click_visibility(self):
        a=self.app; a.doc.add_layer('Ramps'); a.layers_dialog(); self.root.update()
        tree=a.layer_tree; row=next(k for k in tree.get_children() if tree.item(k,'values')[-1]=='Ramps')
        tree.selection_set(row); self.root.update(); self.assertEqual(a.doc.active,'Layer1')
        self.button(a.layer_window,'Set Layer').invoke(); self.assertEqual(a.doc.active,'Ramps')
        self.choose('Lines'); a.pick([0,0]); a.pick([2,0])
        self.assertEqual(a.objects[-1]['layer'],'Ramps')
        self.button(a.layer_window,'Show / Hide').invoke(); self.assertFalse(a.doc.visible(0))
        self.assertIsNone(a.hit([1,0]))
        a.grid_snap.set(False)
        self.assertNotEqual(a.snap_point([2,0])[1],'endpoint')
        a.undo(); self.assertTrue(a.doc.visible(0))
        self.assertFalse(self.errors)

    def test_layer_actual_double_click_bindings(self):
        a=self.app; a.layers_dialog(); self.root.update(); tree=a.layer_tree
        row=next(k for k in tree.get_children() if tree.item(k,'values')[-1]=='Dimension')
        def click_column(column,time):
            x,y,w,h=tree.bbox(row,column)
            tree.event_generate('<ButtonPress-1>',x=x+w//2,y=y+h//2,time=time)
            tree.event_generate('<ButtonRelease-1>',x=x+w//2,y=y+h//2,time=time+10)
            self.root.update()
        click_column('name',10000)
        self.assertEqual(a.doc.active,'Layer1')
        click_column('name',10100)
        self.assertEqual(a.doc.active,'Dimension')
        click_column('#0',20000); click_column('#0',20100)
        self.assertFalse(next(l for l in a.doc.layers if l['name']=='Dimension')['visible'])
        self.assertFalse(self.errors)

    def test_object_editor_length_and_apply(self):
        a=self.app; self.choose('Lines'); a.pick([0,0]); a.pick([1,0]); a.edit_dialog(); self.root.update()
        a.edit_fields['bx'].set('3'); a.edit_fields['by'].set('4'); self.root.update()
        self.assertIn('5 in',a.edit_length.get())
        self.button(a.edit_window,'Apply').invoke(); self.assertEqual(length(a.objects[0]),5)
        self.button(a.edit_window,'Close').invoke(); a.undo(); self.assertEqual(length(a.objects[0]),1)
        self.assertFalse(self.errors)

    def test_every_object_editor(self):
        import cad_geometry as g
        shapes=[{'type':'circle','center':[0,0],'radius':1},g.arc_three([1,0],[0,1],[-1,0]),
                g.ellipse_box([0,0],[2,1]),g.regular_polygon([0,0],[1,0],6),
                {'type':'spline','points':[[0,0],[1,1],[2,0]],'method':'through','closed':False}]
        for shape in shapes:
            self.app.doc.add([shape]); self.app.edit_dialog(); self.root.update()
            self.assertNotIn('check entered',self.app.edit_length.get())
            self.button(self.app.edit_window,'Apply').invoke()
            self.button(self.app.edit_window,'Close').invoke()
        self.assertFalse(self.errors)

    def test_grid_dialog_and_file_round_trip(self):
        a=self.app; a.grid_dialog(); self.root.update()
        dlg=[w for w in self.root.winfo_children() if isinstance(w,tk.Toplevel)][0]
        entries=[w for f in dlg.winfo_children() for w in f.winfo_children() if w.winfo_class()=='TEntry']
        entries[0].delete(0,'end'); entries[0].insert(0,'1/2')
        entries[1].delete(0,'end'); entries[1].insert(0,'8')
        self.button(dlg,'OK').invoke(); self.assertEqual(a.grid_spacing,.5); self.assertEqual(a.grid_subdivisions,8)
        self.choose('Ovals','Center + axis + width')
        for p in [[0,0],[1,1],[-1,1]]: a.pick(p)
        with tempfile.TemporaryDirectory() as tmp:
            filename=str(Path(tmp)/'drawing.json'); a.path=filename; a.save()
            self.assertFalse(a.doc.dirty)
            with patch('draft.filedialog.askopenfilename',return_value=filename): a.open()
            self.assertEqual(a.objects[0]['type'],'ellipse'); self.assertEqual(a.grid_spacing,.5)
        self.assertFalse(self.errors)


if __name__=='__main__': unittest.main()
