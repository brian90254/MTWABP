"""Headless checks for geometry and editor state; run python3 check_geometry.py."""
import copy
import json
import math
from draft import Draft, anchors, distance, hit_distance, validate

class Value:
    def __init__(self,v): self.v=v
    def get(self): return self.v

line={'type':'line','a':[-1,0],'b':[1,0],'color':'#198548'}
circle={'type':'circle','center':[0,0],'radius':.5,'color':'#2465d8'}
assert distance(line['a'],line['b'])==2
assert circle['radius']*2==1
assert hit_distance([0,.2],line)==.2
assert hit_distance([0,.5],circle)==0
assert ([0.,0.],'midpoint') in anchors(line)
assert len(anchors(circle))==5
objects=[line,circle]
assert validate(json.loads(json.dumps({'format':'draft-prototype-1','objects':objects})))==objects
for bad in [float('nan'),float('inf'),-1]:
    obj=copy.deepcopy(circle); obj['radius']=bad
    try: validate({'format':'draft-prototype-1','objects':[obj]})
    except ValueError: pass
    else: raise AssertionError('Bad radius accepted')
a=Draft.__new__(Draft)
a.objects=copy.deepcopy(objects); a.history=[]; a.future=[]; a.selected=0
a.scale=100; a.origin=[400,300]; a.snap=Value(True); a.tool=Value('Line'); a.start=None
a.grid_snap=Value(False); a.grid_spacing=1.; a.grid_subdivisions=4
a.draw=lambda:None
for p in [[-1,0],[.123,-.789],[1000,2000]]:
    assert distance(a.world(*a.screen(p)),p)<1e-10
assert a.snap_point([-.98,.01])==([-1,0],'endpoint')
a.start=[2,2]
assert a.snap_point([2.01,4])==([2,4],'vertical')
a.move(3,4)
assert a.objects[0]['a']==[2,4] and a.objects[0]['b']==[4,4]
a.undo(); assert a.objects==objects
a.redo(); assert a.objects[0]['a']==[2,4]
a.fields={k:Value(v) for k,v in {'x':'-1','y':'0','length':'2','angle':'0','diameter':'1'}.items()}
a.color=Value('#198548');a.exact()
assert a.objects[-1]==line
print('PASS: known geometry, hit testing, snap anchors, JSON validation, coordinate transforms, snapping, move, undo/redo, exact line entry')
