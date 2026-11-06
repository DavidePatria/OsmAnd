#!/usr/bin/env python3
"""Coordinate-linked watch-layout previews from actual captured scenes.

SVG/HTML need only Python. Optional PNG export needs Pillow. These use the
watch's scene, transform, clipping, colors and strokes; fonts are approximate.
They are NOT simulator screenshots. Keep personal route output under build/.
"""
import argparse
import hashlib
import html
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
from replay_scene import recorded


def road_strokes(scene):
    """Same level/color/casing order as JunctionRenderer; geometry is unchanged."""
    paths=scene['paths'];selected=next((p for p in paths if p['role']=='selected'),None)
    if scene['geometryMode']!='layer_context':
        for p in paths:
            if p['role']!='selected':yield p['points'],'#8193a6',4
        if selected:
            yield selected['points'],'black',13;yield selected['points'],'#ffd166',7
        return
    levels={p['layer'] for p in paths if p['role']!='selected'}
    levels.update(selected['segmentLayers'])
    for level in sorted(levels):
        context=[p for p in paths if p['role']!='selected' and p['layer']==level]
        if level>min(levels):
            for p in context:yield p['points'],'black',10
        for p in context:yield p['points'],'#8193a6',4
        if selected:
            for color,width in [('black',13),('#ffd166',7)]:
                for i,value in enumerate(selected['segmentLayers']):
                    if value==level:yield selected['points'][i:i+2],color,width


def watch_svg(scene):
    parts=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 454 454" width="454" height="454">',
           '<defs><clipPath id="face"><circle cx="227" cy="227" r="226"/></clipPath><clipPath id="roads"><rect x="25" y="102" width="404" height="270"/></clipPath></defs>',
           '<rect width="454" height="454" fill="#171c25"/><g clip-path="url(#face)"><rect width="454" height="454" fill="black"/>']
    def text(x,y,label,size=20,color='white',anchor='middle'):
        parts.append(f'<text x="{x}" y="{y}" dominant-baseline="hanging" text-anchor="{anchor}" font-family="DejaVu Sans,sans-serif" font-size="{size}" fill="{color}">{html.escape(label)}</text>')
    text(227,22,'TEST REPLAY',20,'#8ca5bf');text(227,53,str(scene['distanceM'])+' m',42)
    scale=454*.33/scene['radiusDm']
    def xy(p):return 227+p[0]*scale,454*.54-p[1]*scale
    parts.append('<g clip-path="url(#roads)">')
    def line(path,color,width):
        points=' '.join(f'{x:.3f},{y:.3f}' for x,y in map(xy,path['points']))
        parts.append(f'<polyline points="{points}" stroke="{color}" stroke-width="{width}" fill="none"/>')
    for points,color,width in road_strokes(scene):line({'points':points},color,width)
    for i,anchor in enumerate(scene['anchors']):
        x,y=xy(anchor['point']);parts.append(f'<circle cx="{x}" cy="{y}" r="6" fill="black" stroke="#ffd166" stroke-width="2"/>')
        text(x+10,y-23,str(i+1),20,anchor='start')
    parts.append('</g>')
    text(227,382,scene['roadName'][:25],20)
    detail='MOTOR ROADS' if scene['geometryMode'] in ('map_context','layer_context') else 'ROUTE ONLY' if scene['geometryMode']=='route_only' else 'PARTIAL ROADS'
    text(227,414,detail,20,'#8ca5bf')
    parts.append('</g></svg>')
    return ''.join(parts)


def png(scene, path):
    from PIL import Image, ImageDraw, ImageFont
    # Same drawing transform as the SVG and Monkey C renderer, supersampled.
    factor=3;size=454*factor
    image=Image.new('RGB',(size,size),'black');draw=ImageDraw.Draw(image)
    font_path='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    def text(x,y,label,px=20,color='white',anchor='mt'):
        font=ImageFont.truetype(font_path,px*factor)
        draw.text((x*factor,y*factor),label,font=font,fill=color,anchor=anchor)
    text(227,22,'TEST REPLAY',20,'#8ca5bf');text(227,53,str(scene['distanceM'])+' m',42)
    layer=Image.new('RGB',(size,size),'black');roads=ImageDraw.Draw(layer)
    scale=454*.33/scene['radiusDm']
    def xy(p):return (227+p[0]*scale)*factor,(454*.54-p[1]*scale)*factor
    def line(p,color,width):roads.line([xy(q) for q in p['points']],fill=color,width=width*factor)
    for points,color,width in road_strokes(scene):line({'points':points},color,width)
    image.paste(layer.crop((25*factor,102*factor,429*factor,372*factor)),(25*factor,102*factor))
    for i,a in enumerate(scene['anchors']):
        x,y=xy(a['point']);r=6*factor
        draw.ellipse((x-r,y-r,x+r,y+r),fill='black',outline='#ffd166',width=2*factor)
        text(x/factor+10,y/factor-23,str(i+1),20,anchor='lt')
    detail='MOTOR ROADS' if scene['geometryMode'] in ('map_context','layer_context') else 'ROUTE ONLY' if scene['geometryMode']=='route_only' else 'PARTIAL ROADS'
    text(227,382,scene['roadName'][:25]);text(227,414,detail,20,'#8ca5bf')
    mask=Image.new('L',(size,size));ImageDraw.Draw(mask).ellipse((factor,factor,size-factor,size-factor),fill=255)
    face=Image.new('RGB',(size,size),'#171c25');face.paste(image,(0,0),mask)
    face.resize((454,454),Image.Resampling.LANCZOS).save(path)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture',type=Path,required=True);parser.add_argument('--contexts',type=Path,required=True)
    parser.add_argument('--maneuvers',type=int,nargs='+',required=True);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--png',action='store_true',help='also export PNG with Pillow and the local DejaVu Sans font')
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    capture=json.loads(args.capture.read_text());cards=[];manifest=[]
    for number,index in enumerate(args.maneuvers,1):
        value=recorded(args.capture,index,args.contexts/f'context-{index}.json');scene=value['scene']
        if not scene['paths']:raise ValueError('No renderable geometry for maneuver '+str(index))
        (args.out/f'watch-{number}.svg').write_text(watch_svg(scene))
        if args.png:png(scene,args.out/f'watch-{number}.png')
        coords=[]
        for anchor in scene['anchors']:
            lat,lon=capture['locationsLatLon'][anchor['routeIndex']]
            url=f'https://www.openstreetmap.org/?mlat={lat:.7f}&mlon={lon:.7f}#map=19/{lat:.7f}/{lon:.7f}'
            coords.append({'latitude':lat,'longitude':lon,'url':url})
        links=''.join(f'<p>Point {i+1}: <a href="{html.escape(c["url"],quote=True)}" target="_blank" rel="noopener">{c["latitude"]:.6f}, {c["longitude"]:.6f} — OpenStreetMap</a></p>' for i,c in enumerate(coords))
        count=len(scene['paths']);points=sum(len(p['points']) for p in scene['paths'])
        cards.append(f'<article><h2>Example {number} · maneuver {index}</h2><img src="watch-{number}.svg" alt="Watch preview {number}">{links}<p>{count} paths · {points} points · {html.escape(scene["geometryMode"])}</p></article>')
        manifest.append({'example':number,'maneuver':index,'coordinates':coords,'paths':count,'points':points,'provenance':value['provenance']})
        (args.out/f'scene-{number}.json').write_text(json.dumps(value,indent=2)+'\n')
    page='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Junction review</title><style>body{background:#10141c;color:#edf2fa;font:16px system-ui;margin:24px}a{color:#82caff}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(360px,1fr));gap:24px}article{background:#171c25;padding:20px;border-radius:16px}img{width:100%;max-width:454px}p{line-height:1.5}h2{font-size:21px}</style><h1>Your route: watch-layout examples</h1><p>Actual captured OsmAnd route + roads from the same offline map. Same geometry, colors and scale as the watch renderer; approximate fonts, not simulator screenshots. Distance 120 m is illustrative. Approach is from below; gray roads provide context, yellow is the calculated route. Numbered points identify successive decisions. Open the coordinate links to check the layout.</p><div class="grid">'+''.join(cards)+'</div></html>'
    page=page.replace('<div class="grid">','<p>Non-motor paths/cycleways are omitted unless access tags allow motor use. Tracks and service roads remain; this is a display filter, not a legal-access determination. Map data: © <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap contributors</a>.</p><div class="grid">')
    (args.out/'index.html').write_text(page)
    report={'kind':'watch_layout_preview_not_simulator_screenshot','distance':'illustrative 120 m',
            'rendererSha256':hashlib.sha256((Path(__file__).parent/'watch/source/JunctionRenderer.mc').read_bytes()).hexdigest(),'examples':manifest}
    (args.out/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print(args.out/'index.html')
    for item in manifest:print(json.dumps({k:item[k] for k in ('example','maneuver','coordinates','paths','points')}))


if __name__=='__main__':main()
