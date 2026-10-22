"""Known-dimension regression checks; run python3 check_geometry.py."""
import json
import math
from cad_geometry import dist, anchors, hit_distance, length
from cad_document import Document

line={'type':'line','a':[-1,0],'b':[1,0],'color':'#198548'}
circle={'type':'circle','center':[0,0],'radius':.5,'color':'#2465d8'}
assert dist(line['a'],line['b'])==2
assert length(circle)==math.pi
assert hit_distance([0,.2],line)==.2
assert hit_distance([0,.5],circle)==0
assert ([0.,0.],'midpoint') in anchors(line)
assert len(anchors(circle))==5
d=Document(); d.add([line,circle]); original=d.state()
d.selected={0}; d.transform_selected('Move',dx=3,dy=4)
assert d.objects[0]['a']==[2,4] and d.objects[0]['b']==[4,4]
d.undo(); assert d.state()==original
d.redo(); assert d.objects[0]['a']==[2,4]
assert Document.from_payload(json.loads(json.dumps(d.payload()))).state()==d.state()
print('PASS: known dimensions, hit tests, anchors, move, undo/redo, JSON round trip')
