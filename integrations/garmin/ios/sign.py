#!/usr/bin/env python3
"""Sign the two compiled device apps using existing Apple-issued credentials.

No Apple account login, certificate creation or profile renewal is attempted.
Secrets and decoded profiles are confined to a temporary directory/keychain.
"""
import argparse
import base64
import datetime
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

APPS = {
    "OsmAnd-Junction": ("net.osmand.junction.ios", "IOS_OSMAND_PROFILE_BASE64"),
    "Junction-Bridge": ("net.osmand.junction.bridge.ios", "IOS_BRIDGE_PROFILE_BASE64"),
}
SECRETS = ("IOS_CERTIFICATE_BASE64", "IOS_CERTIFICATE_PASSWORD", *[p[1] for p in APPS.values()])


def quiet(args):
    result = subprocess.run(list(map(str, args)), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        # security/codesign output may contain certificate names or device metadata.
        raise ValueError(f"{Path(args[0]).name} failed (exit {result.returncode}); no credentials printed")
    return result.stdout


def credentials():
    missing = [key for key in SECRETS if key not in os.environ or
               (not os.environ[key] and key != "IOS_CERTIFICATE_PASSWORD")]
    if missing:
        raise ValueError("Missing signing secrets: " + ", ".join(missing))


def profile(path, bundle):
    value = plistlib.loads(quiet(["security", "cms", "-D", "-i", path]))
    expiry = value["ExpirationDate"].replace(tzinfo=datetime.timezone.utc)
    if expiry <= datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=5):
        raise ValueError("An Apple provisioning profile is expired or about to expire")
    entitlements = value["Entitlements"]
    team = entitlements.get("com.apple.developer.team-identifier")
    app_id = entitlements.get("application-identifier", "")
    prefixes = value.get("ApplicationIdentifierPrefix", [])
    if not team or not any(app_id == p + "." + bundle for p in prefixes):
        raise ValueError("Provisioning profile must explicitly match the Junction bundle identifier")
    if not value.get("ProvisionedDevices"):
        raise ValueError("Use a device development/ad hoc profile; this workflow does not publish to the App Store")
    groups = entitlements.get("keychain-access-groups", [])
    entitlements["keychain-access-groups"] = [group[:-1] + bundle if group.endswith(".*") else group for group in groups]
    if any("*" in group for group in entitlements["keychain-access-groups"]):
        raise ValueError("Unsupported wildcard keychain entitlement")
    certificates = {hashlib.sha1(c).hexdigest().upper() for c in value["DeveloperCertificates"]}
    return entitlements, team, certificates


def sign(source, destination):
    if sys.platform != "darwin":
        raise ValueError("Actual Apple signing requires the macOS runner")
    credentials()
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="junction-sign-") as directory:
        temporary = Path(directory)
        keychain = temporary / "signing.keychain-db"
        password = os.urandom(32).hex()
        certificate = temporary / "certificate.p12"
        certificate.write_bytes(base64.b64decode(os.environ["IOS_CERTIFICATE_BASE64"], validate=True))
        original_keychains = quiet(["security", "list-keychains", "-d", "user"]).decode()
        search_list = re.findall(r'"([^"\n]+)"', original_keychains)
        try:
            quiet(["security", "create-keychain", "-p", password, keychain])
            quiet(["security", "set-keychain-settings", "-lut", "7200", keychain])
            quiet(["security", "unlock-keychain", "-p", password, keychain])
            quiet(["security", "list-keychains", "-d", "user", "-s", keychain, *search_list])
            quiet(["security", "import", certificate, "-k", keychain, "-P",
                   os.environ["IOS_CERTIFICATE_PASSWORD"], "-T", "/usr/bin/codesign"])
            quiet(["security", "set-key-partition-list", "-S", "apple-tool:,apple:,codesign:",
                   "-s", "-k", password, keychain])
            identities = quiet(["security", "find-identity", "-v", "-p", "codesigning", keychain]).decode()
            manifest = {"signing": "Apple device profiles", "artifacts": {}}
            teams = set()
            for name, (bundle, secret) in APPS.items():
                archive = source / f"{name}-unsigned.ipa"
                if not archive.is_file(): raise ValueError(f"Missing compiled artifact: {archive.name}")
                staging = temporary / name
                with zipfile.ZipFile(archive) as zipped:
                    if any(Path(p.filename).is_absolute() or ".." in Path(p.filename).parts for p in zipped.infolist()):
                        raise ValueError("Unsafe IPA archive entry")
                quiet(["ditto", "-x", "-k", archive, staging])
                apps = list((staging / "Payload").glob("*.app"))
                if len(apps) != 1: raise ValueError("Expected one actual application per IPA")
                app = apps[0]
                if any(p.is_symlink() and not p.resolve().is_relative_to(staging) for p in staging.rglob("*")):
                    raise ValueError("IPA symlink escapes the package")
                if any(app.rglob("*.appex")) or any(app.rglob("*.app")):
                    raise ValueError("Embedded extensions require separate profiles; review this build")
                if plistlib.loads((app / "Info.plist").read_bytes()).get("CFBundleIdentifier") != bundle:
                    raise ValueError("Compiled application has the wrong bundle identity")
                provision = temporary / f"{name}.mobileprovision"
                provision.write_bytes(base64.b64decode(os.environ[secret], validate=True))
                entitlements, team, allowed = profile(provision, bundle)
                teams.add(team)
                if len(teams) != 1: raise ValueError("The two applications must belong to the same Apple team")
                identity = next((fingerprint for fingerprint in sorted(allowed) if fingerprint in identities), None)
                if not identity: raise ValueError("Imported signing identity is not authorized by the provisioning profile")
                shutil.copyfile(provision, app / "embedded.mobileprovision")
                entitlement_path = temporary / f"{name}.plist"
                entitlement_path.write_bytes(plistlib.dumps(entitlements))
                nested = [*app.rglob("*.dylib"), *app.rglob("*.framework")]
                for item in sorted(nested, key=lambda p: len(p.parts), reverse=True):
                    quiet(["codesign", "--force", "--sign", identity, "--keychain", keychain,
                           "--timestamp=none", item])
                quiet(["codesign", "--force", "--sign", identity, "--keychain", keychain,
                       "--timestamp=none", "--generate-entitlement-der", "--entitlements", entitlement_path, app])
                quiet(["codesign", "--verify", "--deep", "--strict", app])
                result = destination / f"{name}-signed.ipa"
                quiet(["ditto", "-c", "-k", "--sequesterRsrc", "--keepParent", staging / "Payload", result])
                manifest["artifacts"][result.name] = hashlib.sha256(result.read_bytes()).hexdigest()
            (destination / "signing.json").write_text(json.dumps(manifest, indent=2) + "\n")
        finally:
            quiet(["security", "list-keychains", "-d", "user", "-s", *search_list])
            if keychain.exists(): quiet(["security", "delete-keychain", keychain])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check-credentials", action="store_true")
    args = parser.parse_args()
    try:
        if args.check_credentials: credentials()
        elif args.source and args.output: sign(args.source.resolve(), args.output.resolve())
        else: parser.error("Provide --source and --output, or --check-credentials")
    except (ValueError, OSError, KeyError, plistlib.InvalidFileException) as error:
        print(f"Signing failed: {error}", file=sys.stderr)
        sys.exit(1)
