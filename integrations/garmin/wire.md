# Compact SDK transport (JC1 / JC2)

This is a lossless encoding at the Garmin SDK boundary. OsmAnd's API JSON and the
logical scene/envelope contract are unchanged. Android `CompactWire` emits a
`byte[]`; SDK 2.4.0 serializes it as `MonkeyByteArray`, received as Monkey C
`ByteArray`. The watch restores the logical reply BEFORE the existing request,
scene, ordering and freshness validators. Legacy dictionary replies still work.
An older watch that only understands dictionaries rejects JC1; update both apps.

## Why this exists / alternatives for a later agent

Actual live tethered testing exposed an unmeasured assumption: a packet below the
SDK's 16384-byte limit is not necessarily fast enough for navigation. The pinned
SDK's `AdbConnection.sendMessage` unconditionally sleeps
`floor(serializedBytes / 600) * 1000` milliseconds before writing. A 2621-byte full
scene slept four seconds and missed our strict three-second reply deadline.
Smaller scenes sometimes arrived in time, causing the user-observed alternation
between the correct junction and POSITION OLD. Scoped SDK logs and the exact
installed SDK bytecode confirm the delay; this is simulated throughput, NOT a
measurement of the physical watch's Bluetooth throughput.

Chosen fix: compact complete snapshots with varints, coordinate deltas and a fixed
string table. Do not remove gray alternatives, falsify timestamps, increase the
three-second deadline/five-second freshness limit or patch the vendor SDK.
Retaining complete snapshots avoids cache synchronization/invalidation changes.
The Rome recording encodes to 84–453 body bytes with a normal request header;
measure actual SDK wire bytes and live behavior separately.

Limits: very large valid scenes or long Unicode metadata can still take several
seconds in the tethered SDK. JC1 does not guarantee 1 Hz for every allowed scene.
If measurements require it, consider geometry-once plus small progress replies,
keyed by session/generation and acknowledged geometry identity. That needs an
explicit geometry-miss/resync path and must never display old-route geometry with
new-route distances. A standard versioned binary format is another alternative;
this small custom codec avoids adding an Android/watch dependency, but requires
shared golden tests and coordinated format evolution. Physical BLE remains a gate.

Separate discovered limit: the current replay generator eagerly materializes all
frames. A 64-frame Rome replay exceeded the NORMAL app heap. The frame-count bound
alone is insufficient; do not claim arbitrary 64-frame traces are safe. A future
streaming/deduplicated replay loader or aggregate decoded-memory bound is needed.
Live delivery retains the current scene instead of a whole recorded sequence.

## Exact version 1 format

All numbers below are canonical unsigned base-128 varints, maximum three bytes and
2,000,000. Signed values use zigzag (`2*n` nonnegative, `-2*n-1` negative). Reject
overlong encodings, truncated input, trailing data and payloads over 8192 bytes.
Strings start with a string-table token (one-based); token 0 instead carries UTF-8
byte length (maximum 320) followed by literal bytes. The append-only version-1 table
is exactly `WORDS` in `protocol/compact.py` / `CompactWire.words`: states, modes,
roles, the two standard context reasons, j0…j3 and c1…c40. Changing existing indexes
requires a NEW format version. No lossy shortening or coordinate quantization is
introduced by this codec.

- Header: 74, 67, format version (1 or 2), reply type (0 snapshot / 1 unavailable), epoch,
  requestId. The restored logical envelope has `version:1` and the ordinary kind.
- Unavailable: reason string, then end.
- Snapshot: session; generation, seq; strings state, geometryMode, reason, roadName,
  maneuver; integers distanceM, sourceAgeMs, fixAgeMs, radiusDm; progress flag 0/1,
  followed by progressAgeMs and speedDmps only if present.
- Anchor count ≤4, then each id, routeIndex, signed x/y.
- Path count ≤40, then each id, role, point count 2…48 and signed x/y DELTAS from
  zero for the first point and the previous point thereafter. Aggregate ≤512.
- Each path then has reference count ≤4, each reference being anchor-array index
  and point index. Restore the original anchor ID; do not infer connectivity.
- Only in layer_context: signed path layer, then (selected path only) one signed
  level per segment. Ordinary modes have no such bytes.

The restored scene must STILL pass all ordinary mode-specific bounds, radial
checks, ID/reference rules, field ranges and lifecycle clearing. Epoch/deadline
validation remains in NavigationRequestGate; wire decoding cannot refresh age.

Public golden vectors: `fixtures/wire/compact.json`. Python verifies exact round
trips and rejects every truncated prefix. Kotlin must match those independently
encoded bytes and round-trip them through the ACTUAL SDK byte-array container.
Monkey C compares every restored field against both ordinary/layered goldens and
checks malformed input plus the unchanged deadline in the actual simulator.
Generated personal packets, runtime logs and SDK inspection artifacts stay in the
ignored review directory, never Git.

## Reconnecting the live desk setup

Launch the bridge activity before its debug start_tethered operation; starting a
foreground service from a background shell receiver can be rejected by Android.
Use only the explicitly verified Waydroid target and its existing exact forward.
Start the simulator ADB connection BEFORE launching the sending navigation app;
otherwise native modal errors can prevent a clean launch. The available tooling
cannot operate that native menu, so one user Start action is still required after
connection-breaking app updates. Wait for actual SDK CONNECTED before deploying.
A source with no valid maneuver can legitimately return unavailable instead of
idle: a positive decoded sequence proves delivery, not a particular source state.
A send-success callback alone does not prove drawing; require actual watch draws
and subsequent matching Android DRAW_ACK events.

## Version 2: destination and native arrival

The sender now emits JC2. The watch still decodes JC1 and legacy dictionary replies.
The existing string-table indexes remain fixed; `arrived` is appended at index58.
After the LAST path in a JC2 snapshot comes a 0/1 destination flag; if1, signed x/y
follow. Negative replies have no new suffix. JC1 has neither the suffix nor token58.
Unknown versions are rejected. The logical scene stays version1; old strict clients
reject new state/physical formats instead of displaying them incorrectly.

The optional destination must equal the selected path's last point, be inside the
scene circle and appear only with active geometry. The shared Java input preserves
the native GLOBAL destination index through route windows; clipped window ends are
never labeled as destinations. A marker is emitted only when the ACTUAL route end
is present and within75 along-route meters of the next anchor. It represents the
routed endpoint, which may be snapped to a road, not arbitrary input coordinates.

The Android exporter reads RoutingHelper.isRouteWasFinished(), an existing native
arrival flag set by finishCurrentRoute AFTER ordinary route clearing. Cancellation
and new route setup clear that flag. An `arrived` snapshot has distance0 and no
roads/anchors/destination field. The watch draws a vector checkered flag and ARRIVED.
An old GPS fix is irrelevant to a completed journey; arrival still requires fresh
source heartbeat/transport (unchanged5s/3s bounds), and cannot survive disconnect.
This is an arrival result, not a watch-side guess based on zero junction distance.
