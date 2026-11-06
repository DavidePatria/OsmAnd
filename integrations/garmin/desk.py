#!/usr/bin/env python3
"""Unattended, explicit-target Waydroid source tests. Personal output stays in build/.

No default phone configuration, system privilege changes or Garmin transport.
Controls operate on the isolated test app's current native calculated route.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import shlex
import subprocess
import sys
import time
import uuid

sys.dont_write_bytecode = True
import route_probe

OSMAND = route_probe.PACKAGE
BRIDGE = 'net.osmand.junction.bridge.debug'
OPERATIONS = ('state', 'start', 'stop', 'pause', 'resume', 'freeze', 'cancel', 'detour', 'reload', 'grant_bridge', 'deny_bridge')
BRIDGE_OPERATIONS = ('start_tethered', 'stop_tethered')


class Desk:
    def __init__(self, config):
        cfg = json.loads(Path(config).expanduser().read_text())
        serial = cfg.get('adb_serial')
        if not isinstance(serial, str) or not serial:
            raise ValueError('explicit Waydroid adb_serial required; no device auto-selection')
        self.adb = [str(Path(cfg['android_sdk']).expanduser()/'platform-tools/adb'), '-s', serial]
        device = self.command('shell', 'getprop', 'ro.product.device').strip()
        if not device.startswith('waydroid_'):
            raise ValueError('refusing non-Waydroid target')

    def command(self, *args, timeout=30):
        return route_probe.command(self.adb+list(args), timeout=timeout)

    def probe(self, operation='state', bridge=False):
        if operation not in OPERATIONS+BRIDGE_OPERATIONS or (operation in BRIDGE_OPERATIONS and not bridge):
            raise ValueError('unknown operation')
        request = uuid.uuid4().hex
        package = BRIDGE if bridge else OSMAND
        component = (BRIDGE+'/net.osmand.junction.bridge.DebugSnapshotReceiver' if bridge else
                     OSMAND+'/net.osmand.plus.routing.companion.DebugJunctionDeskReceiver')
        action = 'net.osmand.junction.bridge.SNAPSHOT' if bridge else 'net.osmand.junction.DESK'
        if operation in BRIDGE_OPERATIONS:action='net.osmand.junction.bridge.DESK'
        self.command('shell', shlex.join(['am', 'broadcast', '-n', component, '-a', action,
            '--es', 'request', request, '--es', 'operation', operation, '--es', 'scenario', 'current-route']))
        deadline = time.monotonic()+8
        path = f'/sdcard/Android/data/{package}/files/junction-desk/latest.json'
        while time.monotonic()<deadline:
            try:
                value = json.loads(self.command('exec-out', 'cat', path))
                if value.get('request')==request:
                    return value
            except (RuntimeError, ValueError):
                pass
            time.sleep(.05)
        raise RuntimeError('debug request did not publish this request; no old result accepted')


def prepare(desk, capture_path, out):
    capture = json.loads(capture_path.read_text())
    errors = route_probe.validate(capture)
    if errors or capture.get('applicationMode')!='motorcycle':
        raise ValueError('a coherent actual motorcycle capture is required')
    result=prepare_endpoints(desk,capture['locationsLatLon'][0],capture['locationsLatLon'][-1],out)
    result['inputSha256']=hashlib.sha256(capture_path.read_bytes()).hexdigest()
    return result


def prepare_endpoints(desk,start,end,out):
    for point in (start,end):
        if len(point)!=2 or any(type(x) not in (int,float) or not math.isfinite(x) for x in point) or abs(point[0])>80 or abs(point[1])>180:
            raise ValueError('valid start/destination latitude and longitude required')
    for permission in ['android.permission.ACCESS_COARSE_LOCATION', 'android.permission.ACCESS_FINE_LOCATION',
                       'android.permission.POST_NOTIFICATIONS']:
        desk.command('shell', 'pm', 'grant', OSMAND, permission)
    desk.command('shell', 'am', 'start', '-W', '-n', OSMAND+'/net.osmand.plus.activities.MapActivity')
    ready_deadline=time.monotonic()+60
    while True:
        profile = route_probe.sample(desk.adb, 'PREPARE_MOTORCYCLE')
        if profile.get('status')=='profile_prepared':break
        if profile.get('status')!='initializing' or time.monotonic()>=ready_deadline:
            raise RuntimeError('app/profile not ready')
        time.sleep(.5)
    url = f'https://osmand.net/map?start={start[0]},{start[1]}&end={end[0]},{end[1]}&profile=motorcycle'
    previous=desk.probe('state').get('routeToken')
    desk.command('shell', shlex.join(['am','start','-W','-n',OSMAND+'/net.osmand.plus.activities.MapActivity',
                 '-a','android.intent.action.VIEW','-d',url]))
    deadline=time.monotonic()+90
    while time.monotonic()<deadline:
        value=route_probe.sample(desk.adb)
        if (not route_probe.validate(value) and value.get('applicationMode')=='motorcycle'
            and value.get('routeToken')!=previous and value.get('currentRoutePoint')==0):
            (out/'route.json').write_text(json.dumps(value,indent=2)+'\n')
            return {'status':'pass','scope':'native route calculated from saved endpoints',
                    'locationCount':value['locationCount'],'maneuvers':len(value['directions'])}
        time.sleep(.5)
    raise RuntimeError('native route not ready; inspect app logs, maps and onboarding')


def capture_active_route(desk,source,out,known):
    """Match native identity after simulation startup/recalculation, never by index alone."""
    token=source.get('routeToken')
    if not source.get('routeCalculated') or source.get('recalculating') or not token:return None
    if token in known:return known[token]
    value=route_probe.sample(desk.adb)
    if route_probe.validate(value) or value.get('routeToken')!=token:return None
    directory=out/'routes';directory.mkdir(exist_ok=True)
    path=directory/f'route-{len(known)}.json'
    path.write_text(json.dumps(value,indent=2)+'\n')
    known[token]=str(path.relative_to(out))
    return known[token]


def monitor(desk, out, seconds, lifecycle, hz=1):
    started=time.monotonic();samples=[];events=[];routes={}
    schedule=[(15,'pause'),(20,'resume'),(30,'freeze')] if lifecycle else []
    deadline=started+seconds;index=0
    with (out/'samples.jsonl').open('w') as stream:
        while time.monotonic()<deadline:
            due=started+index/hz
            if due>time.monotonic():time.sleep(due-time.monotonic())
            while schedule and time.monotonic()-started>=schedule[0][0]:
                _,operation=schedule.pop(0)
                events.append({'atSeconds':time.monotonic()-started,'operation':operation,'result':desk.probe(operation)})
            api=desk.probe(bridge=True)
            source=desk.probe('state')
            value={'sample':index,'hostSeconds':time.monotonic()-started,'api':api,'source':source}
            matched=capture_active_route(desk,source,out,routes)
            if matched:value['routeCapture']=matched
            stream.write(json.dumps(value,separators=(',',':'))+'\n');stream.flush();samples.append(value);index+=1
    (out/'events.json').write_text(json.dumps(events,indent=2)+'\n')
    return {'status':'captured','scope':'actual Binder snapshots and native simulated fixes; not Garmin transport',
            'samples':len(samples),'seconds':time.monotonic()-started}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    sub=parser.add_subparsers(dest='command',required=True)
    prepare_parser=sub.add_parser('prepare');prepare_parser.add_argument('--capture',type=Path)
    prepare_parser.add_argument('--start',type=float,nargs=2,metavar=('LAT','LON'))
    prepare_parser.add_argument('--destination',type=float,nargs=2,metavar=('LAT','LON'))
    probe=sub.add_parser('probe');probe.add_argument('--operation',choices=OPERATIONS+BRIDGE_OPERATIONS,default='state');probe.add_argument('--bridge',action='store_true')
    watch=sub.add_parser('monitor');watch.add_argument('--seconds',type=int,default=60);watch.add_argument('--lifecycle',action='store_true');watch.add_argument('--hz',type=int,choices=(1,5),default=1)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    report={'status':'fail'}
    try:
        desk=Desk(args.config)
        if args.command=='prepare':
            if args.capture and not args.start and not args.destination:report=prepare(desk,args.capture,args.out)
            elif not args.capture and args.start and args.destination:report=prepare_endpoints(desk,args.start,args.destination,args.out)
            else:raise ValueError('provide either --capture or both --start and --destination')
        elif args.command=='probe':
            report=desk.probe(args.operation,args.bridge)
            if args.operation=='start' and not args.bridge and report.get('status')=='ok':
                deadline=time.monotonic()+15
                while time.monotonic()<deadline:
                    state=desk.probe('state')
                    if state.get('following') and state.get('simulating'):
                        report=state;break
                    time.sleep(.2)
                else:raise RuntimeError('native simulation did not enter following/running state')
        else:
            if not 1<=args.seconds<=1800:raise ValueError('duration must be 1..1800 seconds')
            report=monitor(desk,args.out,args.seconds,args.lifecycle,args.hz)
    except (OSError,ValueError,RuntimeError,subprocess.TimeoutExpired) as error:report['reason']=str(error)
    (args.out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    # Do not print private geometry/coordinates into terminal output.
    print(json.dumps({k:v for k,v in report.items() if k in ('status','scope','reason','samples','seconds','locationCount','maneuvers')}))
    return 1 if report.get('status') in ('fail','error') else 0


if __name__=='__main__':raise SystemExit(main())
