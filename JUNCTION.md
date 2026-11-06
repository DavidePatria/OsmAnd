# Junction companion workspace

OsmAnd calculates the motorcycle route on Android. The standalone Garmin Forerunner 970 prototype shows a fixed upcoming-junction schematic, with motorcycle road context, the selected route in yellow and a one-second distance display. Java geometry, optional Android export and bridge/watch delivery code now build and pass host/simulator checks. **Next: verify actual phone progress and live SDK delivery; the current demonstrated journey still uses recorded geometry and synthetic progress.**

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

One repository is enough. The sibling build inputs (`resources`, `core-legacy`,
`build`) are public upstream checkouts recreated by `bootstrap.py`; do not create
personal repositories for them.

1. Fork `osmandapp/OsmAnd` on GitHub (so the full history exists), then push your
   `garmin-junction-plan` branch to the fork. Do not push to a bare empty repository:
   this checkout is shallow.
2. Clone the fork into a suitable workspace parent and enter the clone.
3. Run `python3 integrations/garmin/bootstrap.py`. It clones only missing required
   siblings at the commits recorded in `workspace.lock.json` and refuses to reset
   existing directories. `--check` is read-only and works offline.
4. Install the toolchain recorded in `workspace.lock.json`: JDK 21 (17 minimum),
   Android SDK platform 36 + build-tools 36.0.0, NDK `27.2.12479018`. The Gradle
   wrapper is included. For watch or simulator work also install Connect IQ SDK
   9.3.0 **and** download the `fr970` device profile and fonts; installing the SDK
   archive alone is insufficient.
5. Copy `integrations/garmin/dev-config.example.json` to
   `~/.config/osmand-junction/dev-config.json` and fill in this computer's SDK paths
   and device selection. Never put the private file or signing keys in the clone.
   Transfer the existing Garmin 4096-bit RSA key securely rather than generating a
   new update identity; to update an already-installed bridge you also need the same
   Android debug keystore (normally `~/.android/debug.keystore`). The OsmAnd
   development build uses the repository's existing development signing configuration.
6. On Ubuntu 24.04 the bundled simulator needs an older WebKitGTK ABI. Restore it
   from `integrations/garmin/linux-runtime.lock.json` as described in the
   [setup README](integrations/garmin/README.md), and set `garmin_library_path`.
7. Run `python3 integrations/garmin/dev.py doctor`. Doctor's Garmin warnings do not
   block Android-only route-data investigation.
8. Build with the documented commands in the [setup README](integrations/garmin/README.md):
   the isolated Android test app (2 GB Gradle heap / two workers), the bridge
   (`dev.py build --target bridge`) and the watch (`--target navigation-watch`).
   Update-install with `adb install -r` preserves maps/preferences; a new phone
   needs the small offline test map once.

### Resuming work

After setup, read [tasks/START_HERE.md](tasks/START_HERE.md) for the current status
and next steps, then [tasks/todo.md](tasks/todo.md) and
[tasks/verification.md](tasks/verification.md) for task state and evidence. The next
authorized work is T12a (destination marker, arrival screen, opt-in automatic bridge
start). The optional Waydroid desk workflow in the setup README reproduces the
Android simulation without a phone; physical-device and Bluetooth gates stay open.

Generated evidence is under ignored `build/garmin-review/` inside this clone. It is not pushed. Tracked verification documents summarize the important observations and reproduction commands; recreate device captures locally. The larger sibling `build/` directory outside the clone is a separate upstream input, not the evidence directory.

## Checkpoint discipline

Use small coherent commits and record what was actually tested. Keep unsuccessful experiments visible in the verification record. Do not close physical-watch, active-navigation or geometry-coverage criteria with simulator/compiler results. A temporary handoff can reference the tracked documents; a fresh agent should be able to start from the committed status files alone.
