#!/usr/bin/env python3
"""Prepare pinned iOS siblings and build the separate Junction development apps."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile

HERE = Path(__file__).resolve().parent
LOCK = json.loads((HERE / "workspace.lock.json").read_text())


def run(args, cwd=None, log=None, env=None):
    print("+", " ".join(map(str, args)), flush=True)
    if log:
        with Path(log).open("w") as output:
            result = subprocess.run(list(map(str, args)), cwd=cwd, env=env,
                                    stdout=output, stderr=subprocess.STDOUT)
        if result.returncode:
            print("\n".join(Path(log).read_text(errors="replace").splitlines()[-100:]))
            raise subprocess.CalledProcessError(result.returncode, args)
    else:
        subprocess.run(list(map(str, args)), cwd=cwd, env=env, check=True)


def output(args, cwd=None):
    return subprocess.check_output(args, cwd=cwd, text=True).strip()


def bootstrap(workspace):
    for name, source in LOCK["sources"].items():
        target = workspace / name
        if not target.exists():
            target.mkdir()
            run(["git", "init", "-q", target])
            run(["git", "-C", target, "remote", "add", "origin",
                 "https://github.com/" + source["repository"] + ".git"])
            run(["git", "-C", target, "fetch", "--depth=1", "origin", source["commit"]])
            run(["git", "-C", target, "checkout", "--detach", "FETCH_HEAD"])
        if output(["git", "rev-parse", "--show-toplevel"], target) != str(target):
            raise ValueError(f"Not a standalone checkout: {target}")
        if output(["git", "rev-parse", "HEAD"], target) != source["commit"]:
            raise ValueError(f"Revision differs; existing checkout left untouched: {target}")
        if output(["git", "status", "--porcelain"], target):
            raise ValueError(f"Dirty checkout left untouched: {target}")


def prepare(workspace):
    cmake = workspace / "build/CMakeLists.txt"
    original = cmake.read_text()
    broken = 'if ((OR CMAKE_COMPILER_FAMILY STREQUAL "clang") AND'
    if original.count(broken) != 1:
        raise ValueError("Pinned upstream CMake repair no longer matches; review the source lock")
    cmake.write_text(original.replace(broken, 'if ((CMAKE_COMPILER_FAMILY STREQUAL "clang") AND', 1))
    ios = workspace / "ios"
    project = ios / "OsmAnd.xcodeproj/project.pbxproj"
    source = project.read_text()
    # Remove upstream signing identities, including SDK-specific overrides.
    source = re.sub(r'^\s*(?:"?DEVELOPMENT_TEAM(?:\[[^\]]+\])?"?|'
                    r'"?PROVISIONING_PROFILE(?:_SPECIFIER)?(?:\[[^\]]+\])?"?|'
                    r'"?CODE_SIGN_IDENTITY(?:\[[^\]]+\])?"?) = .*;\n', '', source,
                    flags=re.MULTILINE)
    source = source.replace('APP_DISPLAY_NAME = "OsmAnd Maps";',
                            'APP_DISPLAY_NAME = "OsmAnd Junction";')
    source = source.replace('APP_URL_SCHEME = osmandmaps;',
                            'APP_URL_SCHEME = osmandjunction;')
    # Header preprocessing otherwise overrides PRODUCT_BUNDLE_IDENTIFIER.
    source = source.replace('OSMAND_BUNDLE_ID=net.osmand.maps"',
                            'OSMAND_BUNDLE_ID=net.osmand.junction.ios"')
    source = source.replace('PRODUCT_BUNDLE_IDENTIFIER = net.osmand.maps;',
                            'PRODUCT_BUNDLE_IDENTIFIER = net.osmand.junction.ios;')
    project.write_text(source)
    # A separate development identity cannot use OsmAnd's privileged profiles.
    for name in ("OsmAnd Maps.entitlements", "OsmAnd Nightly.entitlements"):
        (ios / name).write_text('<?xml version="1.0" encoding="UTF-8"?>\n'
                               '<plist version="1.0"><dict/></plist>\n')
    resource = ios / "Scripts/download-shipped-resources.sh"
    resource.write_text(resource.read_text().replace("http://builder.osmand.net/", "https://builder.osmand.net/"))
    overlay = HERE / "source"
    if overlay.exists():
        run([sys.executable, HERE / "install.py", "--ios", ios])


def build(workspace, destination):
    if sys.platform != "darwin":
        raise ValueError("The actual iOS build must run on the macOS Actions runner")
    logs = workspace / "junction-artifacts"
    logs.mkdir(exist_ok=True)
    env = dict(os.environ, LANG="en_US.UTF-8", DOWNLOAD_PREBUILT_QT_FILES="true")
    env["JAVA_HOME"] = output(["/usr/libexec/java_home", "-v", "17"])
    run(["bash", "-e", workspace / "ios/prepare.sh"], cwd=workspace,
        env=env, log=logs / "prepare.log")
    sdk = "iphoneos" if destination == "device" else "iphonesimulator"
    target = "generic/platform=iOS" if destination == "device" else "generic/platform=iOS Simulator"
    core = workspace / "baked/fat-ios-clang.xcode"
    if not (core / "OsmAnd_projects.xcodeproj").is_dir():
        raise ValueError("Native project generation did not produce OsmAnd_projects.xcodeproj; inspect prepare.log")
    for name in ("ZERO_CHECK", "OsmAndCore_static_standalone"):
        run(["xcodebuild", "-project", "OsmAnd_projects.xcodeproj", "-target", name,
             "-sdk", sdk, "-configuration", "Release", "-jobs", "2",
             "ARCHS=arm64", "ONLY_ACTIVE_ARCH=YES", "CODE_SIGNING_ALLOWED=NO"],
            cwd=core, env=env, log=logs / f"core-{name}.log")
    run([sys.executable, workspace / "ios/.github/scripts/configure-shared-build-for-ci.py"])
    derived = workspace / "junction-derived"
    run(["xcodebuild", "-workspace", workspace / "ios/OsmAnd.xcworkspace",
         "-scheme", "OsmAnd Maps", "-configuration", "Release", "-sdk", sdk,
         "-destination", target, "-derivedDataPath", derived, "-jobs", "2",
         "ARCHS=arm64", "ONLY_ACTIVE_ARCH=YES", "CODE_SIGNING_ALLOWED=NO",
         "CODE_SIGNING_REQUIRED=NO", "DEVELOPMENT_TEAM=", "PROVISIONING_PROFILE_SPECIFIER=",
         "PRODUCT_BUNDLE_IDENTIFIER=net.osmand.junction.ios",
         "CURRENT_PROJECT_VERSION=" + os.environ.get("GITHUB_RUN_NUMBER", "1"),
         "MARKETING_VERSION=0.3.0", "build"], cwd=workspace, env=env,
        log=logs / "osmand-build.log")
    apps = {"OsmAnd-Junction": derived / f"Build/Products/Release-{sdk}/OsmAnd Maps.app"}
    bridge = HERE / "bridge"
    if (bridge / "project.yml").exists():
        run(["xcodegen", "generate", "--spec", bridge / "project.yml"])
        run(["xcodebuild", "-project", bridge / "JunctionBridge.xcodeproj",
             "-scheme", "JunctionBridge", "-configuration", "Release", "-sdk", sdk,
             "-destination", target, "-derivedDataPath", workspace / "bridge-derived",
             "CODE_SIGNING_ALLOWED=NO", "ARCHS=arm64", "build"], env=env,
            log=logs / "bridge-build.log")
        apps["Junction-Bridge"] = workspace / f"bridge-derived/Build/Products/Release-{sdk}/Junction Bridge.app"
    records = {"platform": destination, "signing": "unsigned", "sources": LOCK["sources"],
               "androidCommit": output(["git", "rev-parse", "HEAD"], workspace / "android"),
               "xcode": output(["xcodebuild", "-version"]), "artifacts": {}}
    for name, app in apps.items():
        if not app.is_dir():
            raise ValueError(f"Expected actual application missing: {app}")
        package = logs / (name + ("-unsigned.ipa" if destination == "device" else "-simulator.tar.gz"))
        if destination == "device":
            staging = logs / (name + "-package")
            payload = staging / "Payload"
            payload.mkdir(parents=True)
            shutil.copytree(app, payload / app.name, symlinks=True)
            run(["ditto", "-c", "-k", "--sequesterRsrc", "--keepParent", payload, package])
            shutil.rmtree(staging)
        else:
            with tarfile.open(package, "w:gz") as archive:
                archive.add(app, arcname=app.name)
        records["artifacts"][package.name] = hashlib.sha256(package.read_bytes()).hexdigest()
    (logs / "build.json").write_text(json.dumps(records, indent=2) + "\n")
    (logs / "SIGNING.txt").write_text(
        "These are unsigned development artifacts, not installable signed iPhone apps.\n"
        "Apple signing/provisioning or a separate personal-device signing step is required.\n"
        "Compilation is not proof of navigation, Bluetooth or locked-screen operation.\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("bootstrap", "prepare", "build"))
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--destination", choices=("device", "simulator"), default="device")
    args = parser.parse_args()
    root = args.workspace.resolve()
    try:
        if args.operation == "bootstrap": bootstrap(root)
        elif args.operation == "prepare": prepare(root)
        else: build(root, args.destination)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f"iOS CI failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
