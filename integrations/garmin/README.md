# Garmin junction companion — development setup

Authoritative sequence: [plan](../../tasks/plan.md), [status](../../tasks/todo.md), [verification](../../tasks/verification.md). Geometry, optional export and bridge/watch delivery code now build and pass host/simulator checks. Actual phone progress, permissions, Binder lifecycle and physical Garmin/Bluetooth integration are not verified.

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

Also preserve the bridge's Android debug signing key privately for another
computer. Its current default is `~/.android/debug.keystore`. Copy the existing
standard debug keystore to a private path and set `bridge_debug_keystore` in the
local configuration (or `-PjunctionDebugKeystore=/private/path/key` for Gradle).
This affects only the bridge; do not overwrite another machine's global key.
Changing the signing key prevents update-installation over the existing app.
Never commit keystores or private configuration. The OsmAnd test app retains its
upstream development signing configuration.

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

Implemented checks: `protocol|geometry|api|bridge|watch`; implemented watch builds:
`watch` (legacy echo) and `navigation-watch` (real input). `run --mode replay` and
`navigation-smoke` work. `all`, `desk` and `iterate` orchestration remain explicitly
unimplemented; the Android app builds through its verified Gradle task.

## No-phone development checkpoint

```sh
python3 integrations/garmin/dev.py check --suite geometry --out build/garmin-review/geometry
python3 integrations/garmin/dev.py check --suite api --out build/garmin-review/api
python3 integrations/garmin/dev.py check --suite bridge --out build/garmin-review/bridge-tests
python3 integrations/garmin/dev.py check --suite watch --out build/garmin-review/watch-tests
python3 integrations/garmin/dev.py build --target navigation-watch --out build/garmin-review/navigation-watch
python3 integrations/garmin/dev.py run --mode navigation-smoke --out build/garmin-review/navigation-startup
```

These commands do not access ADB or install apps. Host checks parse actual JUnit
XML and require nonzero passing counts; watch tests execute in the actual SDK.
The API tests use pinned test-only Robolectric 4.16.1 on Android API 24/36; 4.17
pulled a transitive class version unsupported by this project's Jetifier.
The current totals are 27 JVM + 8 Parcel + 19 bridge + 27 Monkey C checks and 80
Python checks. Bridge lint has zero errors and three advisory warnings.

The core tests include two small real/native-route inputs from the documented
PUBLIC baseline under `OsmAnd-java/src/test/resources/junction/`. They verify the
actual fork and two close right turns without the phone/full OBF/private capture.
Their original indexes, mode, map/capture hashes and data attribution are recorded
alongside them. Expected turn/anchor assertions come from native route facts, not
golden drawings generated by the simplifier. `JunctionWindow` is shared by the
Android provider and saved-route runner; full/window scene equality is asserted
for each saved-route run. Regenerate public inputs with the optional
`-Pjunction.inputFixtures=true` flag only from the public baseline.

Generate scenes with the SAME Java engine/read-only reader used by Android:

```sh
# With the usual SDK/NDK environment and saved private route/map:
./gradlew '-Dorg.gradle.jvmargs=-Xmx2048m -Dfile.encoding=UTF-8' --max-workers=2 \
  -I integrations/garmin/road-context.gradle :OsmAnd-java:junctionJavaScenes \
  -Pjunction.map=build/garmin-review/map-data/Italy_lazio_europe.road.obf \
  -Pjunction.capture=build/garmin-review/user-route/route.json \
  -Pjunction.maneuver=3,6,7 -Pjunction.out=build/garmin-review/java-scenes
python3 integrations/garmin/dev.py run --mode replay \
  --scene build/garmin-review/java-scenes/scene-3.json --hold \
  --out build/garmin-review/java-watch-replay
```

This path bypasses Python geometry conversion. The production provider copies a
bounded local route window and preserves original native indexes even on long
routes. Map IO/simplification use one worker, never the routing lock/shared reader.
The optional snapshot wrapper and live envelope are documented in [contract.md](contract.md).
The bridge decodes bounded source snapshots and adds API age; the watch checks
request ID/epoch/deadline and conservatively adds its round trip. Live anticipation
is currently disabled pending timestamp verification; recorded tests exercise it.

`navigation-smoke` initializes the actual input/renderer, draws the initial state,
and exits via the SDK with **transport disabled**. This is a startup test, NOT live
communication evidence. Running the real navigation timer with no phone/ADB peer,
then terminating the SDK client, stalled the native simulator during testing.
Do not repeatedly force-kill SDK clients. Use bounded startup tests or recorded
replay; recover only this task's owned simulator if necessary. The production
`navigation-watch` variant compiles separately with its transport timer enabled.

The bridge now opens a simple Start/Stop screen, binds only the isolated OsmAnd
package and selects the single configured Garmin (or offers saved watch choices).
It has a non-exported `connectedDevice` foreground service, nearby-device runtime
permission, an ongoing notification/Stop action, and no boot restart. This follows
the [Android connected-device service prerequisites](https://developer.android.com/develop/background-work/services/fgs/service-types#connected-device).
Notification denial does not trigger repeated permission requests. The legacy echo
activity remains available to the explicit echo tools. Do not run echo and live
SDK clients concurrently. Do not claim screen-off/reconnect behavior until measured.

On the next phone session: update-install the fresh isolated APKs, preserve the
chosen route, grant the bridge existing OsmAnd connected-app access once, start
native current-route simulation and start the bridge. Verify fix/progress ages,
roundabout distance targets, strict expiry and route changes before enabling
anticipation. An API null result is permission denial OR source error in the legacy
service; the bridge reports this ambiguity and does not weaken authorization.
Then verify real SDK payload limits, reconnect and physical Garmin execution.

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
24/14/16 paths; 65 Python tests now pass. Traffic-light/stop-sign symbols are deferred.

The initial eleven state tests were extended to seventeen state/envelope tests.
SDK 9.3.0's `monkeydo -t` returned exit 1 for BOTH
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


## Unattended Waydroid desk workflow

Waydroid API 33/x86_64 now runs the actual native OsmAnd route calculation,
simulation and optional exporter. `desk.py` requires an explicit private config
and refuses targets whose `ro.product.device` is not Waydroid. It never selects the
physical phone automatically. Use the separate development app identities only;
update-install, never uninstall/clear app data. Build its APK with
`:OsmAnd:assembleAndroidFullOpenglX86Debug` using the SDK/NDK environment above.
The first native build took 10m18s; later debug-control updates took 22–44s.

One-time Android debugging trust was approved by the user. No Waydroid root/system
permission change was needed. The standard run-as command fails in this container;
DUMP-protected DEBUG receivers instead write bounded latest evidence to each test
app's own external files/junction-desk directory. They are absent from release
manifests. Personal capture/map/output/config stay under ignored build/ or private
storage. A fixed debug grant enables only the test bridge's app-info/location group;
normal phone use still requires the existing OsmAnd connected-app consent.

With the same offline OBF already placed in the test app's data directory:

```sh
# Explicit Waydroid configuration; do not use the default physical-phone config.
python3 -B integrations/garmin/desk.py --config <private-waydroid.json> \
  --out build/garmin-review/desk/prepare prepare --capture <actual-motorcycle-capture.json>
python3 -B integrations/garmin/desk.py --config <private-waydroid.json> \
  --out build/garmin-review/desk/grant probe --operation grant_bridge
python3 -B integrations/garmin/desk.py --config <private-waydroid.json> \
  --out build/garmin-review/desk/start probe --operation start
python3 -B integrations/garmin/desk.py --config <private-waydroid.json> \
  --out build/garmin-review/desk/journey monitor --seconds 480
python3 -B integrations/garmin/desk.py --config <private-waydroid.json> \
  --out build/garmin-review/desk/cancel probe --operation cancel
python3 -B integrations/garmin/review_live.py \
  --samples build/garmin-review/desk/journey/samples.jsonl \
  --capture build/garmin-review/desk/prepare/route.json \
  --out build/garmin-review/desk/review --png
```

Preparation waits for initialization and a NEW native route identity at progress
zero. Start waits for following/simulation readiness; restart waits for the existing
simulator thread's cooperative stop. No routing-engine logic is changed. The normal
simulation produces fixes around 1.5 s apart; the bridge sampling cadence is 1 Hz.
The gallery contains ACTUAL bridge-decoded scenes, exact recorded distances and
coordinate links, with approximate fonts. It rejects unmatched route identities.
Existing example numbers follow coordinates even if native route indexes shift.
Layered road context retains gray alternatives with bridge/tunnel drawing order;
building passages alone do not suppress context. Unavailable/overflow context
remains explicitly limited. The user approved the gray/yellow style of examples 1–5.
It does not claim screenshots, complete topology or human correctness approval.

For failure checks, `probe --operation` supports pause/resume, freeze (stop fixes),
cancel, fixed permission grant/denial and a named synthetic detour. `monitor
--seconds 45 --lifecycle` schedules pause at 15 s, resume at 20 s and freeze at 30 s.
`--hz 5` is diagnostic sampling for brief recalculation states, not a promised watch
refresh rate. The detour feeds synthetic traveled positions into REAL native
routing; it never constructs route decisions itself. Stop/cancel restore the
in-memory simulation settings; maps and saved app permissions remain.

Export and replay up to 64 actual packets without replacing distance/ages:

```sh
python3 -B integrations/garmin/review_live.py --trace-only \
  --samples build/garmin-review/desk/journey/samples.jsonl \
  --trace-start 10 --trace-count 20 --out build/garmin-review/desk/trace
python3 -B integrations/garmin/dev.py run --mode replay \
  --trace build/garmin-review/desk/trace/actual-trace.json --speed 2 --timeout 40 \
  --out build/garmin-review/desk/watch-trace
# Hold the exact first gallery scene, including its actual recorded distance:
python3 -B integrations/garmin/dev.py run --mode replay \
  --trace build/garmin-review/desk/review/held-1.json --hold \
  --out build/garmin-review/desk/watch-held
python3 -B integrations/garmin/dev.py run --mode capacity-smoke \
  --out build/garmin-review/desk/capacity
```

Actual-packet replay runs once and requires normal completion. Held replay freezes
logical time and is labeled TEST REPLAY / PAUSED; it is not live navigation.
`capacity-smoke` renders synthetic 40-path/512-point layered input under the NORMAL fr970
app heap and exits normally. Synthetic capacity drawings are never used as mapped
junction evidence. Unit-test mode has a different/larger heap.

The bridge's SDK serialization tests use the actual pinned SDK serializer,
including Unicode, negative replies and maximum geometry/string bounds. To measure
private captured samples with the same serializer used by sendMessage:

```sh
./gradlew -p integrations/garmin/bridge verifySdkSamples \
  -PjunctionSamples=<absolute-private-samples.jsonl> \
  -PjunctionWireReport=<absolute-private-report.json>
```

The recorded user's 482 samples round-tripped exactly, maximum 3736 encoded bytes.
The full 32-path/512-point/four-anchor stress case with distinct full-budget UTF-8
IDs/metadata encodes to 14577 bytes, below the SDK 2.4.0 send limit of 16384 bytes.
The new layered 40-path/512-point/four-anchor stress case encodes to 15440 bytes;
layered path IDs are capped at 24 characters to retain this bound. Ordinary mode
keeps its 32-path limit and original drawing behavior. See [contract.md](contract.md).
This proves serialization/size compatibility, not actual wireless transmission.

The normal bridge service can be prepared for a bounded tethered test through the
fixed DEBUG-only `probe --bridge --operation start_tethered` hook; stop with
`stop_tethered`. Launch its normal activity and grant its ordinary permissions
first. Forward only the explicit Waydroid target with --no-rebind. Do not replace
another device's forwarding. The current SDK peer reports NOT_CONNECTED; recorded
watch replay is the verified path. Its native menu start is not automated by these
commands. Do not repeatedly force-kill live SDK clients or claim a live link.

Live delivery now uses JC1 lossless SDK byte arrays; the logical contract stays
unchanged. See [wire.md](wire.md) for the exact format, the measured cause of live
expiry/blinking, compatibility and alternatives. Full packet size alone is not a
latency pass. Keep the SDK connection established before sending watch requests.


### Destination and automatic companion startup

Navigation profile settings now contain **Start Garmin junction companion**, off
by default. Opt in per profile. A false→true following transition launches the
SEPARATE bridge only while the OsmAnd map Activity is resumed; unavailable/missing
bridge or background UI falls back to a manual-start message without affecting
navigation. No Garmin SDK is added to OsmAnd.

The bridge accepts automatic mode only when Android's authenticated callingPackage
is the isolated OsmAnd package. startActivityForResult is intentionally used to
obtain that identity without requiring both APKs to share a signing certificate;
its result is unused. This deprecated API remains supported in our min/target
range, but is a future migration point. An arbitrary launcher intent with an auto
extra does not authenticate its caller. First-time normal Android permissions may
still require interaction; automatic mode does not grant them silently.

The bridge returns to OsmAnd after starting its foreground service and requests
SDK openApplication once after SDK/device readiness. Reconnect callbacks do not arm
new prompts; explicit starts are limited to one attempt per30s. Already-running,
not-installed, prompt-shown and manual-open fallback states are handled. The SDK may
require a watch confirmation; physical Garmin Connect behavior remains a separate
gate. In debug desk mode, the DUMP-only start_tethered hook remembers deskTethered
for automatic-start testing. stop_tethered clears it; release builds ignore it.
This setting is only in the isolated Android test app, not a system permission.

A computer restart loses SDK processes and ADB forwarding but not source/apps/maps.
Start Waydroid session, then **show-full-ui**: a session without an Android window
can report container FROZEN and make ADB shell commands hang. show-full-ui resumed
it in the observed reboot recovery, without root/permission changes. Restore only
the explicit verified Waydroid target's forward, start the visible bridge, start
the native simulator ADB menu, verify CONNECTED, then deploy the live watch app.
Keep the Android UI open when demonstrating both simulators. Never substitute old
comparison replay for a requested live demo without saying so.
