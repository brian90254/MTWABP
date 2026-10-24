import copy
import json
import math
import unittest
import cad_geometry as g
from cad_tools import construct
from cad_document import Document


class ConstructionTests(unittest.TestCase):
    def close(self,a,b):
        self.assertEqual(len(a),len(b))
        for x,y in zip(a,b): self.assertAlmostEqual(x,y,places=8)

    def test_line_methods(self):
        pts=[[0,0],[2,0]]
        for m in ['Two points','Connected points']:
            self.assertEqual(g.length(construct(m,pts,{})),2)
        line={'type':'line','a':[0,0],'b':[2,0]}
        o=construct('Offset from line',pts,{'offset':-.25},[line]); self.close(o['a'],[0,-.25]); self.close(o['b'],[2,-.25])
        with self.assertRaises(ValueError): construct('Offset from line',pts,{'offset':.2})

    def test_arc_center_and_projection(self):
        o=construct('Center + start + end',[[0,0],[1,0],[0,5]],{})
        self.assertAlmostEqual(o['sweep'],math.pi/2); self.assertAlmostEqual(g.length(o),math.pi/2)
        self.close(g.path(o)[-1],[0,1])
        o=construct('Center + start + end',[[0,0],[1,0],[0,1]],{},clockwise=True)
        self.assertAlmostEqual(o['sweep'],-3*math.pi/2)

    def test_three_point_arc_wrap_and_clockwise(self):
        for degrees in [(350,0,10),(10,0,350),(0,180,270)]:
            pts=[g.polar([2,-3],4,math.radians(a)) for a in degrees]
            o=construct('Three-point arc',pts,{})
            self.close(o['center'],[2,-3]); self.assertAlmostEqual(o['radius'],4)
            self.close(g.path(o)[0],pts[0]); self.close(g.path(o)[-1],pts[2])
            self.assertLess(g.hit_distance(pts[1],o),1e-8)

    def test_tangent_arc(self):
        for end in [[1,1],[1,-1],[-1,1],[-1,-1]]:
            for clockwise in [False,True]:
                o=construct('Start tangent + end',[[0,0],[2,0],end],{},clockwise=clockwise)
                self.close(o['center'],[0,end[1]]); self.close(g.path(o)[-1],end)
                self.close(g.path(o)[0],[0,0])
                self.assertEqual(o['sweep']>0,end[1]>0)
                # The directed tangent at the start points toward the second click,
                # including endpoints requiring an arc greater than 180 degrees.
                radial=g.sub([0,0],o['center'])
                tangent=g.mul(g.normal(radial),1 if o['sweep']>0 else -1)
                self.close(g.unit(tangent),[1,0])
        with self.assertRaises(ValueError): construct('Start tangent + end',[[0,0],[0,0],[1,1]],{})
        with self.assertRaises(ValueError): construct('Start tangent + end',[[0,0],[1,0],[2,0]],{})
        with self.assertRaises(ValueError): construct('Start tangent + end',[[0,0],[1,0],[0,0]],{})

    def test_rotated_translated_tangent_arc(self):
        start=[3,-4]; tangent=[3,-2]; end=[2,-3]
        o=construct('Start tangent + end',[start,tangent,end],{})
        self.close(o['center'],[2,-4]); self.close(g.path(o)[-1],end)
        self.assertGreater(o['sweep'],0)

    def test_circle_methods(self):
        o=construct('Center + diameter',[[2,3],[0,0]],{'diameter':1})
        self.close(o['center'],[2,3]); self.assertEqual(o['radius'],.5)
        o=construct('Diameter endpoints',[[-1,0],[1,0]],{}); self.close(o['center'],[0,0]); self.assertEqual(o['radius'],1)
        o=construct('Three-point circle',[[1,0],[0,1],[-1,0]],{}); self.close(o['center'],[0,0]); self.assertEqual(o['radius'],1)
        with self.assertRaises(ValueError): g.circle_three([0,0],[1,0],[2,0])

    def test_tangent_circle_geometry(self):
        a={'a':[-3,0],'b':[3,0]}; b={'a':[0,-3],'b':[0,3]}
        o=construct('Two tangent lines',[[1,0],[0,1]],{},[a,b])
        self.close(o['center'],[1,1]); self.assertEqual(o['radius'],1)
        for line in [a,b]: self.assertAlmostEqual(g.dist(o['center'],g.project(o['center'],line['a'],line['b'])),o['radius'])
        parallel={'a':[-3,2],'b':[3,2]}
        o=g.tangent_circle([1,0],a,parallel,[1,2]); self.close(o['center'],[1,1]); self.assertEqual(o['radius'],1)
        with self.assertRaises(ValueError): g.tangent_circle([1,0],a,a,[2,0])

    def test_ellipse_methods(self):
        cases=[('Center + corner',[[0,0],[2,1]],(2,1)),('Opposite corners',[[-2,-1],[2,1]],(2,1)),
               ('Center + axis + width',[[0,0],[0,2],[1,0]],(2,1)),('Axis endpoints + width',[[0,-2],[0,2],[1,0]],(2,1))]
        for m,pts,radii in cases:
            o=construct(m,pts,{})
            self.close(o['center'],[0,0]); self.close([o['rx'],o['ry']],radii)
            self.assertAlmostEqual(g.dist(g.anchors(o)[1][0],[0,0]),2)
        with self.assertRaises(ValueError): g.ellipse_box([0,0],[0,1])

    def test_polygons(self):
        for method in ['Rectangle corners','Rectangle center']:
            o=construct(method,[[0,0],[2,1]],{})
            self.assertEqual(len(o['points']),4)
        ins=construct('Inscribed polygon',[[0,0],[1,0]],{'sides':6})
        self.assertTrue(all(abs(g.dist(p,[0,0])-1)<1e-8 for p in ins['points']))
        cir=construct('Circumscribed polygon',[[0,0],[1,0]],{'sides':6})
        for a,b in zip(cir['points'],cir['points'][1:]+cir['points'][:1]):
            self.assertAlmostEqual(g.dist([0,0],g.project([0,0],a,b)),1)
        for n in [0,2,4.5,201]:
            with self.assertRaises(ValueError): g.regular_polygon([0,0],[1,0],n)

    def test_splines_fit_and_control(self):
        pts=[[0,0],[1,2],[2,0],[3,1]]
        o=construct('Through points',pts,{})
        for i,p in enumerate(pts): self.close(g.spline_point(o,i/3),p)
        bez=construct('Bezier controls',pts,{})
        self.close(g.spline_point(bez,0),pts[0]); self.close(g.spline_point(bez,1),pts[-1])
        self.close(g.spline_point(bez,.5),[1.5,.875])
        closed=construct('Closed through points',pts,{})
        self.close(g.path(closed)[0],g.path(closed)[-1])
        with self.assertRaises(ValueError): construct('Closed through points',pts[:2],{})

    def test_transform_preserves_analytic_shapes(self):
        arc=g.arc_three([1,0],[0,1],[-1,0])
        reflected=g.transform(arc,'Mirror',angle=0)
        self.assertAlmostEqual(reflected['sweep'],-arc['sweep'])
        for a,b in zip(g.path(arc),g.path(reflected)): self.close([a[0],-a[1]],b)
        e=g.ellipse_axes([1,2],[2,3],[0,3])
        rotated=g.transform(e,'Rotate',pivot=[1,2],angle=90)
        self.close(rotated['center'],[1,2]); self.assertAlmostEqual(rotated['angle'],e['angle']+math.pi/2)
        scaled=g.transform(e,'Scale',pivot=[1,2],factor=3)
        self.assertAlmostEqual(scaled['rx'],e['rx']*3)
        with self.assertRaises(ValueError): g.transform(e,'Scale',factor=0)

    def test_lengths_and_arc_hit(self):
        self.assertAlmostEqual(g.length({'type':'circle','center':[0,0],'radius':.5}),math.pi)
        e={'type':'ellipse','center':[0,0],'rx':1,'ry':1,'angle':0}
        self.assertAlmostEqual(g.length(e),2*math.pi,places=4)
        arc=g.arc_center([0,0],[1,0],[0,1])
        self.assertGreater(g.hit_distance([-1,0],arc),1)
        self.assertAlmostEqual(g.hit_distance([2**-.5,2**-.5],arc),0)


class DocumentTests(unittest.TestCase):
    def setUp(self):
        self.d=Document()
        self.d.add([{'type':'line','a':[0,0],'b':[1,0]}, {'type':'circle','center':[2,0],'radius':.5}])

    def test_layers_and_undo(self):
        d=self.d; d.add_layer('Ramps'); d.set_layer('Ramps')
        d.add([{'type':'line','a':[2,2],'b':[3,3]}]); self.assertEqual(d.objects[-1]['layer'],'Ramps')
        d.toggle_layer('Ramps'); self.assertFalse(d.visible(2)); self.assertFalse(d.selected)
        d.undo(); self.assertTrue(d.visible(2))
        d.rename_layer('Ramps','Wireforms'); self.assertEqual(d.objects[-1]['layer'],'Wireforms')
        d.delete_layer('Wireforms'); self.assertEqual(d.objects[-1]['layer'],'Constraints')
        d.undo(); self.assertEqual(d.objects[-1]['layer'],'Wireforms')
        d.redo(); self.assertEqual(d.active,'Constraints')

    def test_group_transform_copy_lock_and_atomic_undo(self):
        d=self.d; before=d.state(); d.selected={0,1}
        d.transform_selected('Move',dx=1,dy=2); self.assertEqual(d.objects[0]['a'],[1,2]); self.assertEqual(d.objects[1]['center'],[3,2])
        d.undo(); self.assertEqual(d.state(),before)
        d.selected={0,1}; d.transform_selected('Rotate',pivot=[0,0],angle=90,copy_objects=True)
        self.assertEqual(len(d.objects),4); self.assertEqual(d.selected,{2,3})
        d.undo(); self.assertEqual(d.state(),before)
        d.objects[0]['locked']=True; d.selected={0,1}; d.delete_selected(); self.assertEqual(len(d.objects),1)
        self.assertTrue(d.objects[0]['locked'])

    def test_edit_is_validated_before_checkpoint(self):
        d=self.d; before=d.state(); history=len(d.history)
        bad=copy.deepcopy(d.objects[1]); bad['radius']=-1
        with self.assertRaises(ValueError): d.edit(1,bad)
        self.assertEqual(d.state(),before); self.assertEqual(len(d.history),history)
        obj=copy.deepcopy(d.objects[0]); obj['b']=[4,3]; d.edit(0,obj)
        self.assertEqual(g.length(d.objects[0]),5)
        d.undo(); self.assertEqual(d.state(),before)

    def test_old_and_new_file_round_trip(self):
        d=self.d; d.add_layer('Hidden'); d.toggle_layer('Hidden'); d.grid_spacing=.5; d.grid_subdivisions=8
        shapes=[g.arc_three([1,0],[0,1],[-1,0]),g.ellipse_box([0,0],[2,1]),
                g.regular_polygon([0,0],[1,0],5),construct('Through points',[[0,0],[1,2],[3,0]],{})]
        d.add(shapes)
        loaded=Document.from_payload(json.loads(json.dumps(d.payload())))
        self.assertEqual(loaded.state(),d.state()); self.assertFalse(loaded.dirty)
        legacy={'format':'draft-prototype-1','objects':[{'type':'line','a':[-1,0],'b':[1,0],'color':'#198548'}]}
        old=Document.from_payload(legacy); self.assertEqual(old.objects[0]['layer'],'Layer1')
        self.assertEqual(g.length(old.objects[0]),2)

    def test_bad_files(self):
        payload=self.d.payload()
        for change in [{'active_layer':'missing'},{'layers':[]},{'grid':{'spacing':0,'subdivisions':4}},
                       {'objects':[{'type':'circle','center':[0,0],'radius':float('nan')}]},
                       {'objects':[{'type':'line','a':[0,0],'b':[0,0]}]}]:
            bad=copy.deepcopy(payload); bad.update(change)
            with self.assertRaises(ValueError): Document.from_payload(bad)


if __name__=='__main__': unittest.main()
