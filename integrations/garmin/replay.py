"""Recorded geometry replay using the real Monkey C state and vector renderer."""
import copy
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import time
from protocol.scene import validate


def watch_test_result(text, code, minimum=1):
    """SDK 9.3.0 on this host exits 1 for BOTH pass and fail (calibrated).

    Require the actual complete result summary; a process exit or isolated PASS
    lines cannot establish success. Preserve the raw exit code in the report.
    """
    import re
    count=re.search(r'^Ran (\d+) tests?\s*$',text,re.MULTILINE)
    summary=re.search(r'^PASSED \(passed=(\d+), failed=0, errors=0\)\s*$',text,re.MULTILINE)
    tests=int(count.group(1)) if count else 0
    ok=(code in (0,1) and tests>=minimum and summary is not None
        and int(summary.group(1))==tests and not re.search(r'^FAILED\b|^ERROR\b',text,re.MULTILINE))
    return ok,tests


def frames(recorded):
    scene=recorded['scene']
    result=[]
    for at in range(0,6000,1000):
        packet=copy.deepcopy(scene)
        packet.update(distanceM=120-at//100,progressAgeMs=250,speedDmps=100)
        result.append({'atMs':at,'scene':packet})
    packet=copy.deepcopy(scene);packet.update(state='recalculating',geometryMode='unavailable',anchors=[],paths=[],reason='controlled replay reroute')
    result.append({'atMs':6000,'scene':packet})
    packet=copy.deepcopy(scene);packet['distanceM']=35;result.append({'atMs':8000,'scene':packet})
    result.append({'atMs':9000,'scene':None})
    packet=copy.deepcopy(scene);packet['fixAgeMs']=6000;result.append({'atMs':14000,'scene':packet})
    packet=copy.deepcopy(scene);packet.update(state='idle',geometryMode='unavailable',anchors=[],paths=[],reason='controlled replay stop')
    result.append({'atMs':17000,'scene':packet})
    for at in (19000,21000,23000,25000):
        packet=copy.deepcopy(scene);packet['distanceM']=120;result.append({'atMs':at,'scene':packet})
    for frame in result:
        if frame['scene'] is not None:
            errors=validate(frame['scene'])
            if errors:raise ValueError('; '.join(errors))
    return result


def monkey(value):
    if value is None:return 'null'
    if type(value) is bool:return 'true' if value else 'false'
    if isinstance(value,(int,float)):return str(value)
    if isinstance(value,str):return json.dumps(value,ensure_ascii=True)
    if isinstance(value,list):return '['+','.join(monkey(v) for v in value)+']'
    if isinstance(value,dict):return '{'+','.join(monkey(k)+'=>'+monkey(v) for k,v in value.items())+'}'
    raise ValueError('unsupported fixture value')


def generate(recorded, directory, watch, speed, scenario, hold=False):
    directory.mkdir(parents=True,exist_ok=True)
    frame_list=frames(recorded)
    source='import Toybox.Lang;\nmodule ReplayFixtures {\n'
    source+='function frames() as Array<Dictionary> { return '+monkey(frame_list)+'; }\n'
    source+='function speed() as Float { return '+str(float(speed))+'; }\n'
    source+='function hold() as Boolean { return '+monkey(hold)+'; }\n'
    source+='function scenario() as String { return '+monkey(scenario)+'; }\n'
    source+='function sourceHash() as String { return '+monkey(recorded['provenance']['captureSha256'])+'; }\n}\n'
    (directory/'ReplayFixtures.mc').write_text(source)
    jungle=directory/'replay.jungle'
    jungle.write_text('project.manifest = '+json.dumps(str(watch/'manifest.xml'))+'\nbase.resourcePath = '+json.dumps(str(watch/'resources'))+
                      '\nbase.sourcePath = '+ ';'.join(json.dumps(str(p)) for p in [watch/'source',watch/'replay',directory])+'\n')
    (directory/'frames.json').write_text(json.dumps(frame_list,indent=2)+'\n')
    return jungle


def run_replay(dev,cfg,out_dir,scenario,speed,timeout,capture=None,maneuver=None,hold=False,context=None):
    out_dir.mkdir(parents=True,exist_ok=True)
    report={'mode':'replay','status':'fail','scenario':scenario,'speed':speed,'physical_watch':'not_tested','visual_confirmation':'not_checked'}
    client=None
    try:
        if capture:
            from replay_scene import recorded
            value=recorded(capture,maneuver if maneuver is not None else (10 if scenario=='fork' else 5),context)
        elif context:raise ValueError('--context requires --capture and its original maneuver index')
        else:
            value=json.loads((dev.TOOL_DIR/'fixtures/recorded'/f'{scenario}.json').read_text())
        (out_dir/'recorded-scene.json').write_text(json.dumps(value,indent=2)+'\n')
        jungle=generate(value,out_dir.resolve()/'generated',dev.TOOL_DIR/'watch',speed,scenario,hold)
        if dev.build_watch(cfg,out_dir/'build',jungle=jungle):raise RuntimeError('actual watch compilation failed')
        build=json.loads((out_dir/'build/build.json').read_text());sdk=Path(cfg.get('garmin_sdk') or os.environ['GARMIN_SDK_HOME']).expanduser()
        env=os.environ.copy()
        if cfg.get('garmin_library_path'):env['LD_LIBRARY_PATH']=str(Path(cfg['garmin_library_path']).expanduser())+os.pathsep+env.get('LD_LIBRARY_PATH','')
        try:
            with socket.create_connection(('127.0.0.1',1234),timeout=1):report['simulator']='reused_listener'
        except ConnectionRefusedError:
            with (out_dir/'simulator.log').open('wb') as log:
                process=subprocess.Popen([str(sdk/'bin/simulator')],stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True)
            report.update(simulator='started',simulator_pid=process.pid)
            deadline=time.monotonic()+15
            while True:
                if process.poll() is not None:raise RuntimeError('simulator exited; see simulator.log')
                try:
                    with socket.create_connection(('127.0.0.1',1234),timeout=1):break
                except ConnectionRefusedError:
                    if time.monotonic()>deadline:raise RuntimeError('simulator did not start')
                    time.sleep(.1)
        command=[str(sdk/'bin/monkeydo'),build['artifact'],'fr970']
        with (out_dir/'runtime.log').open('wb') as log:
            client=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True)
        report.update(command=command,client_pid=client.pid,artifact_sha256=build['sha256'],capture_sha256=value['provenance']['captureSha256'],
                      generated_source_sha256=dev.sha256(jungle.parent/'ReplayFixtures.mc'),
                      frames_sha256=dev.sha256(jungle.parent/'frames.json'))
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            text=(out_dir/'runtime.log').read_text(errors='replace')
            if 'JUNCTION_REPLAY_REJECT' in text:raise RuntimeError('shared decoder rejected replay input')
            if 'JUNCTION_DRAW' in text and 'state=active' in text:
                report.update(status='pass',evidence='actual app drew captured scene',client_retained=True)
                break
            if client.poll() is not None:raise RuntimeError('deployment exited before the captured scene drew')
            time.sleep(.1)
        else:raise RuntimeError('no captured-scene draw before deadline')
    except (OSError,ValueError,RuntimeError) as error:report['reason']=str(error)
    if report['status']!='pass' and client is not None and client.poll() is None:
        try:os.killpg(client.pid,signal.SIGTERM);client.wait(timeout=5)
        except subprocess.TimeoutExpired:os.killpg(client.pid,signal.SIGKILL);client.wait()
        except ProcessLookupError:pass
    (out_dir/'run.json').write_text(json.dumps(report,indent=2)+'\n')
    dev.log(f"watch replay: {report['status']}; evidence: {out_dir}")
    return 0 if report['status']=='pass' else 1


def check_protocol(dev,out_dir):
    import re
    out_dir.mkdir(parents=True,exist_ok=True)
    env=os.environ.copy();env['PYTHONDONTWRITEBYTECODE']='1'
    result=subprocess.run([dev.sys.executable,'-m','unittest','discover','-s',str(dev.TOOL_DIR/'tests'),'-p','test_scene.py','-v'],
                          cwd=dev.REPO_ROOT,env=env,capture_output=True,text=True,timeout=60)
    text=result.stdout+result.stderr;(out_dir/'tests.log').write_text(text)
    count=re.search(r'Ran (\d+) tests?',text)
    ok=result.returncode==0 and count is not None and int(count.group(1))>0
    report={'suite':'scene-contract-and-diagnostic-conversion','status':'pass' if ok else 'fail','tests':int(count.group(1)) if count else 0,
            'scope':'scene only; live request/epoch envelope and production Java geometry remain pending'}
    (out_dir/'check.json').write_text(json.dumps(report,indent=2)+'\n')
    dev.log(f"scene checks: {report['status']}; evidence: {out_dir}")
    return 0 if ok else 1


def check_watch(dev,cfg,out_dir):
    import re
    out_dir.mkdir(parents=True,exist_ok=True)
    watch=dev.TOOL_DIR/'watch';jungle=out_dir.resolve()/'tests.jungle'
    jungle.write_text('project.manifest = '+json.dumps(str(watch/'manifest.xml'))+'\nbase.resourcePath = '+json.dumps(str(watch/'resources'))+
                      '\nbase.sourcePath = '+ ';'.join(json.dumps(str(p)) for p in [watch/'source',watch/'live',watch/'tests'])+'\n')
    report={'suite':'actual-monkey-c-state-tests','status':'fail'};client=None
    try:
        if dev.build_watch(cfg,out_dir/'build',jungle=jungle,unit_tests=True):raise RuntimeError('unit-test compilation failed')
        build=json.loads((out_dir/'build/build.json').read_text());sdk=Path(cfg.get('garmin_sdk') or os.environ['GARMIN_SDK_HOME']).expanduser()
        env=os.environ.copy()
        if cfg.get('garmin_library_path'):env['LD_LIBRARY_PATH']=str(Path(cfg['garmin_library_path']).expanduser())+os.pathsep+env.get('LD_LIBRARY_PATH','')
        command=[str(sdk/'bin/monkeydo'),build['artifact'],'fr970','-t']
        with (out_dir/'tests.log').open('wb') as log:
            client=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True)
        code=client.wait(timeout=60)
        text=(out_dir/'tests.log').read_text(errors='replace')
        ok,count=watch_test_result(text,code,minimum=11)
        report.update(status='pass' if ok else 'fail',exit_code=code,tests=count,command=command,
                      verdict_basis='complete SDK summary; exit 1 calibrated against known pass and known fail on SDK 9.3.0')
    except (OSError,RuntimeError,subprocess.TimeoutExpired) as error:report['reason']=str(error)
    finally:
        if client is not None and client.poll() is None:
            try:os.killpg(client.pid,signal.SIGTERM);client.wait(timeout=5)
            except subprocess.TimeoutExpired:os.killpg(client.pid,signal.SIGKILL);client.wait()
            except ProcessLookupError:pass
        (out_dir/'check.json').write_text(json.dumps(report,indent=2)+'\n')
    dev.log(f"watch state checks: {report['status']}; evidence: {out_dir}")
    return 0 if report['status']=='pass' else 1
