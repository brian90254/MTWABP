"""Grid and angle regressions. Run: python3 -m unittest -v test_grid."""
import math
import random
import unittest
from draft import (Draft, alignment_candidates, distance, grid_candidates,
                   grid_positions, grid_values, line_grid_candidates)


class Value:
    def __init__(self, v): self.v = v
    def get(self): return self.v
    def set(self, value): self.v = value


def editor():
    app = Draft.__new__(Draft)
    app.objects = []
    app.selected = None
    app.start = None
    app.scale = 100
    app.grid_spacing = 1.
    app.grid_subdivisions = 4
    app.snap = Value(True)
    app.grid_snap = Value(True)
    app.tool = Value('Line')
    return app


class GridTests(unittest.TestCase):
    def assertPoint(self, actual, expected):
        for a, b in zip(actual, expected): self.assertAlmostEqual(a, b, places=10)

    def test_preferences(self):
        self.assertEqual(grid_values('1"', '4'), (1., 4))
        self.assertEqual(grid_values('1/2', '8'), (.5, 8))
        for spacing, count in [('0',4), ('nan',4), ('inf',4), ('1/0',4),
                               (-1,4), ('',4), (1,0), (1,2.5), (1,101), (1,'nan')]:
            with self.assertRaises(ValueError): grid_values(spacing, count)

    def test_grid_intersection_negative_and_positive(self):
        app = editor()
        for p, q in [([.27,.28],[.25,.25]), ([-.27,-.28],[-.25,-.25])]:
            point, label = app.snap_point(p)
            self.assertPoint(point, q); self.assertEqual(label, 'grid intersection')

    def test_grid_lines_without_forcing_other_coordinate(self):
        app = editor(); app.scale = 200
        for p, q, label in [([.26,.37],[.25,.37],'vertical grid line'),
                            ([.37,.26],[.37,.25],'horizontal grid line')]:
            point, name = app.snap_point(p)
            self.assertPoint(point,q); self.assertEqual(name,label)

    def test_changed_spacing_and_one_subdivision(self):
        app=editor(); app.grid_spacing=2.; app.grid_subdivisions=4
        self.assertPoint(app.snap_point([.52,.51])[0],[.5,.5])
        app.grid_subdivisions=1
        self.assertPoint(app.snap_point([2.02,2.01])[0],[2,2])

    def test_screen_pixel_tolerance(self):
        app=editor(); app.snap=Value(False)
        for scale in [40,100,1000]:
            app.scale=scale
            point,label=app.snap_point([1+4/scale,1+4/scale])
            self.assertPoint(point,[1,1]); self.assertEqual(label,'grid intersection')
        app.scale=100
        self.assertEqual(app.snap_point([.11,.11]),([.11,.11],''))

    def test_segment_grid_crossings(self):
        obj={'type':'line','a':[0,0],'b':[2,1]}
        candidates=line_grid_candidates([.26,.13],obj,.25)
        self.assertPoint(min(candidates,key=lambda c:distance(c[0],[.26,.13]))[0],[.25,.125])
        app=editor(); app.objects=[obj]
        point,label=app.snap_point([.26,.13])
        self.assertPoint(point,[.25,.125]); self.assertEqual(label,'line/grid intersection')

    def test_crossings_clipped_and_parallel(self):
        for a,b in [([.3,.31],[.4,.41]),([.4,.41],[.3,.31])]:
            self.assertEqual(line_grid_candidates([.5,.5],{'a':a,'b':b},.25),[])
        self.assertEqual(line_grid_candidates([1,1],{'a':[0,0],'b':[0,0]},.25),[])
        for a,b in [([.12,.25],[1.12,.25]),([.25,.12],[.25,1.12])]:
            points=line_grid_candidates([.51,.51],{'a':a,'b':b},.25)
            self.assertEqual(len(points),1)
            self.assertPoint(points[0][0],[.5,.25] if a[1]==.25 else [.25,.5])

    def test_crossings_against_independent_enumeration(self):
        rng=random.Random(19)
        for _ in range(200):
            a=[rng.uniform(-2,2) for _ in range(2)]
            b=[rng.uniform(-2,2) for _ in range(2)]
            p=[rng.uniform(-3,3) for _ in range(2)]
            exact=[]
            for axis in (0,1):
                for k in range(-8,9):
                    t=(k*.25-a[axis])/(b[axis]-a[axis])
                    if 0<=t<=1: exact.append([a[i]+t*(b[i]-a[i]) for i in (0,1)])
            got=line_grid_candidates(p,{'a':a,'b':b},.25)
            if exact:
                self.assertAlmostEqual(min(distance(p,q) for q in exact),min(distance(p,q) for q,_ in got),places=10)
            else: self.assertFalse(got)

    def test_object_anchor_priority(self):
        app=editor()
        app.objects=[{'type':'line','a':[.27,.28],'b':[2,1]}]
        self.assertEqual(app.snap_point([.27,.28]),([.27,.28],'endpoint'))

    def test_all_eight_angle_directions(self):
        app=editor(); app.grid_snap=Value(False); app.start=[.37,-.13]
        for degrees in range(0,360,45):
            angle=math.radians(degrees)
            target=[app.start[0]+2*math.cos(angle),app.start[1]+2*math.sin(angle)]
            p=[target[0]-.02*math.sin(angle),target[1]+.02*math.cos(angle)]
            point,label=app.snap_point(p)
            self.assertPoint(point,target)
            self.assertIn(label,['horizontal','vertical','45°','135°'])

    def test_angles_use_start_and_tolerance(self):
        app=editor(); app.start=[.37,-.13]; app.grid_snap=Value(False)
        p=[1.37,.97]; point,label=app.snap_point(p)
        self.assertPoint(point,[1.42,.92]); self.assertEqual(label,'45°')
        self.assertEqual(app.snap_point([1.37,.67]),([1.37,.67],''))
        app.start=None
        self.assertEqual(app.snap_point(p),(p,''))

    def test_toggles_and_move_excludes_self(self):
        app=editor(); app.snap=Value(False); app.grid_snap=Value(False)
        self.assertEqual(app.snap_point([.26,.27]),([.26,.27],''))
        app.grid_snap=Value(True)
        self.assertEqual(app.snap_point([.26,.27])[1],'grid intersection')
        app.tool=Value('Move'); app.selected=0
        app.objects=[{'type':'line','a':[.26,.27],'b':[2,1]}]
        app.snap=Value(True)
        self.assertEqual(app.snap_point([.26,.27])[1],'grid intersection')

    def test_dense_grid_is_bounded_and_not_rescaled(self):
        self.assertEqual(list(grid_positions(-1e8,1e8,.000001,.01,8)),[])
        self.assertEqual(list(grid_positions(-1,1,.25,100,8)),list(range(-4,5)))
        points=line_grid_candidates([123,456],{'a':[-1e8,-1e8],'b':[1e8,1e8]},1e-8)
        self.assertLessEqual(len(points),2)
        self.assertEqual(len(grid_candidates([123,456],1e-8)),3)

    def test_grid_rendering_uses_configured_spacing(self):
        class Canvas:
            def __init__(self): self.lines = []
            def delete(self, tag): self.lines.clear()
            def winfo_width(self): return 500
            def winfo_height(self): return 400
            def create_line(self, *coords, **opts): self.lines.append((coords, opts))
            def create_text(self, *args, **kwargs): pass
        class Root:
            def title(self, text): pass
        app=editor(); app.canvas=Canvas(); app.root=Root(); app.origin=[250,200]
        app.grid=Value(True); app.status=Value(''); app.mouse=None; app.marker=None; app.saved=[]
        app.draw()
        vertical=[(coords[0],opts['fill']) for coords,opts in app.canvas.lines
                  if coords[0]==coords[2] and coords[1]==0 and coords[3]==400]
        self.assertIn((350.,'#bcc8d5'),vertical)  # major: one inch at 100 px/in
        self.assertIn((275.,'#e4e9ef'),vertical)  # minor: one quarter inch
        app.scale=.01; app.draw()
        self.assertEqual(len(app.canvas.lines),2)  # axes only; no dense loop
        self.assertIn('dense lines hidden', app.status.get())


if __name__=='__main__': unittest.main()
