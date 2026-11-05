#!/usr/bin/env python3
"""Development tooling for the OsmAnd -> Garmin junction companion.

Command interface (defined in tasks/plan.md section 5):
  doctor   - report environment readiness and source lock (T00)
  build    - build osmand|bridge|watch|all        (planned, later tasks)
  check    - run geometry|api|protocol|watch suites (planned, later tasks)
  run      - run replay|desk scenarios             (planned, later tasks)
  iterate  - incremental build/deploy/launch loop   (planned, later tasks)

`doctor`, `build --target watch|bridge`, and `run --mode watch-smoke|echo-prepare|echo-smoke`
are implemented. Other targets and commands fail explicitly instead of pretending success.

Local configuration: --config <json> (see dev-config.example.json),
environment variables, then defaults. Paths and device serials are local
configuration; the example file is the only committed form.
"""

import argparse
import hashlib
import json
import os
import platform
import re
import signal
import shutil
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOL_DIR = Path(__file__).resolve().parent

# Capability: (key, required for baseline build, needed-by task)
REQUIRED = {
    "java": "Java 17+ (bytecode target 17)",
    "gradle_wrapper": "Gradle wrapper (pinned 8.11.1)",
    "android_sdk": "Android SDK platform 36 + build-tools 36.0.0",
    "ndk": "Android NDK (legacy core build runs for all variants)",
    "resources": "OsmAnd-resources sibling checkout",
    "core_legacy": "OsmAnd-core-legacy sibling checkout",
    "build_dir": "OsmAnd-build sibling (used by legacy externals setup)",
}
OPTIONAL = {
    "garmin_sdk": "Connect IQ SDK (needed from T02)",
    "adb": "ADB + reachable device (needed from T01 install/run)",
    "kvm": "/dev/kvm (emulator acceleration, optional)",
    "core": "OsmAnd-core sibling (only for local OpenGL core AAR)",
}


def log(msg):
    print(msg, file=sys.stderr)


def run(cmd, timeout=30):
    """Run a command, return (exit_code, stdout, stderr)."""
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
        return proc.returncode, proc.stdout, proc.stderr
    except FileNotFoundError:
        return 127, "", f"not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout after {timeout}s: {' '.join(cmd)}"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def git_head(repo):
    code, out, _ = run(["git", "-C", str(repo), "rev-parse", "HEAD"])
    if code != 0:
        return None
    return out.strip()


def git_branch(repo):
    code, out, _ = run(["git", "-C", str(repo), "branch", "--show-current"])
    return out.strip() if code == 0 else None


def git_remote(repo):
    code, out, _ = run(["git", "-C", str(repo), "remote", "get-url", "origin"])
    return out.strip() if code == 0 else None


def git_status_porcelain(repo):
    code, out, _ = run(["git", "-C", str(repo), "status", "--porcelain"])
    if code != 0:
        return None
    return [line for line in out.splitlines() if line.strip()]


def check_java(cfg):
    java_home = cfg.get("java_home") or os.environ.get("JAVA_HOME")
    java_bin = shutil.which("java")
    if java_home:
        cand = Path(java_home) / "bin" / "java"
        if cand.exists():
            java_bin = str(cand)
    if not java_bin:
        return {"present": False, "detail": "java not found on PATH"}
    code, out, err = run([java_bin, "-version"], timeout=15)
    text = (out + err).strip().replace("\n", " | ")
    m = re.search(r'version "(\d+)(?:\.(\d+))?', text)
    major = int(m.group(1)) if m else 0
    ok = code == 0 and major >= 17
    return {
        "present": True,
        "ok": ok,
        "version": text,
        "java_home": java_home or "",
    }


def check_gradle_wrapper():
    gradlew = REPO_ROOT / "gradlew"
    props = REPO_ROOT / "gradle" / "wrapper" / "gradle-wrapper.properties"
    if not gradlew.exists():
        return {"present": False, "detail": "gradlew missing"}
    jar = REPO_ROOT / "gradle" / "wrapper" / "gradle-wrapper.jar"
    info = {
        "present": True,
        "ok": props.is_file() and jar.is_file(),
        "gradlew": str(gradlew.relative_to(REPO_ROOT)),
        "detail": "wrapper script, properties and JAR required",
    }
    if props.exists():
        m = re.search(r"distributionUrl=.*gradle-([\d.]+)-", props.read_text())
        info["pinned_version"] = m.group(1) if m else "unknown"
        info["wrapper_properties_sha256"] = sha256(props)
    return info


def sdk_root(cfg):
    return (
        cfg.get("android_sdk")
        or os.environ.get("ANDROID_SDK_ROOT")
        or os.environ.get("ANDROID_HOME")
        or ""
    )


def check_android_sdk(cfg):
    root = sdk_root(cfg)
    if not root:
        return {"present": False, "detail": "no android_sdk config / ANDROID_SDK_ROOT / ANDROID_HOME"}
    root = Path(root).expanduser()
    if not root.is_dir():
        return {"present": False, "detail": f"configured SDK dir missing: {root}"}
    platform_ok = (root / "platforms" / "android-36").is_dir()
    buildtools_ok = (root / "build-tools" / "36.0.0").is_dir()
    sdkmgr = root / "cmdline-tools" / "latest" / "bin" / "sdkmanager"
    sdkver = ""
    if sdkmgr.exists():
        code, out, _ = run([str(sdkmgr), "--version"], timeout=60)
        if code == 0:
            sdkver = out.strip().splitlines()[0] if out.strip() else ""
    return {
        "present": platform_ok and buildtools_ok,
        "ok": platform_ok and buildtools_ok,
        "path": str(root),
        "platform_36": platform_ok,
        "build_tools_36_0_0": buildtools_ok,
        "sdkmanager_version": sdkver,
        "detail": "platform-36 + build-tools 36.0.0 required (versions.gradle)",
    }


def ndk_root(cfg):
    return cfg.get("ndk") or os.environ.get("ANDROID_NDK_ROOT") or os.environ.get("ANDROID_NDK") or ""


def check_ndk(cfg):
    root = ndk_root(cfg)
    if not root:
        return {"present": False, "detail": "no ndk config / ANDROID_NDK_ROOT"}
    root = Path(root).expanduser()
    if not root.is_dir():
        return {"present": False, "detail": f"configured NDK dir missing: {root}"}
    revision = ""
    props = root / "source.properties"
    if props.exists():
        m = re.search(r"Pkg\.Revision\s*=\s*(\S+)", props.read_text())
        revision = m.group(1) if m else ""
    ndk_build = root / "ndk-build"
    return {
        "present": ndk_build.exists(),
        "ok": ndk_build.exists(),
        "path": str(root),
        "revision": revision,
        "ndk_build": ndk_build.exists(),
        "detail": "required by buildOsmAndCore (old-ndk-build.sh) for every variant",
    }


def check_sibling(name, required_markers):
    path = REPO_ROOT.parent / name
    if not path.is_dir():
        return {"present": False, "detail": f"missing sibling: {name}/"}
    markers = {m: (path / m).exists() for m in required_markers}
    head = git_head(path)
    return {
        "present": True,
        "ok": all(markers.values()),
        "path": str(path),
        "git_head": head,
        "git_branch": git_branch(path),
        "markers": markers,
    }


def check_signing_key(key):
    # Only the public modulus is emitted. Never print private key contents.
    code, out, _ = run(["openssl", "rsa", "-inform", "DER", "-in", str(key), "-noout", "-modulus"])
    match = re.fullmatch(r"Modulus=([0-9A-Fa-f]+)\s*", out)
    bits = int(match.group(1), 16).bit_length() if code == 0 and match else 0
    return {"ok": bits == 4096, "rsa_bits": bits}


def check_garmin(cfg):
    garmin = cfg.get("garmin_sdk") or os.environ.get("GARMIN_SDK_HOME") or ""
    if not garmin:
        return {"present": False, "detail": "no garmin_sdk config / GARMIN_SDK_HOME (needed from T02)"}
    garmin = Path(garmin).expanduser()
    if not garmin.is_dir():
        return {"present": False, "detail": f"configured Garmin SDK dir missing: {garmin}"}
    monkeyc = garmin / "bin" / "monkeyc"
    simulator = garmin / "bin" / "simulator"
    if not simulator.exists():
        simulator = garmin / "bin" / "connectiq"
    device = cfg.get("garmin_device") or "fr970"
    profile = Path(cfg.get("garmin_device_dir") or Path.home() / ".Garmin/ConnectIQ/Devices" / device).expanduser()
    key = Path(cfg.get("garmin_key") or Path.home() / ".config/osmand-junction/ciq_dev_key.der").expanduser()
    key_check = check_signing_key(key) if key.is_file() else {"ok": False, "rsa_bits": 0}
    profile_ok = all((profile / name).is_file() for name in ("compiler.json", "simulator.json"))
    version = ""
    compiler_ok = False
    if monkeyc.exists():
        code, out, _ = run([str(monkeyc), "--version"], timeout=15)
        if code == 0:
            compiler_ok = True
            version = out.strip().splitlines()[0] if out.strip() else ""
    missing = []
    if not compiler_ok:
        missing.append("working compiler")
    if not simulator.is_file():
        missing.append("simulator binary")
    if not profile_ok:
        missing.append(f"{device} compiler/simulator profile")
    if not key.is_file():
        missing.append("development signing key")
    elif not key_check["ok"]:
        missing.append("4096-bit RSA DER signing key (requires openssl)")
    return {
        "present": True,
        "ok": not missing,
        "path": str(garmin),
        "monkeyc": compiler_ok,
        "simulator": simulator.is_file(),
        "device": device,
        "device_profile": profile_ok,
        "signing_key_present": key.is_file(),
        "signing_key_valid": key_check["ok"],
        "signing_key_rsa_bits": key_check["rsa_bits"],
        "version": version,
        "detail": "missing " + ", ".join(missing) if missing else "compiler, profile and key present; GUI runtime not tested",
    }


def check_adb(cfg):
    serial = cfg.get("adb_serial") or ""
    root = sdk_root(cfg)
    sdk_adb = Path(root).expanduser() / "platform-tools/adb" if root else None
    adb = str(sdk_adb) if sdk_adb and sdk_adb.is_file() else shutil.which("adb")
    if not adb:
        return {"present": False, "detail": "adb not found on PATH"}
    code, out, _ = run([adb, "devices"], timeout=20)
    if code != 0:
        return {"present": True, "ok": False, "detail": "adb devices failed"}
    devices = []
    for line in out.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            devices.append(parts[0])
    selected_ok = serial in devices if serial else len(devices) == 1
    return {
        "present": True,
        "ok": bool(devices) and selected_ok,
        "adb": adb,
        "devices": devices,
        "configured_serial": serial,
        "selected_ok": selected_ok,
        "detail": "device selected" if selected_ok else "no unique authorized device; configure adb_serial explicitly when multiple devices are attached",
    }


def doctor(cfg, out_dir):
    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "host": platform.platform(),
        "python": sys.version.split()[0],
        "disk_free_bytes": shutil.disk_usage(REPO_ROOT).free,
        "source": {
            "repo": str(REPO_ROOT),
            "head": git_head(REPO_ROOT),
            "branch": git_branch(REPO_ROOT),
            "origin": git_remote(REPO_ROOT),
            "dirty_count": len(git_status_porcelain(REPO_ROOT) or []),
        },
        "checks": {},
    }

    checks = {
        "java": check_java(cfg),
        "gradle_wrapper": check_gradle_wrapper(),
        "android_sdk": check_android_sdk(cfg),
        "ndk": check_ndk(cfg),
        "resources": check_sibling(
            "resources",
            ["rendering_styles/fonts", "voice", "bundled_assets.json", "poi/poi_categories.json"],
        ),
        "core_legacy": check_sibling("core-legacy", ["externals/configure.sh"]),
        "core": check_sibling("core", ["wrappers/android"]),
        "build_dir": check_sibling("build", ["utils/functions.sh"]),
        "garmin_sdk": check_garmin(cfg),
        "adb": check_adb(cfg),
        "kvm": {
            "present": Path("/dev/kvm").exists(),
            "detail": "emulator acceleration only; physical-device desk tests are primary",
        },
    }
    report["checks"] = checks

    def ok_of(check):
        return check.get("ok", check.get("present", False))

    missing_required = [k for k in REQUIRED if not ok_of(checks[k])]
    missing_optional = [k for k in OPTIONAL if not ok_of(checks[k])]

    if missing_required:
        status = "not_ready"
        exit_code = 1
    elif missing_optional:
        status = "ready_with_warnings"
        exit_code = 0
    else:
        status = "ready"
        exit_code = 0
    report["status"] = status
    report["missing_required"] = missing_required
    report["missing_optional"] = missing_optional

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "environment.json").write_text(json.dumps(report, indent=2))
    (out_dir / "doctor.md").write_text(render_doctor_md(report))

    log(f"doctor status: {status}")
    if missing_required:
        log(f"  missing required: {', '.join(missing_required)}")
    if missing_optional:
        log(f"  missing optional: {', '.join(missing_optional)}")
    log(f"  report: {out_dir}")
    return exit_code


def render_doctor_md(report):
    lines = ["# Environment doctor", ""]
    lines.append(f"- status: **{report['status']}**")
    lines.append(f"- host: {report['host']}")
    lines.append(f"- python: {report['python']}")
    lines.append(f"- disk free: {report['disk_free_bytes'] / 1e9:.1f} GB")
    lines.append("")
    src = report["source"]
    lines.append("## Source")
    lines.append(f"- repo: `{src['repo']}`")
    lines.append(f"- HEAD: `{src['head']}`")
    lines.append(f"- branch: `{src['branch']}`")
    lines.append(f"- origin: `{src['origin']}`")
    lines.append(f"- dirty entries: {src['dirty_count']}")
    lines.append("")
    lines.append("## Checks")
    lines.append("| capability | ok | detail |")
    lines.append("| --- | --- | --- |")
    for key, check in report["checks"].items():
        ok = check.get("ok", check.get("present"))
        ok_txt = {True: "ok", False: "missing", None: "n/a"}.get(ok, str(ok))
        detail = (check.get("detail") or check.get("version") or "").replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {key} | {ok_txt} | {detail} |")
    lines.append("")
    lines.append("## Missing")
    lines.append(f"- required: {report['missing_required'] or 'none'}")
    lines.append(f"- optional: {report['missing_optional'] or 'none'}")
    return "\n".join(lines) + "\n"


def not_implemented(command):
    log(
        f"`{command}` is part of the planned interface but not implemented yet "
        f"(see tasks/todo.md; T00 implements doctor only)."
    )
    return 2


def build_watch(cfg, out_dir):
    """Compile the actual watch application and retain reproducible evidence."""
    out_dir.mkdir(parents=True, exist_ok=True)
    output = out_dir.resolve() / "Junction.prg"
    # A blocked or failed new build must not leave an old deployable artifact.
    output.unlink(missing_ok=True)
    sdk = check_garmin(cfg)
    report = {"target": "watch", "generated_utc": datetime.now(timezone.utc).isoformat()}
    if not sdk.get("ok"):
        report.update(status="blocked", reason=sdk.get("detail", "Garmin SDK unavailable"))
        (out_dir / "build.json").write_text(json.dumps(report, indent=2) + "\n")
        log(report["reason"])
        return 1
    key = Path(cfg.get("garmin_key") or Path.home() / ".config/osmand-junction/ciq_dev_key.der").expanduser()
    command = [
        str(Path(sdk["path"]) / "bin/monkeyc"),
        "-d", sdk["device"], "-o", str(output), "-y", str(key),
        "-f", str(TOOL_DIR / "watch/monkey.jungle"),
    ]
    try:
        result = subprocess.run(command, cwd=REPO_ROOT, capture_output=True, text=True, timeout=180)
        code = result.returncode
        compiler_log = result.stdout + result.stderr
    except (OSError, subprocess.TimeoutExpired) as error:
        code, compiler_log = 1, str(error)
    (out_dir / "compiler.log").write_text(compiler_log)
    report.update(
        status="pass" if code == 0 and output.is_file() else "fail",
        exit_code=code,
        command=command,
        sdk_version=sdk["version"],
        source_head=git_head(REPO_ROOT),
        source_hashes={str(p.relative_to(REPO_ROOT)): sha256(p)
                       for p in sorted((TOOL_DIR / "watch").rglob("*"))
                       if p.is_file() and "build" not in p.relative_to(TOOL_DIR / "watch").parts},
    )
    if report["status"] == "pass":
        report.update(artifact=str(output), sha256=sha256(output), bytes=output.stat().st_size)
    (out_dir / "build.json").write_text(json.dumps(report, indent=2) + "\n")
    log(f"watch build: {report['status']}; evidence: {out_dir}")
    if report["status"] != "pass":
        log(compiler_log)
    return 0 if report["status"] == "pass" else (code or 1)


def watch_frame_seen(text, build_id):
    """A compiler exit or transport connection alone is not runtime evidence."""
    pattern = rf"^JUNCTION_FRAME build={re.escape(build_id)} width=454 height=454\s*$"
    return re.search(pattern, text, re.MULTILINE) is not None


def build_bridge(cfg, out_dir):
    """Standalone Android build; keep Garmin dependencies outside OsmAnd."""
    out_dir.mkdir(parents=True, exist_ok=True)
    report = {"target": "bridge", "status": "fail", "generated_utc": datetime.now(timezone.utc).isoformat()}
    report_path = out_dir / "build.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    project = TOOL_DIR / "bridge"
    artifact = project / "build/outputs/apk/debug/JunctionBridge-debug.apk"
    artifact.unlink(missing_ok=True)
    api_aar = Path(cfg.get("osmand_api_aar") or REPO_ROOT / "OsmAnd-api/build/outputs/aar/OsmAnd-api-debug.aar").expanduser().resolve()
    sdk_check = check_android_sdk(cfg)
    if not api_aar.is_file() or not sdk_check.get("ok"):
        report.update(status="blocked", reason="Android SDK and locally built OsmAnd API AAR required")
        report_path.write_text(json.dumps(report, indent=2) + "\n")
        return 1
    env = os.environ.copy()
    env["ANDROID_SDK_ROOT"] = sdk_check["path"]
    if cfg.get("java_home"):
        env["JAVA_HOME"] = str(Path(cfg["java_home"]).expanduser())
    command = [str(REPO_ROOT / "gradlew"), "-p", str(project), "assembleDebug", "--console=plain", f"-PosmandApiAar={api_aar}"]
    try:
        result = subprocess.run(command, cwd=REPO_ROOT, env=env, capture_output=True, text=True, timeout=600)
        code, output = result.returncode, result.stdout + result.stderr
    except (OSError, subprocess.TimeoutExpired) as error:
        code, output = 1, str(error)
    (out_dir / "compiler.log").write_text(output)
    report.update(exit_code=code, command=command, osmand_api_sha256=sha256(api_aar), garmin_sdk_version="2.4.0")
    if code == 0 and artifact.is_file():
        metadata = json.loads((artifact.parent / "output-metadata.json").read_text())
        if metadata["applicationId"] == "net.osmand.junction.bridge.debug":
            report.update(status="pass", artifact=str(artifact), sha256=sha256(artifact), bytes=artifact.stat().st_size,
                          application_id=metadata["applicationId"], source_head=git_head(REPO_ROOT))
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    log(f"bridge build: {report['status']}; evidence: {out_dir}")
    if report["status"] != "pass":
        log(output)
    return 0 if report["status"] == "pass" else 1


def watch_smoke(cfg, out_dir, timeout):
    """Build, deploy and require the current app's real fr970 drawing callback.

    The callback proves execution, not visual correctness or physical transport.
    Keep the simulator window open for human inspection and subsequent updates.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    report = {"generated_utc": datetime.now(timezone.utc).isoformat(), "status": "fail",
              "mode": "watch-smoke", "visual_confirmation": "not_checked",
              "physical_watch": "not_tested"}
    report_path = out_dir / "run.json"
    # Overwrite stale success even when rebuilding fails.
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    if build_watch(cfg, out_dir / "build") != 0:
        report.update(reason="watch build failed; deployment not attempted")
        report_path.write_text(json.dumps(report, indent=2) + "\n")
        return 1
    build = json.loads((out_dir / "build/build.json").read_text())
    source = (TOOL_DIR / "watch/source/JunctionApp.mc").read_text()
    match = re.search(r'const JUNCTION_BUILD_ID = "([A-Za-z0-9_.-]+)";', source)
    if not match:
        report.update(reason="missing unambiguous build identifier")
        report_path.write_text(json.dumps(report, indent=2) + "\n")
        return 1
    report.update(build_id=match.group(1), artifact_sha256=build["sha256"])
    sdk = Path(cfg.get("garmin_sdk") or os.environ["GARMIN_SDK_HOME"]).expanduser()
    env = os.environ.copy()
    if cfg.get("garmin_library_path"):
        env["LD_LIBRARY_PATH"] = str(Path(cfg["garmin_library_path"]).expanduser()) + os.pathsep + env.get("LD_LIBRARY_PATH", "")
    client = None
    try:
        try:
            with socket.create_connection(("127.0.0.1", 1234), timeout=1):
                report["simulator"] = "reused_listener"
        except ConnectionRefusedError:
            simulator = sdk / "bin/simulator"
            with (out_dir / "simulator.log").open("wb") as log_file:
                process = subprocess.Popen([str(simulator)], stdout=log_file, stderr=subprocess.STDOUT,
                                           env=env, start_new_session=True)
            report.update(simulator="started", simulator_pid=process.pid)
            deadline = time.monotonic() + timeout
            while True:
                if process.poll() is not None:
                    raise RuntimeError("simulator exited; see simulator.log")
                try:
                    with socket.create_connection(("127.0.0.1", 1234), timeout=1):
                        break
                except ConnectionRefusedError:
                    if time.monotonic() >= deadline:
                        raise TimeoutError("simulator did not open its SDK port")
                    time.sleep(0.1)
        command = [str(sdk / "bin/monkeydo"), build["artifact"], "fr970"]
        report["command"] = command
        log_path = out_dir / "runtime.log"
        with log_path.open("wb") as log_file:
            client = subprocess.Popen(command, stdout=log_file, stderr=subprocess.STDOUT,
                                      env=env, start_new_session=True)
        deadline = time.monotonic() + timeout
        while True:
            if watch_frame_seen(log_path.read_text(errors="replace"), report["build_id"]):
                report.update(status="pass", evidence="current-build drawing callback at 454x454")
                break
            if client.poll() is not None:
                raise RuntimeError("monkeydo exited without the current build's frame callback")
            if time.monotonic() >= deadline:
                raise TimeoutError("no current-build frame callback; inspect simulator app log and runtime.log")
            time.sleep(0.1)
    except (OSError, RuntimeError) as error:
        report["reason"] = str(error)
    finally:
        # Stop only this invocation's deployment process tree, never other SDK clients.
        if client is not None:
            try:
                os.killpg(client.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                client.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(client.pid, signal.SIGKILL)
                client.wait()
        report_path.write_text(json.dumps(report, indent=2) + "\n")
    log(f"watch smoke: {report['status']}; evidence: {out_dir}")
    return 0 if report["status"] == "pass" else 1


def selected_adb(cfg):
    check = check_adb(cfg)
    if not check.get("ok"):
        raise RuntimeError(check.get("detail", "ADB unavailable"))
    serial = check["configured_serial"] or check["devices"][0]
    return [check["adb"], "-s", serial]


def bridge_trace(adb):
    code, out, _ = run(adb + ["exec-out", "run-as", "net.osmand.junction.bridge.debug", "cat", "files/echo-probe.jsonl"], timeout=10)
    if code:
        return []
    try:
        return [json.loads(line) for line in out.splitlines() if line]
    except (ValueError, TypeError):
        return []


def forward_garmin(adb):
    code, _, error = run(adb + ["forward", "tcp:7381", "tcp:7381"])
    if code:
        raise RuntimeError("ADB forwarding failed: " + error)
    code, out, _ = run(adb + ["forward", "--list"])
    if code or not any(line.split() == [adb[2], "tcp:7381", "tcp:7381"] for line in out.splitlines()):
        raise RuntimeError("the selected device's Garmin forwarding rule is absent")


def echo_acknowledged(watch_log, events):
    """Correlate phone ACKs with actual watch draws from this particular run."""
    request = re.search(r"^JUNCTION_ECHO_REQUEST epoch=(\S+) id=1 displayed=0$", watch_log, re.MULTILINE)
    if not request:
        return []
    epoch = request.group(1)
    drawn = {int(n) for n in re.findall(r"^JUNCTION_ECHO_DISPLAY id=(\d+)$", watch_log, re.MULTILINE)}
    acknowledged = set()
    for event in events:
        if event.get("transport") != "TETHERED":
            continue
        match = re.fullmatch(rf"REQUEST epoch={re.escape(epoch)} id=(\d+) displayed=(\d+)", event.get("event", ""))
        if match:
            request_id, displayed = map(int, match.groups())
            if 0 < displayed < request_id and displayed in drawn:
                acknowledged.add(displayed)
    return sorted(acknowledged)


def echo_prepare(cfg, out_dir):
    """Build/install the bridge and verify real process readiness, not am's exit."""
    out_dir.mkdir(parents=True, exist_ok=True)
    report = {"mode": "echo-prepare", "status": "fail", "physical_watch": "not_tested"}
    if build_bridge(cfg, out_dir / "bridge-build"):
        report["reason"] = "bridge build failed"
        (out_dir / "run.json").write_text(json.dumps(report, indent=2) + "\n")
        return 1
    try:
        adb = selected_adb(cfg)
        build = json.loads((out_dir / "bridge-build/build.json").read_text())
        code, out, error = run(adb + ["install", "-r", build["artifact"]], timeout=90)
        (out_dir / "install.log").write_text(out + error)
        if code:
            raise RuntimeError("bridge update installation failed")
        ready = False
        launches = []
        for attempt in range(3):
            code, out, error = run(adb + ["shell", "am", "start", "-S", "-W", "-n",
                "net.osmand.junction.bridge.debug/net.osmand.junction.bridge.EchoActivity", "--es", "transport", "tethered"], timeout=30)
            launches.append({"attempt": attempt + 1, "exit_code": code, "output": out + error})
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                _, pid, _ = run(adb + ["shell", "pidof", "net.osmand.junction.bridge.debug"], timeout=5)
                events = bridge_trace(adb)
                current = [e for e in events if str(e.get("pid")) == pid.strip() and e.get("transport") == "TETHERED"]
                if any(e.get("event") == "SDK_READY" for e in current) and any(e.get("event", "").startswith("REGISTERED ") for e in current):
                    ready = True
                    break
                time.sleep(0.2)
            if ready:
                break
        (out_dir / "launches.json").write_text(json.dumps(launches, indent=2) + "\n")
        if not ready:
            raise RuntimeError("new bridge process did not verify TETHERED SDK readiness")
        forward_garmin(adb)
        (out_dir / "bridge-trace.json").write_text(json.dumps(events, indent=2) + "\n")
        report.update(status="prepared", transport="TETHERED", bridge_sha256=build["sha256"],
                      launch_attempts=len(launches), manual_action="Enable adb Connection > Start in the simulator if not connected")
    except (OSError, RuntimeError) as error:
        report["reason"] = str(error)
    (out_dir / "run.json").write_text(json.dumps(report, indent=2) + "\n")
    log(f"echo preparation: {report['status']}; evidence: {out_dir}")
    return 0 if report["status"] == "prepared" else 1


def echo_smoke(cfg, out_dir, timeout):
    """Watch-only automatic iteration using an already connected test bridge."""
    out_dir.mkdir(parents=True, exist_ok=True)
    report = {"mode": "echo-smoke", "status": "fail", "transport": "TETHERED", "physical_watch": "not_tested"}
    client = None
    try:
        adb = selected_adb(cfg)
        forward_garmin(adb)
        events = bridge_trace(adb)
        _, pid, _ = run(adb + ["shell", "pidof", "net.osmand.junction.bridge.debug"], timeout=5)
        if not pid.strip().isdecimal():
            raise RuntimeError("bridge is not running")
        events = [e for e in events if str(e.get("pid")) == pid.strip()]
        states = [e["event"] for e in events if e.get("transport") == "TETHERED" and e.get("event", "").startswith("DEVICE_STATUS ")]
        if not events or events[-1].get("transport") != "TETHERED" or not states or states[-1] != "DEVICE_STATUS status=CONNECTED":
            raise RuntimeError("connected TETHERED bridge required; prepare it and enable the simulator's ADB connection first")
        if build_watch(cfg, out_dir / "watch-build"):
            raise RuntimeError("watch build failed; deployment not attempted")
        build = json.loads((out_dir / "watch-build/build.json").read_text())
        sdk = Path(cfg.get("garmin_sdk") or os.environ["GARMIN_SDK_HOME"]).expanduser()
        env = os.environ.copy()
        if cfg.get("garmin_library_path"):
            env["LD_LIBRARY_PATH"] = str(Path(cfg["garmin_library_path"]).expanduser()) + os.pathsep + env.get("LD_LIBRARY_PATH", "")
        command = [str(sdk / "bin/monkeydo"), build["artifact"], "fr970"]
        report.update(command=command, watch_sha256=build["sha256"])
        with (out_dir / "runtime.log").open("wb") as log_file:
            client = subprocess.Popen(command, stdout=log_file, stderr=subprocess.STDOUT, env=env, start_new_session=True)
        try:
            code = client.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            raise RuntimeError("watch echo did not exit within the bounded test deadline")
        events = bridge_trace(adb)
        (out_dir / "bridge-trace.json").write_text(json.dumps(events, indent=2) + "\n")
        watch_log = (out_dir / "runtime.log").read_text(errors="replace")
        acks = echo_acknowledged(watch_log, events)
        report.update(exit_code=code, acknowledged_draws=acks)
        if code != 0 or not all(n in acks for n in range(1, 6)) or "JUNCTION_ECHO_DONE displayed=6" not in watch_log:
            raise RuntimeError("missing same-run phone ACKs for watch-drawn replies 1 through 5, or clean watch completion")
        report.update(status="pass", evidence="actual SDK request/reply/watch draw/phone ACK; clean probe exit")
    except (OSError, RuntimeError) as error:
        report["reason"] = str(error)
    finally:
        if client is not None and client.poll() is None:
            try:
                os.killpg(client.pid, signal.SIGTERM)
                client.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(client.pid, signal.SIGKILL)
                client.wait()
            except ProcessLookupError:
                pass
        (out_dir / "run.json").write_text(json.dumps(report, indent=2) + "\n")
    log(f"echo smoke: {report['status']}; evidence: {out_dir}")
    return 0 if report["status"] == "pass" else 1


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command")

    p_doctor = sub.add_parser("doctor", help="report environment readiness and source lock")
    p_doctor.add_argument("--out", default="build/garmin-review/doctor", help="output directory (repo-relative)")
    p_doctor.add_argument("--config", help="local config JSON (see dev-config.example.json)")
    p_build = sub.add_parser("build", help="build an implementation target")
    p_build.add_argument("--target", required=True, choices=("osmand", "bridge", "watch", "all"))
    p_build.add_argument("--out", default="build/garmin-review/build")
    p_build.add_argument("--config", help="private local config JSON")
    p_run = sub.add_parser("run", help="run an implementation scenario")
    p_run.add_argument("--mode", required=True, choices=("watch-smoke", "echo-prepare", "echo-smoke", "replay", "desk"))
    p_run.add_argument("--out", default="build/garmin-review/watch-smoke")
    p_run.add_argument("--config", help="private local config JSON")
    p_run.add_argument("--timeout", type=float, default=45, help="runtime timeout in seconds")
    for name in ("check", "iterate"):
        p = sub.add_parser(name, help=f"[planned] {name}")
        p.add_argument("args", nargs="*")

    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 0

    cfg = {}
    config_path = Path(args.config).expanduser() if getattr(args, "config", None) else Path.home() / ".config/osmand-junction/dev-config.json"
    if config_path.is_file():
        cfg = json.loads(config_path.read_text())
    elif getattr(args, "config", None):
        parser.error(f"configuration file not found: {config_path}")

    if args.command == "doctor":
        out_dir = Path(args.out)
        if not out_dir.is_absolute():
            out_dir = REPO_ROOT / out_dir
        return doctor(cfg, out_dir)
    if args.command == "build" and args.target in ("watch", "bridge"):
        out_dir = Path(args.out)
        if not out_dir.is_absolute():
            out_dir = REPO_ROOT / out_dir
        return {"watch": build_watch, "bridge": build_bridge}[args.target](cfg, out_dir)
    if args.command == "run" and args.mode in ("watch-smoke", "echo-prepare", "echo-smoke"):
        if args.timeout <= 0:
            parser.error("--timeout must be positive")
        out_dir = Path(args.out)
        if not out_dir.is_absolute():
            out_dir = REPO_ROOT / out_dir
        if args.mode == "echo-prepare":
            return echo_prepare(cfg, out_dir)
        return {"watch-smoke": watch_smoke, "echo-smoke": echo_smoke}[args.mode](cfg, out_dir, args.timeout)
    return not_implemented(args.command)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
