## Forerunner 265 physical transfer (2026-11-11)

The connected device identified itself through desktop MTP as Forerunner 265.
The prepared `fr265/release-watch/Junction.prg` and
`fr265/release-datafield/Junction.prg` were copied to `GARMIN/Apps` as
`JUNCAPP.PRG` and `JUNCFILD.PRG`, respectively. Both were copied back and their
SHA-256 hashes matched the source files. Private readback artifacts are under
`build/garmin-review/fr265/physical-transfer/`. No launch, installation after
USB disconnect, visual review, communication or physical behavior was tested.
The field's earlier separate simulator startup timed out; its unit suite passed.

# Verification record — junction companion

## iOS implementation checkpoint (2026-11-16)

User scope: native iOS OsmAnd adaptation, complete Garmin integration and GitHub
Actions builds; requested signed iPhone output, with no Apple Developer Program
membership. GitHub CLI authentication now works. The dedicated
`codex/ios-garmin` branch was pushed to the existing `DavidePatria/OsmAnd` remote;
no remote or public repository was created. Existing dirty Android work is kept
outside the isolated worktree.

Observed evidence:

- Initial commit `224774290f`: [run 43847726686](https://github.com/DavidePatria/OsmAnd/actions/runs/43847726686)
  failed before app compilation. Pinned OsmAnd-build CMake line 181 contains
  `if ((OR CMAKE_COMPILER_FAMILY ...`; native project generation failed. Running
  upstream prepare through plain `bash` masked that failure. The adaptation now
  removes that exact stray token, invokes `bash -e`, and checks the generated
  native project explicitly. Original logs/artifacts are retained privately in
  `build/garmin-review/ios-ci/run-43847726686/`.
- Commit `795d8ea18d`: [run 43850668035](https://github.com/DavidePatria/OsmAnd/actions/runs/43850668035)
  remained queued with no macOS 26 runner assigned. This does not establish a
  compiler failure. The subsequent attempt selects macOS 15/Xcode 26.3, whose
  installed toolchain was checked against the runner image documentation.
- Source adaptation smoke `overlay-smoke-03` applied to the exact cached pinned
  iOS source and checked the native CMake repair, exporter registration and
  post-initialization startup injection. This checks source integration points,
  not Objective-C compilation.
- Focused `:OsmAnd-shared:jvmTest --tests net.osmand.shared.junction.JunctionRecordedTest`
  passed four tests, zero failures/errors; final rerun completed in 1m27s.
  It reuses existing recorded native fork/double-turn fixtures and checks motor
  filtering/layer facts. The earlier offline attempt failed because the Ktor
  mock dependency was uncached; online resolution and the subsequent offline
  rerun succeeded. Logs remain under `build/garmin-review/ios-ci/`.
- Python/JSON/YAML syntax and diff whitespace checks passed. No physical iPhone
  installation, Garmin BLE delivery, watch drawing or native iOS navigation has
  been performed.

Implementation decisions: authenticated loopback IPC keeps the phone bridge
separate without relying on App Groups; Keychain credentials and opt-in controls
protect source sharing. This cannot wake suspended OsmAnd. Shared geometry uses
bounded independently owned readers of existing OBF files, and preserves native
roundabout end offsets and road levels. Garmin receives documented dictionary
messages; compact Android ByteArray serialization is not assumed portable.
Full-context dictionary throughput and watch heap use remain open.

The manual signing workflow requires existing Apple-issued `.p12` credentials
and two matching device profiles. It has not executed and no signed/installable
IPA is claimed. Free Personal Team provisioning expires after seven days; see
[Apple's account overview](https://developer.apple.com/help/account/basics/about-your-developer-account).
Source revisions are pinned in the iOS lock; upstream prebuilt downloads remain
mutable, with hashes captured during build. Further hosted outcomes must be
appended below without replacing this failed-attempt record.

### Subsequent portable checks and macOS queue (2026-11-16)

- [Linux Swift run 43852395564](https://github.com/DavidePatria/OsmAnd/actions/runs/43852395564)
  passed all 19 source-age/request-lifecycle assertions with Swift 6.4.2.
  Log: private `ios-ci/run-43852395564.log`. This compiles the actual portable
  bridge validation code; UIKit, Network, Security and Garmin SDK remain outside
  this Linux check.
- The shared port read the existing Piazza map and preserved native route
  capture offline. Native entry/end offsets are 18/46. Its `map_context` scene
  exactly equals the saved Android baseline in mode, 1354 dm radius, anchors,
  all 36 paths and destination field; the selected path has 11 points. Source,
  map, expected/input/output hashes and comparison are in private
  `ios-ci/piazza-port-check.json`. The historical capture has no edge-level
  metadata; its route edges retain the existing 2D baseline. Context levels come
  from the shared OBF reader. No native iOS progress, live SDK delivery, rendering
  pixels or physical behavior is established. The temporary classpath script's
  first attempt had a syntax error; corrected resolution and the replay passed.
- [macOS 15 run 43851410265](https://github.com/DavidePatria/OsmAnd/actions/runs/43851410265)
  also remained queued without assigned runners; there are no compiler results
  to infer from that state. The next revision sends the separate bridge check
  to `macos-15-intel`, retaining the native build on `macos-15`; Xcode 26.3 is
  documented on both images. This is a scheduling alternative, not a fix for a
  measured compiler error.
- Reviewed/corrected source callback identity so an old TCP send completion
  cannot clear a newer source read. Source authentication also has a bounded
  overall read interval. These changes still require the native compiler gate.

### Actual Garmin iOS bridge compilation (2026-11-16)

[Run 43853166772, bridge job 133250653269](https://github.com/DavidePatria/OsmAnd/actions/runs/43853166772/job/133250653269)
passed: Xcode 26.3, Intel macOS 15, Release ARM64 `iphoneos`, actual pinned Garmin
Swift package, unsigned build. All source-age/request tests passed on this Mac
too. Compiler evidence is retained under private `ios-ci/run-43853166772-bridge/`.
SourceConnection, SwiftUI, Keychain, Network and Objective-C SDK boundaries compile.
No installation, signing, BLE delivery or watch drawing was executed.

The main OsmAnd job was still queued without an Apple Silicon runner. The next
revision moves it to the working Intel macOS pool; Xcode cross-compiles iPhone
ARM64 there. The parallel bridge job now also packages its actual unsigned app
and hash, so its successful output is available independently of native OsmAnd.

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

## Fresh-host continuation and restart (2026-11-06)

The ignored local `build/garmin-review/HANDOFF.md` records a later fresh-host
checkpoint: the actual tethered Rome journey delivered successful sends and draw
ACKs at about 1 Hz, and `desk-rome/t12a-arrival2/` captured 1501 native samples,
including destination in 238 samples and native arrival in 788. The watch drew
the arrived state 166 times. These are simulator observations, not physical BLE,
GPS or watch readability. Auto-start end-to-end was interrupted at that checkpoint.

After another desktop restart, Waydroid's visible UI was restored, its explicit
configured target was verified as Waydroid, and the saved Rome route recalculated
with 182 points and 12 maneuvers (`resume-prepare/`). With auto-start enabled and
the bridge stopped, starting native simulation produced `AUTO_START authenticated
OsmAnd caller` and `SOURCE_BOUND`. The normal transport then reported
`GCM_NOT_INSTALLED`, so this is not a watch-open or physical Garmin Connect pass.

For tethered recovery, the exact Waydroid `tcp:7381` forward was verified and the
separate bridge was started in tethered mode. The SDK reported NOT_CONNECTED and
an Android IPv6 listener was observed on port 7381. The user reported a repeating
simulator ADB error even after the forward was verified. The simulator was restarted
with the configured Android SDK tools on PATH; connection and watch opening remain
unverified. Preserve this failure boundary and establish CONNECTED before running a
sending watch app. No physical phone was accessed.

Subsequently, a local TCP probe reached the SDK but may have caused an overlapping
disconnect; the tethered service was restarted. A background debug restart was
rejected with `ForegroundServiceStartNotAllowedException`; foregrounding the bridge
activity allowed it to start. The user selected the simulator connection menu and
the bridge reported `DEVICE_STATUS CONNECTED`. The production navigation watch app
then drew live `map_context` scenes with 11 paths, with observed distance decreasing
from 430 to 374 m. This is live tethered delivery after restart, not recorded replay;
pixel correctness and physical behavior are not established by callbacks. The map
activity was brought back into view. Automatic watch opening remains unverified.

## Physical desk test started (2026-11-06)

The user connected an API 37 ARM64 phone and a paired Forerunner 970. The installed
development OsmAnd signing certificate matched the new ARM64 build; `install -r`
succeeded and the app opened, without changing the saved route. The old development
bridge's certificate did not match this host's key, and its installed version was
the old echo prototype. A separately named `Junction Bridge Test` package was built,
its bridge unit tests passed, and it was installed alongside the old bridge. This
alternate identity requires separate OsmAnd consent and manual bridge startup; it
does not test the normal bridge's automatic startup. See the integration README.

After a power interruption, the user reconnected the watch in MTP mode. The verified
fr970 navigation PRG was copied into the empty visible `GARMIN/Apps` root without
overwriting a file; the reported size matched 134044 bytes, then the MTP volume was
unmounted. This proves transfer only, not watch installation, rendering, BLE or
navigation. The phone and watch share a single USB connection and must be connected
in turn. Continue with phone reconnection, watch app launch, connected-app consent,
real Garmin Connect transport and a user-selected simulated route. Do not access or
replace the personal OsmAnd installation or alter its route.

After reconnecting the phone, the user confirmed Junction is available on the
physical watch and manually opened it. The bridge runs with nearby-device and
notification permissions, sees one watch, and logs repeated Garmin SDK send
successes over the real phone/watch connection. The requests currently return
`permission_or_source_error`; the development OsmAnd had no calculated route and
simulation had not been started. The watch reports waiting/no route. Thus physical
transport is observed, but actual route rendering, data-access consent and automatic
watch opening remain open. The user was asked to grant the separate test bridge's
My location group in OsmAnd Plugins and choose/start a simulated route.

The user enabled access and started an 82-point car-profile simulation. On the
real phone and watch, the bridge logged `source=ok`, successful sends and active
draw acknowledgments. The user observed distance lag and intermittent `DETAIL
LIMITED` after turns. A 35-sample read-only capture on a restarted simulation
found 31 `map_context`, three `layer_context`, and one active `geometry pending`
sample; fix and projection timestamps matched 35/35, simulated speeds 13.3–27.7
m/s. These are indoor simulated fixes, not proof of physical GPS semantics. A few
observed physical SDK sends took about one second; this is not a throughput study.

The exporter now supplies speed for bounded watch anticipation only for valid
speed and matching positive fix/projection timestamps. It still exports unmodified
distance, and the watch applies the existing one-second cap once. The ARM64 app
build and geometry/clock checks passed, and the matching-signed development app
was updated. Actual behavior after this change needs a new run. The watch renderer
was changed at the user's request: 20% greater scale, more screen space, no normal
JUNCTION or MOTOR ROADS labels; partial-data warnings remain. Pending geometry says
LOADING JUNCTION rather than implying a phone connection failure. This does not
reduce the worker's actual preparation time. Watch build and regression checks
passed. The final navigation PRG was copied to the physical watch over MTP, its
reported 134220-byte size verified, and the volume safely unmounted. Watch launch,
the new physical layout and distance comparison are pending user verification.

After the watch update, Garmin Connect stayed paired but the watch and bridge
initially waited without requests. The user closed Junction, stopped and restarted
the bridge, then reopened Junction; physical SDK sends and watch acknowledgments
resumed. After the user restarted simulation, active map-context delivery resumed.
A read-only bridge snapshot showed matching fix/progress age 364 ms and nonzero
speed 342 dm/s from the updated exporter. This verifies the speed is delivered to
the bridge, not that the displayed distance agrees with the phone or that real GPS
speed/timestamps have been validated. The user reported that the enlarged physical
watch layout looks better and that the distance follows the phone during simulation.
This is user visual feedback from an indoor simulated route; real GPS, riding
readability, reconnect robustness and battery/background behavior remain separate.

The user observed unused black space at the sides and requested a more zoomed,
full-round layout with roads twice as wide. The prior renderer mapped the exported
80 m radius to 39.6% of the display width and clipped the drawing to a rectangle;
the compiler itself clips context to a circle. The new renderer centers that circle
and maps its radius to 50% of the display width, removes the rectangular clip,
doubles gray/yellow road widths and their casings, and draws distance/name over the
roads. It retains all exported paths and the partial-data warning. The watch build
and simulator regression checks passed; actual physical transfer and visual review
are pending. Greater scale can crop roads outside the display and thicker casings
may obscure nearby alternatives; the physical review must assess that tradeoff.
At the user's request, a paused Garmin simulator replay was generated from an
actual phone-simulation snapshot (20 paths, layered context). The simulator's
454×454 drawing callback passed; this is recorded input, not live transport or
physical-watch pixel approval. The user reported that this simulator layout looks
good. The first replay attempt rejected missing provenance; the local
review wrapper now records the SHA-256 of the actual snapshot collection.

## Navigation-start prompt (2026-11-07)

The user manually transferred the full-round watch build and reported that it
works well. OsmAnd now offers to open the installed bridge on navigation start,
with a per-profile option to remember automatic startup. Debug OsmAnd prefers the
separately installed physical-test bridge over the older normal bridge. The
following-mode transition now calls the starter after the following state is set.
Physical prompt, bridge startup, Garmin watch-open behavior and connection still
need an end-to-end check; a watch confirmation may be required.
The ARM64 OpenGL debug APK build passed, including OsmAnd-java tests. Output
metadata confirms `net.osmand.plus.junction`; APK SHA-256 is
`751ebafe9c25f50c9fb69bda0a1c914e518f9ccef3324c7e5b777384668feb9d`.
The user later authorized the phone update. The matching separate development
package was updated successfully with `adb install -r`; the installed base APK's
SHA-256 matched the build. The navigation prompt and watch connection have not yet
been exercised on the phone, and no route was started or changed for this update.

## Physical ride crash investigation (2026-11-07)

The user reported Junction crashed a couple of times during a test ride. The
connected Forerunner 970 was inspected read-only through KDE MTP; its visible
`GARMIN/Apps/LOGS` directory was empty and `GARMIN/Debug/err_log.txt` was zero
bytes. The available backup and RAM dumps had old timestamps and were not evidence
of this ride. No cause has been established; the phone's recent Android logs and
symptoms should be checked, and a reproducible crash captured before changing the
watch build. No watch files were modified.

The user clarified that the watch returned to its watch face. On the connected
phone, the Android crash buffer contained no Junction crash; the Bridge process
exit history had no crash, and its foreground service was running at inspection.
Recent filtered logs contained no Bridge delivery events, so neither a watch
exception nor its cause can be inferred. An older OsmAnd low-memory exit was
recorded on November 6, but cannot be tied to the reported ride. Unrelated raw
phone logs collected during inspection were removed. Further diagnosis requires
reproducing the exit with fresh watch and phone evidence; the watch's empty crash
folder alone does not establish whether it crashed or exited another way.

## Fixed simulator endurance suite (2026-11-08)

The user authorized entirely simulated testing with visible Waydroid and the
actual Garmin simulator, initially all directed pairs of five private Rome points,
then only the five routes with most turns. Native OsmAnd motorcycle calculations
completed for all 20 candidates. Frozen active order is R002, R014, R003, R007,
R015, with 28/27/25/25/23 non-straight instructions respectively. Straight C and
arrival are excluded; slight/keep instructions count, ties use route ID. The other
15 are parked. Actual native route captures supply distance and journey estimates;
simulation estimates use distance / 10 m/s. The active simulation total is 3.0053 h
before setup. This is an estimate, not an executed completion measurement.

Separate private reports `sim-suite-rome/routes.md` (active five) and
`all-routes.md` (20 candidates) contain points, lengths, native times, fixed-speed
times, cumulative completion estimates and what the scenarios exercise. Manifest,
selection and capture hashes freeze the planned inputs; installed source/bridge
APK and routing-map hashes are checked during execution. All these files remain
under ignored `build/garmin-review/`; no coordinates or runtime targets are tracked.

`sim_suite.py` implements create/plan/select/prepare/run with an explicit verified
Waydroid-only target. The production navigation input/decoder/renderer are used
through live tethered SDK delivery. A test-only input subclass samples memory
every ten seconds, retains no replay frames, and exits at the requested duration.
Log tails and recent draw/ACK correlation buffers are bounded. Results are atomic,
samples/logs flushed, process identities checked, and unexpected SDK/client/log
termination, active draw/ACK gaps, route timeouts and fatal events are preserved
as distinct failures. A route pass requires native arrival and matching active
and arrived drawing acknowledgements. No crash-recovery/relaunch loop is added.
Normal navigation-start prompts are bypassed by putting the already-running bridge
Activity in front only during debug simulation start; prompt behavior is not tested.

Cold preparation still requires one manual Garmin Connection → Start action.
The user performed it; actual CONNECTED was captured in `prepare-01/ready.json`.
The retained connection supported successive test app launches without a second
click. This does not prove recovery after bridge/simulator restarts. The local
`start-test.sh` wraps the runner in a sleep inhibitor; no persistent host power
policy was changed. Commands and failure boundaries are in
`integrations/garmin/SIMULATOR_TESTS.md`.

Executed checks:

- X86 debug APK build passed, including the debug capture's native
  `remainingTimeSeconds` and loaded `routingMaps` fields. Only the isolated
  Waydroid development app was updated; all 20 native captures contain these data.
- Bounded live observer compiled for fr970 with the normal application heap.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s integrations/garmin/tests -q`
  passed all 95 tests (15 new suite tests), including private input validation,
  deterministic selection, forward ownership, bounded log tails, generation/mode
  draw-ACK correlation, privacy filtering and initial-frame timer behavior.
- `smoke-01` exposed a runner deadline bug: host timing began before the SDK's
  roughly 11-second app launch. The observer later emitted the normal duration
  exit. Deadline now starts at the first actual watch frame and never shifts with
  subsequent frames. Startup still has a separate 30-second bound.
- Repeated 90-second `smoke-02` exited normally, with 130 active draws and 57
  correlated active ACKs; sampled peak watch memory 33,128 bytes. Status is
  **incomplete**, correctly: no selected route can finish in 90 seconds. It is
  collection/exit evidence, not an endurance or full-route pass.
- User-authorized `endurance-01` started at 07:29:31 UTC, four-hour budget,
  detached from the tool/chat. At the 07:31:53 UTC checkpoint it was **running**
  R002, with 193 active draws, 120 active ACKs, sampled peak 34,312 bytes and no
  recorded failure. Read its current `result.json` and
  `sim-suite-rome/endurance-01-launch.log` for later status; no completed-run claim
  is made here. Approximate end is 11:30 UTC / 12:30 Europe/Rome, allowing setup.

Waydroid was set to persistent 600×1000 logical portrait sizing, accelerometer
rotation disabled and user rotation zero. After a session restart Android reported
1200×2000 physical sizing and both rotation values zero (desktop scale factor 2).
Only the verified Waydroid target was used. Saved prior display state is private.

The reported physical watch exit remains unexplained. Simulator stability would
not establish physical BLE/GPS, firmware exits, API 34+ foreground policy or OEM
sleep behavior. Random stationary intersection stops are deferred; they require
fresh zero-speed fixes, not frozen stale fixes. User-requested upcoming-junction
preloading is the LAST implementation task after bug investigation. Evaluate only
bounded Android-side current/next preparation using native turn identities, with
recalculation invalidation and unchanged OsmAnd advancement/freshness authority.
No prefetch production changes are included in this test baseline.

## Turn density and native speed revision (2026-11-08)

The user corrected selection from total turns to turns per kilometre and requested
higher speed plus mixed edge cases, then asked whether scripting all seven adds
too much complexity. Density selection and native speed controls proceeded;
native-first versus timestamped native-simulator fixtures is awaiting preference.
No custom movement engine, fixture generator or injected schedule was added.
The original `sim-suite-rome/endurance-01` remains running with its original
loaded code/selection/speed; no APK update, bridge restart or new watch deployment
was performed for this revision.

Prepared selection version 2 ranks non-straight native instructions / native
distance, ties by shorter distance then route ID. R014/R004/R007/R017/R020 total
48.952 km and 99 turns, densities 2.406/2.339/2.328/1.609/1.528 turns/km, route
lengths 6.4–13.7 km. The former selection ranked total turns; it did not explicitly
rank length, though longer routes tended to win. Private `sim-suite-density/`
holds copied native captures, a separate version-2 selection, route reports,
`REVIEW.md` and an unimplemented 15-event distribution proposal. The original
suite and baseline evidence were preserved. New selection requests native
CONSTANT 20 m/s (72 km/h), rather than 10 m/s.

Source inspection found a timing limit: native CONSTANT mode consumes at most
one route vertex per 1.5-second tick. Distance/speed gave an overly optimistic
41-minute bound. A host estimate that counts those existing native steps gives
about 94 minutes before setup (24.3/10.4/22.0/11.9/25.4 minutes). This models
timing only, never generates positions or controls advancement. Actual completion
and fix cadence still need a live run. Route deadlines now use this step estimate.

The DUMP-only debug Start accepts bounded native mode/speed options; settings are
restored using the existing stop/cancel lifecycle. `desk.py` validates parameters
before broadcasting and retains the verified explicit Waydroid target. Native
simulation/routing code and Garmin transport are unchanged. State exposes native
mode/speed for a runtime mismatch check; the runner rejects old debug controls
before deploying a watch app. Each future run also copies/hashes its host runner
and desk controller for reproducibility.

Executed: 100 host tests pass, including density/shorter-tie selection, explicit
native speed arguments/invalid controls and native vertex timing floors. The x86
debug APK build initially failed in packaging when Gradle's default 512 MiB heap
exhausted. A per-command 3 GiB heap / 768 MiB metaspace and two workers succeeded;
no persistent Gradle settings were changed. Logs:
`sim-suite-density/native-controls-build{,-2}.log`. APK is NOT installed yet.
The copied plan still fingerprints the old installed APK; it must be regenerated
after update before any new selection is run. No new speed or edge-case coverage
is claimed from compilation/tests alone.

Native REALISTIC already supplies road-dependent speed limits, mapped-light
stops and unseeded coordinate noise. It does not guarantee all seven edge cases,
and its motion does not use the constant-speed slider. A reproducible all-seven
version could use the existing timestamped native simulator but needs an explicit
fixture adapter and validation. That extra harness is on hold following the user's
complexity concern. The proposed allocation covers each case twice plus one extra
approach stop; it is labeled proposal-only, not a saved executable event schedule.

## User-selected native realistic endurance run (2026-11-08)

The user selected native REALISTIC first and deferred unsupported scripted edge
cases. No custom movement engine, timestamped fixture adapter, event injector,
prefetch or production routing changes were added. Native OsmAnd controls road
speeds, mapped-light stops, unseeded noise and maneuver advancement. A constant
72 km/h speed does not apply to REALISTIC; the earlier 94-minute constant-step
estimate is comparison history, not the new run's predicted duration.

The original constant run was gracefully interrupted for this requested revision
at 07:58:59 UTC after about 29.5 minutes: 2,867 active draws, 1,737 active ACKs,
sampled peak watch memory 44,256 bytes, no recorded runtime failure. Its status is
interrupted, never passed. All old results/logs remain under `sim-suite-rome/`.
The observer remained alive until normal SDK app replacement; no native simulator
kill or bridge restart was required, and no new manual Connection click was used.

The final x86 debug APK built successfully with the per-command Gradle heap from
the prior entry, was update-installed ONLY on verified Waydroid, and its controls
report deskVersion 2. A missing version bump was caught during preflight review
and corrected before this install. Source state now exposes native mode/speed and
fix accuracy; these are DUMP-protected debug observations, not release controls.
All 20 candidates were recalculated with the installed APK and unchanged offline
maps, then frozen into selection version 3. Ranking remains R014/R004/R007/R017/
R020, 48.952 km, 99 non-straight instructions, other 15 parked. Native journey
references total about 118 minutes; realistic completion remains unmeasured.

New detached four-hour run: ignored
`build/garmin-review/sim-suite-realistic/endurance-01/`, launched 08:02:58 UTC /
09:02:58 Europe/Rome, expected timer end about 13:04 local with startup. Sleep
inhibitor presence is verified. Actual source sample has `simulationMode=real_mode`,
following/simulating true, a fresh fix and native reported speed 11.111111 m/s.
At 08:04:19 UTC, R014 was running with 95 active watch draws and 58 matched ACKs,
41 distinct observed fix timestamps, two native turn changes, no zero-speed fix
yet and sampled peak 44,896 bytes. No completed-route/endurance pass is claimed.
Consult the current result before acting; do not modify active inputs or restart
either simulator while it is running. Desktop lock was allowed; the inspected
lock flag was still false, so post-lock continuity is not yet proven.

The runner records bounded per-route summaries of distinct observed fixes,
zero-speed fixes, speed range, native turn changes and changes on consecutive
observed zero-speed fixes. Per-scenario `observations.jsonl` retains both source
states for turn changes. Repeated polls of the same fix do not count as extra
stationary evidence, and route replacement is separated from same-route progress.
These are review observations, not an automatic judgment that a junction was
crossed too early. Completed routes record actual simulation and total elapsed
seconds. Realistic route timeout is three times the larger of native journey
seconds and 1.5 seconds per route point, plus 300 seconds (minimum 600). This is
a stall guard, not an ETA; freshness and active draw/ACK gap gates are unchanged.

Readiness diagnostic correction: the original CONNECTED log event rolled out of
Android's finite buffer during endurance, although the existing watch was still
exchanging requests and ACKs. Readiness now accepts a current-PID connection event
or a drawing ACK no older than five seconds, using Android's clock. A recent
NOT_CONNECTED status wins; send-success alone, old ACKs and another PID are
rejected. Native epoch-log leading padding is handled. This avoids an unnecessary
SDK restart/manual click without inventing connection evidence. It is covered by
host regressions; no bridge/SDK implementation change was made.

104 host tests pass, including realistic-mode arguments without constant speed,
fixed density selection, stop-observation deduplication, route replacement and
readiness evidence. Native live watch build passed. Private `REVIEW.md` and
`routes.md` under `sim-suite-realistic/` describe exact routes, timing references,
enabled/observed coverage, deferred cases and launch commands. The older seven-
case/15-event allocation is explicitly superseded and NOT executed. Physical
watch-exit cause, physical BLE/GPS/firmware and sleep/battery gates remain open.

Later running checkpoint at 08:07:24 UTC: 381 active draws, 242 matched active
ACKs, 164 distinct observed fix timestamps, 18 zero-speed fixes, native speed
range 0–13.333333 m/s, five native turn changes and zero flagged changes between
consecutive zero-speed observations. Sampled peak remains 44,896 bytes. No recorded
failure; R014 is not yet completed. Current host tool hashes match the run's saved
snapshots. Native stationary behavior is now observed rather than just enabled;
this still does not establish exact physical traffic-light placement or close the
reported premature-advancement issue.

## Interim analysis on user's return (2026-11-08, 11:32 UTC / 12:32 local)

The four-hour realistic run remains active with no recorded runtime failure.
Seven route executions completed with native and watch arrival evidence: all five
in cycle 1, plus R014 and R004 in cycle 2. Measured first-pass native simulation
times: R014 36.55 min, R004 14.31, R007 34.12, R017 16.21, R020 39.27. Total
including per-route setup is 141.11 min. These replace the earlier uncertainty
about realistic duration but are not a final four-hour verdict. No route or
simulator was stopped/restarted during analysis.

Streaming analysis of the collected trace found no watch runtime exceptions,
scoped Android fatal events or SDK disconnect events. Maximum observed draw gap
was 2.044 seconds. Ten-second watch heap samples have hourly minima around 27 KB,
medians around 38–42 KB and maximum 51,888 bytes, with no sustained upward baseline
evident. Sampling does not exclude shorter peaks or physical-device problems.

A concrete geometry limitation WAS reproduced: on R007 cycle 1, generations
130/131 returned `map context path capacity exceeded: 35` and `...: 33`. Compiler
source confirms the ordinary limit is 32, after the existing same-level compaction
attempt. The exported scene falls back to route_only with only the selected path;
actual watch traces contain two such episodes, 47 and approximately 22 seconds
(69.013 seconds total). This loses surrounding gray context, not a crash. Captured
fallback scenes themselves do not contain the discarded context. Two private case
bundles preserve their actual live sample, matching native route capture, APK/map
hashes and OpenStreetMap decision-location links for later bounded reproduction.
No synthetic full scene, arbitrary branch removal or capacity change was made.

The interim actual draw trace has 128 active/unavailable geometry episodes,
approximately 141.2 seconds total, longest 2.037 seconds, consistent with observed
geometry-pending/loading source snapshots. This quantifies the preloading idea;
it has not been implemented. Offline native-fix inspection found no turn changes
on entering a zero-speed observation or between consecutive zero-speed observations;
19 changes occurred when leaving a stop. This does not establish physical crossing
correctness or disprove the earlier traffic-light report. Five sampled unavailable
source states explicitly report off_route with native deviation true; noise is a
possible contributor, not a proven cause. They recovered without a recorded crash.

Private outputs: `sim-suite-realistic/interim-analysis.json`,
`limited-detail-analysis.json`, `capacity-cases.json`, `INTERIM_FINDINGS.md`,
`findings/path-capacity/case-{01,02}/`. The separate `routes.md` now includes actual
first-pass timing measurements. All remain ignored; active suite/plan/selection,
host code and watch build are unchanged. Run still needs its normal timer exit
and final status inspection around 13:04 Europe/Rome. Physical crash cause is open.

## Short routine tests replace four-hour default (2026-11-08)

The user requested shorter tests. The long realistic runner was gracefully
interrupted, preserving seven completed journeys and the partial eighth, without
calling it a four-hour pass. No crash was recorded before that interruption. The
full parent routes, original 20 candidate captures and saved capacity cases remain
unchanged. No route/bridge was silently restarted to manufacture a successful run.

New private version-2 short suite has five explicit endpoint pairs derived from
approximately 600 m native windows of R014/R004/R007/R017/R020. These are NOT all
pairs among the derived endpoints. Native recalculation gives Q001 596 m/5 turns,
Q002 574/4, Q003 600/3, Q004 588/3, Q005 598/3: 2.956 km and 18 instructions.
Native journey references sum to 571 s; actual full-pass simulation is unmeasured.
Nearby repeated endpoint pairs are avoided. Q003 is anchored on both saved R007
capacity locations and the recalculated route contains both at zero coordinate
distance. Endpoint-window provenance and input capture hashes are private. Native
OsmAnd still calculates routes and owns REALISTIC motion, stops/noise and advancement.
No custom location generator, accelerated simulation clock or prefetch was added.

Profiles: default regression is one pass, 1800-second deployed-watch cap; smoke is
one focused route, 300-second cap; only explicit endurance accepts hours/repeats.
Routine profiles reject long manifests. The test-only input counts arrivals after
active drawings and exits normally ten seconds after the final required arrival,
allowing its real drawing ACK and host check. The host still verifies native and
watch arrival; it does not force-kill the SDK or wait idly to the cap after a pass.
Source is cancelled before watch deployment so old guidance cannot count toward
the new arrival goal. Smoke exclusions are recorded separately from required routes.

Executed smoke-01: pass for native journey/live delivery/normal lifecycle. Q003
native simulation 151.713 s, total command wall time 183.705 s; normal SDK client
exit, observer reason=completed, no repeat, four other short routes explicitly
excluded. Both known geometry failures reproduced: 35-piece fallback at 34.918 s,
33-piece fallback at 85.201 s (45/17 sampled occurrences). This is NOT a geometry
visual pass or a fix for missing gray roads. Captures under `sim-suite-short/`
include actual short route plans, target-check.json, smoke-analysis.json and
smoke-01/. Full short-pass timing is still unexecuted; 15–20 min is a provisional
expectation only, with a 30-minute cap plus startup/cleanup overhead.

Normal early exit exposed an idle-readiness defect in the host harness: after the
original CONNECTED event rolled out, the old fallback required fresh draw ACKs,
which stop when the watch app exits normally. Do NOT accept stale ACKs or fake
connection logs. Instead the DUMP-only debug bridge now handles sdk_state by reading
the existing ConnectIQ singleton's known devices/getDeviceStatus for the same
selected device. It returns actual SDK strategy/status and current process ID;
the fresh request-ID handshake prevents reuse of an old response. It never
initializes transport, changes SDK strategy, opens a watch app or reconnects.
Production bridge/watch delivery and packet/source freshness are unchanged.

108 host tests pass, covering short explicit pairs, caps/no repeats/explicit
endurance, focus smoke coverage, normal completion markers and live current-PID
tethered SDK status rejection. The short observer and debug bridge APK build pass.
The bridge update was installed ONLY on verified Waydroid, restarting that SDK
connection. Live sdk_state now correctly reports NOT_CONNECTED. One simulator
Connection → Start action has been requested; native GUI controls are unavailable.
No watch sends are attempted while it is disconnected. After that action, verify
current idle readiness before/after normal watch exit. This final SDK verification
is pending, not passed. Fresh five-route plan native-plan-sdk-state/ and immutable
selection-sdk-state.json fingerprint the updated bridge; original smoke hashes
are preserved. The launcher and documented commands use the new plan/selection.

Private REVIEW.md/routes.md document exact points, cases, timing references,
measurements, coverage and commands. No personal coordinates or runtime identifiers
are tracked, and no commit/push is authorized. Physical watch-exit cause, precise
scripted edge cases and preloading remain open/deferred.


## SDK idle-exit boundary and turn-cache request (2026-11-08)

After the user's Connection → Start action, the fresh existing-SDK/current-PID
query returned CONNECTED. A five-second live observer built successfully, ran
normal NavigationInput callbacks and exited normally with code 0/reason=duration.
Six idle seconds later the fresh query returned NOT_CONNECTED. Therefore the
normal-exit readiness expectation FAILED; do not call this an idle readiness pass.
The query correctly rejects the disconnected state. Normal deployment exit on
this simulator may require another manual menu action for the next deployment;
there is no such exit between routes in one running suite. No automatic reconnect,
logs/ACK freshness workaround or long route run was introduced. Private evidence:
`sim-suite-short/idle-sdk-probe/{before,after,result}.json` and `watch.log`.

The user then explicitly requested upcoming-turn caching. Implementation/validation
is in progress. Earlier entries describing no prefetch remain historical baseline
evidence. Physical exit and 35/33-piece geometry failures remain unresolved.


## Host simulator native crash, before cache installation (2026-11-08)

The user reported that the Garmin simulator closed/froze when reconnecting.
Process inventory confirmed no simulator; Waydroid source remained healthy and
idle, with actual SDK NOT_CONNECTED. A host coredump records SIGSEGV at 13:16:10
Europe/Rome. The native main-thread stack starts in g_type_check_instance_is_a /
GTK3; the preceding simulator log contains GTK/FreeType drawing warnings. This
establishes a host native crash, not its root cause or the physical watch-exit
cause. The cache APK was still building and had NOT been installed at that time.
The preceding five-second watch observer had exited normally before this event.

Crash metadata, process/source/SDK state, log copy and offline native backtrace
are preserved under private `turn-cache/simulator-failure/`. An initial backtrace
attempt timed out during automatic symbol lookup; the second completed with
symbol downloads disabled. Simulator was reopened only after preserving evidence.
The user selected Connection → Start again. Cache APK then installed only in
verified Waydroid, and all five frozen short routes were recalculated into
`sim-suite-short/native-plan-turn-cache/` with `selection-turn-cache.json`. Earlier
captures/hashes remain untouched. A focused live cache smoke is now in progress;
no full five-case or long pass is claimed.


## Bounded upcoming-turn cache — focused live pass (2026-11-08)

Implemented after the user's explicit request: Java JunctionSnapshotCache holds
at most current + one following native direction; one worker ticket, current-first
priority. The Kotlin provider copies the same independent bounded route window and
uses the same OBF reader/compiler for each target. In-flight next geometry can
survive forward promotion; replacement/recalculation, pause/deviation/unavailable,
arrival/cancel and backwards movement invalidate prepared and pending results.
Forward skips evict obsolete scenes. Preparation never selects a turn, increments
its navigation generation or refreshes fix/progress samples. No watch queue or
wire change. Error cooldown is per failed target/route, not a block on other turns.

32 focused JVM junction tests pass (including promotion/native authority, unfinished
next builds, skipped turns, lifecycle/route replacement, backwards movement,
failed prefetch and fresh distances/ages). 108 host tests pass. x86 development APK
build passes; only verified Waydroid was update-installed. Five frozen native short
cases re-planned into native-plan-turn-cache/ with a new selection/APK hash. The
launcher references these inputs; old baseline hashes/captures are unchanged.

Actual Q003 cache smoke: pass, native arrival plus actual-watch arrival ACK, normal
observer exit reason=completed; 149.420 s native simulation and 188.577 s complete
command. Three native turn changes; four scenes exactly equal uncached baseline
including all paths/anchors/mode/reason/name/maneuver/radius. Baseline source had
three geometry-pending samples (startup + transitions); cache run one (startup).
Actual baseline watch drew two inter-turn geometry-loading episodes 1007/1014 ms;
cache run zero. This is one unseeded REALISTIC run, not universal latency statistics
or a full five-route/physical pass. Sampled watch peak 47,568 bytes. Both known
35/33-piece route_only capacity failures reproduced unchanged, not fixed/passed
as full context. Our 32-piece ordinary format cap is not a Garmin road-count limit.

Private evidence: turn-cache/{source.json,geometry/check.json,android-build/,
installed.json,smoke-01/result.json,analysis.json}. Actual final source is idle,
not simulating; SDK query remains CONNECTED after this route's normal app exit.
Thus earlier idle-probe NOT_CONNECTED does NOT prove every normal exit disconnects
SDK. Host gate must query actual state, without stale logs/ACKs or reconnect loops.
No test is running, no personal device touched, no commit/push. Physical exit,
capacity correction, full short-pass timing and physical cache verification remain
open. The separate host SIGSEGV evidence above is preserved, not attributed to cache.


## Haptic alert and Piazza dei Re di Roma reproduction (2026-11-08)

User accepted the live Q001 cache demonstration after the first deployment stalled
at the Garmin startup triangle with no first frame. That failed run is preserved
in `cache-demo/demo-01/`; a task-owned client and simulator were stopped with
SIGTERM, simulator/bridge restarted and user reconnected. `demo-02/` passed native
and watch arrival, and user reported the cache works. This does not establish a
permanent simulator startup fix.

User requested a watch vibration for each new junction. NavigationInput now calls
Attention.vibrate with one 300 ms profile when a fresh drawable scene is first
rendered. `JunctionAlert` compares session/first anchor route index/maneuver and
retains its last identity across reconnect and unavailable/stale states. Repeated
seq/distance/generation updates do not vibrate; idle/arrival clear the identity.
There is no replay/echo haptic, and no watch protocol change. Different reroutes
that happen to use the same identity can be indistinguishable; physical Forerunner
motor strength and settings remain unverified. The 970 SDK documents Forerunner
fixed duty cycle, so the profile's requested strength is not a hardware guarantee.

Production navigation watch build passed. Official simulator Monkey C tests: 29
passed including new first-junction, duplicate, status and new-route scenarios.
Live native Q001: pass, seven distinct valid scene identities and seven haptic API
calls, zero errors, native/watch arrival. Logs and analysis under private
`junction-vibration/`. This verifies simulator calls, not physical vibration.

User supplied exact Piazza endpoints. Exact native motorcycle route is 2,507 m
with a detour. Focused 825 m case starts from point 125 of its actual capture and
retains the requested destination; native recalculation confirms the same Piazza
entry, second exit and Via Appia Nuova. `piazza-re-di-roma/` contains both fixed
cases, separate native captures, privacy-preserving report and a local launcher.
Native REALISTIC baseline passed actual watch arrival in 124.4 s. Roundabout native
entry/end offsets are 18/46, 130.3 m along route; exporter stops selected geometry
75 m after entry and thus omits the actual exit. After entry with native direction
still retained, 32/33 sequential source/API observations reported distance zero,
spanning 40.7 s. Watch log also records repeated zero-metre draws. Source and API
polls are not simultaneous. Road mode was map_context inside. This reproduces the
reported Piazza problem and identifies two code-level causes; neither is fixed.
This is distinct from the 32-path context fallback and unknown physical app exit.


## Roundabout exit, context capacity and version checkpoint (2026-11-08)

User requested a fix and explicitly chose one full roundabout diagram with an
exit countdown while inside. The source copies native roundabout end offsets; route
windows retain the complete selected arc plus 20 m of exit approach, subject to
existing bounded input limits. Geometry expands its radius only as needed, up to
200 m on the wire, preserving the selected native exit and continuation. Ordinary
junction geometry keeps its earlier scale. Oversized roundabouts are explicitly
unavailable rather than silently inventing or omitting a selected exit.

Before entry, distance targets the native entry; while the native roundabout is
retained after entry, distance targets the native end/exit. The target change can
cause a numerical increase at entry. OsmAnd still selects and advances directions;
the watch does not advance locally, and age/anticipation limits remain unchanged.
Focused target tests cover before, entry, inside, end, after and invalid offsets.

The enlarged Piazza scene exposed the pre-existing 32-path fallback. Ordinary
map-context now supports 40 paths, matching layered context, with the 48/path,
512-total and compact-wire bounds unchanged. Compiler, bridge, watch, Python and
JSON schema were changed together. Older strict bridge/watch versions reject
ordinary scenes with >32 paths, so upgrade both before using the new source.
More complex cases may still fall back; no motor-road arms are silently dropped.

Evidence under private `roundabout-fix/`: 37 focused JVM tests (including roundabouts without an exit number), 19 bridge tests,
29 actual Garmin SDK watch tests, 109 Python tests, source/bridge/watch builds.
A synthetic ordinary 40-path/512-point scene rendered under the normal fr970 app
heap. The actual SDK encoded the tested maximum-length compact ordinary packet in
6,636 bytes; this does not prove physical BLE throughput. The captured Piazza scene
has 36 paths and radius 135.4 m, includes the actual exit and continuation, and
matches full/windowed calculations. The two prior actual overflow captures now
produce map_context with 40/39 paths, also matching full/windowed calculations.

Live native REALISTIC Piazza run passed native and watch arrival with normal exit.
Inside the roundabout, 37 sequentially sampled snapshots decreased from 132 m to
1 m, zero samples at zero; each had 36 map-context paths. Peak sampled watch heap
was 52,544 bytes. The baseline had 32/33 zero snapshots and clipped before exit.
User chose the full diagram with exit countdown; this is not a confirmed pixel or
physical-watch review. The physical watch-exit cause remains unknown, and watch/
phone hardware, BLE, battery and real vibration remain unverified.

The root AGENTS.md has been consolidated to retain the user's current product,
privacy, simulation, device, visual, haptic, documentation and versioning rules.
Five routine short routes were re-planned for current APK hashes; original private
captures are unchanged. The user authorized local commits and pre-1.0 version
tracking. No remote push or GitHub change is authorized.

The final Android build also passed after broadening native roundabout detection to
include RNDB/RNLB directions without a numbered exit. The 37 focused JVM tests
include that case. The live Piazza run above used RNDB2; it predates this narrow
detection change and remains evidence for that numbered-roundabout path.

A final-build live rerun (`roundabout-fix/live-final/`) failed at watch startup
with `no_initial_watch_frame`; no Piazza scenario began. The connected simulator
was retained for diagnosis. This does not replace the earlier RNDB2 live pass and
leaves live validation of the exact final APK open. Both private route suites were
re-planned against the final installed Waydroid APK before this attempt.

Final-build Piazza retry `piazza-re-di-roma/demo-20261108/` passed after restarting
the retained stuck simulator: native and watch arrival acknowledged. Among 33
sampled RNDB observations after entry, distance went 121 m to 8 m with no zeros;
all had 36 map-context paths. Sequential samples do not prove pixel readability.
The earlier `live-final` no-initial-frame failure remains preserved.

## Ride diagnostics and physical simulated watch exit (2026-11-08)

The debug bridge now has an opt-in private rolling recorder and Android document
export. Bridge host tests passed 20/20, the diagnostic bridge and fr970 watch
builds passed, and a fresh ARM64 OsmAnd development build passed. The isolated
OsmAnd phone app was update-installed with matching signing and verified APK hash;
its data was retained. The watch PRG transfer passed a size check; the Garmin MTP
volume was unmounted. Existing bridge signing keys did not match, so a new separate
`net.osmand.junction.bridge.diagnostics` package was installed without removal of
existing apps. This package requires its own OsmAnd connected-app permission and
manual start; automatic startup still targets the older identities.

The user enabled recording and ran native simulated navigation on the physical
phone and watch. Source requests initially returned `permission_or_source_error`;
after granting access, SDK sends and watch active draw acknowledgements succeeded.
The user then reported the watch returned to its face. The current private log and
the user-exported report were preserved under ignored `diagnostics/physical-watch-exit/`.
The export contained 659 valid JSONL records, including watch requests, source
scenes and send results; no absolute GPS or road-name fields were found. No dropped
log events were recorded. Android's picker appended `.json` and saved in Downloads.

The last watch request acknowledged active generation 10/sequence 80. The bridge
sent sequence 81 and Garmin's SDK reported success; that is not proof of watch
receipt or drawing. No further request was present in the captured interval. The
last full preceding geometry was map context with 26 paths/78 points; no conclusion
about the cause of the watch exit follows from those counts. The bridge process was
still running. The user's report and these events narrow the failure window; a
watch crash log and reproduction are still needed before declaring a root cause or
fix. Physical Bluetooth is exercised, but real GPS, riding, battery and haptics
remain separate checks. The user is connecting the watch for read-only log review.

A 16-frame replay was prepared from the last 29 seconds of the exported scenes,
reconstructing repeated geometry from the prior full entry. The diagnostic log
omits session and road name, so replay substitutes a fixed session and blank name;
this is not a complete wire replay or physical Bluetooth test. The Garmin simulator
itself exited during startup, before playback, so the replay is a failure with no
verdict about the captured diagrams. Evidence is in ignored
`diagnostics/physical-watch-exit/simulator-replay/`; no automatic retry was made.
