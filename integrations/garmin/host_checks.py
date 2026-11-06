"""Real Gradle/JVM checks; no ADB, installation or device discovery."""
import json
import os
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET


def check(dev,cfg,out,suite):
    out.mkdir(parents=True,exist_ok=True)
    if suite=='geometry':
        task=':OsmAnd-java:test';pattern='net.osmand.router.junction.*'
        reports=dev.REPO_ROOT/'OsmAnd-java/build/test-results/test'
        files='TEST-net.osmand.router.junction.*.xml';minimum=25
    elif suite=='api':
        task=':OsmAnd-api:testDebugUnitTest';pattern='net.osmand.aidlapi.info.AppInfoNavigationSnapshotTest'
        reports=dev.REPO_ROOT/'OsmAnd-api/build/test-results/testDebugUnitTest'
        files='TEST-net.osmand.aidlapi.info.AppInfoNavigationSnapshotTest.xml';minimum=8
    elif suite=='bridge':
        task='testDebugUnitTest';pattern='net.osmand.junction.bridge.*'
        reports=dev.TOOL_DIR/'bridge/build/test-results/testDebugUnitTest'
        files='TEST-net.osmand.junction.bridge.*.xml';minimum=15
    else:raise ValueError('unknown host suite')
    command=[str(dev.REPO_ROOT/'gradlew'),'-Dorg.gradle.jvmargs=-Xmx2048m -Dfile.encoding=UTF-8','--max-workers=2',task,'--tests',pattern,'--console=plain']
    if suite=='bridge':
        command[1:1]=['-p',str(dev.TOOL_DIR/'bridge'),'-PosmandApiAar='+str(dev.REPO_ROOT/'OsmAnd-api/build/outputs/aar/OsmAnd-api-debug.aar')]
    env=os.environ.copy()
    if cfg.get('android_sdk'):env['ANDROID_SDK_ROOT']=str(Path(cfg['android_sdk']).expanduser())
    if cfg.get('ndk'):env['ANDROID_NDK_ROOT']=str(Path(cfg['ndk']).expanduser())
    if cfg.get('java_home'):env['JAVA_HOME']=str(Path(cfg['java_home']).expanduser())
    report={'suite':suite,'status':'fail','command':command,'device_access':'none'}
    try:
        # Only generated reports for this suite; missing outputs also make Gradle
        # rerun it rather than using an old result after a failed compilation.
        for path in reports.glob(files):path.unlink()
        with (out/'gradle.log').open('wb') as log:
            result=subprocess.run(command,cwd=dev.REPO_ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=300)
        counts={'tests':0,'failures':0,'errors':0,'skipped':0}
        for path in reports.glob(files):
            root=ET.parse(path).getroot()
            for key in counts:counts[key]+=int(root.attrib.get(key,0))
        ok=result.returncode==0 and counts['tests']>=minimum and all(counts[k]==0 for k in ('failures','errors','skipped'))
        report.update(counts,exit_code=result.returncode,status='pass' if ok else 'fail',source_head=dev.git_head(dev.REPO_ROOT))
    except (OSError,subprocess.TimeoutExpired,ET.ParseError) as error:report['reason']=str(error)
    (out/'check.json').write_text(json.dumps(report,indent=2)+'\n')
    dev.log(f"host {suite} checks: {report['status']}; evidence: {out}")
    return 0 if report['status']=='pass' else 1
