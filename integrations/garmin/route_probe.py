#!/usr/bin/env python3
"""Capture real route data from the debug-only, shell-protected OsmAnd probe.

Default: read the current calculated route. --baseline opens the public Lazio
scenario; --motorcycle prepares that built-in profile before --baseline.
--install validates and update-installs the already-built isolated debug APK.
All output belongs under ignored build/garmin-review, not in tracked fixtures.
"""
import argparse
import collections
import json
import math
from pathlib import Path
import re
import shlex
import subprocess
import sys
import time
import uuid

PACKAGE = "net.osmand.plus.junction"
RECEIVER = PACKAGE + "/net.osmand.plus.routing.companion.DebugRouteProbeReceiver"
BASELINE_URL = "https://osmand.net/map?start=41.4472,12.6286&end=41.4675,12.9030&profile=motorcycle"


def command(args, timeout=30):
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or f"command failed: {args[0]}")
    return result.stdout


def sample(adb, action="CAPTURE_ROUTE"):
    request = uuid.uuid4().hex
    command(adb + ["shell", shlex.join(["am", "broadcast", "-n", RECEIVER, "-a",
        "net.osmand.junction." + action, "--es", "request", request])])
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        for reader in (["cat", f"/sdcard/Android/data/{PACKAGE}/files/junction-desk/route.json"],
                       ["run-as", PACKAGE, "cat", "files/junction-probe/latest.json"]):
            result = subprocess.run(adb + ["exec-out", *reader], capture_output=True, text=True, timeout=15)
            if result.returncode == 0:
                try:
                    value = json.loads(result.stdout)
                except ValueError:
                    continue
                if value.get("request") == request:
                    return value
        time.sleep(0.2)
    raise RuntimeError("probe did not publish this request; check debug APK, receiver permission and app initialization")


def validate(value):
    errors = []
    if value.get("probeVersion") != 1 or value.get("status") not in ("captured", "truncated") or value.get("coherent") is not True:
        return ["capture is not a coherent supported route sample"]
    points = value.get("locationsLatLon", [])
    references = value.get("locationSegmentIds", [])
    ids = [s.get("id") for s in value.get("segments", [])]
    if not points or len(points) != value.get("locationCount") or len(references) != len(points):
        errors.append("route point/reference counts differ or are empty")
    if len(ids) != len(set(ids)) or any(ref not in ids for ref in references):
        errors.append("unknown or duplicate selected-segment reference")
    for point in points:
        if len(point) != 2 or not all(isinstance(n, (int, float)) and math.isfinite(n) for n in point) or not (-90 <= point[0] <= 90 and -180 <= point[1] <= 180):
            errors.append("invalid route coordinate")
            break
    for direction in value.get("directions", []):
        if not isinstance(direction.get("routePointOffset"), int) or not 0 <= direction["routePointOffset"] < len(points):
            errors.append("maneuver offset outside route")
            break
    return errors


def summarize(value):
    entries = [a for segment in value["segments"] for a in segment["attachments"]]
    return {key: value.get(key) for key in ("status", "coherent", "applicationMode", "routingProfile", "derivedProfile",
                "locationCount", "segmentReferenceCount", "uniqueSegmentCount", "distanceM")} | {
        "maneuvers": len(value["directions"]), "attachmentNodes": len(entries),
        "attachedStorage": dict(collections.Counter(a["attachedStorage"] for a in entries)),
        "attachedBranchEntries": sum(len(a["attached"]) for a in entries),
        "preAttachedBranchEntries": sum(len(a["preAttached"]) for a in entries),
        "limitations": value["limitations"],
    }


def main():
    # Imported only for execution; validation tests need no SDK/device.
    sys.dont_write_bytecode = True
    import dev
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path.home() / ".config/osmand-junction/dev-config.json")
    parser.add_argument("--out", type=Path, default=dev.REPO_ROOT / "build/garmin-review/route-probe")
    parser.add_argument("--baseline", action="store_true")
    parser.add_argument("--motorcycle", action="store_true")
    parser.add_argument("--install", action="store_true")
    parser.add_argument("--apk", type=Path, help="explicit isolated APK (for example the x86 Waydroid variant)")
    args = parser.parse_args()
    if args.motorcycle and not args.baseline:
        parser.error("--motorcycle requires --baseline so the route is recalculated with that profile")
    args.out.mkdir(parents=True, exist_ok=True)
    report = {"status": "fail", "mode": "actual-route-probe"}
    try:
        cfg = json.loads(args.config.expanduser().read_text())
        adb = dev.selected_adb(cfg)
        if args.install:
            apk = args.apk or dev.REPO_ROOT / "OsmAnd/build/outputs/apk/androidFullOpenglArm64/debug/OsmAnd-androidFull-opengl-arm64-debug.apk"
            aapt = Path(dev.sdk_root(cfg)).expanduser() / "build-tools/36.0.0/aapt"
            badging = command([str(aapt), "dump", "badging", str(apk)])
            if not re.search(r"^package: name='net\.osmand\.plus\.junction' ", badging, re.MULTILINE):
                raise RuntimeError("refusing to install APK without verified separate development identity")
            report["apk_sha256"] = dev.sha256(apk)
            (args.out / "install.log").write_text(command(adb + ["install", "-r", str(apk)], timeout=90))
        if args.baseline:
            command(adb + ["shell", "am", "start", "-W", "-n", PACKAGE + "/net.osmand.plus.activities.MapActivity"])
            if args.motorcycle:
                for _ in range(10):
                    prepared = sample(adb, "PREPARE_MOTORCYCLE")
                    if prepared.get("status") == "profile_prepared":
                        break
                    time.sleep(0.5)
                else:
                    raise RuntimeError("motorcycle profile setup did not finish")
            launch = ["am", "start", "-W", "-n", PACKAGE + "/net.osmand.plus.activities.MapActivity",
                      "-a", "android.intent.action.VIEW", "-d", BASELINE_URL]
            command(adb + ["shell", shlex.join(launch)])
        for attempt in range(20):
            value = sample(adb)
            errors = validate(value)
            if not errors and (not args.motorcycle or value.get("applicationMode") == "motorcycle"):
                (args.out / "route.json").write_text(json.dumps(value, indent=2) + "\n")
                summary = summarize(value)
                (args.out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
                template = Path(__file__).with_name("route-viewer.html").read_text()
                embedded = json.dumps(value, separators=(",", ":")).replace("<", "\\u003c")
                (args.out / "review.html").write_text(template.replace("__ROUTE_DATA__", embedded))
                report.update(status="pass", summary=summary, route_sha256=dev.sha256(args.out / "route.json"))
                break
            if args.baseline and attempt in (3, 8):
                # A successful am exit is insufficient after Android restores an updated activity.
                command(adb + ["shell", shlex.join(launch)])
            time.sleep(0.5)
        else:
            report["last_probe"] = value
            raise RuntimeError("no validated ready route in the requested mode")
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
        report["reason"] = str(error)
    (args.out / "run.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
