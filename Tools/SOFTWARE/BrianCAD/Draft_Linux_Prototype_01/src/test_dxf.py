"""DXF read-back geometry, scope, styling and atomic file handling."""
import copy
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
try: import ezdxf
except ImportError: ezdxf=None
import cad_geometry as g
import cad_selection as s
from cad_document import Document
from cad_dxf import build_dxf, export_dxf, snapshot_drawing, require_ezdxf, DXFDependencyError, FLATTEN_TOLERANCE


class OptionalDXFTests(unittest.TestCase):
    def test_dependency_is_lazy_and_has_install_guidance(self):
        with patch.dict('sys.modules',{'ezdxf':None}):
            with self.assertRaises(DXFDependencyError) as error: require_ezdxf()
        self.assertIn('pip install -r',str(error.exception)); self.assertIn('requirements-dxf.txt',str(error.exception))


@unittest.skipUnless(ezdxf,'Install requirements-dxf.txt to test DXF export')
class DXFTests(unittest.TestCase):
    def make(self,objects):
        d=Document(); d.add(objects); return d

    def test_native_entities_units_styles_hidden_layers_and_readback(self):
        d=self.make([{'type':'line','a':[-2,3],'b':[4,-5],'color':'#2465d8','weight':.01,'pattern':'Dashed'},
                     {'type':'circle','center':[0,0],'radius':.5},
                     {'type':'polygon','points':[[0,0],[2,0],[1,1]],'closed':True},
                     {'type':'polygon','points':[[3,0],[5,0],[4,1]],'closed':False}])
        d.layers[-1]['visible']=False
        snapshot=snapshot_drawing(d); before=d.state(); history=len(d.history)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'drawing.dxf'; report=export_dxf(path,snapshot)
            out=ezdxf.readfile(path)
        self.assertEqual(report['objects'],4); self.assertEqual(report['entities'],4)
        self.assertEqual(out.units,1); self.assertEqual(out.dxfversion,'AC1032')
        audit=out.audit(); self.assertFalse(audit.errors); self.assertFalse(audit.fixes)
        entities=list(out.modelspace()); self.assertEqual([e.dxftype() for e in entities],['LINE','CIRCLE','LWPOLYLINE','LWPOLYLINE'])
        self.assertEqual(tuple(entities[0].dxf.start),(-2,3,0)); self.assertEqual(tuple(entities[0].dxf.end),(4,-5,0))
        self.assertEqual(entities[0].dxf.true_color,int('2465d8',16)); self.assertEqual(entities[0].dxf.lineweight,25)
        self.assertEqual(entities[0].dxf.linetype,'BRIANCAD_DASHED')
        self.assertAlmostEqual(entities[1].dxf.radius,.5)
        self.assertTrue(entities[2].closed); self.assertFalse(entities[3].closed)
        self.assertTrue(out.layers.get('Layer1').is_off())
        self.assertEqual(d.state(),before); self.assertEqual(len(d.history),history)

    def test_clockwise_wrapped_and_full_circle_arcs(self):
        for sweep in (math.pi/2,-math.pi/2,3*math.pi/2,-3*math.pi/2,g.TAU,-g.TAU):
            o={'type':'arc','center':[2,-3],'radius':2,'start':math.radians(350),'sweep':sweep}
            out,_=build_dxf(snapshot_drawing(self.make([o]))); entity=list(out.modelspace())[0]
            if abs(sweep)==g.TAU: self.assertEqual(entity.dxftype(),'CIRCLE'); continue
            actual=list(entity.vertices(entity.angles(17)))
            expected=[g.polar(o['center'],2,o['start']+sweep*i/16) for i in range(17)]
            if sweep<0: expected.reverse()
            for p,q in zip(actual,expected): self.assertLess(g.dist((p.x,p.y),q),1e-8)

    def test_ellipse_major_axis_swap_rotation_and_trim_sweep(self):
        for rx,ry in [(3,1),(1,3)]:
            for sweep in (.8,-.8,4.8,-4.8):
                o={'type':'ellipse','center':[2,-3],'rx':rx,'ry':ry,'angle':.7,'start':5.9,'sweep':sweep}
                out,_=build_dxf(snapshot_drawing(self.make([o]))); entity=list(out.modelspace())[0]
                self.assertLessEqual(entity.dxf.ratio,1)
                actual=list(entity.vertices(entity.params(17))); expected=[g.ellipse_point(o,i/16) for i in range(17)]
                if sweep<0: expected.reverse()
                for p,q in zip(actual,expected): self.assertLess(g.dist((p.x,p.y),q),1e-8)

    def test_exact_bezier_and_open_closed_through_splines(self):
        for method,closed,points in [('bezier',False,[[0,0],[1,2],[2,0]]),
                                     ('bezier',False,[[i,math.sin(i)] for i in range(11)]),
                                     ('through',False,[[0,0],[1,2],[2,0]]),
                                     ('through',True,[[0,0],[1,2],[2,0]])]:
            o={'type':'spline','method':method,'closed':closed,'points':points}
            out,report=build_dxf(snapshot_drawing(self.make([o]))); entities=list(out.modelspace())
            self.assertEqual(report['approximated'],0); spans=s._spline_spans(o)
            self.assertEqual(len(entities),len(spans))
            for e,span in zip(entities,spans):
                self.assertEqual(e.dxftype(),'SPLINE'); tool=e.construction_tool()
                for t in (0,.2,.5,.8,1): self.assertLess(g.dist(tuple(tool.point(t))[:2],s._bezier_point(span,t)),1e-8)
            self.assertFalse(out.audit().errors)
            if closed: self.assertLess(g.dist(tuple(entities[-1].construction_tool().point(1))[:2],tuple(entities[0].construction_tool().point(0))[:2]),1e-8)

    def test_high_degree_bezier_has_bounded_polyline_fallback(self):
        o={'type':'spline','method':'bezier','closed':False,'points':[[i/5,math.sin(i/3)] for i in range(16)]}
        out,report=build_dxf(snapshot_drawing(self.make([o]))); entity=list(out.modelspace())[0]
        self.assertEqual(report['approximated'],1); self.assertEqual(entity.dxftype(),'LWPOLYLINE')
        points=list(entity.get_points('xy'))
        for i in range(101):
            q=g.spline_point(o,i/100)
            error=min(g.dist(q,g.project(q,a,b,True)) for a,b in zip(points,points[1:]))
            self.assertLessEqual(error,FLATTEN_TOLERANCE*1.01)

    def test_selected_scope_partial_owners_snapshot_and_empty(self):
        d=self.make([{'type':'circle','center':[i*3,0],'radius':1} for i in range(3)])
        d.selected={0}; d.point_selection={1:{'radius'}}; snap=snapshot_drawing(d)
        d.objects[0]['center']=[999,999]; d.selected={2}
        out,report=build_dxf(snap,True); self.assertEqual(report['objects'],2)
        self.assertEqual([tuple(e.dxf.center) for e in out.modelspace()],[(0,0,0),(3,0,0)])
        self.assertEqual(build_dxf(snap)[1]['objects'],3)
        snap['selected']=[]
        with self.assertRaises(ValueError): build_dxf(snap,True)
        with self.assertRaises(ValueError): build_dxf({'objects':[],'layers':[],'selected':[]})

    def test_layer_sanitization_case_collisions_and_unicode(self):
        d=Document(); names=['Ramps/Upper','Ramps:Upper','FOO','foo','指示','A\nB','Defpoints']
        for i,name in enumerate(names):
            d.add_layer(name); d.add([{'type':'circle','center':[i*3,0],'radius':1,'layer':name}])
        out,report=build_dxf(snapshot_drawing(d)); mapping=report['layer_names']
        self.assertEqual(len({name.casefold() for name in mapping.values()}),len(names))
        self.assertEqual(mapping['指示'],'指示'); self.assertNotEqual(mapping['Ramps/Upper'],mapping['Ramps:Upper'])
        self.assertNotIn('\n',mapping['A\nB']); self.assertNotEqual(mapping['Defpoints'],'Defpoints')
        self.assertEqual([e.dxf.layer for e in out.modelspace()],[mapping[name] for name in names])
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'unicode.dxf'; out.saveas(path)
            self.assertFalse(ezdxf.readfile(path).audit().errors)

    def test_atomic_failures_preserve_destination_and_remove_temporary_files(self):
        d=self.make([{'type':'circle','center':[0,0],'radius':1}]); snap=snapshot_drawing(d)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'out.dxf'; path.write_text('original')
            with patch('cad_dxf.os.replace',side_effect=OSError('write blocked')):
                with self.assertRaises(OSError): export_dxf(path,snap)
            self.assertEqual(path.read_text(),'original'); self.assertEqual(list(Path(folder).iterdir()),[path])
            broken=copy.deepcopy(snap); broken['objects'][0]['radius']=-1
            with self.assertRaises(ValueError): export_dxf(path,broken)
            self.assertEqual(path.read_text(),'original')


if __name__=='__main__': unittest.main()
