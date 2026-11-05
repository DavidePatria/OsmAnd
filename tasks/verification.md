# Verification record — junction companion

Reviewed/continued on 2026-11-05 from `/tmp/opencode/handoff-junction-companion.md`. This record distinguishes observed behavior, inference and unexecuted checks. The detailed task acceptance criteria remain in [todo.md](todo.md).

## Current verdict

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
