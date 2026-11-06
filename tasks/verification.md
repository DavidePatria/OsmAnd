# Verification record — junction companion

Reviewed/continued on 2026-11-05 from `/tmp/opencode/handoff-junction-companion.md`. This record distinguishes observed behavior, inference and unexecuted checks. The detailed task acceptance criteria remain in [todo.md](todo.md).

## Historical initial verdict

| Area | Observed result | Remaining gate |
| --- | --- | --- |
| T00 setup | Android toolchain, sibling inputs, Garmin compiler/profile/fonts and authorized phone ready; doctor corrected | Linux simulator compatibility libraries are a temporary host workaround |
| T01 baseline | pristine and isolated Android APK/API builds; update installation; actual offline calculated route | motorcycle profile and active navigation/simulation |
| T02 watch scaffold | real fr970 compilation, current-build drawing callbacks, repeated update and automatic cold launch; readable text confirmed by user | physical 970 installation and repeated update |
| T03 echo | one real tethered request/reply/draw/ACK run passed; repeat launch timed out | reliable iteration, rate/size, reconnect and physical Bluetooth; deferred |
| T06 raw-data probe | debug-only shell-protected capture and motorcycle-mode data validation passed | physical junction/map comparison and geometry-usability verdict |
| Other T04–T17 feature work | not implemented | contract, bounded production geometry/export, live delivery and full desk automation |

No GitHub fork, remote change or push was performed. The user subsequently authorized focused local commits for this checkpoint. Original F-Droid installation/data were not replaced. Generated evidence and private configurations remain outside the index.

## T00 review corrections

`doctor` previously accepted broken installed optional tools, missing wrapper files and failed Java startup; it also omitted the required `build/` sibling and could not find configured-SDK ADB or select uniquely among attached devices. These cases now have focused regression tests. SDK readiness checks compiler execution, fr970 profile files and the development signing key, while explicitly avoiding a claim of GUI runtime success based on file presence.

Run:

```sh
python3 integrations/garmin/dev.py doctor --out build/garmin-review/review-T00-host
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s integrations/garmin/tests -v
```

The authorized host doctor exits 0, `ready_with_warnings`, missing only optional `kvm` and local OpenGL `core/`. Sandboxed ADB cannot open its server socket and is correctly reported unavailable there. Twenty-three focused tooling/validation tests passed; they cover environment false positives, unusable signing keys, stale PRG removal, current-build frame matching and refusal to deploy after a failed rebuild.

Current evidence: `build/garmin-review/review-T00-host/{environment.json,doctor.md,source-lock.json}`. The original `T00/` report is historical; its “not installed” statements do not describe the current environment. The current lock records sibling commits, cached remote OpenGL AAR hashes and built Android artifacts.

## T01 Android baseline

The previous model's successful build logs were inspected and copied to `build/garmin-review/review-T01/` for persistence. The initial ENOSPC log is retained as a failure, not a passing build. No unrelated source was removed to compile.

| Artifact | SHA-256 |
| --- | --- |
| Pristine APK (previous build record; overwritten by later output) | `01dacc06252002547a410b769e91cb66f0e4038c3155dad07d6859fec4a0128e` |
| Identity-only APK before the debug probe (rehashed during review) | `d2551fd22316288417c18d1ac221aa5c5ed1c144d0a4e7dd037451fc0018a61c` |
| Current API debug AAR | `c70bd7b23e284129abe61f2021074ff4570261a0c26f243ef9d597e96747037d` |
| Legacy ARM64 `libosmand.so` | `8320730ff21be057277f2f9f7acb80b2a33d5b992c19b84c663a5a15ba073596` |

Identity changes are confined to debug package/label/icon configuration and a FileProvider placeholder. Code already obtains FileProvider authority from the installed package name. Final review moved the provider override into the debug manifest with `tools:replace`; the main manifest is unchanged, preserving all release-flavor provider declarations. Install/update targets `net.osmand.plus.junction`; the user's F-Droid app remains separate.

A correctly remote-shell-quoted route deep link produced an actual offline route, shown in `route-screen.png` and confirmed by app-PID-filtered native routing logs:

- public start `41.4472,12.6286`, end `41.4675,12.9030`;
- map `Italy_lazio_europe.road.obf`, SHA-256 `db01a72e15bdf1cb4e74660e4f88e62f27476216ab71287294ea29d2d91518a0` (queried on phone);
- native HH/JNI backend, 946 points, distance 26,708.8 m;
- native backend logs reported vehicle **car**. The later probe established that the first application mode was also car, and then explicitly verified motorcycle mode after test-profile preparation.

The URL parser falls back when the requested profile key is unavailable and enters route planning. Do not label this as motorcycle-mode or active-navigation proof. Remote shell quoting matters: an unprotected `&` previously truncated the query.

Evidence: `build/garmin-review/review-T01/{route.json,route-screen.png,app-logcat.txt,artifacts.json,t01-build2.log,t01-identity.log}`.

## T02 actual Garmin execution

Installed SDK 9.3.0, fr970 device profile and fonts; corrected manifest `minSdkVersion` and string-resource application name. UUID stays `9d7c2b1a-4f6e-4b3a-9c1d-2e8f5a6b7c8d`.

The previous handoff's key was a 2048-bit RSA PEM. Converting it to DER allowed compilation but the simulator rejected the signature. The simulator error was found in `/tmp/com.garmin.connectiq/GARMIN/APPS/LOGS/CIQ_LOG.YML`. A new 4096-bit RSA PKCS#8 DER development key was created privately; the old key was preserved. All subsequent successful update tests use the same corrected key. The doctor now rejects 2048-bit keys before compilation. [Garmin signing requirements](https://developer.garmin.com/connect-iq/connect-iq-basics/getting-started/).

The automated command really compiles and runs the PRG:

```sh
python3 integrations/garmin/dev.py run --mode watch-smoke --out build/garmin-review/review-T02/cold-launch-T02-5
```

Verified runs: `smoke-T02-3`, `smoke-T02-4`, `smoke-T02-5`, and `cold-launch-T02-5`. The cold test first closed only this session's simulator, then the tool started the actual simulator and observed:

```text
JUNCTION_START build=T02-5
JUNCTION_FRAME build=T02-5 width=454 height=454
```

Each run has `run.json`, `runtime.log`, compiler log and source/artifact hashes. Runtime callbacks are deliberately recorded separately from visual confirmation. The user supplied an image exposing white text drawn on white text backgrounds; `JunctionView` now explicitly uses white foreground on black. The user confirmed readable “Junction / BUILD T02-4”; do not retroactively claim a screenshot of T02-5 was reviewed.

Desktop screenshot capture was rejected by automatic approval review because native UI capture must use CUA, whose available surfaces here contain no native apps. No alternate capture workaround was attempted after rejection. The user will supply screenshots when useful. Physical watch transfer, launch, update count and firmware behavior remain untested; T02 is partial.

## T03 transport checkpoint — deferred in favor of route data

The standalone Kotlin bridge uses Garmin Android SDK 2.4.0 and the actual locally built OsmAnd API AAR; no AIDL declarations were copied. Its separate package is `net.osmand.junction.bridge.debug`. The watch UUID and corrected private signing key remain stable. This is a labeled transport probe, without navigation Binder access or a background service.

Observed and fixed:

- Simulator packets arrived with an **empty application ID**. An additional empty-ID listener restores callback delivery **only in explicit TETHERED test mode**; wireless mode stays scoped to the real UUID. This was observed, not just inferred from the [developer report](https://forums.garmin.com/developer/connect-iq/f/discussion/379720/android-mobile-sdk---tethered-connection---app-status-unknown).
- Tethered `sendMessage` performs synchronous socket I/O. Moving sends to one worker fixed the probe's `NetworkOnMainThreadException`; UI and one-in-flight state remain on the main thread.
- Decoded Monkey C strings need value comparison. The `.equals` fix changed received-but-rejected replies into accepted, drawn replies.
- Android can restore an updated activity without the requested mode argument. `echo-prepare` retries a bounded number of times and requires current-PID TETHERED SDK readiness; the exercised preparation needed two launches. A successful `am start` exit alone did not prove the mode.
- The bridge keeps the latest 256 events atomically in its private app storage. Run epochs prevent old acknowledgments with repeated numeric IDs from passing a new test.

`echo-smoke-2` **passed**: T03-3 drew replies 1–6; the phone acknowledged drawn replies 1–5; `monkeydo` exited normally with code 0. The observed USB/simulator round trips were 26–50 ms. These are not Bluetooth latency measurements.

The unchanged `echo-smoke-3` **failed**: no app-start output before its 45-second deadline. ADB forwarding disappeared again and the phone recorded NOT_CONNECTED. Later ADB reported no device at all. USB availability is a demonstrated blocker, but the cause of every earlier forwarding loss is not established. A separate simulator reconnection also aborted natively with `malloc_consolidate(): invalid chunk size`, exit 134. Do not claim a reliable repeated-launch loop or a resolved native SDK issue.

Commands implemented: `build --target bridge|watch`, `run --mode watch-smoke|echo-prepare|echo-smoke`. After bridge update/simulator restart, its ADB menu connection remains a measured human action. One watch-only iteration did reuse the existing connection without phone installation/reconnect.

Evidence: `build/garmin-review/review-T03/{prepared-worker-bridge,echo-smoke-1,echo-smoke-2,echo-smoke-3}/`. Physical 970 installation, actual Garmin Connect Bluetooth exchange, packet headroom, background operation and reconnection remain unverified. T03 and Checkpoint A stay open. The user explicitly prioritized actual OsmAnd data usefulness before further transport work.

## T06 raw-route probe checkpoint — passed; usability assessment remains open

The debug-only Kotlin receiver is under `OsmAnd/src-debug/`, explicitly added only to the debug source set. Its exported manifest entry requires the signature/privileged `android.permission.DUMP` held by ADB shell. It writes only the latest capture atomically in app-private storage. It neither modifies the native router nor queries a second road database.

`CAPTURE_ROUTE` reads the calculated route, exact location-to-segment references, original maneuver offsets, selected road geometry, attached and pre-attached branch geometry, road direction metadata and actual mode settings. Missing/cleared attachment storage, bounded truncation, initialization, recalculation and route/progress changes during capture are explicit. The process-local route object token is **not** presented as a production navigation-generation counter. The diagnostic before/after checks do not substitute for the eventual lifecycle-safe exporter.

`PREPARE_MOTORCYCLE` is a separate shell-only test setup action: it makes the built-in motorcycle profile available and selects it in the isolated test instance. Capture itself is read-only. The setup is performed only with the CLI's explicit `--motorcycle --baseline` options.

The first build failed in unchanged `OsmAnd-java` from the default heap. The final source builds with:

```sh
ANDROID_SDK_ROOT=/path/to/android-sdk \
ANDROID_NDK_ROOT=/path/to/android-sdk/ndk/27.2.12479018 \
./gradlew '-Dorg.gradle.jvmargs=-Xmx2048m -Dfile.encoding=UTF-8' --max-workers=2 \
  :OsmAnd:assembleAndroidFullOpenglArm64Debug --console=plain
```

The probe source build passed in 23 seconds (`review-T06-build-checkpoint.log`); the final debug-manifest-only isolation check is recorded in `review-T06-build-commit.log`. The final debug-isolated probe APK SHA-256 is `7c2b1ae063262f436c3c1985defd0b6894c109e65bf3becaea08b05b22371b43`; its final build passed in 25 seconds.

The actual capture command passed on the connected phone:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 integrations/garmin/route_probe.py \
  --install --baseline --motorcycle --out build/garmin-review/review-T06/motorcycle
```

It verifies APK package identity before update installation, uses remote-shell-safe route URLs, waits for the matching atomic response, rejects inconsistent indexed data/stale captures, and produces `route.json`, `summary.json`, `run.json` and self-contained `review.html`. No raw private captures are staged.

Verified motorcycle-mode capture on the public Lazio baseline:

| Field | Observed |
| --- | --- |
| application / derived / base routing profile | `motorcycle` / `motorcycle` / `car` |
| route locations / indexed segment references | 946 / 946 |
| unique selected segment objects | 99 |
| maneuvers | 20 |
| inspected attachment points | 1,044; storage available at all inspected points |
| attached / pre-attached entries | 252 / 1,336 (entries, not unique physical roads) |
| route API whole distance | 26,748 m (distinct from the earlier native core distance metric) |
| capture status | `captured`, coherent, not truncated |
| route JSON SHA-256 | `b78b92af50754d42ee9103e1804f1ecfd24863744edaee7bb9b3b2400dcb0575` |

The exact final APK was also update-installed and captured successfully under `review-T06/commit-check/` (same mode/counts; route SHA-256 `0a58cf1db4cbec158e5e24c09563c357d1e559740f67aa489133489866c86c51`). A second capture without installation or route setup also passed; its full content matches the first motorcycle capture after removing only request ID and capture time. The capture retains the original native/JNI route data. Two right-turn records at indexes 5 and 6 are about 42 m apart along the calculated route. The HTML reviewer was exercised in the permitted browser at maneuver 5 and the slight-left/fork candidate at maneuver 10, including its raw-candidate toggle. It renders actual captured points, selected route and competing road geometry with approach-up orientation. Browser evidence: `review.png` in the local motorcycle output directory.

This is encouraging evidence that useful data exists. **T06 as a whole is not closed:** candidate junctions still need comparison with the underlying map/physical layout; duplicates, filtering and missing-road behavior need review. The diagnostic viewer is not a topology-preserving simplifier or the watch renderer, and crossings of drawn lines alone do not establish connectivity. Active navigation/simulation and production snapshot lifecycle behavior are not tested.

## Portable source setup and next step

`JUNCTION.md` is the entry point for another computer. The current OsmAnd Git root holds all customization, companion code, tooling and authoritative docs; required siblings are recreated from `workspace.lock.json` using `bootstrap.py`. The offline bootstrap check passes for all three pinned inputs. It never resets or overwrites existing checkouts; three regression tests cover this behavior. SDKs, signing keys, device identifiers and raw evidence remain local.

That committed checkpoint is superseded by the simulator/layout-review work below. The user will push manually; future commits still require authorization.

## T04/T05/T06 — fixed junction scene, actual simulator and user review

User clarification: stable next-junction layout, all recognizable road arms gray,
selected route yellow, distance refreshed each second. No moving map/rider marker.
OsmAnd alone chooses and advances the junction. Small optional anticipation is
limited to one second of known route-matched sample delay. Real position cadence
must be measured separately from display refresh. The user selected a meaningful
route on the phone; capture did not replace endpoints/profile or reinstall.

**Real data:** the new read-only motorcycle capture has 163 indexed points,
32 selected segments, 12 maneuvers and API distance 2,986 m. Its local SHA-256 is
`fe56fe0c1f81c04b80c00d59cf65ee47a3fe5c65dc7df0070c7c43cad8fc90dd`.
The same Lazio OBF was copied read-only from the isolated test app; SHA-256
`db01a72e15bdf1cb4e74660e4f88e62f27476216ab71287294ea29d2d91518a0`.
Coordinates, road names and raw data remain under ignored
`build/garmin-review/user-route/`, not tracked fixtures.

Filtered attached turns are insufficient: source inspection confirms one-way
filtering in RouteResultPreparation and profile acceptance in RoutingContext.
The new optional `road-context.gradle` / `RoadContextProbe.java` uses OsmAnd's
existing BinaryMapIndexReader on a dedicated desktop read-only stream, with a
400 m query box, ≤512 roads / 50,000 points, explicit truncation and no router
profile/one-way filter. This adds no Android production code or second database.
The first isolated Gradle task failed from a shadowed Groovy `source` name;
corrected task compiled and ran successfully (12 s, then 14 s batch). Logs:
`user-route/{road-context-build,contexts-build}.log`.

Diagnostic Python conversion clips to 75 m with an 80 m fixed scale, preserves
shared map vertices and original decision indexes, and does not assert topology
for context lines. The three review scenes (original maneuver indexes 3, 6, 7)
contain 29/30/29 paths and 113/90/88 points. Map-context limits are explicitly
32 paths / 48 points per path / 512 total; legacy branch scenes retain 8/24/96.
These bounds are not transport/heap certification. Any overflow or unsupported
grade-separated context yields an explicit limited route-only view. Maneuver 2
exposed the grade-separation gap and was excluded from the full-context gallery;
it has not been fixed or claimed complete.

**Actual watch:** shared Monkey C decoder/state/renderer, recorded input adapter,
pause/frame stepping/speed, fixed diagram and one-second countdown execute in the
real fr970 simulator. Idle/rerouting/stale states clear geometry. Optional distance
estimation is capped, stops at zero and never advances a decision. The live echo
build remains separate. Generated fixtures live under ignored build output.

`T05/user-full-layout-final/` passed using the actual captured scene. Its trace:

```text
JUNCTION_START build=T05-2
JUNCTION_DRAW seq=1 state=active mode=map_context paths=29 anchors=2 distance=118 elapsedMs=4
JUNCTION_DRAW seq=2 state=active mode=map_context paths=29 anchors=2 distance=108 elapsedMs=1013
JUNCTION_DRAW seq=3 state=active mode=map_context paths=29 anchors=2 distance=98 elapsedMs=2009
JUNCTION_DRAW seq=4 state=active mode=map_context paths=29 anchors=2 distance=88 elapsedMs=3009
```

The route geometry is real; progress, speed, fix ages and lifecycle events in this
replay are SYNTHETIC. This does not establish a continuous OsmAnd position feed,
real GPS cadence, live navigation simulation or phone-to-watch delivery.
`run.json` records PRG/capture/generated-source/frame hashes. Repeated deployments
reused the simulator without phone installation, ADB forwarding or menu actions.

**Checks:** 42 Python tests pass. Eleven real Monkey C tests pass under
`T05/full-layout-tests/`, including rejection/freshness/generation, geometry ownership,
bounded distance prediction, stop/zero and context capacity/connectivity rules.
The initial test wrapper falsely failed because SDK 9.3.0 emits exit 1 even on
success and uses a different result summary. Calibration under
`T05/test-runner-calibration/{pass,fail}/` proved BOTH known pass and intentional
failure return 1; their complete summaries differ. The corrected checker requires
positive matching counts and an all-pass summary and preserves the raw code.
It rejects missing/inconsistent/failing summaries and crash exit codes.

The old temporary Linux WebKitGTK library directory had disappeared. Restoring
hash-verified official Ubuntu packages into the persistent user cache recovered
actual SDK startup; no system packages were changed. URLs/versions/hashes are in
`integrations/garmin/linux-runtime.lock.json`; setup is documented in its README.

**Visual review:** `preview.py` produced three SVG/PNG watch-layout examples and a
coordinate-linked HTML gallery under `user-route/watch-review/`. The gallery was
opened in the permitted browser at `http://127.0.0.1:8766/index.html`; its accessible
state contains all three images and four expected coordinate links. PNG previews
were inspected locally. They use actual scene geometry and watch transforms,
colors and strokes, but approximate fonts: they are NOT simulator screenshots.
The user will open OpenStreetMap links and assess the junctions. Do not record that
review as passed before feedback. Actual simulator drawing callbacks remain
distinct from pixel/physical-watch approval. The simulator is left on a held
review scene (`T05/user-layout-held/`) when that final launch passes.

**Next:** incorporate the user's geometry feedback, resolve grade-separated and
roundabout layout coverage, then implement/measure a lightweight route-matched
progress probe with OsmAnd desk simulation. Target 1 Hz fresh phone progress,
measure real fix ages and transport delay, and only then reconnect live delivery.
T04 full envelope, T07 production Java geometry/lifecycle, T08/T09 live exporter,
physical-watch/Bluetooth checks and end-to-end field validation remain open.

### User visual feedback — omit non-motor roads

The user inspected the previews/map links and identified cycleways/footpaths
appearing misleadingly as solid roads. They explicitly authorized filtering those
out and deferred traffic-light/stop-sign symbols. The diagnostic display filter
now uses highway class plus motorcycle/motor_vehicle/vehicle/access precedence,
preserves motor-permission overrides, tracks/service roads and the yellow route,
and records omission reasons. Dashed map styling is not itself a filter. It does
not decide country-specific or conditional legal access.

The same desktop OBF queries were rebuilt with access fields and an explicit
`accessTagsVersion:1` marker; older extracts are rejected until refreshed. Build
passed in 12 s (`user-route/contexts-filter-build.log`). The three review scenes
changed from 29/30/29 to **24/14/16 paths**, with 94/47/52 points. Their endpoints,
decision indexes and yellow selected geometry are preserved. **45 Python tests
pass**, including class defaults, access precedence/overrides, unpaved-track and
restricted-road retention, and unchanged selected route. The unchanged watch
decoder/state still has eleven real passing tests; the filtered replay is rebuilt
and checked separately under `T05/user-layout-motorcycle-filter/`.

The local gallery at port 8766 is regenerated with the same coordinate links and
filtered layouts. Traffic lights/stop signs have NOT been added. Traffic lights
are a plausible junction landmark if associated with the correct approach;
stop-sign direction needs particular care. They remain a later design question.

## Offline Java geometry and optional exporter checkpoint — 2026-11-06

The user authorized continuing without the phone. This phase has used no ADB,
installation or route changes. `JunctionGeometry` owns immutable route/decision/
road/scene data; `JunctionCompiler` implements fixed approach-up projection,
anchored simplification, edge clipping, motor-road filtering and explicit limits.
`JunctionRoadReader` opens dedicated worker-owned OBF streams and bounds reads;
it never queries ResourceManager's shared streams. Grade-separated context and
dateline map-query wrapping remain explicit limited cases.

Ten geometry, four cache and two fix-clock JVM tests passed. Tests cover original
indexes, shared vertices, clipping through/outside the circle, access overrides,
capacity/grade fallback, ownership, deterministic output, roundabout metadata,
dateline distance, reroute/pause/cancel/off-route invalidation, stale worker
rejection, one worker slot, stable geometry across progress and monotonic fix age.
Commands/logs: `T07-java-tests.log`, `T08-offline-build.log`; reproducible wrapper:
`dev.py check --suite geometry --out build/garmin-review/T07/host-check`.

The desktop `JunctionCaptureRunner` invokes the SAME Java reader/compiler intended
for Android on the saved user route + same OBF. Four scenes were generated under
`T07/java-scenes/`. The three approved scenes contain 24/14/16 paths and 95/48/51
points. Original decision anchors match the Python prototype exactly; measured
maximum vertex-to-corresponding-polyline distances are 0.0743 / 0.0989 / 0.8740 m
(`T07/comparison.json`). The fourth remains explicitly route-only for grade
separation. The initial desktop adapter build failed from an ambiguous `Path`
import; its corrected build passed in 12 s (`T07-java-capture.log`).

Actual watch replay accepts precompiled Java scenes via `--scene`; no Python
geometry conversion is involved in this path. `T07/watch-java-scene/run.json`
passed and records a real draw: map_context, 24 paths, 2 anchors, 454×454. Distance
samples remain explicitly synthetic. This is simulator execution, not a physical
watch/phone integration or pixel approval.

The optional API Bundle uses `navigationSnapshot` without changing constructors
or existing turnInfo/keys. Its v1 wrapper carries sceneJson (same scene fields),
capturedElapsedMs and exportAgeMs; all clock-long fields stay phone-side. Eight
Robolectric Parcel checks passed on API 24 and 36: current round trip, old writer /
new reader, new writer / old reader, absent-field clearing and wrapper ownership.
Robolectric 4.17 initially failed Jetifier on bcprov 1.85's class version 69;
pinning test-only Robolectric 4.16.1 resolved it. Logs:
`T08-api-parcel-tests.log` (failed), `T08-api-parcel-tests-compatible.log` (passed).
Test source is under `OsmAnd-api/test/java`, explicitly separate from production's
custom `src` root. These are actual host Android Parcel checks, not phone Binder
interruption tests.

`JunctionSnapshotProvider` serializes lifecycle observation on the UI queue, bounds
the caller's observation wait at 200 ms, copies route data under the routing lock,
uses one geometry worker and validates the current route/junction/state before
publishing. Gson serialization is outside the routing lock. Busy UI returns no
snapshot instead of cached old guidance. Pause/off-route/recalc invalidate geometry.
Live anticipation remains OFF pending real timestamp/projection verification.
An earlier provider/API/app revision assembled successfully in 1m13s; final edited
source build is still required before closing this offline checkpoint.

No claim yet: actual GPS/progress cadence, roundabout progress semantics, Android
UI/Binder lifecycle, physical Bluetooth, screen-off behavior or physical Garmin
execution. Next work is bridge/watch delivery gating, source age conversion and
final-source builds. Keep hardware gates open.


## Final offline implementation checkpoint — 2026-11-06

This section supersedes the earlier pending final-build/delivery notes. No phone
access, ADB, installation, endpoint changes or route replacement was performed.
All changes after `0c6b7f8` remain uncommitted pending a new user commit request.

**Final builds:** `offline-final-root.log` records a successful 29-second Android
app/API build, Parcel checks, core checks and saved-route Java compilation. The
source includes the final bounded route-window provider and anchor-relative
cumulative geometry; subsequent additions were two test fixtures/tests only.
`offline-final-bridge.log` records successful bridge assembly, seven host tests
and lint (0 errors, 3 advisory warnings). APK identities were read from the build
artifacts without accessing a device: `net.osmand.plus.junction` (ARM64) and
`net.osmand.junction.bridge.debug` (version 2 / 0.2-navigation). These are separate
from the user's F-Droid app. The bridge artifact is named
`integrations/garmin/bridge/build/outputs/apk/debug/JunctionBridge-debug.apk`.

**105 passing tests:** 53 Python, 20 JVM geometry/cache/fix-clock, 8 Android host
Parcel (API 24/36), 7 bridge and 17 actual Monkey C tests. The 30 protocol tests
are a subset of the 53 Python tests, not an additional count. Evidence:
`offline-checkpoint/python-tests.log`, `offline-final-geometry/check.json`, API
and bridge JUnit XML, and `offline-final-watch-tests/check.json`. SDK exit 1 is
accepted only with the previously calibrated complete matching all-pass summary.
The schema check in `T04/schemas.json` also validates both schemas and three
contract examples. Aggregate report `offline-checkpoint/summary.json` records
report/artifact hashes, APK identities and open gates; all evidence paths here
are relative to ignored `build/garmin-review/` unless stated otherwise.

**Portable real-data tests:** two PUBLIC baseline native route windows and raw
OBF contexts are under `OsmAnd-java/src/test/resources/junction/`, with source/map
hashes and OSM/ODbL attribution. They test independently known native TR/TR and
fork decisions and geometry direction, without the private route or full OBF.
A million-point source test confirms only a bounded local window is copied.
The desktop runner asserts exact full-route/window output equality on all four
saved user examples. Current outputs in `T07/java-final-scenes/` preserve approved
24/14/16 paths (95/48/51 points); the grade-separated example remains route-only.

**Actual simulator:** production `navigation.jungle` compiles with the final
source (`offline-final-navigation-build/build.json`, T09-1). A fresh held replay
from the final Java output passed under `offline-final-java-watch/`:

```text
JUNCTION_START build=T09-1
JUNCTION_DRAW seq=1 state=active mode=map_context paths=24 anchors=2 distance=118 elapsedMs=0
JUNCTION_FRAME build=T09-1 width=454 height=454
```

The client is retained for inspection. This is actual simulator drawing execution;
it is not a screenshot/pixel review, live position evidence or physical-watch
validation. Replay distance/progress samples remain synthetic.

**Delivery implemented, hardware verification open:** the optional app-info Bundle
is compatible with old callers; a read-only provider observes lifecycle on the UI
queue, uses a single geometry worker and rejects obsolete results. The bridge's
user-started foreground service/Start-Stop UI binds only the separate development
OsmAnd identity. Requests have bounded epochs/deadlines, one pending work/send
slot, typed scene decoding and drawing acknowledgments. Age conversion preserves
source/fix/progress age; stale/unsupported/unavailable sources clear guidance.
The existing API returns null both for denied access and source failure, so the
bridge honestly reports that ambiguity. Live speed/anticipation stays disabled.

**Simulator failure boundary:** early real-navigation/no-phone launches stalled
native SDK communication/client termination; an epoch-string correction and
first-tick deferral did not establish a complete transport fix. Only task-owned
simulator/client processes were recovered; no user hardware or simulator state
reset was used. The bounded `navigation-smoke` uses the SAME input initialization
and renderer but explicitly disables the transport timer, draws and exits normally
through the SDK (`T09/navigation-bounded-startup/run.json`). Its pass proves that
limited startup path only. Production transport stays an open hardware gate.
Do not repeatedly deploy unattended live input with no phone and treat a compile
or startup-only pass as a communication pass.

**Next checkpoint:** update-install the two APKs without uninstalling, preserve the
selected route, enable OsmAnd connected-app access once and exercise its current
route simulation. Grant bridge Nearby Devices permission through Start, then
measure source observation/fix/progress cadence, age semantics, roundabout distance
and advancement, permissions/Binder interruption, foreground/screen-off behavior,
reconnect and real message size/headroom. Physical Bluetooth/sideload/readability
remain separate gates. Grade separation and complex roundabout/coverage tests
also remain open; traffic-light/stop-sign symbols stay deferred.


## Waydroid access checkpoint — 2026-11-06

Waydroid was installed by the user/another model. Container service was active;
starting `waydroid session start` booted Android successfully. API 33 reports
`x86_64,x86`, boot complete, and no initial `net.osmand` packages. The first
explicit-target ADB connection failed authentication. The user approved the
Android trust dialog; subsequent explicit-target shell commands passed without
root. The normal Waydroid administrative shell requires a sudo password and was
not used; no system privilege changes were needed.

The verified existing `JunctionBridge-debug.apk` installed successfully and its
NavigationActivity launched cold (`Status: ok`, 275 ms) with a running process.
Garmin transport was not started. Physical-phone ADB/default configuration was
not used. Private Waydroid address/config and environment results are in ignored
`build/garmin-review/waydroid/`. The first x86 OsmAnd build passed in 10m18s under
`x86-build.log`. Its APK identity was checked with aapt: net.osmand.plus.junction,
version 5550, x86/x86_64. Installation and MapActivity cold launch passed; after an
8-second startup observation the process remained running with no fatal exception
or fatal-signal marker in its process-scoped recent logs. `osmand-launch.json`
records the APK hash/size and limited verdict; raw logs are adjacent. This proves
installation/launch, not native route calculation or full navigation behavior.

The existing offline map was copied into a dedicated Android Download/junction-desk
folder. Android-side SHA-256 exactly matches
`db01a72e15bdf1cb4e74660e4f88e62f27476216ab71287294ea29d2d91518a0`.
It still needs app data-directory placement/indexing. Next: prepare map/profile and
reuse the saved meaningful route's inputs, then verify route calculation,
simulation, optional snapshot export/cadence and only then Garmin exchange.
No further human action is currently known to be required for Android-side setup;
actual watch hardware and visual judgment remain separate gates.


## Waydroid native navigation / actual API checkpoint — 2026-11-06

The user authorized unattended work and asked to minimize remaining physical
checks. No physical-phone access or system permission changes were used. The
existing Android debugging trust approval was sufficient. Waydroid's run-as fails
with a supplementary-group restriction; DEBUG-only evidence is now written to the
isolated apps' own external files directories instead. Debug receivers require
DUMP, accept a fixed current-route scenario/operation allowlist, and cannot take
arbitrary paths, packages or coordinates. Both OsmAnd receivers are absent from
the generated release merged manifest; bridge release separation is checked too.

A native motorcycle route was recalculated from the saved user route's endpoints:
162 points / 11 maneuvers (the original capture had 163 / 12). This is actual native
routing, not GPX-following or desktop-generated geometry. Repeating setup produced
a new route identity with progress reset, retaining maps, Android permissions and
connected-app settings across update installs. An update test caught an activity-
launch/initialization race; the runner now waits for actual profile readiness and
a NEW route identity at progress zero. The failed initial attempts remain in the
ignored evidence directory, not overwritten as passes.

Evidence root: ignored `build/garmin-review/waydroid/desk/`. First lifecycle run:
46/46 actual getAppInfo Binder samples decoded through the PRODUCTION bridge codec.
Pausing cleared geometry; freezing fixes increased age instead of resetting it.
`watch-lifecycle/` replays those actual packets unchanged (including distance,
source order and ages) in the real fr970 decoder/renderer. It completed normally,
showing active, unavailable during pause, and stale_source / POSITION OLD after
fixes stopped. `watch-transition/` completed another 20 actual packets across close
junction/roundabout transitions; sampled used heap peaked at 392824 bytes with
389056 bytes free. This is simulator trace-fixture memory, not physical battery or
production single-scene heap evidence. Existing 17 Monkey C regressions also pass.

The user's journey was sampled in two recorded phases (331 + 151 samples) through
arrival, which cleared route/following/simulation normally. Within the continuous
331-sample phase: median polling ~1.000 s, native fix interval 1500–1501 ms, median
Binder round trip 5 ms / maximum 128 ms, largest raw snapshot JSON 2883 bytes.
The separate-phase sampling gap is not a continuous-delivery pass. Source generation
order and fixed geometry within generations passed; live anticipation stays OFF.
Native roundabout guidance retains its entry anchor at distance zero until OsmAnd
advances beyond the maneuver; this is not independently advanced by the companion.

A named synthetic detour fed positions into the REAL location/routing pipeline:
151 diagnostic samples at 5 Hz saw 16 off-route samples, 10 recalculating samples
and 3 route identities. Geometry was absent during recalculation; source order
never regressed. `reroute-2/measurements.json` records the pass. Permission revocation
returned the existing ambiguous null API result; restoration recovered decoding.
Cancellation produced idle with zero paths. Force-stopping the source followed by
actual bridge re-binding recovered a NEW source session without MapActivity;
`permission-cancel-restart.json` records the pass. This tests actual Binder behavior,
not the production Garmin service's Bluetooth reconnection.

Nine exported scene geometries match the desktop Java compiler EXACTLY (anchors,
paths, mode, road name, maneuver and scale; runtime progress excluded), recorded in
`android-java-parity.json`. A local gallery at http://127.0.0.1:8767/index.html has
five full motor-road layouts first, then four explicitly limited grade-separated
route-only views. SVG/PNG previews use approximate fonts and are NOT simulator
screenshots. Coordinate links let the user compare OpenStreetMap; personal scenes,
coordinates and raw logs remain ignored. The page was opened and its nine images /
map links inspected in the permitted browser. Human correctness/readability approval
is still pending. Traffic-light/stop-sign symbols remain deferred.

Current additional run: a 30-minute Android-framework screen-off source test on the
PUBLIC baseline route is running; no endurance pass is claimed yet. Waydroid power
reports Dozing, but this does not reproduce physical GPS, kernel suspend, OEM power
management, battery use or API 34+ foreground-service policy. The normal bridge
service starts in explicit tethered mode and its port is forwarded without rebinding
another target. Its SDK currently reports NOT_CONNECTED; no live Garmin delivery
pass is claimed. Recorded watch replay and real Android API delivery remain separate.


### Final unattended results and cleanup — 2026-11-06

The PUBLIC-route Android-framework screen-off run completed in 1800.09 s, with
1801/1801 decoded samples and following mode throughout. `screen-off-30min/measurements.json`
passes: median poll interval 1.00006 s / maximum 1.203 s; native fresh-fix interval
1500–1501 ms; median API round trip 2 ms / maximum 7 ms; source-age maximum 4 ms,
fix-age maximum 1297 ms, zero freshness gaps >5 s. All 12 observed geometry
generations stayed fixed while distance decreased. The source route identity
stayed constant. Projection and fix timestamps matched exactly in all 1801 samples.
Anticipation remains OFF: these are native simulation timestamps, not measured
physical GPS behavior. This is a Waydroid API 33 framework pass, not physical
kernel suspend/OEM Doze, battery, GPS, Bluetooth or newer Android FGS-policy proof.

A third actual-packet watch replay (`watch-reroute/`, 39 packets) completed normally,
including native recalculation clearing and new generations; its trace comes from
the actual 5 Hz diagnostic recording after synthetic detour input. `--trace` playback
preserves original scene values/order/ages and exits normally. The exact one-frame
`review/held-1.json` is now paused in the real simulator (`watch-held-final/`):
24 paths, two anchors, recorded distance 125 m, 454×454. It is clearly labeled TEST
REPLAY / PAUSED and freezes logical time; it is not a live phone feed. The gallery
at port 8767 remains open/served, with five full layouts then four limited views.

Capacity verification distinguishes heaps: the unit-test runtime reports a larger
heap, so its passing 512-point ownership/bounds test alone is insufficient for
normal-app headroom. `watch-normal-heap-capacity/` ALSO passed actual decode/render
and normal exit under the normal fr970 app heap: 32 paths / 512 points / 4 anchors,
sampled 63072 bytes used / 718808 free. That drawing is explicitly SYNTHETIC and is
not part of the mapped junction gallery. The normal held real scene sampled about
57 KB used / 724 KB free. These are sampled SDK heap observations, not battery or
physical-watch measurements.

Four added bridge tests use Garmin companion SDK 2.4.0's ACTUAL Serializer, the same
method called by sendMessage. Integer/nested container types, Unicode names and
negative replies round-trip exactly. All 482 recorded user-journey scenes round-
trip in production reply envelopes with a maximum-length stress epoch/request;
maximum encoded bytes 3736 / limit 16384 / headroom 12648. The full 32-path/512-point/
four-anchor case with distinct maximum-length UTF-8 IDs/metadata encodes to 14577,
leaving 1807 bytes. This is serialization/limit evidence, not measured radio traffic.
`verifySdkSamples`, `sdk-wire-report.json` and bridge JUnit XML reproduce it.

Final automated regression counts: 65 Python, 20 JVM geometry/cache/clock, 8 Android
Parcel, 11 bridge (including four real SDK wire tests), 18 actual Monkey C = 122.
The normal-app capacity smoke and three actual Android trace replays are additional
integration evidence. Root x86 app build and both release merged-manifest checks
pass. Bridge build/tests/lint pass (0 errors, 3 advisory warnings). Personal data,
SDK extracts, signing keys/config and generated artifacts remain out of Git.

The standard bridge foreground service started successfully in explicit tethered
mode and the verified Waydroid port forwarding was established with --no-rebind;
the peer still reported NOT_CONNECTED, so no live Android→Garmin SDK delivery pass
is claimed. The SDK shell's help/CIQ commands were inspected; no supported tethered
start command was found. Its --list_transports probe itself exited -11 while normal
help commands worked; this does not prove a failure in our messages or establish
a simulator transport fix. Native UI automation is unavailable; no workaround to
its restrictions was attempted. This remaining SDK integration check can still be
done at a desk; it is NOT inherently a motorcycle/field-test requirement.

Cleanup passed: public simulation canceled, temporary simulation settings restored,
normal tethered service stopped, ONLY the verified task-owned forwarding removed,
Android display awakened. The meaningful saved user route was recalculated/restored
in Waydroid (162 points / 11 maneuvers) in planning mode. No physical-phone state was
accessed. The exact full junction is left paused in the watch; gallery server stays
bound to localhost. All source/docs are staged when this checkpoint closes; no new
commit or push is authorized. Next: user review, grade-separated/complex geometry
coverage, bounded live SDK integration, then physical-only behavior/readability.


## Current checkpoint — full context and connected Rome demo (2026-11-06)

Supersedes earlier grade/transport limits for the MEASURED scenarios. T07c passes:
comparison examples 1–5 preserve exactly the approved visual geometry; former
limited examples 6–9 now have 28/35/20/17 paths, respectively. Nine Android geometries
exactly match the desktop shared compiler on the SAME active route. Building
passages remain ordinary level zero; bridge/tunnel drawing order preserves all
alternatives. All four replacements draw in the actual normal Garmin app.
Ten comparison layouts and seven new Rome layouts have coordinate-linked previews.
Human approval of the new replacements remains separate from callback evidence.

Native simulation startup recalculated the route (163 →162 points), changing its
identity and shifting indexes. The active route was captured before matching scenes;
no coordinate links use the stale capture. desk.monitor now saves coherent native
captures per identity and rejects identity races. Review numbering follows existing
coordinates, preserving example IDs even when indexes shift/missing scenes occur.

The user then requested a genuinely CONNECTED demo using their newly supplied
Rome endpoints. Actual full nested replies exposed SDK 2.4.0's unconditional
floor(bytes/600)-second tethered delay: a 2621-byte reply slept four seconds, outside
the unchanged three-second request deadline. Some smaller scenes alternated between
valid drawing and POSITION OLD. No threshold was relaxed or road removed.
JC1 lossless ByteArray delivery at the SDK boundary fixes the measured route;
see integrations/garmin/wire.md for the full format, alternatives and residuals.

FINAL actual connected run: ignored `rome-challenge/compact-live/summary.json`
relative to build/garmin-review. 241 source samples, seven stable geometry
iterations with decreasing distance, 217 full watch draws, 217 matching subsequent
Android DRAW_ACK events, zero expiry draws between first/last active layout.
Draw interval median1001 ms / min910 / max2001. Maximum actual SDK packet466 bytes
(body453), ZERO simulated BLE sleeps. Native fix intervals1500–1501 ms. API median4 /
max90 ms. Native simulation reached arrival and stopped; the watch cleared to idle.
This is the REAL OsmAnd/Binder/production bridge/SDK request/reply/draw/ACK chain,
not replay or a substitute messaging backend. Anticipation stays OFF (speed zero).
Physical GPS/Bluetooth/watch, OEM sleep and newer Android FGS rules remain gates.

The public golden tests compare complete ordinary/layered Unicode scenes across
independent Python encoding, Kotlin and actual Monkey C decoding; the real SDK
round-trips them as MonkeyByteArray. Every truncated prefix and trailing/unknown
version/noncanonical data is rejected. Invalid UTF-16 is rejected by Android
instead of silently altering names. Maximum layered stress compact wire5762 bytes
(vs legacy15440), safely below16384, but its tethered delay still exceeds our
navigation deadline. Compact encoding alone does NOT establish 1 Hz for every
allowed maximum-size scene. Header-stress serialization of241 Rome samples has
compact max641; normal runtime epoch/header yields the measured max466 above.

Regression totals now77 Python +25 JVM geometry/cache/clock +8 Parcel (unchanged
API code) +15 bridge +23 actual Monkey C =148. Root x86 build passed after level
changes; final compact bridge builds/tests pass. NORMAL fr970 40-path/512-point
layered decode/render passed before compact encoding; current live compact render
covers actual8–25-path scenes, not a maximum binary-packet normal-heap test.
Installed demo APK/hash and watch build are in summary.json. Final bridge source
adds invalid-Unicode rejection after that demo APK; host build/test passes, valid
Rome-path behavior is unchanged, and no further install interrupts the connection.

Separate failure/limit: eager64-frame Rome replay OOMed under normal app heap;
its current frame-count bound does not bound decoded memory. Do not call that a
successful full replay. The user explicitly prefers live connected demonstration.
Background debug FGS start was rejected; opening the bridge activity first fixed
it without permission/system changes. Starting watch sends before SDK connection
caused native errors/exits; establish the real SDK connection FIRST. One user menu
Start remains necessary with current UI tooling after connection-breaking updates.
The current connection is intentionally left intact after arrival for iteration.

The user now requested a checkered destination marker, an arrival screen and
opt-in automatic startup. They chose KEEPING THE BRIDGE SEPARATE. T12a tracks that
next slice; none of those new behaviors is implemented/claimed by this checkpoint.
No SDK binaries, user coordinates, device IDs or keys are staged. No commit/push.
