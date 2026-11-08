# Moving map prototype

This is a separate experimental Forerunner 970 watch app, with its own app
identity. It uses Garmin's `MapTrackView` and a yellow sample polyline. It
requests the watch position while running, so the native map can follow the
device. Its line and matching GPS track are invented test geometry: **they are
not a navigable route**. The screen says `DEMO ROUTE` for that reason. It does
not connect to OsmAnd, Junction, or the phone bridge, and does not record an
activity.

## Run in the Garmin simulator

With the Garmin SDK and local configuration described in the companion README:

```sh
python3 integrations/garmin/dev.py run --mode moving-map --hold --out build/garmin-review/moving-map-demo
```

This builds the standalone prototype, starts or reuses the simulator and
deploys it. Leave the command running while inspecting the window; Ctrl+C
stops the demo client. Without `--hold` it is a short drawing-callback check.
The app has a separate identity from the existing Junction watch app and needs
no simulator ADB connection.

To try movement, open **Simulation → Activity Data** in the Garmin simulator,
select FIT/GPX playback and choose `watch/moving-map/demo-track.gpx` from this
directory. Start playback and leave that simulator window open. The five-point
synthetic track covers the same area as the sample line. Confirm that the
watch location and map actually move; callback output alone cannot prove this.
The simulator may use network map imagery, so a blank map is not proof that a
watch's installed maps are blank. Menu names can differ by simulator version.

The prototype was compiled and its 454×454 drawing callback ran in the
simulator. Visual map tiles, polyline placement, simulated movement, GPS
permissions and physical watch behavior have not yet been verified. An early
simulator run crashed when the map's screen area was unset; setting the full
screen area, as in Garmin's SDK sample, allowed drawing to proceed. The moving
map was drawn in two short checks, but the later held review launch failed:
the simulator exited, and a restart did not expose its SDK port. Restarting
and inspecting the simulator is required before the movement review.
The moving
map itself, activity integration, live OsmAnd route transfer, recalculation,
orientation, memory and battery behavior remain experimental.

Do not use this demo for navigation. The existing Junction app is unchanged.
