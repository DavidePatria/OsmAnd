# Start here: implement the Garmin junction companion

## Latest — roundabout exit and full context verified (2026-11-08)

The user requested the Piazza roundabout fix and authorized local commits and
pre-1.0 version tags. `AGENTS.md` was consolidated to reflect the session's
standing requirements. Current work targets native end-offset distance after entry,
a selected-path window through the actual exit, and an adaptive bounded radius.
Ordinary mapped context now allows 40 paths, still 48 points/path and 512 total;
old watch/bridge builds must be updated before consuming ordinary scenes above 32.

37 JVM geometry/progress, 19 bridge and 29 Garmin watch tests plus 109 host tests
passed. Synthetic 40-path/512-point ordinary context rendered in the normal Garmin
application heap; worst tested 40-path compact SDK packet was 6,636 bytes. Captured
Piazza scene now includes its real exit and continuation with 36 paths, and two
previous 33/35-piece fallbacks now yield 40/39 mapped paths. All captured-scene
checks agree between full and local route windows. These are offline and simulator
checks, not a physical-device or pixel review. The two isolated Waydroid apps were
updated; the user reconnected the simulator. Native Piazza live verification passed at `roundabout-fix/live-01/`: 37 inside
samples counted down 132 m → 1 m, with 36 map-context paths, native/watch arrival
and normal exit. That run used RNDB2 before the final change that also recognizes
roundabouts without a numbered exit; the final build and focused test passed.
A final-build live rerun stopped before route start with `no_initial_watch_frame`;
its evidence is under `roundabout-fix/live-final/` and it is not a live pass.
The user chose one full roundabout diagram and exit countdown.
Visual readability and physical-device verification remain open. Five short test
cases were re-planned for the current APK hashes under `native-plan-v0_1_0-final/` and
`selection-v0_1_0-final.json`; the local launchers use current fingerprints. The user
requested the local v0.1.0 checkpoint. Check Git for the current commit and tag.

## Earlier checkpoint — haptic alert and Piazza reproduction (2026-11-08)

The requested Garmin alert is implemented: one 300 ms pulse when a fresh,
drawable native junction first appears, including the first junction. Distance
updates, stale/loading data and reconnect to the same scene do not retrigger it.
The identity uses session + first anchor route index + maneuver; idle/arrival
clears it. Identical keys after reroute can represent a different junction, a
known limitation until the wire carries a route identity. Simulator SDK tests:
29 pass, including duplicate/reconnect checks; production watch build passes.
A live Q001 native route passed with seven distinct valid scene identities and
seven vibration calls, no vibration errors. The physical motor/strength/ride has
NOT been tested and no watch transfer was made. Evidence: private
`junction-vibration/{watch-build,watch-tests,live-01,analysis.json}`.

The user supplied exact Piazza dei Re di Roma endpoints. OsmAnd's exact 2.507 km
route contains an initial detour; a separately labeled 825 m test starts from a
captured point on that same approach and uses the exact requested destination.
Native recalculation confirms the same Piazza entry, second exit and Via Appia
Nuova departure. Native live simulation arrived normally in 124.4 s. Entry to
exit is 130.3 m along the route; current yellow route export stops at 75 m from
entry, so it cannot reach the exit. After entering, 32 of 33 sequential samples
reported zero distance while OsmAnd still retained that roundabout; 40.7 s span.
The watch recorded repeated zero draws. The findings are reproduced, not fixed.
The 32-path fallback bug and physical watch-exit cause are separate and still open.
Private route/report/launcher: `piazza-re-di-roma/README.md`, `start-test.sh`,
`baseline-01/` and `baseline-analysis.json`. Exact and short cases are preserved.

The first user-facing cache demo initially failed with no first watch frame and a
stalled Garmin triangle. After preserving evidence, the stalled client and
simulator were stopped with SIGTERM and restarted; user reconnected, second demo
passed and user confirmed it worked. No claim that simulator startup is fixed.
No personal phone or physical watch was accessed. No commit or push.

## Latest checkpoint — current/next cache verified (2026-11-08)

The user explicitly requested implementation after the connection check. Android
now keeps current + one upcoming native junction scene, with one geometry worker.
Current work wins; route identity/lifecycle invalidation discards obsolete scenes.
Only OsmAnd advances the current turn. Watch protocol, route/fix freshness and
road geometry are unchanged. First scene/cache misses can still require loading.

32 focused JVM junction tests, 108 host tests and x86 debug APK build pass. Update
was ONLY in verified Waydroid. All five frozen short cases were freshly re-planned.
Live Q003 cache smoke passed native/actual-watch arrival and normal observer exit
in 188.6 s total / 149.4 s native simulation. All four scene geometries exactly
match the uncached baseline. Baseline had two inter-turn geometry-loading draws
lasting 1007/1014 ms; this cache run had none (initial build excluded). Native
REALISTIC timing is unseeded; this one route is not a full five-case/physical pass.
Private evidence: `turn-cache/{geometry,android-build,smoke-01,analysis.json}`.

Both 35/33-piece capacity fallbacks still reproduce. The 32-piece ordinary cap is
our exporter/format budget, NOT a Garmin 32-road ceiling or an effect of caching.
40-piece layered scenes already have simulator/SDK tests; any ordinary-budget
revision must preserve all context and verify validators, packets and memory.
This issue and the physical watch-exit cause remain OPEN.

A separate host Garmin simulator SIGSEGV happened when the user reconnected,
BEFORE cache installation. Saved core shows GObject/GTK3 main-thread frames;
preceding log has GTK/FreeType errors. Cause is not established. Preserved evidence
in `turn-cache/simulator-failure/`; simulator reopened after capture, user connected,
and short cache test then completed. No production workaround was introduced.

No test is running. Source is idle/not simulating. The fresh SDK query AFTER this
normal route-test exit reports CONNECTED. The earlier five-second idle probe had
reported NOT_CONNECTED after exit; do not infer that every normal exit disconnects
SDK. Query actual current state, request manual Connection → Start only if needed.
The current launcher uses `native-plan-turn-cache/plan.json` and
`selection-turn-cache.json`; earlier baselines/hashes remain untouched. No phone,
commit or push. See [test instructions](../integrations/garmin/SIMULATOR_TESTS.md).

## Current workflow — short tests, no automatic endurance (2026-11-08)

The user rejected multi-hour routine tests. The long realistic run was deliberately
interrupted with seven completed journeys; preserve all evidence, never call it a
four-hour pass. No test is currently running. Short smoke Q003 completed normally
in 183.7 s wall time / 151.7 s native simulation, with real arrival ACKs and normal
observer exit reason=completed, before its five-minute cap. The capacity defects
reproduced at 34.9 s (35 pieces) and 85.2 s (33 pieces); they are NOT fixed.

Use ignored `build/garmin-review/sim-suite-short/`: five explicit native endpoint
pairs, approximately 570–600 m each, 3–5 turns each, 2.96 km / 18 turns total.
They derive from the same five dense parents; Q003 includes both saved capacity
locations, and native recalculation contains both. Normal OsmAnd REALISTIC motion
and advancement are unchanged. No custom fix stream or speed-up clock. The newer cache checkpoint above supersedes
this uncached baseline.

Default `start-test.sh NEW_NAME` is regression: five short routes ONCE, 30-minute
cap with normal early exit after arrivals. `start-test.sh NEW_NAME smoke` is one
focus route, five-minute cap. Endurance requires explicit profile and hours.
Routine profiles reject long manifests and hours arguments. Actual full short
pass remains unmeasured; native journey references total 9.52 min, provisional
expectation about 15–20 min with native cadence/stops, never a four-hour default.

**Current handoff:** the user selected Connection → Start and the fresh SDK query
reported CONNECTED. A five-second observer exited normally (code 0, reason=duration),
but six seconds later the actual SDK reported NOT_CONNECTED. This is a recorded
simulator/deployment lifecycle limitation, NOT an idle-readiness pass. The read-only
query correctly detects it without stale ACKs or fake logs. One manual menu action
may be needed per new deployment, not between routes within one suite. Evidence:
`sim-suite-short/idle-sdk-probe/`. No long test was started.

**Cache continuation:** implementation and focused live verification are complete;
see the newer checkpoint above. Earlier no-prefetch entries describe older builds.

Current inputs are `native-plan-turn-cache/plan.json` and `selection-turn-cache.json`;
the local launcher and instructions reference them. Older smoke files retain their
original bridge hash. 108 host tests, focused native smoke and debug bridge build
pass. No phone/personal installation was touched. See private `REVIEW.md`,
`routes.md`, and [instructions](../integrations/garmin/SIMULATOR_TESTS.md).

## Interim findings — user returned (2026-11-08, 12:32 local)

The realistic run is still active; leave its inputs, apps and simulators unchanged
until its approximately 13:04 local timer end. All five routes completed once,
R014/R004 also completed a second time. First pass measured about 141 minutes
including setup. No watch runtime exception, scoped Android fatal event or SDK
disconnect was found. This is an interim result, not the final endurance pass or
closure of the physical watch-exit investigation.

Concrete finding: two R007 junctions exceed the ordinary 32-path capacity after
existing compaction (35/33 pieces). Actual watch output falls back to route_only
for about 47/22 seconds, losing surrounding gray-road context. Two live samples,
native route captures, hashes and decision-location links are saved privately in
`sim-suite-realistic/findings/path-capacity/`. Investigate these without silently
dropping road arms or relaxing limits. No fix has been implemented.

The interim trace also has 128 brief loading episodes (maximum about 2.04 seconds).
No sampled turn change occurred on entering or remaining stopped; this does not
disprove the user's uncontrolled physical traffic-light report. Preloading stays
last. Read private `sim-suite-realistic/INTERIM_FINDINGS.md` and updated `routes.md`
for measured timings, limitations and saved cases, then the current result.json.

## Current run — native REALISTIC and five densest routes (2026-11-08)

The user chose native realistic simulation first and deferred unsupported scripted
edge cases. The new four-hour run is detached and active under ignored
`build/garmin-review/sim-suite-realistic/endurance-01/`, launched 08:02:58 UTC /
09:02:58 Europe/Rome, approximate timer end 13:04 local. Read its `result.json`
before touching the simulators. First live validation confirms `real_mode`,
following/simulating true, actual watch draws and correlated bridge ACKs. This is
running evidence, not a completed-route pass or explanation of the physical exit.
The task sleep inhibitor is present; locking the desktop is permitted, but actual
lock/suspend behavior must be judged from the run rather than assumed.

All 20 routes were freshly calculated after the verified Waydroid-only APK update.
The version-3 selection remains R014/R004/R007/R017/R020, 48.952 km and 99 turns.
REALISTIC owns speed, mapped-light stops and unseeded noise; the 72 km/h setting
and 94-minute estimate below are superseded constant-mode proposals. Native
journey references total about 118 min; actual realistic durations are unmeasured.
`routes.md` and `REVIEW.md` explain timings, coverage and commands. No custom
movement, timestamped fixture generator, preloading or altered freshness policy.

The old `sim-suite-rome/endurance-01` was deliberately interrupted at 07:58:59 UTC
for this revision: 2,867 active draws, 1,737 active ACKs, sampled peak 44,256 bytes,
no recorded crash. It is interrupted, not passed. Preserve its evidence. Native
speed/mode controls and x86 APK build pass; 104 host tests pass. New runs copy/hash
the host tools. A readiness fix accepts a fresh current-process draw ACK if the
initial CONNECTED event has rolled out of Android's finite log buffer; send-success
alone is not sufficient. Unsupported seven-case scripts remain deferred by choice.

## Historical density/native-simulation proposal (2026-11-08)

The user requested higher speed, five routes ranked by turn DENSITY, and mixed
edge cases, then questioned whether scripted movement adds too much complexity.
Native-first versus timestamped native input is awaiting their preference. No
scripted movement or event generator has been added. The current four-hour run
below is unchanged; do not report the proposed edge-case allocation as executed.

Density selection is prepared under ignored `sim-suite-density/`: R014/R004/R007/
R017/R020, 48.952 km, 99 non-straight instructions, 1.5–2.4 turns/km. Version 2
selects native CONSTANT 20 m/s (72 km/h). IMPORTANT: native visits at most one
route vertex per 1.5-second tick, so distance/speed underestimates timing. The
vertex-step estimate is about 94 minutes plus setup, not the 41-minute lower bound.
Private `REVIEW.md`, `routes.md` and `edge-cases-proposal.json` explain the change.

Debug-only native speed/mode controls compile in the x86 APK; 100 host tests pass.
No APK update or live new-speed validation has run. Before switching: preserve or
deliberately interrupt the original run, update only Waydroid, regenerate the
APK/map-hashed plan and selection, then verify actual mode/speed. The revised
runner rejects old controls and version-1 selections. Existing runtime retains
its already-loaded code and inputs. The physical watch exit is still unexplained.

## Earlier constant baseline — reproduce the watch exit (2026-11-08)

The user authorized a four-hour unattended live Waydroid + Garmin simulator run.
`build/garmin-review/sim-suite-rome/endurance-01/` is the current evidence directory;
read its `result.json` and launch log before touching either simulator. At launch,
R002 was active with actual watch draws and matching bridge acknowledgements.
This is an observed running checkpoint, not a completed endurance pass or a cause
for the physical watch exit. Do not restart apps, change maps/APKs, or deploy a
different watch build while the run is active. A stale running marker after host
loss is not success. See [simulator instructions](../integrations/garmin/SIMULATOR_TESTS.md).

All 20 directed routes between the user's five private points were calculated by
native OsmAnd. The five with the most non-straight instructions are frozen in
`selection.json`; the other 15 are parked. Their fixed-speed simulation estimate
is about three hours plus setup. `routes.md` is the separate private route/timing
report. Inputs, captures and runtime configuration remain outside Git. Waydroid
portrait sizing and rotation lock survived a session restart.

Crash diagnosis comes first. The user requested evaluating a small queue of
upcoming junctions as the LAST implementation task. Consider bounded Android-side
current/next geometry preparation with invalidation on route recalculation;
OsmAnd must retain advancement authority. No prefetch change is implemented.
Seeded stationary-intersection scenarios also remain deferred; see todo.md.

## Navigation-start prompt (2026-11-07)

The user transferred the full-round watch build and reported that it works well.
OsmAnd now prompts to open the bridge at navigation start, with a remembered
per-profile automatic option, and the debug build prefers the installed physical
test bridge. See the latest verification entry for build and physical-test status.

## Latest continuation — restored host and T12a (2026-11-06)

The local `build/garmin-review/HANDOFF.md` records a newer fresh-host checkpoint
than the historical section below. Destination marker, arrival screen and opt-in
separate-bridge startup are implemented. On this host a real tethered Rome run
produced about 1 Hz successful sends and drawing ACKs; a later native-arrival run
showed destination markers and 166 actual watch arrival draws. Auto-start was not
fully verified there. See the latest section of verification.md for the current
restart and authenticated-launch observations. Physical behavior remains open.

After restart Waydroid was restored with its visible UI, its explicit target was
verified, and the saved Rome route was recalculated. After a simulator ADB error and
tethered bridge restart, the user connected the simulator and the production watch
app drew live map context with decreasing distance. Automatic watch opening is still
unverified. No new commit is authorized.

## Latest checkpoint — connected Rome demo passed (2026-11-06)

Read this before the historical checkpoints below. The user accepted the gray-road /
yellow-route style in examples 1–5; all four previously limited examples now have
full context. Layered bridges retain gray alternatives; building passages do not
suppress context. Approved geometry 1–5 is identical. Gallery at port 8767 has ten
comparison examples; `/rome/` has seven actual Android scenes from the new route.

The REAL Waydroid → Binder → bridge → Garmin SDK TETHERED → fr970 drawing/ACK path
now passes: 241 samples, seven junctions, 217 full draws and 217 matching ACKs,
zero expiry draws during active guidance. Median draw interval 1001 ms (max 2001).
Largest observed wire packet 466 bytes, no SDK sleeps; native fixes 1500–1501 ms.
Arrival currently clears to idle/NO ROUTE; a dedicated arrival screen is NEXT.
The live watch/service/forward remain connected for iteration; do not replace the
watch with old comparison replays without telling the user.

Important cause/fix: nested replies triggered the SDK's simulated BLE delay and
expired. JC1 lossless binary encoding preserves geometry, metadata, request identity
and strict freshness checks. See `integrations/garmin/wire.md` for exact format,
compatibility, alternatives and limits (including large-scene latency and 64-frame
replay OOM). Current regression counts: 77 Python +25 JVM +8 Parcel +15 bridge +23
actual Monkey C =148. Evidence: ignored `build/garmin-review/grade-review/` and
`build/garmin-review/rome-challenge/compact-live/summary.json`.

NEXT user-approved work: destination checkered flag, distinct arrival screen, then
opt-in OsmAnd setting to start the SEPARATE bridge and request watch-app opening.
User chose keeping the bridge separate; do not embed Garmin SDK in OsmAnd. Use
native arrival evidence, not manual cancellation/zero distance. Coordinate inputs
are in ignored Rome captures; never stage them. Keep workaround notes current.
No new commit/push authorized; stage intended files, preserve the physical phone.

## Historical unattended checkpoint (2026-11-06)

Actual Waydroid native route simulation and bridge Binder export now pass, including
pause/frozen fixes, native detour/recalculation, permission loss/restoration,
cancellation and source restart without MapActivity. Three actual-packet Garmin
replays completed normally; 18 Monkey C regressions pass. The user's journey
reached arrival. Nine scene geometries exactly match the desktop Java engine.

Review: http://127.0.0.1:8767/index.html — five full layouts and four explicitly
limited views, with coordinate links. Local files/evidence are under ignored
`build/garmin-review/waydroid/desk/`. These are approximate-font previews, not
screenshots; user visual approval is pending. The public-route 30-minute screen-off
run PASSED (1801 fresh samples, no >5 s freshness gaps). Tethered SDK service starts, but simulator
peer reports NOT_CONNECTED; no live Garmin transport pass. SDK wire round trips also pass (482 samples, maximum 3736 bytes; maximum UTF-8/geometry stress 14577 < 16384). The normal-app 512-point render test passes. The public simulation and tethered bridge are stopped; the saved user route is restored in Waydroid and the first full scene is paused in the watch simulator. Continue from the latest verification section. Preserve the physical phone and do not commit without request.

## Waydroid continuation (2026-11-06)

The user installed Waydroid and approved Android debugging trust. Its session was
started successfully: Android 13/API 33, x86_64/x86, fully booted, no initial OsmAnd
installation. Explicit-target shell commands work without root. No physical phone
was accessed. The x86 development APK build passed in 10m18s; OsmAnd and bridge
installed and launched successfully. OsmAnd remained running with no fatal error
in its scoped recent startup logs. See ignored `build/garmin-review/waydroid/`
(`x86-build.log`, `osmand-launch.json`, startup/install logs). The same offline map
was staged in Android Download/junction-desk with a matching SHA-256; it still
needs placing/indexing in the test app's selected data directory. Runtime address
and private configuration are in that evidence directory; do not use the default
phone ADB target. Next: prepare app map/profile/selected-route inputs, then prove
route simulation and Android-side live data. Export cadence and Garmin transport
are NOT verified by successful installation/launch.
The offline checkpoint below remains the source/test baseline.

## Offline continuation (2026-11-06)

The no-phone implementation checkpoint is verified; no ADB/device access was used.
Java geometry, immutable inputs, a bounded dedicated OBF reader and saved-capture
runner now exist. Approved examples retain 24/14/16 paths and identical anchors,
with <1 m measured polyline differences. An actual fr970 replay of the Java scene
passed. Production input copies only a ~125 m route window on either side of the
decision, retaining original native indexes, so long routes are not capped by
the diagnostic's whole-route limit.

The Kotlin read-only provider + optional app-info API hook, foreground bridge
service/Start-Stop UI, strict snapshot decoder and watch request/epoch/deadline
input are implemented and compile. The bridge binds ONLY net.osmand.plus.junction.
UI observation is bounded at 200 ms; map work has one worker slot; obsolete work
cannot publish. Live anticipation is OFF until timestamp semantics are verified.
Unavailable replies clear guidance without resetting source order. Old API callers
keep their constructor/keys; absent snapshots denote unsupported exporters.

Evidence: 53 Python tests, 20 JVM geometry/cache/clock tests (including two portable
public real-data fixtures), 8 Android host Parcel
tests (API 24/36), 7 bridge host tests, 17 actual Monkey C tests. Final Android
app/API and bridge builds pass; bridge lint has 0 errors/3 existing advisory
warnings. The production navigation-watch variant compiles. A bounded startup
smoke draws through the SAME input initialization/renderer and exits through the
SDK, with transport explicitly disabled. Do NOT run an unattended real navigation
input against a no-phone simulator: native transport/client termination stalled
the SDK during development. See latest verification for failed attempts/recovery.

Next hardware gate: update-install both APKs, enable the bridge's existing OsmAnd
connected-app access once, start OsmAnd current-route simulation, grant bridge
nearby-device permission through its Start UI, and measure actual progress/fix
cadence, API observation and SDK exchange. Do not replace endpoints or uninstall.
Physical Bluetooth, reconnect, foreground/screen-off behavior, packet headroom and
Garmin sideload/readability remain unverified. Grade-separated layouts and larger
roundabout/coverage cases remain explicit geometry limitations. Traffic symbols
stay deferred. All edits after `0c6b7f8` are uncommitted; new commits require a user
request. Commands and current evidence are in the integration README/verification.

This is the entry point for a fresh implementation model. Read repository [AGENTS.md](../AGENTS.md), then [plan.md](plan.md) and [todo.md](todo.md). The plan is authoritative; `research/` contains earlier feasibility notes and alternatives, not a competing execution plan.

The relevant upstream Android repository is already cloned here from upstream base `f22eeb0c1322a9f5784eed6e4d0addb43a0c2e32`, with local checkpoint commits on branch `garmin-junction-plan`. Reuse it. The Android build and actual 970 simulator work. Optional export/live-delivery CODE now exists; live DEVICE integration is not verified. Earlier checkpoint notes below explain how this point was reached; the offline continuation above is current.

**Current priority: real junction-layout review with the actual watch simulator in the loop.** A read-only capture of the user's chosen motorcycle route has 163 points, 32 segments and 12 maneuvers. The simulator draws recorded scenes with gray road context, yellow selected route, fixed orientation/scale, one-second simulated progress and bounded distance anticipation. Nearby roads come from a bounded desktop query of the SAME offline OBF with OsmAnd's own reader; filtered attached turns alone are insufficient. See the latest checkpoint in [verification.md](verification.md) and `integrations/garmin/contract.md`.

The user is reviewing three generated watch-layout previews with OpenStreetMap coordinate links. They are approximate-font preview renders, not simulator screenshots; the simulator's actual drawing callbacks are separate evidence. Private captures/previews are under ignored `build/garmin-review/user-route/`. Do not overwrite the phone's selected route or stage its coordinates. Full map-context coverage and grade-separated crossings remain open. The production exporter is implemented and built, but the continuous position feed is NOT verified: current replay distance samples are synthetic. Next: measure route-matched progress/fix cadence from OsmAnd desk simulation and verify live transport.

Latest feedback applied: omit non-motor footpaths/cycleways using road class and access precedence, preserving motor overrides, tracks/service roads and the selected route. Updated scenes have 24/14/16 paths (53 Python tests now pass). Existing road-context extracts must include `accessTagsVersion:1`; regenerate older ones. The user asked only for this filtering change now. Traffic lights/stop signs were discussed but explicitly deferred; do not implement those symbols in the next step without renewed direction.

T00 setup passes. T01 still needs active-navigation/simulation evidence. T02 has simulator evidence but no physical sideload. T03 has one actual tethered echo/ACK pass followed by repeat-launch/USB failures; real transport stays open. T04 now has scene/envelope schemas and validators. T05 has replay and seventeen actual Monkey C checks. T07 has portable real/native inputs and twenty JVM checks; T08/T09 code builds but needs phone/Bluetooth verification. Pixel approval and physical watch evidence remain separate. Human supervision is available; automate routine setup rather than repeatedly asking for menu operations.

Work locally. The user will fork and push after building/testing. Do not set up GitHub access, create a fork, change remote destinations or push. The user subsequently authorized focused local commits and requested a clean index at this checkpoint. Stage intended changes as AGENTS.md requires. Preserve the user's existing F-Droid installation and test only the separate development app identity.

Every completed task needs actual evidence. Record blocked/not-run checks honestly. Follow the plan's boundaries: read-only export, actual OsmAnd-calculated routes, separate bridge and standalone watch app. Do not alter native routing or build a separate map-data engine to bypass a failed geometry gate. Do not substitute synthetic geometry for evidence from the real route adapter.

At each checkpoint, produce the defined summary. After implementation, the original reviewing agent will examine the patch, recorded commands/results, actual junction geometry, API/thread/lifecycle correctness and automation usability. Read `tasks/verification.md` for the actual evidence and unresolved limitations.

Suggested skills: use focused testing/TDD for new geometry and protocol behavior, following the local skill setup instructions if invoked; use diagnosis for reproducible difficult failures; use handoff to leave an evidence-based continuation when stopping. Do not initialize issue-tracker workflows or spawn other agents merely to implement this plan.
