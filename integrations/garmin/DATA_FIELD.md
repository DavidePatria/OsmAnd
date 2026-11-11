# Junction activity data field

The Forerunner 970 data field is a separate Connect IQ app from the standalone
Junction app. It shows the same junction and distance during a Garmin activity;
the activity controls the field's update rate. Use a single-field activity page
for the road diagram. On smaller multi-field layouts it shows the distance or a
status instead, because the diagram would not be legible. The watch vibrates
when a new junction is displayed, as in the standalone app.

Both watch versions show direction chevrons on the yellow route. Junction
numbers use the device font closest to twice their former height, with
collision-aware placement and thin connectors to their markers. Where the
larger labels cannot fit, the renderer selects a smaller available font. On
2026-11-10 the user approved the placement in a recorded simulator preview;
physical readability and other crowded layouts remain to be checked.

## Build

Use the local SDK and signing configuration described in the companion README:

```sh
python3 integrations/garmin/dev.py build --target datafield --out build/garmin-review/datafield-build
python3 integrations/garmin/dev.py build --target bridge --out build/garmin-review/bridge-build
python3 integrations/garmin/dev.py check --suite datafield --out build/garmin-review/datafield-tests
```

The first command produces a separately identified PRG and build evidence. The
normal `navigation-watch` build remains the standalone app. Install the data
field and a bridge built with the same Android application ID and signing key
as the existing development bridge; installation and physical verification
are separate steps. Do not replace a personal OsmAnd installation.

## Use and hardware verification

1. Install the field on the watch and the updated separate bridge on the phone.
2. In the Garmin activity's data-screen settings, add a Connect IQ data field
   named Junction. Prefer a page with only that field.
3. In Junction Diagnostics or Junction Bridge Test on the phone, select **Use
   activity data screen**, then start the connection. Changing this selection
   stops the existing connection; start it again after changing modes.
4. Start an activity on the watch, show the Junction page, and start an OsmAnd
   navigation simulation. Check the junction, distance, vibration, background
   behavior when changing pages, and normal activity recording. End or discard
   the test activity as appropriate.
5. To use the standalone watch app again, turn the selection off and restart
   the connection. The bridge communicates with one selected watch identity at
   a time. A data field runs within the activity and cannot be opened by the
   phone's standalone-app prompt.

Phone-to-watch delivery, activity lifecycle, vibration, layout and battery
behavior on real hardware remain to be verified. On 2026-11-09 the user
reviewed and approved a paused simulator preview of an actual recorded Piazza
junction with 19 road paths. Separately, a live Waydroid native realistic
simulation of the saved Piazza route ran with the actual Garmin simulator and
tethered SDK. The user confirmed that junctions and distance updated correctly.
The bridge recorded 75 active drawing acknowledgements over about 121 seconds,
then acknowledged the arrival screen; the SDK was still connected. This is one
short simulator run, not physical-watch verification. The source working tree
also contained the separate moving-map experiment; artifact hashes and the
captured bridge log are under ignored `build/garmin-review/datafield/poc-live/`.
The separately investigated
standalone app's prompted-launch exit is not resolved by this feature.

## Simulator and memory boundaries

The data field uses the same validated compact protocol and renderer as the
standalone app, but its activity callbacks replace the standalone timer. A
freshly decoded compact packet transfers ownership of its road points to the
field to reduce peak allocations; the standalone app retains its normal copy
semantics. The field validates the expected packet header and releases its old
scene before decoding the replacement, because holding two maximum scenes caused
an out-of-memory error. An expected but malformed replacement clears the old
scene; an unrelated or expired packet does not. This can briefly leave no scene
if a replacement is invalid, but never displays fabricated or stale roads.
Duplicate validation was removed from the ownership path to avoid a watchdog
timeout. These are field-memory tradeoffs, not physical transport measurements.

After those changes, 32 data-field and 32 standalone watch regression tests
passed. A simulator stress fixture decoded and drew two consecutive synthetic
40-path/512-point compact scenes in the actual data-field runtime, with about
55 KB free after the second draw. It does not cover live SDK transport, every
possible scene, physical Bluetooth, or a real activity lifecycle. Further live
routes and real-watch checks remain necessary before relying on it for a ride.
Evidence is in ignored `build/garmin-review/datafield/poc-*` directories.
