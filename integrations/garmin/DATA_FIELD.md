# Junction activity data field

The Forerunner 970 data field is a separate Connect IQ app from the standalone
Junction app. It shows the same junction and distance during a Garmin activity;
the activity controls the field's update rate. Use a single-field activity page
for the road diagram. On smaller multi-field layouts it shows the distance or a
status instead, because the diagram would not be legible. The watch vibrates
when a new junction is displayed, as in the standalone app.

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
behavior on real hardware remain to be verified. The separately investigated
standalone app's prompted-launch exit is not resolved by this feature.

## Simulator and memory boundaries

The data field uses the same validated compact protocol and renderer as the
standalone app, but its activity callbacks replace the standalone timer. A
freshly decoded compact packet transfers ownership of its road points to the
field to reduce peak allocations; the standalone app retains its normal copy
semantics. A synthetic maximum-size scene has rendered in the field simulator;
that alone does not prove successive maximum-size packets, actual transport,
physical Bluetooth behavior, or visual readability. Repeat the full end-to-end
and real-watch checks before relying on it for a ride.
