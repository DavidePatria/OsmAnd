# Junction companion workspace

OsmAnd calculates the motorcycle route on Android. The planned standalone Garmin Forerunner 970 app will show a compact junction schematic. **Current priority: prove that OsmAnd's actual route/branch data is useful before further watch integration.**

Start with [current status](tasks/START_HERE.md), [verification evidence](tasks/verification.md), and the [execution tasks](tasks/todo.md). [AGENTS.md](AGENTS.md) records project instructions. This is an implementation in progress, not a finished navigation companion.

## One repository to push and clone

This directory is the Git project. It retains upstream OsmAnd history and contains the custom Android code, independent companion projects, tooling and documentation. No outer Git repository or custom submodule is required. The original upstream remote has not been changed; create/configure your personal destination and push manually. This checkout is shallow: an upstream fork already has the base history; for an unrelated empty repository, fetch the complete upstream history first (`git fetch --unshallow origin`).

```text
workspace/                    # local parent directory, not another required repo
  your-cloned-project/        # this Git repository; its name may differ
    OsmAnd/                   # upstream Android application module
      src-debug/              # shell-protected route-data diagnostic, debug builds only
    OsmAnd-api/               # actual AIDL library consumed by the bridge
    OsmAnd-java/              # Java routing/data module
    integrations/garmin/
      dev.py                  # build/deploy/evidence commands
      bootstrap.py            # locked sibling source setup
      workspace.lock.json
      bridge/                 # standalone Android Gradle root
      watch/                  # standalone Monkey C project
    tasks/                    # plan, current status, verification
  resources/                  # local build input, recreated from lock
  core-legacy/                # local build input, recreated from lock
  build/                      # local build-helper checkout, recreated from lock
```

Keeping this single repository makes the user's push/clone workflow straightforward. Build-only dependencies are external sibling checkouts rather than vendored source. The lock records resolved commits and tested tool versions. The remote OpenGL `master-snapshot` AARs are mutable: cached hashes detect changes but cannot recover an upstream-overwritten binary. This is not a fully reproducible F-Droid dependency build.

## Another computer

1. Clone your personal project into an otherwise suitable workspace parent, then enter the clone. Use the same branch/commits you pushed.
2. Run `python3 integrations/garmin/bootstrap.py`. It clones only missing required siblings at locked commits and refuses to reset existing directories. `--check` is read-only and works offline.
3. Install the Android toolchain listed in `workspace.lock.json`: JDK 17+ (21 tested), SDK platform/build-tools 36, NDK `27.2.12479018`. The Gradle wrapper is included. Garmin SDK/profile/fonts and the existing private signing key are needed only for watch work.
4. Copy `integrations/garmin/dev-config.example.json` to `~/.config/osmand-junction/dev-config.json` and fill in this computer's SDK paths/device selection. Never put the private file or signing key in the clone. Back up/transfer the existing Garmin key securely rather than generating a new update identity. Updating the already-installed bridge on another computer also needs the same Android debug keystore (normally `~/.android/debug.keystore`); transfer it securely outside Git. The OsmAnd development build uses the repository's existing development signing configuration.
5. Run `python3 integrations/garmin/dev.py doctor`. Follow the [setup and commands](integrations/garmin/README.md). Doctor's Garmin warnings do not block Android-only route-data investigation.
6. Build the separate Android test instance using the documented 2 GB Gradle heap/two-worker command. Connect the phone with USB debugging; update-install preserves maps/preferences. A new phone needs the small offline test map once.

Generated evidence is under ignored `build/garmin-review/` inside this clone. It is not pushed. Tracked verification documents summarize the important observations and reproduction commands; recreate device captures locally. The larger sibling `build/` directory outside the clone is a separate upstream input, not the evidence directory.

## Checkpoint discipline

Use small coherent commits and record what was actually tested. Keep unsuccessful experiments visible in the verification record. Do not close physical-watch, active-navigation or geometry-coverage criteria with simulator/compiler results. A temporary handoff can reference the tracked documents; a fresh agent should be able to start from the committed status files alone.
