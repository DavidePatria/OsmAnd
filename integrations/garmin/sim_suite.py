#!/usr/bin/env python3
"""Fixed, private route suites for Waydroid + the live Garmin simulator.

Never selects a phone, installs an APK, clears logs, or retries a failed run.
Use create, plan, prepare, then run. See SIMULATOR_TESTS.md.
"""
import argparse
from collections import Counter, deque
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import threading
import time

sys.dont_write_bytecode = True
import desk
import dev


def utc():
    return datetime.now(timezone.utc).isoformat()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def save(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    temporary.replace(path)


def private_path(path):
    """Coordinates and raw evidence must remain under the ignored review root."""
    path = path.expanduser().resolve()
    root = dev.REPO_ROOT / 'build/garmin-review'
    if not path.is_relative_to(root.resolve()):
        raise ValueError('suite/evidence paths must be inside ignored build/garmin-review/')
    return path


def make_suite(points):
    if not isinstance(points, list) or not 2 <= len(points) <= 32:
        raise ValueError('provide between 2 and 32 points')
    ids, coordinates, normalized = set(), set(), []
    for point in points:
        if not isinstance(point, dict) or not isinstance(point.get('id'), str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,23}', point['id']):
            raise ValueError('each point needs a short alphanumeric ID')
        lat, lon = point.get('lat'), point.get('lon')
        if any(type(x) not in (int, float) or not math.isfinite(x) for x in (lat, lon)) or not -80 <= lat <= 80 or not -180 <= lon <= 180:
            raise ValueError('invalid point latitude/longitude')
        if point['id'] in ids or (lat, lon) in coordinates:
            raise ValueError('point IDs and coordinates must be unique')
        ids.add(point['id']); coordinates.add((lat, lon))
        normalized.append({'id': point['id'], 'lat': lat, 'lon': lon})
    scenarios = [{'id': f'R{i+1:03d}', 'from': a['id'], 'to': b['id']}
                 for i, (a, b) in enumerate((a, b) for a in normalized for b in normalized if a['id'] != b['id'])]
    return {'version': 1, 'profile': 'motorcycle', 'simulationSpeedMps': 10,
            'points': normalized, 'scenarios': scenarios}


def load_suite(path):
    value = json.loads(private_path(path).read_text())
    normalized = (make_short_suite(value.get('points'), value.get('scenarios'), value.get('provenance'))
                  if value.get('version') == 2 else make_suite(value.get('points')))
    if value != normalized:
        raise ValueError('suite differs from the fixed version-1 directed-pair manifest')
    return value


def make_short_suite(points, scenarios, provenance):
    """Explicit endpoint pairs; OsmAnd still calculates and simulates each route."""
    normalized = make_suite(points)['points']
    ids = {p['id'] for p in normalized}
    if not isinstance(scenarios, list) or not 1 <= len(scenarios) <= 20 or not isinstance(provenance, dict):
        raise ValueError('short suite needs named routes and provenance')
    routes = []; names = set(); pairs = set()
    for route in scenarios:
        if not isinstance(route, dict): raise ValueError('named short route object required')
        sid, origin, target = route.get('id'), route.get('from'), route.get('to')
        if not isinstance(sid, str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,23}', sid) or sid in names:
            raise ValueError('unique safe scenario ID required')
        if origin not in ids or target not in ids or origin == target or (origin, target) in pairs:
            raise ValueError('distinct existing route endpoints required')
        if not re.fullmatch(r'R\d{3}', route.get('parent', '')) or type(route.get('focus')) is not bool:
            raise ValueError('short route needs a parent and explicit focus flag')
        names.add(sid); pairs.add((origin, target))
        routes.append({'id': sid, 'from': origin, 'to': target, 'parent': route['parent'], 'focus': route['focus']})
    return {'version': 2, 'kind': 'short_native_routes', 'profile': 'motorcycle',
            'simulationSpeedMps': 10, 'points': normalized, 'scenarios': routes, 'provenance': provenance}


def run_policy(profile='regression', hours=None):
    if profile == 'endurance':
        if type(hours) not in (int, float) or not math.isfinite(hours) or not 1/60 <= hours <= 24:
            raise ValueError('endurance requires explicit --hours between 1 minute and 24 hours')
        return {'profile': profile, 'seconds': int(hours*3600), 'repeat': True, 'maxRoutes': 5}
    if hours is not None:
        raise ValueError('--hours only applies to explicit --profile endurance')
    if profile not in ('smoke', 'regression'): raise ValueError('unknown run profile')
    return {'profile': profile, 'seconds': 300 if profile == 'smoke' else 1800,
            'repeat': False, 'maxRoutes': 1 if profile == 'smoke' else 5}


def profile_scenarios(suite, selection, policy):
    scenarios = [next(s for s in suite['scenarios'] if s['id'] == sid) for sid in selection['active']]
    if policy['profile'] == 'smoke':
        scenarios.sort(key=lambda s: not s.get('focus', False))
    return scenarios[:policy['maxRoutes']]


def connect(config):
    # Restore the visible Android UI before ANY ADB shell, avoiding a frozen container.
    subprocess.run(['waydroid', 'show-full-ui'], check=True, capture_output=True, timeout=30)
    cfg = json.loads(config.expanduser().read_text())
    serial = cfg.get('adb_serial')
    if not isinstance(serial, str) or not serial:
        raise ValueError('explicit Waydroid target required')
    # USB identifiers are never auto-selected; Desk verifies ro.product.device read-only.
    if ':' in serial:
        subprocess.run([str(Path(cfg['android_sdk']).expanduser() / 'platform-tools/adb'), 'connect', serial],
                       capture_output=True, check=True, timeout=15)
    return desk.Desk(config)


def checked_probe(client, operation, bridge=False, simulation=None):
    value = client.probe(operation, bridge, simulation=simulation) if simulation is not None else client.probe(operation, bridge)
    if value.get('status') not in ('ok', 'decoded'):
        raise RuntimeError(f'{operation} probe failed: {value.get("status")}')
    return value


def minutes(seconds):
    return f'{seconds / 60:.1f} min'


def native_constant_seconds(route, speed):
    """Estimate existing CONSTANT stepping; short segments still take one tick.

    This models timing only, never generates fixes or drives route advancement.
    LocationSimulationThread/Utils use 1.5 s ticks and consume at most one
    route vertex per tick. Allow two initial/final ticks for their first step.
    """
    points = route['locationsLatLon']
    if len(points) < 2 or not math.isfinite(speed) or not 1 <= speed <= 35:
        raise ValueError('route points and bounded native speed required')
    ticks = 0
    for a, b in zip(points, points[1:]):
        lat1, lat2 = math.radians(a[0]), math.radians(b[0])
        h = math.sin((lat2-lat1)/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(math.radians(b[1]-a[1])/2)**2
        distance = 6371000 * 2 * math.asin(min(1, math.sqrt(h)))
        ticks += max(1, math.ceil(distance / (speed * 1.5)))
    return (ticks + 2) * 1.5


def native_route_timeout(route, simulation):
    if simulation['mode'] == 'realistic':
        # Guard against a stalled journey; not an ETA or an altered simulator.
        reference = max(route['remainingTimeSeconds'], len(route['locationsLatLon']) * 1.5)
        return max(600, reference * 3 + 300)
    return native_constant_seconds(route, simulation['speedMps']) * 1.5 + 120


class NativeObservations:
    """Bounded summaries of observed native fixes, without injecting any events."""
    def __init__(self):
        self.previous = None
        self.summary = {'freshFixes': 0, 'zeroSpeedFixes': 0, 'nativeTurnChanges': 0,
                        'turnChangesWhileStopped': 0, 'speedMinMps': None, 'speedMaxMps': None}

    def sample(self, source):
        stamp = source.get('fixTimeMs')
        if stamp is None or (self.previous and stamp == self.previous.get('fixTimeMs')):
            return None
        self.summary['freshFixes'] += 1
        speed = source.get('fixSpeedMps')
        if type(speed) in (int, float) and math.isfinite(speed):
            if speed == 0: self.summary['zeroSpeedFixes'] += 1
            self.summary['speedMinMps'] = speed if self.summary['speedMinMps'] is None else min(speed, self.summary['speedMinMps'])
            self.summary['speedMaxMps'] = speed if self.summary['speedMaxMps'] is None else max(speed, self.summary['speedMaxMps'])
        event = None
        old = self.previous
        if (old and source.get('routeToken') == old.get('routeToken') and source.get('routeToken')
                and source.get('nextRouteIndex', -1) >= 0 and old.get('nextRouteIndex', -1) >= 0
                and source['nextRouteIndex'] != old['nextRouteIndex']):
            self.summary['nativeTurnChanges'] += 1
            stopped = speed == 0 and old.get('fixSpeedMps') == 0
            if stopped: self.summary['turnChangesWhileStopped'] += 1
            event = {'type': 'native_turn_change', 'stoppedOnBothObservedFixes': stopped,
                     'previousSource': old, 'currentSource': source,
                     'interpretation': 'observation only; not proof of premature advancement or a crash'}
        self.previous = source
        return event


def choose_routes(suite, plan, count=5):
    if any(plan.get('routes', {}).get(s['id'], {}).get('status') != 'planned' for s in suite['scenarios']):
        raise ValueError('all candidates must be natively planned before ranking')
    for scenario in suite['scenarios']:
        route = plan['routes'][scenario['id']]
        if not math.isfinite(route['distanceM']) or route['distanceM'] <= 0:
            raise ValueError('positive native distance required for turn density')
    ranked = sorted(suite['scenarios'], key=lambda s: (
        -plan['routes'][s['id']]['turns'] / plan['routes'][s['id']]['distanceM'],
        plan['routes'][s['id']]['distanceM'], s['id']))
    ids = [s['id'] for s in ranked[:count]]
    return {'version': 3, 'suiteSha256': digest(suite), 'planSha256': digest(plan),
            'criterion': 'most non-straight native turn instructions per kilometre; ties by shorter distance, then scenario ID',
            'simulation': {'mode': 'realistic', 'randomness': 'native_unseeded'},
            'active': ids, 'parked': [s['id'] for s in suite['scenarios'] if s['id'] not in ids]}


def write_route_report(suite, plan, path, selection=None):
    scenarios = suite['scenarios'] if selection is None else [next(s for s in suite['scenarios'] if s['id'] == sid) for sid in selection['active']]
    lines = ['# Fixed simulator route suite', '', f'Suite SHA-256: `{digest(suite)}`', '',
             f'{len(suite["points"])} points; {len(scenarios)} directed routes in this report; motorcycle profile.',
             'Order is fixed. Reverse routes are separate scenarios. Coordinates below are private local inputs.', '',
             '| Point | Latitude | Longitude |', '|---|---:|---:|']
    lines += [f'| {p["id"]} | {p["lat"]} | {p["lon"]} |' for p in suite['points']]
    if suite.get('version') == 2:
        lines += ['', 'Short endpoint pairs derived from saved parent routes. Each pair is recalculated by native OsmAnd; it is not a forced replay of the original geometry.',
                  'Parent references: ' + ', '.join(s['id']+' → '+s['parent'] for s in suite['scenarios']) + '.',
                  'Routine regression: one pass, 30-minute cap. Smoke: one focus route, 5-minute cap. Only explicit endurance repeats.']
    realistic = bool(selection and selection.get('simulation', {}).get('mode') == 'realistic')
    speed = selection['simulation']['speedMps'] if selection and selection.get('version') == 2 else suite['simulationSpeedMps']
    lines += ['', ('Native REALISTIC simulation: road-dependent speed, mapped traffic-light stops and native unseeded noise.' if realistic else f'Native constant-speed simulation: {speed:g} m/s ({speed*3.6:g} km/h).'),
              'Turn density is non-straight native instructions per kilometre, not total instruction count.', '',
              ('Realistic simulation duration is not measured yet. Native journey estimates below are planning references, not simulated completion estimates. Per-route timeout is 3× the larger of native journey time and vertex tick floor, plus 5 minutes.' if realistic else 'Simulation timing includes native 1.5-second route-point stepping where captured. Distance/speed alone is a lower bound; this is not a completed-run measurement.'), '',
              '| Scenario | From → to | Native length | OsmAnd journey estimate | Native simulation estimate | Turns | Turns/km | All maneuvers | Estimated finish from launch | Planning result |',
              '|---|---|---:|---:|---:|---:|---:|---:|---:|---|']
    elapsed = 0
    for scenario in scenarios:
        r = plan.get('routes', {}).get(scenario['id'], {})
        if r.get('status') == 'planned':
            duration = r['nativeTimeSeconds'] if realistic else r.get('constantSimulationEstimates', {}).get(str(speed), math.ceil(r['distanceM'] / speed))
            elapsed += duration + r['planningSeconds'] + 5
            density = f'{1000*r["turns"]/r["distanceM"]:.3f}' if 'turns' in r else '—'
            timing = 'not measured' if realistic else minutes(duration)
            cumulative = minutes(elapsed) + (' reference' if realistic else '')
            lines.append(f'| {scenario["id"]} | {scenario["from"]} → {scenario["to"]} | {r["distanceM"]/1000:.2f} km | {minutes(r["nativeTimeSeconds"])} | {timing} | {r.get("turns", "—")} | {density} | {r["maneuvers"]} | {cumulative} | Calculated; see run results for execution |')
        else:
            lines.append(f'| {scenario["id"]} | {scenario["from"]} → {scenario["to"]} | — | — | — | — | — | — | — | {r.get("status", "not calculated")} |')
    routes = [plan['routes'][s['id']] for s in scenarios if plan.get('routes', {}).get(s['id'], {}).get('status') == 'planned']
    simulated = sum(r['nativeTimeSeconds'] if realistic else r.get('constantSimulationEstimates', {}).get(str(speed), math.ceil(r['distanceM'] / speed)) for r in routes)
    overhead = sum(r['planningSeconds'] + 5 for r in routes)
    lines += ['', f'Calculated routes: {len(routes)}/{len(scenarios)}.',
              f'{"Native journey reference total (not simulated ETA)" if realistic else "Simulation estimate for one complete pass"}: **{simulated/3600:.2f} hours**.',
              f'{"Journey reference including setup (not simulated ETA)" if realistic else "Estimated pass including measured route setup plus 5 s/start"}: **{(simulated+overhead)/3600:.2f} hours**.',
              'Allow additional margin for native recalculation, SDK delay and arrival detection. These are estimates, not measured completed runs.',
              '', '## What this exercises', '',
              'Each route runs native OsmAnd motorcycle navigation in Waydroid, through the separate bridge and actual Garmin SDK tethered connection into the normal Garmin simulator app heap. No recorded replay is substituted.',
              'Directions are tested both ways because junction approaches and selected turns differ. The runner records actual maneuvers and road layouts; endpoints alone do not prove that a particular roundabout, bridge or road feature is exercised.',
              '', '## Evidence and operation', '',
              'See integrations/garmin/SIMULATOR_TESTS.md for commands and one-time connection steps. The run manifest copies this suite, its hash, native plan, build metadata and runtime limits. Scenario captures and logs live beside results.',
              'A scenario passes only after native arrival and an arrived watch drawing/acknowledgment. Process exits, source errors and delivery gaps stop route advancement and preserve evidence. A route timeout is not labeled a crash.',
              'A shorter time budget can leave scenarios unexecuted; the result lists coverage and never calls an unexecuted route passed.',
              'Routes are freshly calculated using the installed offline map. Route captures and map/build hashes allow later comparison; identical endpoints alone do not lock geometry across changed maps or builds.', '']
    if selection is not None:
        lines += ['## Selection and parked routes', '', selection['criterion'] + '.',
                  'Straight-ahead C instructions and arrival are excluded from the turn ranking. Slight turns and keep-left/right instructions count.',
                  'The other candidates are parked, not scheduled: ' + ', '.join(selection['parked']) + '.',
                  'See [all-routes.md](all-routes.md) for their native measurements.', '',
                  '## Deferred stationary-intersection scenario', '',
                  'User observation: when stopped at a traffic light before crossing a junction, the next junction was sometimes displayed prematurely. Cause unconfirmed.',
                  'Later testing should inject fresh repeated stationary fixes with speed zero before/inside/after the decision; freezing fix timestamps or pausing navigation would test different behavior. Log OsmAnd maneuver advancement and the watch generation separately. OsmAnd retains ownership of junction advancement.',
                  'Native REALISTIC stops/noise are unseeded and opportunistic. Precisely placed stops, speed spikes, crawling sequences and fix gaps remain deferred. A future scripted suite would need a saved schedule; none is added here.', '']
    path.write_text('\n'.join(lines))


def plan_routes(client, suite, directory):
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / 'plan.json'
    plan = {'suiteSha256': digest(suite), 'createdUtc': utc(), 'routes': {}}
    if path.exists():
        plan = json.loads(path.read_text())
        if plan['suiteSha256'] != digest(suite):
            raise ValueError('existing plan belongs to a different suite')
    by_id = {p['id']: [p['lat'], p['lon']] for p in suite['points']}
    for scenario in suite['scenarios']:
        sid = scenario['id']
        if plan['routes'].get(sid, {}).get('status') == 'planned':
            continue
        out = directory / sid
        out.mkdir(exist_ok=True)
        started = time.monotonic()
        try:
            # Intentional simulation setup; no personal installation is addressed.
            if client.probe('state').get('following'):
                checked_probe(client, 'cancel')
            desk.prepare_endpoints(client, by_id[scenario['from']], by_id[scenario['to']], out)
            route = json.loads((out / 'route.json').read_text())
            if route.get('currentRoutePoint') != 0 or type(route.get('remainingTimeSeconds')) is not int:
                raise RuntimeError('updated debug capture with native route duration at progress zero required')
            environment = environment_hashes(client, route)
            if plan.get('environment') not in (None, environment):
                raise RuntimeError('map or Android APK changed during planning; use a new plan directory')
            plan['environment'] = environment
            plan['routes'][sid] = {'status': 'planned', 'distanceM': route['distanceM'],
                'nativeTimeSeconds': route['remainingTimeSeconds'], 'simulationSeconds': math.ceil(route['distanceM'] / suite['simulationSpeedMps']),
                'maneuvers': len(route['directions']), 'turns': sum(d['turn'] != 'C' for d in route['directions']),
                'planningSeconds': round(time.monotonic() - started, 3),
                'captureSha256': dev.sha256(out / 'route.json')}
            print(f'{sid}: calculated ({len(plan["routes"])}/{len(suite["scenarios"])})', flush=True)
        except Exception as error:
            plan['routes'][sid] = {'status': 'planning_failed', 'errorType': type(error).__name__, 'reason': str(error)}
            save(path, plan); write_route_report(suite, plan, directory.parent / 'routes.md')
            raise
        save(path, plan)
        write_route_report(suite, plan, directory.parent / 'routes.md')
    return plan


def environment_hashes(client, route):
    import shlex
    paths = route.get('routingMaps')
    if not isinstance(paths, list) or not paths or not all(isinstance(p, str) and p.endswith('.obf') for p in paths):
        raise RuntimeError('native capture must identify loaded routing maps')
    files = {}
    for package in (desk.OSMAND, desk.BRIDGE):
        apks = client.command('shell', 'pm', 'path', package).splitlines()
        for i, apk in enumerate(apks):
            if not apk.startswith('package:'): raise RuntimeError('APK path unavailable')
            path = apk[len('package:'):].strip()
            files[f'{package}-apk-{i}'] = client.command('shell', shlex.join(['sha256sum', path])).split()[0]
    for path in sorted(paths):
        files['map:' + Path(path).name] = client.command('shell', shlex.join(['sha256sum', path])).split()[0]
    return files


def sdk_env(cfg):
    env = os.environ.copy()
    if cfg.get('garmin_library_path'):
        env['LD_LIBRARY_PATH'] = str(Path(cfg['garmin_library_path']).expanduser()) + ':' + env.get('LD_LIBRARY_PATH', '')
    return env


def forward(client):
    # Never replace a forward belonging to another device, even if stale.
    text = client.command('forward', '--list')
    wanted = [client.adb[2], 'tcp:7381', 'tcp:7381']
    if any(len(p := line.split()) == 3 and p[1] == 'tcp:7381' and p != wanted for line in text.splitlines()):
        raise RuntimeError('port 7381 is owned by another forwarding rule')
    if not any(line.split() == wanted for line in text.splitlines()):
        client.command('forward', '--no-rebind', 'tcp:7381', 'tcp:7381')
    if not any(line.split() == wanted for line in client.command('forward', '--list').splitlines()):
        raise RuntimeError('explicit Waydroid forwarding not verified')


def sdk_connected_state(value, pid):
    """Live SDK state, including while the watch app is normally closed."""
    return (pid.isdecimal() and value.get('status') == 'ok' and str(value.get('pid')) == pid
            and value.get('sdkStrategy') == 'ConnectIQAdbStrategy' and value.get('deviceStatus') == 'CONNECTED')


def connected(client):
    pid = client.command('shell', 'pidof', desk.BRIDGE).strip()
    value = client.probe('sdk_state', bridge=True)
    return sdk_connected_state(value, pid)


def owned_android_line(line, pids):
    match = re.match(r'\d\d-\d\d \S+\s+(\d+)\s+\d+\s+[A-Z]\s+', line)
    return bool(match and (match[1] in pids or any(pkg in line for pkg in (desk.OSMAND, desk.BRIDGE))))


def capture_android(stream, path, pids):
    # Filter before writing; do not retain unrelated Android crash contents.
    with path.open('w', buffering=1) as out:
        for line in stream:
            if owned_android_line(line, pids): out.write(line)


def prepare(client, cfg, out):
    out.mkdir(parents=True, exist_ok=False)
    client.command('shell', 'am', 'start', '-W', '-n', desk.OSMAND + '/net.osmand.plus.activities.MapActivity')
    ready_deadline = time.monotonic() + 60
    while client.probe('state').get('status') != 'ok':
        if time.monotonic() >= ready_deadline: raise RuntimeError('OsmAnd did not finish initializing')
        time.sleep(.5)
    # Open UI BEFORE using the foreground service control.
    client.command('shell', 'am', 'start', '-W', '-n', desk.BRIDGE + '/net.osmand.junction.bridge.NavigationActivity')
    checked_probe(client, 'stop_tethered', True)
    checked_probe(client, 'start_tethered', True)
    forward(client)
    try:
        with socket.create_connection(('127.0.0.1', 1234), timeout=1):
            pass
    except OSError:
        with (out / 'simulator.log').open('wb') as log:
            subprocess.Popen([str(Path(cfg['garmin_sdk']).expanduser() / 'bin/simulator')],
                             stdout=log, stderr=subprocess.STDOUT, env=sdk_env(cfg), start_new_session=True)
    print('In the Garmin simulator select Connection → Start. Waiting up to 180 seconds; no watch sends yet.', flush=True)
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        if connected(client):
            save(out / 'ready.json', {'status': 'connected', 'utc': utc(), 'bridgePid': client.command('shell', 'pidof', desk.BRIDGE).strip()})
            print('Verified CONNECTED. The suite run command can now deploy the live watch app.', flush=True)
            return
        time.sleep(1)
    raise RuntimeError('simulator menu connection not established; inspect prepare evidence')


class Tail:
    """Incremental log reader: no whole-run buffer, bounded recent events."""
    def __init__(self, path):
        self.path = path
        self.offset = 0
        self.partial = ''

    def read(self):
        if not self.path.exists():
            return []
        with self.path.open() as f:
            f.seek(self.offset); text = f.read(); self.offset = f.tell()
        text = self.partial + text
        parts = text.split('\n'); self.partial = parts.pop()
        return parts


class Progress:
    def __init__(self, now):
        self.last_draw = now
        self.first_draw = None
        self.draws = deque(maxlen=64)
        self.draw_modes = {}
        self.acks = deque(maxlen=64)
        self.confirmed_events = deque(maxlen=128)
        self.event_id = 0
        self.confirmed = Counter()
        self.last_active = now
        self.memory_peak = 0
        self.failure = None
        self.expected_exit = False
        self.exit_reason = None
        self.states = Counter()

    def watch(self, line, now):
        if re.search(r'(Unhandled Exception|Out Of Memory|Unexpected Type|Error:|Stack:)', line, re.I):
            self.failure = 'watch_runtime_error'
        m = re.search(r'JUNCTION_DRAW seq=(-?\d+) state=(\w+)', line)
        if m:
            seq, state = int(m[1]), m[2]; self.last_draw = now
            if self.first_draw is None: self.first_draw = now
            if len(self.draws) == self.draws.maxlen: self.draw_modes.pop(self.draws[0], None)
            self.draws.append((seq, state))
            mode = re.search(r' mode=(\w+)', line)
            self.draw_modes[(seq, state)] = mode[1] if mode else None
            self.states[state] += 1
        m = re.search(r'JUNCTION_SUITE_EXIT reason=(duration|completed)', line)
        if m:
            self.expected_exit = True; self.exit_reason = m[1]
        m = re.search(r'JUNCTION_SUITE_HEALTH used=(\d+)', line)
        if m:
            self.memory_peak = max(self.memory_peak, int(m[1]))
        self.correlate(now)

    def android(self, line, now):
        m = re.search(r'DRAW_ACK generation=(\d+) seq=(\d+) state=(\w+)', line)
        if m:
            self.acks.append((int(m[1]), int(m[2]), m[3]))
        if 'DEVICE_STATUS NOT_CONNECTED' in line:
            self.failure = 'sdk_disconnected'
        if 'FATAL EXCEPTION' in line or 'Fatal signal' in line:
            self.failure = 'android_fatal_event'
        self.correlate(now)

    def correlate(self, now):
        for ack in list(self.acks):
            generation, seq, state = ack
            pair = (seq, state)
            if pair in self.draws:
                self.acks.remove(ack); self.draws.remove(pair)
                self.confirmed[pair[1]] += 1
                self.event_id += 1
                self.confirmed_events.append({'id': self.event_id, 'generation': generation, 'seq': seq,
                    'state': state, 'mode': self.draw_modes.pop(pair, None), 'at': now})
                if pair[1] == 'active':
                    self.last_active = now


def test_build(cfg, out, seconds, arrival_goal=0):
    """Same live NavigationInput/decoder/renderer, bounded observer and normal exit."""
    out.mkdir(parents=True, exist_ok=True)
    (out / 'BuildInput.mc').write_text('''import Toybox.Lang;
import Toybox.System;
const REPLAY_MODE = false;
const NAVIGATION_MODE = true;
function createInput(app as JunctionApp) as InputAdapter { return new SuiteInput(app.nav); }
class SuiteInput extends NavigationInput {
    private var _started as Number = 0;
    private var _health as Number = 0;
    private var _arrivals as Number = 0;
    private var _activeSeen as Boolean = false;
    private var _arrivalAt as Number = 0;
    private var _lastArrival as String = "";
    function initialize(state as NavigationState) { NavigationInput.initialize(state,false); }
    function start() as Void { _started=System.getTimer();_health=_started;NavigationInput.start(); }
    function didDraw(scene as Dictionary?,status as String) as Void {
        NavigationInput.didDraw(scene,status);
        if(status.equals("active")) { _activeSeen=true; }
        if(scene!=null && status.equals("arrived") && _activeSeen) {
            var identity=scene["session"]+":"+scene["generation"];
            if(!identity.equals(_lastArrival)) {
                _arrivals+=1;_arrivalAt=System.getTimer();_lastArrival=identity;
            }
            _activeSeen=false;
        }
    }
    function afterFrame() as Void {
        var now=System.getTimer();
        if(now-_health>=10000) {
            var stats=System.getSystemStats();
            System.println("JUNCTION_SUITE_HEALTH used="+stats.usedMemory+" free="+stats.freeMemory+" elapsedMs="+(now-_started));
            _health=now;
        }
        // Leave time for the final real drawing ACK and host arrival check.
        if(''' + str(arrival_goal) + '''>0 && _arrivals>=''' + str(arrival_goal) + ''' && now-_arrivalAt>=10000) {
            System.println("JUNCTION_SUITE_EXIT reason=completed");System.exit();
        }
        if(now-_started>=''' + str(seconds * 1000) + ''') {
            System.println("JUNCTION_SUITE_EXIT reason=duration");System.exit();
        }
    }
}
''')
    watch = dev.TOOL_DIR / 'watch'
    jungle = out / 'suite.jungle'
    jungle.write_text('project.manifest = ' + json.dumps(str(watch / 'manifest.xml')) + '\nbase.resourcePath = ' + json.dumps(str(watch / 'resources')) + '\nbase.sourcePath = ' + ';'.join(json.dumps(str(p)) for p in (watch / 'source', out.resolve())) + '\n')
    if dev.build_watch(cfg, out / 'build', jungle=jungle):
        raise RuntimeError('suite watch build failed')
    return json.loads((out / 'build/build.json').read_text())


def run_suite(client, cfg, suite, plan, selection, out, policy):
    seconds = policy['seconds']
    out.mkdir(parents=True, exist_ok=False)
    save(out / 'suite.json', suite); save(out / 'plan.json', plan); save(out / 'selection.json', selection)
    tooling = out / 'tooling'; tooling.mkdir()
    for name in ('sim_suite.py', 'desk.py'):
        (tooling / name).write_bytes((dev.TOOL_DIR / name).read_bytes())
    result = {'status': 'running', 'scope': 'live Waydroid + Garmin simulator; no physical devices',
              'suiteSha256': digest(suite), 'selectionSha256': digest(selection),
              'toolingSha256': {name: dev.sha256(tooling / name) for name in ('sim_suite.py', 'desk.py')},
              'startedUtc': utc(), 'secondsLimit': seconds, 'runPolicy': policy,
              'attempts': [], 'unexecuted': []}
    save(out / 'result.json', result)
    watch = logs = None
    log_thread = None
    try:
        if not policy['repeat'] and suite.get('kind') != 'short_native_routes':
            raise RuntimeError('routine profiles require a short native-route suite; full routes are explicit endurance only')
        if selection != choose_routes(suite, plan):
            raise RuntimeError('fixed top-five density selection for this exact native plan required')
        scenarios = profile_scenarios(suite, selection, policy)
        result['requiredScenarios'] = [s['id'] for s in scenarios]
        result['excludedByRunProfile'] = [sid for sid in selection['active'] if sid not in result['requiredScenarios']]
        result['simulation'] = selection['simulation']
        if plan['suiteSha256'] != digest(suite) or any(plan.get('routes', {}).get(s['id'], {}).get('status') != 'planned' for s in suite['scenarios']):
            raise RuntimeError('complete native route plan for this exact suite required')
        forward(client)
        if not connected(client):
            raise RuntimeError('CONNECTED tethered bridge required before watch deployment; run prepare first')
        if client.probe('state').get('deskVersion', 0) < 2:
            raise RuntimeError('updated debug native simulation controls required before watch deployment')
        # We only operate the isolated Waydroid apps. No installs or resets.
        checked_probe(client, 'grant_bridge')
        checked_probe(client, 'cancel')
        build = test_build(cfg, out / 'watch', seconds, 0 if policy['repeat'] else len(scenarios))
        build['testInputSha256'] = dev.sha256(out / 'watch/BuildInput.mc')
        save(out / 'watch-build.json', build)
        if not connected(client): raise RuntimeError('SDK connection lost during build; no watch deployment attempted')
        base_pids = {pkg: client.command('shell', 'pidof', pkg).strip() for pkg in (desk.OSMAND, desk.BRIDGE)}
        if any(not pid.isdecimal() for pid in base_pids.values()):
            raise RuntimeError('source and bridge processes must be running')
        result['initialPids'] = base_pids
        result['androidApi'] = client.command('shell', 'getprop', 'ro.build.version.sdk').strip()
        result['sourceHead'] = dev.git_head(dev.REPO_ROOT)
        for pkg in base_pids:
            (out / (pkg + '-exit-info-before.txt')).write_text(client.command('shell', 'dumpsys', 'activity', 'exit-info', pkg))
        logs = subprocess.Popen(client.adb + ['logcat', '-T', '1', '-b', 'main', '-b', 'crash', '-v', 'threadtime',
            '-s', 'JunctionBridge:I', 'AndroidRuntime:E', 'libc:F', 'ActivityManager:I', '*:S'], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        log_thread = threading.Thread(target=capture_android, args=(logs.stdout, out / 'bridge.log', set(base_pids.values())), daemon=True)
        log_thread.start()
        watch_file = (out / 'watch.log').open('wb')
        watch = subprocess.Popen([str(Path(cfg['garmin_sdk']).expanduser() / 'bin/monkeydo'), build['artifact'], 'fr970'],
                                 env=sdk_env(cfg), stdout=watch_file, stderr=subprocess.STDOUT, start_new_session=True)
        started = time.monotonic(); deadline = started + seconds
        tails = Tail(out / 'watch.log'), Tail(out / 'bridge.log')
        progress = Progress(started)

        def poll():
            now = time.monotonic()
            for line in tails[0].read(): progress.watch(line, now)
            for line in tails[1].read(): progress.android(line, now)
            if progress.failure:
                raise RuntimeError(progress.failure)
            if logs.poll() is not None:
                raise RuntimeError('android_log_stream_ended')
            if watch.poll() is not None and now < deadline - 2:
                raise RuntimeError('watch_client_exited_unexpectedly')
            if progress.first_draw is not None and now - progress.last_draw > 12:
                raise RuntimeError('watch_draw_gap_over_12_seconds')
            return now

        # A new client must produce a NEW callback, not pass from an old build log.
        while progress.first_draw is None:
            poll()
            if time.monotonic() - started > 30:
                raise RuntimeError('no_initial_watch_frame')
            time.sleep(.2)
        result['watchStartupSeconds'] = progress.first_draw - started
        started = progress.first_draw
        deadline = started + seconds
        by_id = {p['id']: [p['lat'], p['lon']] for p in suite['points']}
        index = 0
        with (out / 'samples.jsonl').open('w', buffering=1) as samples:
            while time.monotonic() < deadline - 10 and (policy['repeat'] or index < len(scenarios)):
                scenario = scenarios[index % len(scenarios)]
                attempt = {'scenario': scenario['id'], 'cycle': index // len(scenarios) + 1,
                           'status': 'running', 'startedSeconds': time.monotonic() - started}
                print(f'Starting {scenario["id"]}, cycle {attempt["cycle"]}', flush=True)
                result['attempts'].append(attempt); save(out / 'result.json', result)
                scenario_out = out / f'{index+1:04d}-{scenario["id"]}'
                scenario_out.mkdir()
                checked_probe(client, 'cancel')
                desk.prepare_endpoints(client, by_id[scenario['from']], by_id[scenario['to']], scenario_out)
                route = json.loads((scenario_out / 'route.json').read_text())
                if environment_hashes(client, route) != plan.get('environment'):
                    raise RuntimeError('map or Android APK changed since native plan')
                poll()
                if time.monotonic() >= deadline - 10:
                    attempt['status'] = 'time_budget'
                    break
                # The bridge is already armed. Start with its Activity in front
                # so normal navigation-start prompts cannot block the unattended run.
                client.command('shell', 'am', 'start', '-W', '-n', desk.BRIDGE + '/net.osmand.junction.bridge.NavigationActivity')
                checked_probe(client, 'start', simulation=selection['simulation'])
                attempt['routeTimeoutSeconds'] = native_route_timeout(route, selection['simulation'])
                route_deadline = min(deadline, time.monotonic() + attempt['routeTimeoutSeconds'])
                active_generations = set(); full_active = 0; last_event = progress.event_id
                observations = NativeObservations(); attempt['nativeObservations'] = observations.summary
                live_started = None; routes = {}; last_pid_check = 0; last_checkpoint = 0
                while time.monotonic() < route_deadline:
                    now = poll()
                    source = checked_probe(client, 'state')
                    observation = observations.sample(source)
                    if observation:
                        with (scenario_out / 'observations.jsonl').open('a') as evidence:
                            evidence.write(json.dumps(dict(observation, atSeconds=now-started)) + '\n')
                    api = client.probe(bridge=True)
                    if api.get('status') != 'decoded':
                        raise RuntimeError('source_snapshot_' + str(api.get('status')))
                    scene = api['scene']
                    if scene['state'] == 'active': active_generations.add(scene['generation'])
                    for event in progress.confirmed_events:
                        if event['id'] > last_event and event['state'] == 'active' and event['generation'] in active_generations and event['mode'] not in (None, 'unavailable'):
                            full_active += 1
                    last_event = progress.event_id
                    capture = desk.capture_active_route(client, source, scenario_out, routes)
                    sample = {'atSeconds': now - started, 'scenario': scenario['id'], 'cycle': attempt['cycle'],
                              'source': source, 'api': api, 'routeCapture': capture}
                    samples.write(json.dumps(sample, separators=(',', ':')) + '\n')
                    if now - last_checkpoint >= 30:
                        result.update(lastSampleUtc=utc(), sampledWatchMemoryPeakBytes=progress.memory_peak,
                                      watchDrawStates=dict(progress.states), acknowledgedStates=dict(progress.confirmed))
                        save(out / 'result.json', result)
                        print(f'{scenario["id"]}: {api.get("scene", {}).get("state")} / {int(now-started)} s elapsed', flush=True)
                        last_checkpoint = now
                    if now - last_pid_check >= 5:
                        for pkg, pid in base_pids.items():
                            if client.command('shell', 'pidof', pkg).strip() != pid:
                                raise RuntimeError('android_process_changed_' + pkg)
                        last_pid_check = now
                    if source.get('following') and source.get('simulating') and live_started is None:
                        expected_mode = 'real_mode' if selection['simulation']['mode'] == 'realistic' else 'const_mode'
                        if source.get('simulationMode') != expected_mode or (expected_mode == 'const_mode' and source.get('simulationSpeedMps') != selection['simulation']['speedMps']):
                            raise RuntimeError('source_native_simulation_configuration_mismatch')
                        live_started = now; progress.last_active = now
                        attempt['simulationStartedSeconds'] = now-started
                        client.command('shell', 'am', 'start', '-W', '-n', desk.OSMAND + '/net.osmand.plus.activities.MapActivity')
                    if live_started is None and now - (started + attempt['startedSeconds']) > 30:
                        raise RuntimeError('simulation_did_not_start')
                    if live_started is not None and source.get('following') and now - progress.last_active > 12:
                        raise RuntimeError('active_watch_ack_gap_over_12_seconds')
                    if source.get('routeFinished') and scene['state'] == 'arrived' and any(e['state'] == 'arrived' and e['generation'] == scene['generation'] for e in progress.confirmed_events):
                        if full_active == 0:
                            raise RuntimeError('arrival_without_active_watch_evidence')
                        attempt.update(status='pass', completedSeconds=now-started,
                                       activeDrawAcks=full_active, nativeSimulationSeconds=now-live_started,
                                       routeElapsedSeconds=now-started-attempt['startedSeconds'])
                        print(f'{scenario["id"]}: native arrival and watch arrival acknowledged', flush=True)
                        break
                    time.sleep(1)
                else:
                    attempt['status'] = 'time_budget' if time.monotonic() >= deadline else 'route_timeout'
                    if attempt['status'] == 'route_timeout':
                        raise RuntimeError('route_timeout')
                save(out / 'result.json', result)
                index += 1
            checked_probe(client, 'cancel')
        all_routes_passed = all(any(a['scenario'] == s['id'] and a['status'] == 'pass' for a in result['attempts']) for s in scenarios)
        # A single pass exits after its last actual arrival. No idle wait until
        # the full cap, no forced SDK termination and no transport changes.
        exit_deadline = min(deadline+10, time.monotonic()+20) if all_routes_passed and not policy['repeat'] else deadline+10
        while time.monotonic() < exit_deadline and watch.poll() is None:
            for line in tails[0].read(): progress.watch(line, time.monotonic())
            time.sleep(.2)
        for line in tails[0].read(): progress.watch(line, time.monotonic())
        if watch.poll() != 0 or not progress.expected_exit or progress.failure:
            raise RuntimeError(progress.failure or 'watch_did_not_exit_normally')
        result['watchExitReason'] = progress.exit_reason
        result['sampledWatchMemoryPeakBytes'] = progress.memory_peak
        result['watchDrawStates'] = dict(progress.states)
        result['status'] = 'pass'
    except KeyboardInterrupt:
        result.update(status='interrupted', reason='operator_interrupt')
        if result['attempts'] and result['attempts'][-1]['status'] == 'running':
            result['attempts'][-1]['status'] = 'interrupted'
    except Exception as error:
        result.update(status='fail', errorType=type(error).__name__, reason=str(error))
        if result['attempts'] and result['attempts'][-1]['status'] == 'running':
            result['attempts'][-1]['status'] = 'failed'
    finally:
        passed = {a['scenario'] for a in result['attempts'] if a['status'] == 'pass'}
        result['unexecuted'] = [sid for sid in result.get('requiredScenarios', selection.get('active', [])) if sid not in passed]
        result['parked'] = selection.get('parked', [])
        if result['status'] == 'pass' and result['unexecuted']:
            result['status'] = 'incomplete'
        result['endedUtc'] = utc()
        if logs is not None:
            logs.terminate()
            try: logs.wait(timeout=5)
            except subprocess.TimeoutExpired: logs.kill(); logs.wait()
        if log_thread is not None: log_thread.join(timeout=5)
        # On failure preserve the live client for inspection; its bounded input
        # will exit at the declared duration. Never auto-relaunch or kill the SDK.
        if watch is not None and watch.poll() is None:
            result['watchClientRetainedPid'] = watch.pid
            result['watchExit'] = 'bounded observer still running; preserved after failure'
        if watch is not None and result['status'] != 'pass':
            try:
                result['sourceCleanup'] = client.probe('stop').get('status')
            except Exception:
                result['sourceCleanup'] = 'unavailable'
        for pkg in (desk.OSMAND, desk.BRIDGE):
            try:
                text = client.command('shell', 'dumpsys', 'activity', 'exit-info', pkg, timeout=10)
                (out / (pkg + '-exit-info.txt')).write_text(text)
            except Exception:
                pass
        save(out / 'result.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    create = sub.add_parser('create'); create.add_argument('--points', type=Path, required=True); create.add_argument('--out', type=Path, required=True)
    select = sub.add_parser('select'); select.add_argument('--suite', type=Path, required=True); select.add_argument('--plan', type=Path, required=True); select.add_argument('--out', type=Path, required=True)
    for name in ('plan', 'prepare', 'run'):
        p = sub.add_parser(name); p.add_argument('--waydroid-config', type=Path, required=True); p.add_argument('--out', type=Path, required=True)
        if name != 'prepare': p.add_argument('--suite', type=Path, required=True)
        if name != 'plan': p.add_argument('--garmin-config', type=Path, required=True)
        if name == 'run':
            p.add_argument('--plan', type=Path, required=True); p.add_argument('--hours', type=float)
            p.add_argument('--profile', choices=('smoke', 'regression', 'endurance'), default='regression')
            p.add_argument('--selection', type=Path, required=True)
    args = parser.parse_args()
    out = private_path(args.out)
    try:
        if args.command == 'create':
            if out.exists(): raise ValueError('refusing to replace an existing suite')
            suite = make_suite(json.loads(args.points.expanduser().read_text())['points'])
            out.parent.mkdir(parents=True, exist_ok=True); save(out, suite)
            write_route_report(suite, {}, out.parent / 'routes.md')
            print(f'Fixed suite saved: {len(suite["scenarios"])} directed routes; SHA-256 {digest(suite)}')
            return 0
        if args.command == 'select':
            suite = load_suite(args.suite); plan_path = private_path(args.plan); plan = json.loads(plan_path.read_text())
            if plan['suiteSha256'] != digest(suite): raise ValueError('plan belongs to another suite')
            for scenario in suite['scenarios']:
                record = plan['routes'][scenario['id']]
                capture = plan_path.parent / scenario['id'] / 'route.json'
                if dev.sha256(capture) != record['captureSha256']: raise ValueError('native route capture changed')
                route = json.loads(capture.read_text())
                record['turns'] = sum(d['turn'] != 'C' for d in route['directions'])
                record['constantSimulationEstimates'] = {str(speed): native_constant_seconds(route, speed) for speed in (10, 20)}
            save(plan_path, plan)
            selection = choose_routes(suite, plan)
            if out.exists() and json.loads(out.read_text()) != selection: raise ValueError('refusing to change an existing selection')
            save(out, selection)
            write_route_report(suite, plan, out.parent / 'all-routes.md')
            write_route_report(suite, plan, out.parent / 'routes.md', selection)
            print('Fixed active routes:', ', '.join(selection['active']), '; parked:', len(selection['parked']))
            return 0
        suite = load_suite(args.suite) if args.command != 'prepare' else None
        cfg = json.loads(args.garmin_config.expanduser().read_text()) if hasattr(args, 'garmin_config') else None
        policy = run_policy(args.profile, args.hours) if args.command == 'run' else None
        # Serializes preparation, planning and execution for this task's simulators.
        lock_path = dev.REPO_ROOT / 'build/garmin-review/sim-suite.lock'
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with lock_path.open('w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            client = connect(args.waydroid_config)
            if args.command == 'plan':
                plan_routes(client, suite, out); print('Native route plan and routes.md written. No navigation simulation started.')
            elif args.command == 'prepare': prepare(client, cfg, out)
            else:
                plan = json.loads(private_path(args.plan).read_text())
                selection = json.loads(private_path(args.selection).read_text())
                result = run_suite(client, cfg, suite, plan, selection, out, policy)
                print('Suite result:', result['status'], '; see result.json in the requested output folder')
                return 0 if result['status'] == 'pass' else 1
        return 0
    except Exception as error:
        # Detailed errors may include private deep links; keep terminal text bounded.
        out.parent.mkdir(parents=True, exist_ok=True)
        save(out.parent / 'sim-suite-error.json', {'status': 'failed', 'errorType': type(error).__name__, 'reason': str(error), 'utc': utc()})
        print('Suite command failed; inspect sim-suite-error.json beside the requested output.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
