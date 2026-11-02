"""Native clipboard snapshots and atomic, layer-aware placed copies."""
import copy
import json
import math
import cad_geometry as g
import cad_groups
from cad_document import Document

FORMAT='briancad-clipboard-1'


def snapshot(document,indices,near=None):
    ids=sorted(document.group_members(indices))
    if not ids:raise ValueError('Select objects to copy first.')
    objects=copy.deepcopy([document.objects[i] for i in ids]);used={o['layer'] for o in objects}
    layers=copy.deepcopy([l for l in document.layers if l['name'] in used])
    visible=[o for i,o in zip(ids,objects) if document.visible(i)] or objects
    candidates=[(list(p),label) for o in visible for p,label in g.anchors(o)]
    anchor,label=min(candidates,key=lambda item:g.dist(near,item[0])) if near is not None else candidates[0]
    return {'format':FORMAT,'anchor':anchor,'anchor_label':label,'drawing':{
        'format':'briancad-2','units':'inches','objects':objects,'layers':layers,'active_layer':objects[0]['layer']}}


def encode(data):return json.dumps(data,allow_nan=False)


def decode(text):
    try:
        if len(text)>64000000:raise ValueError('Clipboard data is too large.')
        data=json.loads(text)
        if not isinstance(data,dict) or data.get('format')!=FORMAT:raise ValueError()
        anchor=data.get('anchor')
        if not isinstance(anchor,list) or len(anchor)!=2 or not all(isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) and abs(v)<=1e7 for v in anchor):raise ValueError()
        document=Document.from_payload(data.get('drawing'))
        if not document.objects:raise ValueError()
        data={'format':FORMAT,'anchor':list(anchor),'anchor_label':str(data.get('anchor_label','anchor'))[:40],'drawing':document.payload()}
        return data
    except (ValueError,TypeError,KeyError,OverflowError) as ex:
        raise ValueError('The clipboard does not contain valid BrianCAD objects. Copy geometry in BrianCAD first.') from ex


def place(document,data,point):
    dx,dy=g.sub(point,data['anchor']);drawing=data['drawing']
    objects=cad_groups.remap([g.transform(o,'Move',dx=dx,dy=dy) for o in drawing['objects']])
    if len(document.objects)+len(objects)>100000:raise ValueError('Paste would exceed 100000 drawing objects.')
    layers=copy.deepcopy(document.layers);names={l['name'] for l in layers};used={o['layer'] for o in objects}
    for layer in drawing['layers']:
        if layer['name'] in used and layer['name'] not in names:
            layers.append(copy.deepcopy(layer));names.add(layer['name'])
    if len(layers)>1000:raise ValueError('Paste would exceed 1000 layers.')
    candidate=Document();candidate.layers=layers;candidate.active=document.active
    pending=[candidate.prepare(o) for o in objects]
    document.checkpoint();start=len(document.objects)
    document.layers=layers;document.objects.extend(pending);document.selected=set(range(start,len(document.objects)));document.point_selection={}
    return len(pending)
