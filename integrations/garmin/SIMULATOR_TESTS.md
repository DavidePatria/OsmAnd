# Short native OsmAnd + Garmin simulator tests

Routine tests use five short routes calculated and simulated by native OsmAnd in
Waydroid, through the normal separate bridge and live Garmin SDK into the fr970
simulator. There is no custom motion engine, recorded replay, fixture injector,
production routing change or phone fallback. Native REALISTIC mode owns speeds,
mapped-light stops, unseeded noise and advancement. Precise scripted edge cases
remain deferred. Upcoming-junction geometry caching does not change native motion.

## Profiles and limits

| Profile | Coverage | Limit | Repeats |
|---|---|---|---|
| `smoke` | One saved-problem focus route | 5 minutes | Never |
| `regression` (default) | Five short routes, one pass | 30 minutes | Never |
| `endurance` | Selected routes repeatedly | Explicit `--hours` required | Yes |

A limit is a cap, not a mandatory wait. The test-only live input observer exits
normally after the required arrivals, allowing ten seconds for final draw ACKs.
The host still requires real native arrival and correlated active/arrived draws.
It checks normal observer exit; it does not kill/restart the SDK to end a pass.
A budget exhausted before required arrivals is incomplete, never passed. The cap
covers the deployed watch run; allow startup/build and bounded cleanup overhead.
Only the explicit endurance profile accepts an hours argument. Routine profiles
reject the old long-route manifest, preventing accidental multi-hour tests.

Long runs remain useful for intermittent failures, but are opt-in. The former
four-hour run was deliberately interrupted at the user's request; its evidence
is preserved. Short-test success cannot establish four-hour stability or physical
BLE/GPS, watch firmware, OEM battery behavior or riding readability.

## Fixed short scenarios and private reports

Current inputs are under ignored `build/garmin-review/sim-suite-short/`:

- `suite.json`: explicit five endpoint pairs (not every pair among their endpoints),
  source hashes, parent route references and chosen native route-point windows.
- `native-plan-v0_1_0-final/`: current actual recalculated routes, native length/journey time/turn count,
  capture hashes and installed source/bridge APK plus routing-map hashes.
- `selection-v0_1_0-final.json`: current fixed native instruction-density ordering and REALISTIC mode.
- `routes.md`: separate full endpoint/route/time report.
- `REVIEW.md`: rationale, limitations and observed short-test results.
- `start-test.sh`: local convenience launcher, default regression.

Q001–Q005 come from the five previously selected turn-dense parent routes
R014/R004/R007/R017/R020. Windows are approximately 600 metres with 3–5 native
turn instructions, about 3 km total instead of 49 km. Nearby repeated endpoint
pairs are avoided. Q003 is anchored around both saved R007 path-capacity failures;
the freshly calculated native route includes both decision locations. That alone
is not proof that its rendered scene will reproduce the same capacity fallback.
Native recalculation between shorter endpoints is allowed to choose its route;
we do not force parent geometry or inject synthetic turns. The full parent routes,
original 20-pair plan, parked 15 and old evidence remain in their original folders.

Native journey estimates are planning references. Actual REALISTIC duration depends
on native vertex stepping, road speed and mapped stops. Do not reuse the former
94-minute constant-speed or 141-minute full-route duration for this short suite.
Precise noisy traces are not reproducible because native noise is unseeded.

## Roundabout regression: Piazza dei Re di Roma

This focused scenario covers the reported problem where the watch stayed at
zero metres while travelling around the Piazza. The locally saved short route
is approximately 825 m and takes roughly two minutes in native REALISTIC mode;
the runner caps it at five minutes. OsmAnd calculates and drives the route, and
the separate bridge sends live data to the Forerunner 970 simulator. The private
route endpoints, actual route report and earlier results are in
`build/garmin-review/piazza-re-di-roma/README.md`. These local inputs are ignored
by Git; copy or recreate them on a new machine rather than expecting a checkout
alone to contain them. Setup, SDK, map and private configuration prerequisites
are described below and in [JUNCTION.md](../../JUNCTION.md).

With the simulators connected, from the repository root run:

```sh
./build/garmin-review/piazza-re-di-roma/start-test.sh roundabout-01
```

Choose a new name for each run: the runner refuses to overwrite existing
evidence. If the connection is not ready, use the `prepare` command below with a
new output directory and select **Connection → Start** in Garmin when prompted.
Leave Waydroid visible, with its offline map and development apps installed. The
launcher inhibits sleep; keep the machine powered with its lid open. The test
changes the route in the isolated Waydroid development app, not on the phone.

On the watch, check that the full roundabout and its actual exit are visible,
with surrounding motor roads in grey and the selected route in yellow. Before
entry, the distance refers to the entry; after entry, it refers to the exit and
can rise at the moment the target changes. It should count down towards the exit
rather than remain at zero inside the roundabout. OsmAnd controls advancement to
the next junction. Visual inspection is still necessary: an automated arrival or
drawing callback alone does not establish that the exit is readable.

Find the run under `build/garmin-review/piazza-re-di-roma/roundabout-01/`.
`result.json` records completion or failure and native/watch arrival; inspect
`samples.jsonl` and `watch.log` for progress and draws. A timeout, an incomplete
route, or `no_initial_watch_frame` is not a pass. The latter occurred once when
the Garmin simulator was stuck at its startup triangle; save the failure and
restart the simulator before reconnecting. Physical Bluetooth, GPS, watch
vibration and riding readability require separate device testing.

On 2026-11-08, `demo-20261108` passed with the final build: native and watch
arrival were acknowledged. The 33 sampled observations after entry counted from
121 m to 8 m, with 36 mapped paths and no zero-distance samples. This records
observed simulator behavior, not a substitute for a visual or physical review.

After an app or map update, create a new plan and selection so the saved
environment fingerprints match the installed Waydroid apps and maps:

```sh
python3 -B integrations/garmin/sim_suite.py plan \
  --waydroid-config ~/.config/osmand-junction/waydroid.json \
  --suite build/garmin-review/piazza-re-di-roma/short-suite.json \
  --out build/garmin-review/piazza-re-di-roma/plan-NEW
python3 -B integrations/garmin/sim_suite.py select \
  --suite build/garmin-review/piazza-re-di-roma/short-suite.json \
  --plan build/garmin-review/piazza-re-di-roma/plan-NEW/plan.json \
  --out build/garmin-review/piazza-re-di-roma/selection-NEW.json
```

Update the private `start-test.sh` to point to those new paths before using it;
preserve prior plans and evidence. Planning recalculates routes in Waydroid, so
do not run it while another test owns the simulator or navigation is active.

## Setup and launch

Use the private explicit Waydroid target for every Android command. Source debug
controls version 2, offline maps, normal permissions and the debug bridge must
already be installed. The runner never installs/resets apps or clears logs.
Show the full Waydroid UI before relying on ADB; its invisible container previously
froze. Persistent portrait sizing/rotation lock is already configured locally.
The physical phone and personal OsmAnd are not accessed.

If the retained SDK connection is ready, use a new output name:

```sh
./build/garmin-review/sim-suite-short/start-test.sh check-01
./build/garmin-review/sim-suite-short/start-test.sh smoke-02 smoke
```

The local launcher holds a sleep inhibitor for the command. Keep the machine
powered with its lid open. A desktop lock must not be interpreted as a successful
test if the simulator later stalls. Ctrl+C records an interruption, not a crash.

Equivalent direct regression command from the repository root:

```sh
python3 -B integrations/garmin/sim_suite.py run \
  --suite build/garmin-review/sim-suite-short/suite.json \
  --plan build/garmin-review/sim-suite-short/native-plan-v0_1_0-final/plan.json \
  --selection build/garmin-review/sim-suite-short/selection-v0_1_0-final.json \
  --waydroid-config ~/.config/osmand-junction/waydroid.json \
  --garmin-config ~/.config/osmand-junction/dev-config.json \
  --profile regression --out build/garmin-review/sim-suite-short/check-01
```

Use `--profile smoke` for the focused five-minute cap. A long run requires both
`--profile endurance --hours NUMBER`; it is never the default. Do not start another
suite or prepare/restart the bridge while a run owns the simulator lock.

Cold setup may still require the one manual Garmin **Connection → Start** action:

```sh
python3 -B integrations/garmin/sim_suite.py prepare \
  --waydroid-config ~/.config/osmand-junction/waydroid.json \
  --garmin-config ~/.config/osmand-junction/dev-config.json \
  --out build/garmin-review/sim-suite-short/prepare-NEW
```

Preparation verifies the exact task-owned tcp:7381 forward and actual connection;
a conflicting device forward is rejected. It opens the source and bridge UI before
foreground operations. No sending watch app is deployed before readiness. Readiness queries the existing bridge SDK singleton for its current tethered
device status, with a fresh request ID and matching process ID. It does not rely
on old log messages or require the watch app to be running. The query never
initializes SDK transport, opens an app or changes the connection.
One idle-exit probe reported SDK disconnection; after a simulator restart, a
completed native-route test exited normally and retained CONNECTED. Do not assume
either outcome: query current state and use Connection → Start only if disconnected.
Routes inside a running suite reuse the connection. The query does not reconnect. There is no reconnect/relaunch loop hiding a failed run.

To re-plan after an APK/map change, use the frozen suite with a NEW plan folder,
then run `select` against it and a NEW selection file. Never edit the old captures
or keep their old environment hashes after updating the APK/maps.

## Evidence and interpretation

`result.json` is atomic at checkpoints. It records profile, cap, required routes,
routes excluded by the smoke profile, failures, measured durations and unfinished
coverage. A stale running marker after power loss is not success. Source samples,
filtered bridge events and watch output are streamed/flushed to private files.
Host tools, manifests, selection and build hashes identify the actual tested inputs.

Every route pass requires native arrival plus correlated active and arrived watch
ACKs. PID changes, fatal events, SDK disconnect, client/log termination, active
ACK/draw gaps and route stalls stop progression without automatic recovery. A
route timeout is a stall guard, not evidence of a crash. Freshness is unchanged.
On failure the healthy client is preserved for inspection and still has its cap.

Distinct-fix summaries and scenario `observations.jsonl` record zero speeds, native
turn changes and changes between consecutive zero-speed observations. These do
not automatically establish physical junction crossing correctness. The native
realistic features are enabled; coverage is claimed only when observed. Precisely
placed before/mid-junction stops, crawling schedules, erroneous speed spikes and
missing-fix sequences remain deferred by the user's native-first choice.

The saved capacity cases and their original full-route logs remain under
`sim-suite-realistic/findings/path-capacity/`. Their missing gray-road context is
an open geometry issue, not the established cause of the physical watch exit.


## Upcoming-turn cache checkpoint

Android prepares one native direction ahead, using the same bounded window and
geometry compiler as the current diagram. Current + next scenes only; one worker.
Only native observation selects the current turn; route replacement/recalculation,
pause, off-route, arrival/cancel, unavailable state and backwards movement discard
preparation. Watch protocol, freshness and native REALISTIC motion are unchanged.

Focused Q003 live cache test completed in 188.6 s / 149.4 s native motion, with
native and actual-watch arrival ACKs and normal early exit. All four scene geometries
exactly match uncached Q003. Between-turn loading draws were 1007/1014 ms in the
baseline and absent in this cache run; initial geometry still required a build.
Unseeded timing differs, so this is one observed regression comparison, not a
universal no-loading guarantee. Capacity fallbacks at 35/33 pieces are unchanged;
the old ordinary 32-piece limit was our format budget, not a Garmin road-count limit.
The revised 40-piece budget has passed saved-scene and maximum-heap tests; see
the latest verification entry for live coverage and remaining bounds.
See private `turn-cache/analysis.json` and `turn-cache/smoke-01/`. No full five-case
cache pass or physical-device verification is claimed.


## Piazza roundabout regression

The user's exact route and separately labeled shorter 825 m route are private in
`build/garmin-review/piazza-re-di-roma/README.md`. The shorter route retains the
same native Piazza entry, second exit and requested destination. Its local launcher
uses native REALISTIC navigation and the current installed APK hashes. After entry,
distance refers to the selected native exit; the same full roundabout diagram
continues to be shown. The user's chosen behavior is one diagram, not a separate
exit close-up. Existing point/path/200 m bounds remain enforced.

Baseline: native direction was retained through the circle while 32/33 sampled
inside snapshots reported zero; the selected path stopped after 75 m, short of
the 130.3 m exit. Updated live test: 37 sampled inside snapshots counted from
132 m to 1 m with 36 map-context paths; native/watch arrival and normal exit passed.
Real rendering readability and physical-watch operation remain separate checks.
The two saved former path-overflow cases also now compile with map context; scenes
above the new 40-path/512-point bounds can still be explicitly limited.
