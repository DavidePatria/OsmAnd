# Garmin junction companion — development setup

Authoritative implementation sequence: [plan](../../tasks/plan.md), [task status](../../tasks/todo.md), and [verification record](../../tasks/verification.md). This is an early implementation: the isolated Android baseline and minimal watch display work; navigation export and live companion delivery are still pending.

## Locked source and build inputs

Reuse the existing Android checkout at `f22eeb0c1322a9f5784eed6e4d0addb43a0c2e32`, branch `garmin-junction-plan`. Keep upstream origin unchanged. The user will fork, commit and push after testing.

| Sibling of `OsmAnd/` | Required | Resolved commit |
| --- | --- | --- |
| `resources/` ([OsmAnd-resources](https://github.com/osmandapp/OsmAnd-resources)) | app assets | `d0ed5113a2a7b9eaebffa4d4f293e42f9819fba3` |
| `core-legacy/` ([OsmAnd-core-legacy](https://github.com/osmandapp/OsmAnd-core-legacy)) | native build, including OpenGL variants | `31f6b7fd5e2779528aca4391baaa78f932744ee9` |
| `build/` ([OsmAnd-build](https://github.com/osmandapp/OsmAnd-build)) | legacy externals helper scripts | `54356f2a6d1d07fe67510a25ec7912c0c63b277d` |
| `core/` | optional local OpenGL AAR build; not cloned | — |

Clone only missing required siblings; no manifest-wide synchronization is needed. The OpenGL build currently resolves `net.osmand:OsmAndCore_android*:master-snapshot` AARs. Their cached hashes are recorded in ignored `build/garmin-review/review-T00-host/source-lock.json`; a moving snapshot coordinate alone does not guarantee future reproducibility.

## Toolchain actually exercised on 2026-11-05

| Component | Verified configuration |
| --- | --- |
| Java | OpenJDK 21.0.12.1; bytecode target 17 |
| Gradle / Android plugin / Kotlin | wrapper 8.11.1 / AGP 8.10.1 / Kotlin 2.1.20 |
| Android | SDK platform 36; build-tools 36.0.0; NDK r27c `27.2.12479018` |
| Phone | authorized ARM64 Android device; update installation and actual offline route calculation verified |
| Garmin | Connect IQ SDK 9.3.0; downloaded `fr970` compiler/simulator profiles and fonts |
| Garmin signing | **4096-bit RSA, PKCS#8 DER**; private key kept outside Git |
| Emulation | no `/dev/kvm`; real Android phone plus Garmin desktop simulator work without it |

The baseline native build and remote OpenGL dependencies succeeded. An early build failed with disk exhaustion; later builds succeeded. Recheck free space before substantial downloads; do not delete user data as a recovery step.

## Private local configuration

Copy `dev-config.example.json` to `~/.config/osmand-junction/dev-config.json`, or pass `--config /private/path/config.json`. The default private file is loaded automatically. Configure Android SDK, NDK, Garmin SDK and signing-key paths. Set `adb_serial` when multiple authorized devices are connected; an empty value accepts exactly one device. Never stage the private configuration, key, device identifiers or personal routes.

For a fresh Garmin setup, use the SDK Manager to download the SDK, **Forerunner 970 device profile and fonts**. Merely installing the SDK archive is insufficient. On this host, the already-installed community `connect-iq-sdk-manager` CLI downloaded the profile after the user signed in locally through its browser flow. Never request the user's credentials in chat.

Generate a signing key **once**, only if a suitable key does not already exist:

```sh
umask 077
openssl genrsa -out /private/path/developer.pem 4096
openssl pkcs8 -topk8 -inform PEM -outform DER \
  -in /private/path/developer.pem -out /private/path/developer.der -nocrypt
```

Keep that key stable for subsequent updates. The previous handoff's 2048-bit key compiled but produced simulator `Signature check failed` errors; it was preserved and a valid 4096-bit development key selected privately. Garmin documents the required key size in [Getting Started](https://developer.garmin.com/connect-iq/connect-iq-basics/getting-started/).

Ubuntu 24.04 lacks the older WebKitGTK ABI linked by this simulator. The previous `/tmp/opencode/wkgtk` workaround disappeared and prevented launch. It was replaced with a persistent, user-local extraction at `~/.cache/osmand-junction/garmin-linux-runtime/root/usr/lib/x86_64-linux-gnu`; private `garmin_library_path` now points there. No system packages were changed. `linux-runtime.lock.json` records official Ubuntu package URLs, versions and SHA-256 for WebKitGTK 4.0, JavaScriptCore 4.0 and ICU 70. To restore on a compatible Linux host: download those three packages, require matching hashes, extract each with `dpkg-deb -x package.deb /chosen/cache/root`, configure the resulting library directory and check `ldd` before launch. Their other runtime dependencies still come from the host. This is a tested host compatibility workaround, not a general SDK installer.

## Implemented commands

Run from the Android repository root (`OsmAnd/`):

```sh
python3 integrations/garmin/dev.py doctor --out build/garmin-review/doctor
python3 integrations/garmin/dev.py build --target watch --out build/garmin-review/watch-build
python3 integrations/garmin/dev.py build --target bridge --out build/garmin-review/bridge-build
python3 integrations/garmin/dev.py run --mode watch-smoke --out build/garmin-review/watch-smoke
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s integrations/garmin/tests -v
```

- `doctor` records environment/source details and rejects missing Android build prerequisites. Optional capabilities that are installed but broken appear as warnings. Watch readiness includes profile files and a valid 4096-bit RSA DER key. ADB selection is explicit when needed.
- `build --target watch` invokes the real `monkeyc`; writes `compiler.log`, `build.json`, artifact/source SHA-256 values and PRG. An old PRG is removed before attempting a new build, including blocked builds.
- `run --mode watch-smoke` rebuilds, starts the actual simulator when its SDK port is absent, invokes `monkeydo`, and requires `JUNCTION_FRAME` for the **current build ID at 454 × 454**. It writes `runtime.log` and `run.json`, times out on missing feedback, and stops only its own deployment process group. The simulator stays open for inspection/reuse. Both cold startup and repeated update were exercised.
- The frame callback is evidence of actual app execution after drawing calls. **It does not certify visual appearance, Bluetooth delivery, or physical-watch installation.** Visual confirmation is recorded separately. The user provides screenshots when useful; desktop screenshot automation is unavailable in this session.

The first simulator start may require Linux desktop/network access unavailable inside a restricted runner. On this host, sandboxed ADB also cannot open its local server socket. Run the same commands in the authorized host environment; do not substitute a mocked success.

`check --suite protocol|watch` and `run --mode replay` are implemented (below). Other build targets, check suites, `run --mode desk` and `iterate` remain explicitly unimplemented.

## Recorded watch replay and coordinate-linked review

The shared Monkey C scene decoder/state/renderer runs on the actual fr970
simulator. Replay input substitutes recorded geometry and explicitly simulated
progress/state; it is not a live phone position feed. Live echo builds keep their
separate input adapter. See [scene draft](contract.md).

```sh
python3 integrations/garmin/dev.py check --suite protocol --out build/garmin-review/scene-tests
python3 integrations/garmin/dev.py check --suite watch --out build/garmin-review/watch-tests
python3 integrations/garmin/dev.py run --mode replay --scenario double-turn --out build/garmin-review/replay
# User-selected route, captured without install/baseline/profile changes:
python3 integrations/garmin/route_probe.py --out build/garmin-review/user-route
```

Next/previous controls step frames and pause; Start/Select toggles pause.
`--speed 0.25..8` changes test speed; `--hold` freezes the initial scene for review.
Distance normally changes once per second; the diagram has no moving rider marker.
The 26-second loop includes deliberately stale/reroute/idle states. These messages
are expected test cases. Replay requires an actual drawing callback, keeps the
successful deployment open, and records artifact/generated-source/frame hashes.

For complete local road context, use OsmAnd's own reader with the same downloaded
OBF. This optional desktop-only Gradle init task adds nothing to the Android app:

```sh
# Copy the test app's existing OBF to ignored build/garmin-review/map-data once.
# Set Android SDK/NDK environment as for the normal build. These maneuver indexes
# are examples from the current user's route; inspect another route first.
./gradlew '-Dorg.gradle.jvmargs=-Xmx2048m -Dfile.encoding=UTF-8' --max-workers=2 \
  -I integrations/garmin/road-context.gradle :OsmAnd-java:junctionRoadContext \
  -Pjunction.map=build/garmin-review/map-data/Italy_lazio_europe.road.obf \
  -Pjunction.capture=build/garmin-review/user-route/route.json \
  -Pjunction.maneuver=3,6,7 -Pjunction.out=build/garmin-review/user-route/contexts
python3 integrations/garmin/dev.py run --mode replay \
  --capture build/garmin-review/user-route/route.json --maneuver 3 \
  --context build/garmin-review/user-route/contexts/context-3.json \
  --out build/garmin-review/user-layout --hold
python3 integrations/garmin/preview.py \
  --capture build/garmin-review/user-route/route.json \
  --contexts build/garmin-review/user-route/contexts --maneuvers 3 6 7 \
  --out build/garmin-review/user-route/watch-review
```

`preview.py` exports self-contained local SVG/HTML plus scene/provenance JSON.
Optional `--png` needs Pillow and the local DejaVu Sans font. These previews use
the watch transform/colors/strokes with approximate fonts, NOT simulator pixels.
Each diagram has OpenStreetMap links to the original decision coordinates.
Personal coordinates/images stay under ignored build output. Share the local
HTML with a loopback-only server when convenient; no map screenshots are needed.

The query is bounded to a 400 m box, with road/point caps and explicit truncation;
display context is clipped to 75 m at an 80 m scale. No profile or one-way filtering
is applied. No topology is invented for nearby crossing lines. Grade-separated
context currently falls back to route-only and does not satisfy the full-layout
goal. Real map completeness, visual usability and production lifecycle are open.

The user-approved DISPLAY filter removes non-motor highway classes and explicit
non-motor access while preserving more specific motor-permission overrides,
tracks/service roads and selected geometry. Refreshed extracts contain access
tags and `accessTagsVersion:1`; older extracts must be regenerated. Omission
reasons appear in generated scene provenance. Current filtered examples contain
24/14/16 paths; 45 Python tests pass. Traffic-light/stop-sign symbols are deferred.

Eleven actual watch tests pass. SDK 9.3.0's `monkeydo -t` returned exit 1 for BOTH
a known pass and a known intentional failure. The checker therefore requires the
complete consistent `PASSED (passed=N, failed=0, errors=0)` report and positive
matching test count; raw exit code is retained. Missing output/crashes fail.

## Current priority: actual route-data review

The user prioritized data usefulness before further watch integration. The raw probe is debug-only (`OsmAnd/src-debug/`), shell/DUMP-protected, and bounded. It keeps exact route point/segment references, original maneuver offsets and attachment relationships. Capture itself is read-only; the optional motorcycle preparation selects the built-in profile only in the isolated test instance.

After building the APK with the 2 GB heap/two-worker command below:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 integrations/garmin/route_probe.py \
  --install --baseline --motorcycle --out build/garmin-review/route-probe
# Repeat capture of the current route without reinstalling or setting up a route:
PYTHONDONTWRITEBYTECODE=1 python3 integrations/garmin/route_probe.py \
  --out build/garmin-review/route-probe-recheck
```

`--install` inspects the APK's actual package before `adb install -r`. `--baseline` calculates the public Lazio scenario; `--motorcycle` explicitly enables/selects that built-in test profile before calculation. The tool waits for its own atomic response, validates references/coordinates/maneuver offsets, and writes JSON, a summary, and self-contained `review.html`. Open the HTML locally to select maneuvers, change radius and show/hide raw pre-attached candidates. No network map service is needed for this reviewer.

The real motorcycle capture passed: 946 indexed points, 99 selected segments, 20 maneuvers, 252 attached entries and 1,336 raw pre-attached entries, without capture truncation. Maneuvers 5/6 are 42 m apart. These are routing-data entries, not a guarantee of complete physical roads. The reviewer is diagnostic, not the production simplifier or Garmin renderer; map/physical junction comparison remains open. See [verification](../../tasks/verification.md).

## Tethered echo iteration

The T03 probe uses Garmin's actual Android/Monkey C SDK transport with the physical phone and desktop watch simulator. This is separate from physical Garmin Connect/Bluetooth validation.

```sh
# After a bridge source change: build, update-install and verify the running process.
python3 integrations/garmin/dev.py run --mode echo-prepare --out build/garmin-review/echo-prepare
# With the simulator running, enable adb Connection > Start once.
# Then repeat this command for watch changes without reinstalling the phone app:
python3 integrations/garmin/dev.py run --mode echo-smoke --out build/garmin-review/echo-smoke
```

`echo-prepare` handles Android's post-install activity-restore race with bounded launch retries. It checks the current PID and actual TETHERED SDK readiness rather than accepting `am start` exit 0. It reapplies and verifies the selected device's exact port-forwarding rule. Its success status is **prepared**, not a claim of connected echo. The simulator's ADB menu remains a human action after starting/restarting the simulator or updating the phone bridge.

`echo-smoke` requires an already-connected TETHERED bridge, rebuilds/deploys only the watch, and compares the current run's drawn reply IDs with phone-observed acknowledgments. It accepts only matching run epochs and requires acknowledgments 1–5 plus normal probe completion. The probe self-exits after drawing reply 6, or after a bounded unsuccessful run; the SDK client is retained through normal completion. No synthetic messaging backend is substituted.

Simulator-specific compatibility: incoming packets were observed with an empty application UUID. An additional empty-ID listener is registered **only in explicit TETHERED test mode**. WIRELESS mode uses the actual UUID. SDK tethered sends execute on one worker because they perform synchronous socket I/O; UI and one-send-in-flight state stay on the main thread. A bounded atomic app-private trace retains the newest 256 events across watch iterations.

A native simulator heap abort was observed during reconnection (`malloc_consolidate(): invalid chunk size`, exit 134); its underlying cause is unresolved. Fresh-process and clean probe-exit results must be distinguished from that failure. Keep hardware and simulator behavior separate in verdicts.

## Android baseline

The verified command is:

```sh
ANDROID_SDK_ROOT=/path/to/android-sdk \
ANDROID_NDK_ROOT=/path/to/android-sdk/ndk/27.2.12479018 \
./gradlew '-Dorg.gradle.jvmargs=-Xmx2048m -Dfile.encoding=UTF-8' --max-workers=2 \
  :OsmAnd:assembleAndroidFullOpenglArm64Debug :OsmAnd-api:assembleDebug --console=plain
```

The dev package is `net.osmand.plus.junction`, label `OsmAnd~ Junction`, with its own FileProvider authority and dark debug launcher background. Update with `adb install -r`; never uninstall or clear data during ordinary iteration. The original F-Droid installation remains separate.

A public test route from `41.4472,12.6286` to `41.4675,12.9030` calculated using `Italy_lazio_europe.road.obf`: 946 points, 26,708.8 m, native HH backend. The first captured application mode was **car**; the later explicit motorcycle setup/capture verified application mode and derived profile `motorcycle`, while the base engine profile remains `car`. Active navigation/simulation remains unverified.

When invoking Android shell commands containing route URLs, quote for the **remote** shell too. For example, pass `adb shell` a command produced with Python `shlex.join([...])`; otherwise `&end=...&profile=...` may be consumed by the remote shell. The deep link enters route planning; it does not itself prove active navigation.

## Remaining gates

Physical 970 deployment/update, actual Garmin Connect Bluetooth echo, packet-size/rate measurements, background operation and reconnect are unexecuted. Simulator results must not close these acceptance criteria. T03 has one passing real tethered numbered request/reply/draw/ack experiment followed by a failed repeat launch. It is deferred. T06 now has real motorcycle route/branch captures; assess their usability before further watch wiring. Keep all per-task evidence under ignored `build/garmin-review/`, and summarize reviewable facts in tracked `tasks/verification.md`.
