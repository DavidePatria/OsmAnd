#!/usr/bin/env python3
"""Review ACTUAL bridge-decoded Android scenes; no desktop geometry conversion.

Requires matching native route identity/indexes. Previews use approximate fonts,
not simulator screenshots. Inputs/outputs containing personal data stay in build/.
"""
import argparse
import hashlib
import html
import json
from pathlib import Path
import statistics
import sys

sys.dont_write_bytecode=True
from preview import watch_svg, png
from protocol.scene import validate


def geometry_key(scene):
    return json.dumps({k:scene[k] for k in ('geometryMode','anchors','paths','roadName','maneuver','radiusDm')},sort_keys=True,separators=(',',':'))


def write_trace(samples, out, start=0, count=32):
    out.mkdir(parents=True,exist_ok=True)
    (out/'actual-trace.json').unlink(missing_ok=True)
    if type(start) is not int or start<0 or type(count) is not int or not 1<=count<=64:
        raise ValueError('trace needs a nonnegative start and 1..64 frames')
    rows=[json.loads(line) for line in samples.read_text().splitlines()][start:start+count]
    if not rows:raise ValueError('no samples in this trace window')
    first=rows[0]['api']['receivedElapsedMs'];frames=[]
    for row in rows:
        api=row['api']
        if api.get('status')!='decoded' or validate(api.get('scene')):raise ValueError('trace contains unavailable or invalid API evidence')
        at=api['receivedElapsedMs']-first
        if type(at) is not int or not 0<=at<=300_000 or (frames and at<=frames[-1]['atMs']):raise ValueError('invalid trace time order/duration')
        frames.append({'atMs':at,'scene':api['scene']})
    value={'provenance':{'kind':'actual_osmand_capture','captureSha256':hashlib.sha256(samples.read_bytes()).hexdigest(),
                        'source':'actual Android Binder packets; values and relative timing preserved','sampleStart':start},'frames':frames}
    (out/'actual-trace.json').write_text(json.dumps(value,indent=2)+'\n')
    return {'status':'pass','frames':len(frames),'out':str(out/'actual-trace.json')}


def analyze(rows):
    failures=[];groups={};fixes=[];api_times=[];geometry={};modes={};last_order={}
    if not rows:failures.append('no actual samples')
    for row in rows:
        api=row['api'];source=row['source'];scene=api.get('scene')
        if api.get('status')!='decoded':failures.append('API sample did not decode');continue
        errors=validate(scene)
        if errors:failures.append('invalid scene: '+','.join(errors));continue
        order=(scene['generation'],scene['seq'])
        if scene['session'] in last_order and order<=last_order[scene['session']]:failures.append('source order regressed')
        last_order[scene['session']]=order
        api_times.append(api['apiRoundTripMs'])
        if (source.get('fixTimeMs',0)>0 and 0<=source.get('fixAgeMs',60000)<=5000
            and (not fixes or fixes[-1]!=source['fixTimeMs'])):fixes.append(source['fixTimeMs'])
        if scene['state']!='active' or not scene['paths']:continue
        modes[scene['geometryMode']]=modes.get(scene['geometryMode'],0)+1
        group=(scene['session'],scene['generation'])
        key=geometry_key(scene)
        if group in geometry and geometry[group]!=key:failures.append('geometry changed within a generation')
        geometry[group]=key
        groups.setdefault(group,[]).append(scene['distanceM'])
    intervals=[b-a for a,b in zip(fixes,fixes[1:]) if b>a]
    polling=[b['hostSeconds']-a['hostSeconds'] for a,b in zip(rows,rows[1:])]
    decreasing=sum(len(set(distances))>1 and distances[-1]<distances[0] for distances in groups.values())
    return {'status':'fail' if failures else 'pass','samples':len(rows),'failures':sorted(set(failures)),
            'scope':'actual Android Binder/source invariants; not physical GPS or Garmin transport',
            'activeGeometryGenerations':len(groups),'generationsWithDecreasingDistance':decreasing,'geometryModes':modes,
            'fixIntervalMs':{'median':statistics.median(intervals),'min':min(intervals),'max':max(intervals)} if intervals else None,
            'apiRoundTripMs':{'median':statistics.median(api_times),'max':max(api_times)} if api_times else None,
            'pollIntervalSeconds':{'median':statistics.median(polling),'max':max(polling)} if polling else None,
            'maximumSourceBytes':max((r['api'].get('sourceBytes',0) for r in rows),default=0)}


def build_review(samples, capture_path, out, make_png=False):
    rows=[json.loads(line) for line in samples.read_text().splitlines()]
    capture=json.loads(capture_path.read_text());capture_hash=hashlib.sha256(capture_path.read_bytes()).hexdigest()
    report=analyze(rows);out.mkdir(parents=True,exist_ok=True)
    (out/'measurements.json').write_text(json.dumps(report,indent=2)+'\n')
    if report['status']!='pass':raise ValueError('live source invariant failure; see measurements.json')
    selected={};native={d['routePointOffset']:d for d in capture['directions']}
    for row in rows:
        scene=row['api'].get('scene',{});source=row['source']
        if (scene.get('state')!='active' or not scene.get('paths') or scene.get('fixAgeMs',60000)>3000
            or source.get('routeToken')!=capture['routeToken']):continue
        anchor=scene['anchors'][0]['routeIndex']
        if anchor!=source.get('nextRouteIndex') or anchor not in native:continue
        # Prefer an observed approach within 200 m, while retaining unusual cases.
        if anchor not in selected or abs(scene['distanceM']-120)<abs(selected[anchor]['api']['scene']['distanceM']-120):selected[anchor]=row
    cards=[];manifest=[]
    previous={};next_number=1
    old_manifest=out/'manifest.json'
    if old_manifest.exists():
        for old in json.loads(old_manifest.read_text()).get('examples',[]):
            next_number=max(next_number,old['example']+1)
            coordinate=old['coordinates'][0]
            for k in selected:
                lat,lon=capture['locationsLatLon'][k]
                if abs(lat-coordinate['latitude'])<1e-7 and abs(lon-coordinate['longitude'])<1e-7:previous[k]=old['example']
    ordered=sorted(selected.items(),key=lambda item:(0,previous[item[0]]) if item[0] in previous else (1,item[1]['api']['scene']['geometryMode'] not in ('map_context','layer_context')))
    for index,row in ordered:
        if index in previous:number=previous[index]
        else:number=next_number;next_number+=1
        scene=row['api']['scene'];coordinates=[]
        for anchor in scene['anchors']:
            k=anchor['routeIndex']
            if k not in native or not 0<=k<len(capture['locationsLatLon']):raise ValueError('unmatched native anchor')
            lat,lon=capture['locationsLatLon'][k]
            url=f'https://www.openstreetmap.org/?mlat={lat:.7f}&mlon={lon:.7f}#map=19/{lat:.7f}/{lon:.7f}'
            coordinates.append({'latitude':lat,'longitude':lon,'url':url})
        provenance={'kind':'actual_osmand_capture','captureSha256':capture_hash,'applicationMode':'motorcycle',
                    'maneuverIndex':native[index]['index'],'routePointOffset':index,
                    'conversion':'actual Android provider -> app-info Binder -> production bridge SnapshotCodec',
                    'sourceSample':row['sample'],'sourceSampleSha256':hashlib.sha256(json.dumps(row,sort_keys=True).encode()).hexdigest()}
        (out/f'scene-{number}.json').write_text(json.dumps({'provenance':provenance,'scene':scene},indent=2)+'\n')
        (out/f'held-{number}.json').write_text(json.dumps({'provenance':provenance,'frames':[{'atMs':0,'scene':scene}]},indent=2)+'\n')
        (out/f'watch-{number}.svg').write_text(watch_svg(scene))
        if make_png:png(scene,out/f'watch-{number}.png')
        links=''.join(f'<p>Decision {i+1}: <a href="{html.escape(c["url"],quote=True)}" target="_blank" rel="noopener">{c["latitude"]:.6f}, {c["longitude"]:.6f} — OpenStreetMap</a></p>' for i,c in enumerate(coordinates))
        limited=scene['geometryMode'] not in ('map_context','layer_context')
        label='LIMITED: selected route only' if limited else 'Motor-road layout'
        detail=html.escape(scene['reason']) if limited else 'Gray roads provide context; yellow is the selected route.'
        cards.append(f'<article><h2>Example {number} · {label}</h2><img src="watch-{number}.svg" alt="Watch layout {number}"><p>{detail}</p>{links}<p>Observed distance: {scene["distanceM"]} m · {len(scene["paths"])} paths · Native turn {html.escape(native[index]["turn"])}</p></article>')
        manifest.append({'example':number,'nativeIndex':index,'mode':scene['geometryMode'],'coordinates':coordinates,'provenance':provenance})
    if not cards:raise ValueError('no scenes match this native route identity')
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Android junction review</title>
<style>body{background:#10141c;color:#edf2fa;font:16px system-ui;margin:24px}a{color:#82caff}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(360px,1fr));gap:24px}article{background:#171c25;padding:20px;border-radius:16px}img{width:100%;max-width:454px}p{line-height:1.5}h2{font-size:21px}</style>
<h1>Your route: layouts exported by Android</h1><p>These scenes came from the running OsmAnd app through the real bridge API, during native route simulation. Geometry and distances are recorded values. Previews use the watch transform/colors/strokes with approximate fonts; they are not simulator screenshots. Approach is from below. Open the coordinate links to compare the roads. Limited scenes deliberately omit road context and are not complete junction layouts.</p>
<p>Non-motor paths are filtered. Traffic-light/stop-sign symbols remain deferred. Map data © <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>.</p><div class="grid">'''+''.join(cards)+'</div></html>'
    (out/'index.html').write_text(page)
    (out/'manifest.json').write_text(json.dumps({'kind':'actual_android_export_preview_not_screenshot','examples':manifest,'measurements':report},indent=2)+'\n')
    return {'status':'pass','examples':len(manifest),'fullLayouts':sum(m['mode'] in ('map_context','layer_context') for m in manifest),'out':str(out)}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--samples',type=Path,required=True);p.add_argument('--capture',type=Path);p.add_argument('--out',type=Path,required=True);p.add_argument('--png',action='store_true')
    p.add_argument('--trace-only',action='store_true');p.add_argument('--trace-start',type=int,default=0);p.add_argument('--trace-count',type=int,default=32);a=p.parse_args()
    if a.trace_only:result=write_trace(a.samples,a.out,a.trace_start,a.trace_count)
    else:
        if not a.capture:p.error('--capture is required for coordinate-linked review')
        result=build_review(a.samples,a.capture,a.out,a.png)
    print(json.dumps(result))


if __name__=='__main__':main()
