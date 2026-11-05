#!/usr/bin/env python3
"""Recreate the required sibling source checkouts next to this cloned repository.

--check inspects existing checkouts without network or writes. Default mode only
clones missing directories. Existing directories are never reset or overwritten.
Toolchains, private keys, maps and local device configuration are separate setup.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
LOCK = Path(__file__).with_name("workspace.lock.json")


def git(*args):
    return subprocess.run(["git", *map(str, args)], capture_output=True, text=True, check=True).stdout.strip()


def bootstrap(check_only):
    lock = json.loads(LOCK.read_text())
    failed = False
    for dependency in lock["siblings"]:
        name = dependency["directory"]
        if name not in ("resources", "core-legacy", "build"):
            raise ValueError("unsupported dependency directory")
        target = ROOT.parent / name
        if not target.exists():
            if check_only:
                print(f"missing: {name}")
                failed = True
                continue
            print(f"cloning locked build input: {name}", flush=True)
            git("clone", "--no-checkout", "--filter=blob:none", dependency["url"], target)
            git("-C", target, "fetch", "--depth=1", "origin", dependency["commit"])
            git("-C", target, "checkout", "--detach", dependency["commit"])
        try:
            top = Path(git("-C", target, "rev-parse", "--show-toplevel")).resolve()
            if top != target.resolve():
                print(f"not a standalone dependency checkout: {name}; left untouched")
                failed = True
                continue
            head = git("-C", target, "rev-parse", "HEAD")
            dirty = git("-C", target, "status", "--porcelain")
        except subprocess.CalledProcessError:
            print(f"invalid existing checkout: {name}; left untouched")
            failed = True
            continue
        if head != dependency["commit"] or dirty:
            print(f"needs review: {name}; revision_match={head == dependency['commit']}, dirty={bool(dirty)}; left untouched")
            failed = True
        else:
            print(f"ok: {name} {head}")
    return 1 if failed else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        return bootstrap(args.check)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"bootstrap failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
