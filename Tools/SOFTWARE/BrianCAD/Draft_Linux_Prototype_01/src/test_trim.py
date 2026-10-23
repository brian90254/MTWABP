"""Exact trim intervals, finite boundaries, style preservation and atomic history."""
import math
import unittest
import cad_geometry as g
from cad_trim import intersections, trim
from cad_document import Document


def line(a,b): return {'type':'line','a':a,'b':b}
def circle(c=(0,0),r=1): return {'type':'circle','center':list(c),'radius':r}
def arc(start,sweep): return dict(circle(),type='arc',start=start,sweep=sweep)


class TrimTests(unittest.TestCase):
    def test_line_divides_circle_click_either_half(self):
        boundary=line([0,-2],[0,2])
        for click,kept in [([1,0],[-1,0]),([-1,0],[1,0])]:
            result=trim(circle(),[boundary],click)
            self.assertEqual(len(result),1); o=result[0]
            self.assertEqual(o['type'],'arc'); self.assertAlmostEqual(o['sweep'],math.pi)
            self.assertAlmostEqual(g.hit_distance(kept,o),0)
            self.assertGreater(g.hit_distance(click,o),1)

    def test_circle_cuts_line_middle_and_each_outside(self):
        target=line([-3,0],[3,0])
        pieces=trim(target,[circle()],[0,0])
        self.assertEqual([(o['a'],o['b']) for o in pieces], [([-3,0],[-1,0]),([1,0],[3,0])])
        for click,endpoints in [([-2,0],([-1,0],[3,0])),([2,0],([-3,0],[1,0]))]:
            result=trim(target,[circle()],click)
            self.assertEqual(len(result),1)
            self.assertEqual((result[0]['a'],result[0]['b']),endpoints)

    def test_multiple_boundaries_remove_only_clicked_interval(self):
        boundaries=[line([x,-1],[x,1]) for x in (-1,1)]
        result=trim(line([-3,0],[3,0]),boundaries,[0,0])
        self.assertEqual(len(result),2)
        self.assertEqual(result[0]['b'],[-1,0]); self.assertEqual(result[1]['a'],[1,0])
        # Cutting at an existing cut is deterministic and removes the next interval.
        self.assertEqual(trim(line([-3,0],[3,0]),boundaries,[-1,0]),result)

    def test_finite_arc_boundaries_and_clockwise_target(self):
        upper=arc(0,math.pi)
        self.assertEqual(intersections(line([-2,-.5],[2,-.5]),upper),[])
        self.assertEqual(len(intersections(line([-2,.5],[2,.5]),upper)),2)
        target=arc(math.pi,-math.pi); boundary=line([0,-2],[0,2])
        kept=trim(target,[boundary],[-.7,.7])[0]
        self.assertLess(kept['sweep'],0)
        self.assertAlmostEqual(abs(kept['sweep']),math.pi/2)
        self.assertAlmostEqual(g.hit_distance([math.sqrt(.5),math.sqrt(.5)],kept),0)
        # Boundary arc excludes the lower circle intersection.
        pieces=trim(line([-2,.5],[2,.5]),[upper],[0,.5])
        self.assertEqual(len(pieces),2)

    def test_circle_circle_crossings_and_wrap_interval(self):
        target=circle(); boundary=circle((1,0))
        self.assertEqual(len(intersections(target,boundary)),2)
        kept=trim(target,[boundary],[1,0])[0]
        self.assertAlmostEqual(kept['sweep'],4*math.pi/3)
        self.assertAlmostEqual(g.hit_distance([-1,0],kept),0)
        opposite=trim(target,[boundary],[-1,0])[0]
        self.assertAlmostEqual(opposite['sweep'],2*math.pi/3)
        self.assertAlmostEqual(g.hit_distance([1,0],opposite),0)

    def test_noop_tangent_coincident_and_finite_nonintersection(self):
        for a,b in [(circle(),line([-2,1],[2,1])),(circle(),circle((2,0))),
                    (circle(),circle()),(circle(),line([0,2],[0,3])),
                    (line([0,0],[1,0]),line([0,1],[1,1])),
                    (line([0,0],[1,0]),line([1,-1],[1,1]))]:
            with self.assertRaises(ValueError): trim(a,[b],[0,0])
        with self.assertRaises(ValueError): trim(circle(),[line([0,0],[0,2])],[1,0])

    def test_polygon_as_boundary_deduplicates_corner_crossings(self):
        box={'type':'polygon','points':[[-1,-1],[1,-1],[1,1],[-1,1]]}
        result=trim(line([-2,-2],[2,2]),[box],[0,0])
        self.assertEqual(len(result),2)
        self.assertEqual(result[0]['b'],[-1,-1]); self.assertEqual(result[1]['a'],[1,1])

    def test_document_atomic_history_style_and_boundary_selection_remap(self):
        d=Document(); d.add([line([-3,0],[3,0]),circle()]); d.selected={1}
        d.objects[0].update(color='#2465d8',pattern='Dashed',weight=.03,controls=True)
        before=d.state(); n=len(d.history); boundary=d.objects[1]
        pieces=d.trim_object(0,{1},[0,0])
        self.assertEqual(len(d.history),n+1); self.assertEqual(d.selected,{2})
        self.assertIs(d.objects[2],boundary)
        for o in pieces:
            for key in ('layer','color','pattern','weight','controls'):
                self.assertEqual(o[key],before['objects'][0][key])
        after=d.state(); self.assertEqual(Document.from_payload(d.payload()).state(),after)
        d.undo(); self.assertEqual(d.state(),before)
        d.redo(); self.assertEqual(d.state(),after)

    def test_failures_never_mutate_or_add_history(self):
        d=Document(); d.add([circle(),line([0,2],[0,3])]); d.selected={1}
        before=d.state(); n=len(d.history)
        with self.assertRaises(ValueError): d.trim_object(0,{1},[1,0])
        self.assertEqual(d.state(),before); self.assertEqual(len(d.history),n)
        d.objects[0]['locked']=True
        with self.assertRaises(ValueError): d.trim_object(0,{1},[1,0])
        with self.assertRaises(ValueError): d.trim_object(1,{1},[0,2])
        with self.assertRaises(ValueError): d.trim_object(0,set(),[1,0])


if __name__=='__main__': unittest.main()
