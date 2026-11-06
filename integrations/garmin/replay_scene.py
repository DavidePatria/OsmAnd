"""Diagnostic conversion of an actual raw route capture to bounded watch scenes.

Not the production Java geometry implementation. Preserve explicit decision
anchors and incident-road identity; on overflow return an honestly limited view.
"""
import copy
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
from protocol.scene import validate
from route_probe import validate as validate_capture


def distance(a, b):
    y = math.radians(b[0]-a[0]); x = math.radians(b[1]-a[1])*math.cos(math.radians((a[0]+b[0])/2))
    return 6371000*math.hypot(x, y)


def simplify(points, fixed, tolerance=1.0):
    keep = set(fixed) | {0, len(points)-1}
    def reduce(a, b):
        ax, ay = points[a]; bx, by = points[b]; dx, dy = bx-ax, by-ay
        greatest, split = tolerance, None
        for i in range(a+1, b):
            px, py = points[i]; t = max(0, min(1, ((px-ax)*dx+(py-ay)*dy)/(dx*dx+dy*dy))) if dx or dy else 0
            error = math.hypot(px-ax-t*dx, py-ay-t*dy)
            if error > greatest: greatest, split = error, i
        if split is not None:
            keep.add(split); reduce(a, split); reduce(split, b)
    ordered = sorted(keep)
    for a, b in zip(ordered, ordered[1:]): reduce(a,b)
    ordered = sorted(keep)
    return [points[i] for i in ordered], {old: new for new, old in enumerate(ordered)}


def quantize(point):
    # Keep rounded boundary points inside the radius without changing anchors.
    x, y = (round(n*10) for n in point)
    while x*x+y*y > 2000*2000:
        if abs(x) >= abs(y): x -= 1 if x > 0 else -1
        else: y -= 1 if y > 0 else -1
    return [x,y]


def route_frame(capture, maneuver):
    locations=capture['locationsLatLon'];offset=capture['directions'][maneuver]['routePointOffset']
    cumulative = [0.0]
    for a,b in zip(locations,locations[1:]): cumulative.append(cumulative[-1]+distance(a,b))
    origin = locations[offset]
    approach = offset-1
    while approach > 0 and cumulative[offset]-cumulative[approach] < 30: approach -= 1
    def en(p):
        return (math.radians(p[1]-origin[1])*6371000*math.cos(math.radians(origin[0])), math.radians(p[0]-origin[0])*6371000)
    east,north = en(locations[approach]); bearing = math.atan2(-east,-north)
    def project(p):
        east,north=en(p);return (east*math.cos(bearing)-north*math.sin(bearing),east*math.sin(bearing)+north*math.cos(bearing))
    return cumulative,offset,project


def compile_scene(capture, maneuver, source_sha, radius_m=195):
    errors = validate_capture(capture)
    if errors: raise ValueError('; '.join(errors))
    if capture['status'] != 'captured': raise ValueError('truncated raw capture cannot establish branch coverage')
    locations, refs = capture['locationsLatLon'], capture['locationSegmentIds']
    directions = capture['directions']
    if type(maneuver) is not int or not 0 <= maneuver < len(directions):raise ValueError('original maneuver index out of range')
    direction = directions[maneuver]
    cumulative,offset,project=route_frame(capture,maneuver)
    indexes = [offset]
    if maneuver+1 < len(directions):
        nxt = directions[maneuver+1]['routePointOffset']
        if 0 < cumulative[nxt]-cumulative[offset] <= min(100,radius_m): indexes.append(nxt)
    anchors = [{'id':f'j{i}','point':quantize(project(locations[k])),'routeIndex':k} for i,k in enumerate(indexes)]
    first = next(i for i in range(offset+1) if cumulative[offset]-cumulative[i] <= radius_m)
    last = offset
    while last+1 < len(locations) and cumulative[last+1]-cumulative[offset] <= radius_m: last += 1
    raw = [project(p) for p in locations[first:last+1]]
    prefix=0
    if first>0:
        a,b=project(locations[first-1]),raw[0]
        fraction=(cumulative[offset]-radius_m-cumulative[first-1])/(cumulative[first]-cumulative[first-1])
        raw.insert(0,(a[0]+fraction*(b[0]-a[0]),a[1]+fraction*(b[1]-a[1])));prefix=1
    if last+1<len(locations):
        a,b=raw[-1],project(locations[last+1])
        fraction=(cumulative[offset]+radius_m-cumulative[last])/(cumulative[last+1]-cumulative[last])
        raw.append((a[0]+fraction*(b[0]-a[0]),a[1]+fraction*(b[1]-a[1])))
    selected, mapping = simplify(raw,{k-first+prefix for k in indexes})
    selected_path = {'id':'selected','role':'selected','points':[quantize(p) for p in selected],
                     'anchorRefs':[[a['id'],mapping[k-first+prefix]] for a,k in zip(anchors,indexes)]}
    scene = {'version':1,'session':'replay-'+source_sha[:16],'generation':1,'seq':1,'state':'active',
             'geometryMode':'routing_branches','reason':'routing data may omit roads','distanceM':120,
             'roadName':(direction.get('streetName') or '')[:80],'maneuver':direction['turn'],
             'radiusDm':round((radius_m+5)*10),'sourceAgeMs':0,'fixAgeMs':0,'anchors':anchors,'paths':[selected_path]}
    by_id={s['id']:s for s in capture['segments']}; branches=[]; limited=[]
    for anchor,k in zip(anchors,indexes):
        seen = set(); candidates=[]; selected_legs=set()
        for ref in dict.fromkeys([refs[max(0,k-1)],refs[k]]):
            segment=by_id[ref]; nodes={p[0]:p for p in segment['points']}
            matching=[p for p in segment['points'] if p[3:]==locations[k]]
            if len(matching)!=1:
                limited.append('ambiguous incident-road index');continue
            node=matching[0][0]
            def leg(road, start, step, stop):
                points={p[0]:p for p in road['points']}
                if start not in points or start+step not in points:return
                key=(road['roadId'],tuple(points[start][1:3]),tuple(points[start+step][1:3]))
                candidates.append((key,road,start,step,stop))
            # Known route roads provide physical continuations, including filtered travel directions.
            for step in (-1,1): leg(segment,node,step,0 if step<0 else segment['roadPointCount']-1)
            travel=1 if segment['endPointIndex']>segment['startPointIndex'] else -1
            if ref==refs[k] and node+travel in nodes:selected_legs.add((segment['roadId'],tuple(nodes[node][1:3]),tuple(nodes[node+travel][1:3])))
            if k>0 and ref==refs[k-1] and node-travel in nodes:selected_legs.add((segment['roadId'],tuple(nodes[node][1:3]),tuple(nodes[node-travel][1:3])))
            attached=next((a for a in segment['attachments'] if a['roadPointIndex']==node),None)
            if attached is None or attached['attachedStorage']!='available':limited.append('attached storage unavailable');continue
            for branch in attached['attached']:
                if branch.get('pointsTruncated'):limited.append('branch points truncated');continue
                pts={p[0]:p for p in branch['points']};start,end=branch['startPointIndex'],branch['endPointIndex']
                if start not in pts or pts[start][3:]!=locations[k]:limited.append('unmatched branch anchor');continue
                if start!=end:leg(branch,start,1 if end>start else -1,end)
        for key,road,start,step,stop in candidates:
            if key in selected_legs or key in seen:continue
            seen.add(key);pts={p[0]:p for p in road['points']};line=[];node=start
            while node in pts:
                point=project(pts[node][3:]);radius=math.hypot(*point)
                if radius>radius_m:
                    if line:
                        # End at the circle boundary along the current road edge.
                        a=line[-1];lo,hi=0.,1.
                        for _ in range(32):
                            mid=(lo+hi)/2;p=(a[0]+(point[0]-a[0])*mid,a[1]+(point[1]-a[1])*mid)
                            if math.hypot(*p)<=radius_m:lo=mid
                            else:hi=mid
                        line.append((a[0]+(point[0]-a[0])*lo,a[1]+(point[1]-a[1])*lo))
                    break
                line.append(point)
                if node==stop:break
                node+=step
            if len(line)<2:continue
            reduced,_=simplify(line,{0})
            branches.append({'id':f'b{len(branches)}','role':'branch','points':[quantize(p) for p in reduced],
                             'anchorRefs':[[anchor['id'],0]]})
    if limited or len(branches)+1>8 or any(len(p['points'])>24 for p in branches) or sum(len(p['points']) for p in branches)+len(selected)>96:
        scene['geometryMode']='route_only';scene['reason']=limited[0] if limited else 'branch capacity exceeded'
    else:scene['paths']+=branches
    if len(selected)>24:
        scene.update(geometryMode='unavailable',reason='selected-route capacity exceeded',paths=[],anchors=[])
    errors=validate(scene)
    if errors:raise ValueError('; '.join(errors))
    return scene


def clip_circle(points, radius):
    """Clip every edge, retaining entering/leaving and outside-to-outside edges.

    Separate fragments remain separate; never join across an out-of-view arc.
    """
    pieces=[];current=[]
    for a,b in zip(points,points[1:]):
        dx,dy=b[0]-a[0],b[1]-a[1];length2=dx*dx+dy*dy
        if length2==0:continue
        dot=a[0]*dx+a[1]*dy;disc=dot*dot-length2*(a[0]*a[0]+a[1]*a[1]-radius*radius)
        if disc<=0:
            if current:pieces.append(current);current=[]
            continue
        root=math.sqrt(disc);lo=max(0,(-dot-root)/length2);hi=min(1,(-dot+root)/length2)
        if lo>=hi:
            if current:pieces.append(current);current=[]
            continue
        start=(a[0]+lo*dx,a[1]+lo*dy);end=(a[0]+hi*dx,a[1]+hi*dy)
        if current and math.dist(current[-1],start)>1e-6:pieces.append(current);current=[]
        if not current:current=[start]
        current.append(end)
        if hi<1:pieces.append(current);current=[]
    if current:pieces.append(current)
    return pieces


NON_MOTOR_HIGHWAYS={'footway','cycleway','path','pedestrian','steps','bridleway','corridor','platform'}
MOTOR_ACCESS={'yes','permissive','designated','destination','delivery','customers','private','permit','agricultural','forestry','discouraged'}


def non_motor_reason(road):
    """Display filter, not a second router or a country-specific legal decision.

    More specific motorcycle permission overrides generic motor/vehicle/access
    restrictions. Restricted motor access remains visible. Unknown road classes
    and ordinary tracks stay visible; dashed map styling alone is not a filter.
    """
    for tag in ('motorcycle','motor_vehicle','vehicle','access'):
        value=road.get(tag)
        if value in ('no','dismount','use_sidepath'):return tag+'='+value
        if value in MOTOR_ACCESS:return None
    if road.get('highway') in NON_MOTOR_HIGHWAYS:return 'non-motor highway='+road['highway']
    return None


def add_map_context(scene, capture, maneuver, context):
    """Unfiltered map lines are context, NOT invented junction connectivity.

    Grade-separated scenes are explicitly limited until the renderer can show
    their ordering. No road is silently removed to meet the display budget.
    """
    _,_,project=route_frame(capture,maneuver)
    paths=[scene['paths'][0]] if scene['paths'] else []
    reason=None
    # Hold every shared map vertex while simplifying. Road lines may cross
    # without a shared vertex; projection alone never creates a connection.
    counts=Counter(tuple(p[:2]) for road in context['roads'] for p in road['points31LatLon'])
    shared={project(p[2:]) for road in context['roads'] for p in road['points31LatLon'] if counts[tuple(p[:2])]>1}
    for road in context['roads']:
        if non_motor_reason(road) is not None:continue
        pieces=clip_circle([project(p[2:]) for p in road['points31LatLon']],75)
        if not pieces:continue
        if road.get('layer') not in (None,'0') or road.get('bridge') not in (None,'no') or road.get('tunnel') not in (None,'no'):
            reason='grade-separated road context unsupported';break
        for piece in pieces:
            reduced,_=simplify(piece,{i for i,p in enumerate(piece) if p in shared})
            points=[quantize(p) for p in reduced]
            if len(set(map(tuple,points)))<2:continue
            paths.append({'id':'c'+str(len(paths)),'role':'context','points':points,'anchorRefs':[]})
    if not paths:return scene
    candidate=copy.deepcopy(scene)
    candidate.update(geometryMode='map_context',reason='motorcycle road context; intersections do not imply connectivity',paths=paths)
    if reason is None and validate(candidate):reason='map context capacity exceeded'
    if len(paths)==1 and reason is None:reason='no local map roads available'
    if reason:
        scene.update(geometryMode='route_only',reason=reason,paths=scene['paths'][:1])
        return scene
    return candidate


def recorded(capture_path, maneuver, context_path=None):
    raw=Path(capture_path).read_bytes();sha=hashlib.sha256(raw).hexdigest()
    capture=json.loads(raw);scene=compile_scene(capture,maneuver,sha,75 if context_path else 195)
    result={'provenance':{'kind':'actual_osmand_capture','captureSha256':sha,'applicationMode':capture['applicationMode'],
                          'maneuverIndex':maneuver,'routePointOffset':capture['directions'][maneuver]['routePointOffset'],
                          'conversion':'diagnostic Python projection/simplification; production uses JunctionCompiler'},'scene':scene}
    if context_path:
        context_raw=Path(context_path).read_bytes();context=json.loads(context_raw)
        if (context.get('version')!=1 or context.get('kind')!='same_obf_unfiltered_routing_roads'
            or context.get('captureSha256')!=sha or context.get('maneuver')!=maneuver or context.get('truncated') is not False):
            raise ValueError('map context must be a complete query of this exact capture and maneuver')
        if context.get('accessTagsVersion')!=1:
            raise ValueError('refresh road context with motorcycle/vehicle access tags before filtering')
        result['scene']=add_map_context(scene,capture,maneuver,context)
        reasons=Counter(non_motor_reason(r) for r in context['roads'])
        result['provenance'].update(contextSha256=hashlib.sha256(context_raw).hexdigest(),mapSha256=context['mapSha256'],
                                    displayFilter='motorcycle-relevant roads; explicit access overrides non-motor class defaults',
                                    omittedRoadsByReason={k:v for k,v in reasons.items() if k is not None})
    return result
