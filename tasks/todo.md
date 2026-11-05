# Execution tasks: Garmin junction companion

Read [plan.md](plan.md) first. T00 is complete; T01/T02/T03 are partially verified. The T06 raw-data probe checkpoint passes; geometry-usability review remains in progress. The user explicitly prioritized T06 before further watch integration. Read [verification.md](verification.md) for the reviewed evidence and outstanding gates. Record each task as `not_started`, `in_progress`, `pass`, `fail`, or `blocked`, with evidence paths. Do not mark a task complete using future-tense claims.

Commands mentioning `integrations/garmin/dev.py`, new test classes or new apps are the interface to implement. Existing Gradle task names must be confirmed during baseline setup. `build/garmin-review/` is ignored output. The user subsequently authorized focused local commits for this checkpoint; pushing remains manual.

## T00 — Lock the source and make environment readiness observable

**Status:** pass. **Dependencies:** none. **Scope:** S/M, about 3 tracked files plus local configuration.

Evidence: current `build/garmin-review/review-T00-host/{environment.json,doctor.md,source-lock.json}` (original T00 report retained as history); 23 focused tooling/validation tests pass; setup document `integrations/garmin/README.md`; local config at `~/.config/osmand-junction/dev-config.json` (outside Git). Sibling clones recorded in `source-lock.json`: resources `d0ed5113`, core-legacy `31f6b7fd`, build `54356f2a` (required by `core-legacy/externals/configure.sh`); `core/` not cloned (plain `opengl` builds use remote master-snapshot AARs; only `Opengldebug` needs `binaries/`). NDK r27c `27.2.12479018` selected (Application.mk comment references r27; no version pinned upstream).

**Description:** Establish what can actually run in this environment and record a repeatable source/tool setup before adding a feature. Reuse the existing clone at the plan's pinned commit. Read source `AGENTS.md`; inventory later changes before touching the tree.

**Acceptance criteria:**
- [x] `doctor` reports actual Java/SDK/NDK/Gradle/Garmin versions, source commit, required sibling inputs, device readiness and explicit missing items without printing secrets.
- [x] Required resources/native sources or binary artifacts have resolved versions and hashes; unrelated OsmAnd repositories are not cloned. SDK paths and device serial selection are local configuration.
- [x] A tracked setup document lists the exact preparation steps and facts still unverified; Git origin stays upstream, and no fork/commit/push occurs.

**Historical baseline verification:** initial `git rev-parse HEAD` = `f22eeb0c1322a9f5784eed6e4d0addb43a0c2e32`; `git status --short` = only intended staged docs + this todo; `./gradlew --version` = Gradle 8.11.1 on JDK 21.0.12.1 (run 2026-11-05); `python3 integrations/garmin/dev.py doctor --out build/garmin-review/T00 --config ~/.config/osmand-junction/dev-config.json` → exit 0, status `ready_with_warnings` (original report missing Garmin/ADB; current reviewed report missing only: kvm, core). Doctor returns exit 1 `not_ready` while required capabilities are missing (verified before SDK install).

**Verifiable output:** environment JSON, source/dependency lock manifest, setup transcript and setup README. Hardware IDs/paths stay in ignored local output; public dependency hashes/versions may be tracked.

**Files likely touched:** `integrations/garmin/dev.py`, `integrations/garmin/README.md`, `integrations/garmin/dev-config.example.json`. No app implementation.

## T01 — Build the unchanged Android baseline and isolate the test installation

**Status:** in_progress. **Dependencies:** T00. **Scope:** M; build/setup effort is uncertain and may require a focused subtask.

Progress reviewed 2026-11-05: pristine APK/API AAR and isolated-identity APK built; isolated package update-installed successfully. Existing logs are copied to `build/garmin-review/review-T01/`. Legacy ARM64 core built with NDK r27c; remote OpenGL AARs resolved. An initial ENOSPC failure was followed by a successful build. Do not delete user data for disk recovery.

The identity-only baseline build had package `net.osmand.plus.junction`, label `OsmAnd~ Junction`, separate FileProvider authority, and a dark debug launcher background. Baseline APK SHA-256 `d2551fd22316288417c18d1ac221aa5c5ed1c144d0a4e7dd037451fc0018a61c`; the later installed probe APK and actual motorcycle-mode evidence are recorded under T06/verification.md. A real offline route has been calculated and visually inspected on the phone: 946 points, 26,708.8 m, native HH backend, `Italy_lazio_europe.road.obf`. The observed profile is **car**; motorcycle selection and active navigation/simulation remain unverified.

**Description:** Prove the selected source can build before introducing navigation-export code, then establish a separate signed development installation. This separates environment failures from feature failures.

**Acceptance criteria:**
- [x] The unchanged pinned Android baseline and API AAR build with recorded commands, native/artifact versions and hashes. No unrelated source is removed to make it compile.
  - Pristine APK: `OsmAnd/build/outputs/apk/androidFullOpenglArm64/debug/OsmAnd-androidFull-opengl-arm64-debug.apk`, SHA-256 `01dacc06252002547a410b769e91cb66f0e4038c3155dad07d6859fec4a0128e`, 234.3 MB, package `net.osmand.plus` 5.5.0 (5550), targetSdk 36. Logs: `t01-build.log` (first attempt failed ENOSPC), `t01-build2.log` (success, 4m28s).
  - API AAR: `OsmAnd-api/build/outputs/aar/OsmAnd-api-debug.aar`, SHA-256 `c70bd7b23e284129abe61f2021074ff4570261a0c26f243ef9d597e96747037d`.
  - Native: legacy core built with NDK r27c ARM64_ONLY → `libosmand.so` 8.7 MB; opengl core from remote `net.osmand:OsmAndCore_android*:master-snapshot` AARs (resolved OK).
- [x] A minimal debug identity configuration produces `net.osmand.plus.junction` (or a documented collision-free identity), retaining the androidFull behavior. Install/update only that package; the user's F-Droid app/data remain intact.
  - Change: `debug { applicationIdSuffix ".junction" }` in `OsmAnd/build.gradle`; FileProvider authority override → `${applicationId}.fileprovider` in `AndroidManifest-debug.xml` (main manifest unchanged; code already resolves `getPackageName() + ".fileprovider"`).
  - Identity APK: SHA-256 `df3841474241e86b2a214fbc3d7decc05cc88e28b26d06659cce97fdaec28022`, package `net.osmand.plus.junction`, authority `net.osmand.plus.junction.fileprovider`. Log: `t01-identity.log` (30s incremental).
- [ ] The test instance loads the chosen small offline map and calculates/navigates a route with the built-in engine. API library, installed APK identity, signing and build inputs are recorded.
  - **partial:** authorized phone, offline map and real calculated-route screenshot/log verified (`build/garmin-review/review-T01/{route.json,route-screen.png,app-logcat.txt,artifacts.json}`). Motorcycle mode and active navigation/simulation are not yet verified; no hardware-access blocker for the phone.

**Verification:** confirm `./gradlew :OsmAnd:tasks --all`; run the verified ARM64/OpenGL assemble command and `./gradlew :OsmAnd-api:assembleDebug`. Inspect the APK manifest using installed Android tooling. Update-install with explicit ADB serial, launch the actual resolved activity and calculate the baseline route. Keep output from both pristine build and identity-only build.

**Verifiable output:** baseline build logs, APK/AAR SHA-256, application-ID/ABI manifest output, baseline route screenshot and routing-engine metadata.

**Files likely touched:** debug identity configuration in `OsmAnd/build.gradle`, setup README and version manifest. Avoid broad version upgrades. If needed, split native build recovery into a separately documented setup subtask.

## T02 — Run a minimal app in the 970 simulator and on the watch

**Status:** in_progress. **Dependencies:** T00. **Scope:** M, minimal scaffold; split device setup from source work if it grows.

Verified: real compiler, fr970 profile/fonts, stable UUID and valid 4096-bit RSA DER key. Automatic `watch-smoke` passed for T02-3/T02-4/T02-5 and cold-start T02-5. User confirmed readable Junction / BUILD T02-4; supplied screenshot exposed the earlier white-on-white text background, now explicitly black. Runtime callback and visual approval remain distinct. No physical-watch sideload/update test has run.

**Description:** Prove the actual Monkey C compiler, device profile, persistent app UUID and sideload method before developing the junction renderer.

**Acceptance criteria:**
- [x] A standalone watch app builds for the 970 and displays a build identifier in the actual Garmin simulator. Current-frame logs and user visual confirmation are recorded separately in verification.md.
- [ ] The same app identity runs on the physical 970 and can be updated twice without changing UUID or key. The output PRG filename and exact copy/deploy method are recorded.
- [ ] Simulator launch, physical USB/file-transfer transitions, app launch and remaining human actions are documented from observation. A missing simulator or unreachable device is not reported as a pass.

**Verification:** run the pinned SDK's real `monkeyc`/simulator commands and record them in build tooling. Use official tooling or a configured file-copy backend for the single expected PRG. Verify the actual watch displays the correct build ID after each update.

**Verifiable output:** compiler logs, PRG hash, simulator screenshot, firmware/device-profile versions and deployment action-count log. Human visual confirmation is explicitly labeled.

**Files likely touched:** `integrations/garmin/watch/manifest.xml`, `monkey.jungle`, minimal source/resources and dev build wrapper. Private signing material is external.

## T03 — Prove real phone-to-watch communication and measure basic limits

**Status:** in_progress. **Dependencies:** T01, T02. **Scope:** M; keep bridge UI minimal.

Progress: one real tethered echo/phone-ACK test passed (T03-3, replies 1–6 drawn and 1–5 acknowledged), followed by an unsuccessful repeat launch and intermittent USB/ADB loss. Empty simulator app IDs, worker-thread sending and Monkey C string comparisons were fixed and exercised. Physical Bluetooth, reliable repeated launch, size/rate and reconnect are not verified. **Deferred by user priority: assess actual OsmAnd data first.** See verification.md for exact results.

**Description:** Send a numbered echo message from a new Android bridge to the actual watch app and acknowledge it. Prove the chosen sideloaded app works with Garmin Connect rather than assuming store publication is necessary.

**Acceptance criteria:**
- [ ] The actual phone's bridge initializes the Garmin SDK and selects the intended paired watch/app UUID; watch-originated numbered requests receive matching phone replies, and displayed replies are acknowledged.
- [ ] A bounded size/rate test records encoded message sizes, errors, queue behavior and usable headroom. No invented universal payload limit is used.
- [ ] Update/launch/reconnect steps are exercised twice. The report identifies whether a largely automatic physical iteration is possible and the exact unavoidable actions if not.

**Verification:** actual Android bridge debug build/install; real Garmin Connect/Bluetooth echo at 1x wall-clock time; intentionally interrupt one connection and restore it. Check watch-displayed sequence against bridge acknowledgment. Do not use only the SDK send callback as success evidence.

**Verifiable output:** timestamped echo/ack trace, packet-size/latency observations, failure/reconnect record and physical deployment feasibility verdict.

**Files likely touched:** standalone bridge Gradle/manifest/activity/service scaffold, watch echo handler and tooling. Split scaffold generation from behavior if more than roughly five meaningful files are needed.

## Checkpoint A — Baseline and connection

- [ ] T00–T03 evidence exists and the unmodified baseline build failure risk is resolved.
- [ ] Physical app identity, actual messaging and update constraints are verified.
- [ ] Write `build/garmin-review/checkpoint-A/summary.md`; document any unavoidable manual physical actions. Do not begin extensive UI work while transport/deployment feasibility is unknown.

## T04 — Specify the versioned snapshot and executable contract examples

**Status:** in_progress. **Dependencies:** T03. **Scope:** M, 3–5 files.

Draft scene validators, public recorded fixtures and `integrations/garmin/contract.md` are implemented. Full AIDL/live request/epoch envelope and machine-readable delivery schema remain pending. Scene-only checks do not close T04.

**Description:** Freeze the data boundary for the exporter, bridge, watch and test fixtures. Use the plan's fixed defaults and T03 measurements. This task writes the exact field schema, not a second approximate prose description.

**Acceptance criteria:**
- [ ] Schema/examples define field types, units, axes, origin, path roles, selected route, explicit junction connectivity/anchor references, bounds and optional/unknown values. Equal screen coordinates alone do not imply connected roads.
- [ ] State transitions, session/generation/sequence and current-request/connection-epoch rules, conservative source vs transport freshness, bounded number handling and compatibility are specified with valid and invalid examples.
- [ ] A validator accepts every valid example and rejects unsupported versions, inconsistent graph/path references, nonfinite/out-of-range coordinates and geometry overflow. Minimal old-client/absent-snapshot behavior is defined.

**Verification:** `python3 integrations/garmin/dev.py check --suite protocol --out build/garmin-review/T04`; test at least active, idle, partial geometry, stale-source, old-generation and malformed cases. Implement the command rather than assuming it already exists.

**Verifiable output:** tracked `contract.md`, machine-readable schema, example fixtures and validator results.

**Files likely touched:** `integrations/garmin/protocol/`, `fixtures/contract/`, validator tests/tooling. Do not introduce an additional serialization framework merely to validate these small messages.

## T05 — Replay fixtures through the actual watch state and drawing code

**Status:** in_progress. **Dependencies:** T02, draft T04 scene boundary; promoted by the user's request for simulator-based data review. **Scope:** M.

Actual replay, fixed yellow-route/gray-road layout, one-second simulated progress, bounded distance anticipation, pause/frame stepping/speed and stale/reroute clearing work. Eleven actual Monkey C tests pass. Three coordinate-linked approximate-font previews are ready for user review. Pixel correctness, full road coverage/grade separation and physical watch remain open; see verification.

**Description:** Establish the fast iteration loop using the production Monkey C decoder/state/renderer. Draw a simple route and known alternatives; use fixture input through a small adapter.

**Acceptance criteria:**
- [ ] The 970 simulator shows correct geometry orientation, route highlighting, distance/name, limited-data status and a clear rerouting/stale state from controlled inputs.
- [ ] Replay supports restart, frame advance and selectable speed through tooling; the same decoder/state/drawing implementation handles live and replay input.
- [ ] Semantic assertions and representative frame captures exist; synthetic replay is visibly labeled TEST and never presented as real route-extraction evidence.

**Verification:** `python3 integrations/garmin/dev.py run --mode replay --scenario fork --speed 1 --out build/garmin-review/T05`; run real Monkey C tests via the pinned simulator/SDK. Do not substitute a Python/HTML drawing for the watch app.

**Verifiable output:** actual watch-app frames, event trace, decoder/state test results and replay reproduction command.

**Files likely touched:** watch decoder, navigation state, renderer, fixture input adapter and replay wrapper. Generated fixture sources belong under ignored build output.

## T06 — Capture actual calculated-route data for two ambiguous junctions

**Status:** in_progress. **Dependencies:** calculated-route baseline from T01; promoted ahead of T03/T04 by explicit user direction. **Scope:** M, approximately 3 files.

Latest: captured the user's selected motorcycle route read-only (163 points / 32 segments / 12 maneuvers). A bounded desktop query of the same OBF using OsmAnd's reader supplies unfiltered road context; three watch-layout previews have coordinate links. Grade-separated scenes remain limited. User-selected endpoints are preserved; continuous progress export and fix cadence measurement remain pending.

**Completed sub-checkpoint:** debug-only shell/DUMP-protected capture builds and passes on the real phone in actual motorcycle/derived-motorcycle mode. It retains 946 indexed points, 99 selected segments, 20 maneuvers, 252 attached entries and 1,336 raw pre-attached entries. CLI capture, structural validation and HTML diagnostic review work. Evidence: `build/garmin-review/review-T06/motorcycle/`; build `review-T06-build-checkpoint.log`. Map comparison and a geometry-usability verdict for the close-turn/fork candidates are still open; do not mark the whole task complete.

**Description:** Add a narrow read-only native adapter/probe that obtains the current calculated route, indexed maneuver position, selected route segments and available attached branches. Establish whether existing data is useful before broad geometry implementation.

**Acceptance criteria:**
- [ ] Public-location fork and double-turn scenarios calculate in the actual OsmAnd engine with pinned map/profile settings, and the adapter captures indexed route/branch data without a second routing engine.
- [ ] Dumps identify repeated segment references, branch direction/one-way limitations, missing attachments and route generation. Captures are coherent; unavailable data is explicit.
- [ ] A reviewer can match captured selected exits and junction anchors to the displayed underlying route/map. A synthetic graph is not substituted when capture fails.

**Verification:** an instrumentation test or debug-only probe against the actual test instance; run both scenarios and save raw bounded input plus reference map frames. Record how the selected native routing backend was identified. Do not broadly patch routing internals.

**Verifiable output:** two real route-input fixtures, map hashes, routing settings, expected selected branches/anchors and visual reference images under local run evidence; approved public small fixtures may be tracked.

**Files likely touched:** `NavigationSnapshotProvider.kt`/route adapter in `plus/routing/companion/`, a focused instrumentation/probe test, scenario metadata. Debug dump helpers must remain isolated.

## T07 — Produce bounded local junction geometry with plain-data tests

**Status:** not_started. **Dependencies:** T04, T06. **Scope:** M, split projection from simplification if needed.

**Description:** Implement local coordinates, route/branch selection, topology-preserving simplification and bounds using plain Java. Start from T06's actual captured inputs and independently specified small graphs.

**Acceptance criteria:**
- [ ] Fork branch order/choice and double-turn anchors survive projection, simplification and integer quantization; close bearings and disconnected crossings do not merge.
- [ ] Geometry obeys point/path/radius bounds while preserving selected-route decisions. Unknown/overflow/missing inputs produce the specified limited view rather than invented topology.
- [ ] Roundabout exit metadata is retained, orientation remains stable across approaching updates, and deterministic inputs produce deterministic geometry.

**Verification:** verify/run `./gradlew :OsmAnd-java:test --tests 'net.osmand.router.junction.*'` or a documented narrower equivalent, wrapped by `check --suite geometry`. Tests include left/right signs, north/wrap bearings, duplicates, short segments, same-coordinate disconnected nodes and capacity overflow. Avoid expectations generated by the simplifier itself.

**Verifiable output:** focused test XML/report, real-input geometry fixtures and diagnostic previews clearly labeled as diagnostic (not Garmin renderer evidence).

**Files likely touched:** new plain Java DTO/projection/simplification package and focused Java tests; adapter mapping only as needed. No Android classes in this package.

## T08 — Expose compatible coherent snapshots through AIDL

**Status:** not_started. **Dependencies:** T04, T06, T07. **Scope:** M, 4–5 files.

**Description:** Add the optional Bundle field and minimal existing-call hook. Implement lifecycle, source age and cached geometry by route/maneuver, preserving existing clients.

**Acceptance criteria:**
- [ ] AIDL parcel round-trips optional snapshots and preserves existing constructor/keys/turnInfo/null behavior; old-model/new-model combinations behave as specified.
- [ ] Recalculation, pause, cancel, unavailable route and new sessions invalidate stale geometry appropriately. No mixed-generation snapshot is published; unchanged geometry is cached while distance/state update.
- [ ] Existing connected-app permission checks apply. App/API builds and focused integration tests pass, including a source-change-during-capture case.

**Verification:** `./gradlew :OsmAnd-api:assembleDebug` plus verified focused Android test task for the selected variant. `check --suite api` must produce actual parcel/compatibility and route-state results. Stress route replacement during capture; verify no lock held during geometry work/transport.

**Verifiable output:** APK/AAR hashes, compatibility matrix, focused test report and exported snapshot traces from actual navigation.

**Files likely touched:** `AppInfoParams.java`, `OsmandAidlApi.java`, provider/cache helper, focused tests. Avoid adding a new Binder method or changing the callback payload.

## Checkpoint B — Useful actual geometry and compatible export

- [ ] T04–T08 evidence demonstrates actual fork and double-turn geometry with correct selected branches.
- [ ] Compatibility, source age and route-generation behavior are tested.
- [ ] Write checkpoint-B summary. If ordinary cases need a map-query engine/native-routing change, report the failing examples and request a scope review before proceeding with that change.

## T09 — Feed live AIDL snapshots through the Android bridge

**Status:** not_started. **Dependencies:** T03, T04, T08. **Scope:** M.

**Description:** Extend the echo bridge with authorized OsmAnd binding, source snapshot parsing, bounded delivery and visible diagnostic status. Use the freshly built API AAR.

**Acceptance criteria:**
- [ ] Bridge binds the explicit test OsmAnd instance, reports absent/unsupported API and permission denial distinctly, and reconnects after a controlled Binder/process interruption.
- [ ] User-started foreground operation survives screen locking in a preliminary run. Source/fix age is preserved; heartbeat, newer sequence and SDK send success do not fabricate source freshness.
- [ ] Current watch requests receive only the newest coherent snapshot; one in-flight send prevents backlog, and expired requests are discarded. Transport logs/acks identify actual received and drawn versions. Service stops cleanly on user stop.

**Verification:** bridge unit/state tests plus real AIDL-to-watch run; freeze exporter input while bridge continues, block sends temporarily and inspect queue behavior. Check the foreground-service type/permissions against the actual Android version. Do not weaken permissions/battery settings globally to hide failures.

**Verifiable output:** bridge build hash, source/poll/send/ack trace, bounded-queue test report and preliminary screen-off result.

**Files likely touched:** bridge OsmAnd client, snapshot mapper, connection/service state, tests. No copied AIDL declarations.

## T10 — Display the first actual junction on the physical Garmin

**Status:** not_started. **Dependencies:** T05, T09. **Scope:** S/M, integration corrections only.

**Description:** Join the complete production path using a simulated journey on the phone. Replace synthetic fixture input with actual calculated-route snapshots.

**Acceptance criteria:**
- [ ] Physical Garmin shows the actual fork and double-turn scenes with correct highlighted exits, distances and geometry mode from the current OsmAnd route.
- [ ] Controlled off-route movement triggers actual recalculation; the watch transitions to the new generation without a late packet restoring the old selected exit.
- [ ] Actual routing, AIDL, Garmin Connect and wireless receipt/draw are all evidenced. Any manual visual verdict is recorded separately from automated assertions.

**Verification:** real phone/watch desk run for `fork`, `double-turn` and `reroute`, with logs/ack plus underlying map reference. It is acceptable to start this first integration manually; repeated setup automation is delivered next and remains mandatory.

**Verifiable output:** checkpoint-C event trace and human visual result, matching simulator frame captures if used, and exact reproduction details.

**Files likely touched:** configuration or focused integration fixes. Do not add unrelated styling or new navigation features.

## Checkpoint C — Actual end-to-end junction display

- [ ] Geometry is actually exported by OsmAnd and drawn by the physical watch.
- [ ] A reroute is observed in the real engine and propagated correctly.
- [ ] Write checkpoint-C summary with data provenance for every shown frame. A canned diagram is not a pass.

## T11 — Automate deterministic scenario start, reset and completion

**Status:** not_started. **Dependencies:** T10. **Scope:** M.

**Description:** Remove repeated menu navigation. Define named public scenarios and programmatic control of the isolated OsmAnd instance's normal navigation/simulation pipeline.

**Acceptance criteria:**
- [ ] A run restores the scenario's route/profile, waits for route-ready, starts deterministic simulated movement and emits run-ID-scoped progress/completion without manual route selection.
- [ ] Repeating a run or recovering after failure does not require clearing app data; previous simulation is stopped and temporary test settings are restored. Intended navigation route and simulated traveled trace are separate inputs.
- [ ] Any new control component lives in explicit `src-debug`/debug manifest wiring and is absent from release packaging. It accepts named test scenarios rather than arbitrary external commands.

**Verification:** start the same scenario twice, then interrupt/restart mid-scenario; inspect input positions, state transitions and retained maps/preferences. Verify release merged sources/manifest or APK contains no debug controller. Confirm background input path without relying on MapActivity's location receiver.

**Verifiable output:** scenario manifest/trajectory fixtures, two replay traces, interruption recovery record and debug/release separation check.

**Files likely touched:** debug-only scenario activity/controller, debug source-set/manifest wiring, scenario fixtures and a runner adapter. Split lifecycle tests from controller if needed.

## T12 — Make update installation and incremental deployment repeatable

**Status:** not_started. **Dependencies:** T03, T11. **Scope:** M, tooling only unless a launch hook is proven necessary.

**Description:** Turn the measured Android/Garmin deployment process into a repeatable workflow that preserves setup and rebuilds/deploys only the components affected by a change.

**Acceptance criteria:**
- [ ] Tooling uses update installation with stable IDs/signing, explicit ADB device selection, safe PRG target naming and verified app launch/reconnect. No uninstall/data clear or original-app targeting occurs.
- [ ] Two consecutive runs preserve maps/settings/permissions; a bridge-only change does not rebuild/reinstall OsmAnd, and simulator renderer iteration does not require physical watch deployment.
- [ ] Every remaining physical interaction is counted and reported from actual runs. Unavailable USB/app-launch automation fails explicitly; the script never prints manual instructions and calls that a completed automatic deploy.

**Verification:** change a visible bridge build ID, a watch build ID and a harmless exporter diagnostic independently; execute each appropriate incremental build/deploy path twice. Verify on-device identities against expected build hashes/IDs and preserve settings sentinel values.

**Verifiable output:** deploy transcripts, before/after setup identity checks, rebuilt/deployed component list and residual-action report.

**Files likely touched:** `dev.py`, Android and Garmin deployment adapters, README/local-config example. Protect exact target paths; no broad device-file cleanup.

## T13 — Lock ambiguity cases and actual watch rendering regressions

**Status:** not_started. **Dependencies:** T07, T10, T12. **Scope:** M, fixtures/tests with only targeted fixes.

**Description:** Extend coverage from the first junctions to the common cases and semantic failures listed in plan section 6. Validate correctness before approving screenshot baselines.

**Acceptance criteria:**
- [ ] Crossroads, fork, double-turn, roundabout and disconnected crossing fixtures have independently recorded expected choices/connectivity and honest geometry capability.
- [ ] The actual watch app renders readable scenes at 454×454 in wrist and mounted modes using the same protocol, with correct orientation and no clipping at worst-case bounds.
- [ ] Missing/overflow geometry selects the limited view. Regressions fail semantic checks or reviewed frame comparisons; goldens are not silently regenerated to pass.

**Verification:** `check --suite geometry`, `check --suite watch`, scenario replay for the named cases, and selected physical visual confirmations. Save initial and maneuver-transition frames; match them to source generation/geometry IDs.

**Verifiable output:** semantic result table, approved frame baselines, worst-case geometry render and reviewed public fixture manifest.

**Files likely touched:** geometry/watch tests, scenario fixtures, small renderer fixes. Do not expand into general map rendering or interchange reconstruction.

## T14 — Verify state, freshness and connection failure behavior

**Status:** not_started. **Dependencies:** T09, T12. **Scope:** M, split tests from fixes as needed.

**Description:** Exercise asynchronous failures that can produce convincing but obsolete instructions. Fault injection must identify the layer where it acts.

**Acceptance criteria:**
- [ ] Pause/cancel/arrival/rerouting, invalid schema, duplicate, delayed and old-generation messages produce the specified states and never restore obsolete selected guidance.
- [ ] Source stall and transport gap are detected independently with boundary/clock-wrap tests; delayed new packets are checked against the local request deadline and conservative age. Heartbeats/malformed/expired replies do not reset freshness.
- [ ] A real Bluetooth interruption/reconnect recovers the newest coherent snapshot; simulated packet loss tests bounded queues and no unbounded resend backlog.

**Verification:** controlled-clock tests plus `source-stall`, `link-gap`, `reorder-invalid`, `reroute` and lifecycle scenarios. Include a process/Binder interruption on the phone and one real wireless disconnect. Acceleration is not used for reported physical latency.

**Verifiable output:** state transition assertions, event/ack traces, rejection counters, actual disconnect/reconnect record and observed timing distributions.

**Files likely touched:** protocol state tests, bridge fault injector, watch freshness tests and targeted fixes. Debug injection must remain excluded/inactive in normal production input.

## T15 — Deliver a single-command supervised desk iteration

**Status:** not_started. **Dependencies:** T11, T12, T13, T14. **Scope:** M, orchestration and evidence.

**Description:** Assemble the workflow the user actually wants: keep devices available, invoke one command, inspect the result. Reuse verified operations, not a second route/test implementation.

**Acceptance criteria:**
- [ ] `iterate --mode replay` builds changed watch code, launches/restores replay and writes frames/results with no manual scenario menus after initial tooling setup.
- [ ] `iterate --mode desk` incrementally updates changed components, restores/starts a named actual OsmAnd scenario and collects run-ID-scoped logs/acks/results. Verified unavoidable watch-mode actions are clearly prompted and timed, not disguised as automation.
- [ ] Three consecutive runs reuse maps, signing, grants and pairing; a failed run returns failure and preserves evidence. No stale screenshot/build from another run can be mistaken for the new result.

**Verification:** `python3 integrations/garmin/dev.py iterate --mode replay --scenario fork --out build/garmin-review/T15-replay`; corresponding desk run; repeat three times and include a deliberate failure. Human visual supervision is allowed; repeated reinstall/route-selection instructions are not the routine workflow.

**Verifiable output:** three run manifests with component IDs, logs, result tables, frame provenance, actual human action counts and a short demonstration transcript.

**Files likely touched:** orchestration/evidence writer and README. Do not build an unrelated dashboard; a small inspectable report is enough.

## Checkpoint D — Iteration usability

- [ ] The user can supervise a repeatable run rather than perform the setup sequence on every edit.
- [ ] Replay and hardware evidence are clearly distinguished, with no hidden manual steps.
- [ ] Write checkpoint-D summary. If recurring hardware actions make the workflow unacceptable, report the measured limitation for a decision; do not silently waive the automation requirement.

## T16 — Validate locked-phone and prolonged watch operation

**Status:** not_started. **Dependencies:** T15. **Scope:** S/M, measurement and targeted fixes.

**Description:** Verify the conditions a short foreground demo misses. Run real-time desk playback for service survival, display modes and long-run resource behavior.

**Acceptance criteria:**
- [ ] A 30-minute active simulated trip with phone locked reports source/transport ages and no unexplained gap above 5 seconds; a quiet/stopped source is not mistaken for a healthy stream.
- [ ] A 60-minute watch run reports crashes, memory observations where available, display/wake behavior and battery observations. Battery conclusions identify whether devices were charging; endurance measurement uses unplugged devices.
- [ ] Offline-map operation is checked with internet unavailable while Bluetooth remains enabled, plus recovery after the tested disruptions. Residual actual-riding readability limits are disclosed.

**Verification:** `run --mode desk` at 1x with timed screen-lock and long-duration scenarios; collect actual sample/ack counts and max/typical gaps. Use bounded polls for agent supervision and emit useful status rather than one uninterruptible hour-long shell wait.

**Verifiable output:** duration/count/timing report, phone/firmware/settings versions, charging state, battery deltas, crash record and honest pass/fail/blocked table. Repeat only a failed or changed concern.

**Files likely touched:** scenario duration/config, reporting and focused fixes. No speculative global battery-setting changes.

## T17 — Package the patch and evidence for the original reviewer

**Status:** not_started. **Dependencies:** T16 and all checkpoints. **Scope:** S, about 2 tracked documentation files.

**Description:** Make it possible for a fresh reviewing agent to assess implementation without replaying the entire conversation or trusting completion prose.

**Acceptance criteria:**
- [ ] `tasks/verification.md` indexes actual run IDs/outputs for every task and plan scenario, including not-run/blocked items, residual manual actions and limits.
- [ ] A local review bundle contains the patch/stat, staged/unstaged/untracked inventory, source/dependency/build IDs, compatibility matrix, frames/results and exact reproduction commands. Private keys and personal/device identifiers are not staged.
- [ ] Required focused tests/builds and `git diff --check` pass after the final relevant edit. Intended files are staged per AGENTS.md; no commit, fork or push is performed.

**Verification:** execute the documented one-command reproduction on the initialized environment; inspect all final acceptance rows; run `git diff --check`, `git diff --cached --check`, `git status --short` and artifact existence/hash checks. Review synthetic-vs-real provenance explicitly.

**Verifiable output:** tracked verification index, ignored final review packet and a concise implementation handoff stating what remains for human/original-agent review.

**Files likely touched:** `tasks/verification.md`, integration README and task status. The original reviewer will prioritize real geometry correctness, thread/lifecycle safety, old-message rejection and the actual automatic iteration workflow.

## Completion ledger

| Item | Status at planning | Evidence |
| --- | --- | --- |
| Relevant Android checkout | Complete | local commit `f22eeb0c1322a9f5784eed6e4d0addb43a0c2e32` |
| Source/API/platform research | Complete as research | `research/` snapshots; no runtime validation |
| Detailed execution plan/task list | Complete; 18-task structure/dependency and document checks passed | `plan.md`, this file |
| T00–T17 | Not started | None |
| Android/Garmin builds or hardware tests | Not run | None |
| Personal fork/commit/push | Deferred to user | None |
