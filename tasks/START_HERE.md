# Start here: implement the Garmin junction companion

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
