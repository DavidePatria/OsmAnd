# Implemented junction scene draft

Executable validators: `protocol/scene.py`, `protocol/envelope.py`,
`watch/source/NavigationState.mc`, `NavigationRequestGate.mc`, bridge `SnapshotCodec`.
Public real-route-derived examples: `fixtures/recorded/`. Personal route output
stays under ignored `build/garmin-review/`. Machine schemas are
`protocol/{scene,envelope}.schema.json`; register both local `$id` resources to
resolve the URN reference without network access. Custom validators additionally
check radial bounds, aggregate point counts, anchor consistency and state clearing.
The wire rules are implemented and host/watch tested; actual delivery and encoded
payload limits remain device gates.

| Field | Type / meaning |
| --- | --- |
| `version` | Integer 1; reject unknown versions |
| `session` | Nonempty string ≤64 |
| `generation`, `seq` | Integers 0…1,000,000. Reject older generations and duplicate/older sequences in the same session. Live session authorization remains the input adapter's job. |
| `state` | `active`, `idle`, `recalculating`, `unavailable` |
| `geometryMode` | `routing_branches` (filtered), `map_context` (local OBF motor-road context), `layer_context` (same context with drawing levels), `route_only` (partial), `unavailable` |
| `reason`, `roadName`, `maneuver` | Strings ≤80 |
| `distanceM` | Integer 0…1,000,000; along-route distance to the FIRST decision anchor before entry; while inside a native roundabout, distance to its selected exit |
| `sourceAgeMs`, `fixAgeMs` | Integers 0…60,000 |
| `progressAgeMs`, `speedDmps` | Optional PAIR: route-matched progress age 0…60,000 ms; forward speed 0…700 decimeters/second. Both absent disables anticipation. |
| `radiusDm` | Integer 1…2,000 |
| `anchors` | ≤4 unique `id` strings ≤32, `point:[x,y]`, original integer `routeIndex` 0…1,000,000 |
| `paths` | Unique `id` ≤32 (≤24 for `layer_context`), `role`, `points:[[x,y],…]`, `anchorRefs:[[anchorId,pointIndex],…]` |
| `layer`, `segmentLayers` | ONLY in `layer_context`: every path requires integer `layer` −10…10; selected path additionally requires one integer level per segment. Context paths forbid `segmentLayers`. Ordinary modes forbid both fields. |

Coordinates are integer decimeters in a circle about the first decision: positive
x rider-right, positive y forward. Approach-up orientation and scale stay FIXED
for that junction. Only the renderer inverts screen y. Equal coordinates alone
do not establish connectivity. `selected` references every decision anchor;
`branch` has explicit anchor references. `context` is allowed only in the two context modes,
has EMPTY anchor references and makes no connectivity claim. Shared OBF vertices
are retained during simplification. Selected-route level transitions are also
retained. Levels control drawing order only; they never invent connectivity or
change OsmAnd's route. Lower roads draw first; black casing separates upper roads
from lower roads. All retained motor alternatives stay gray, selected route yellow.

Legacy bounds: 8 paths / 24 points per path / 96 total. Ordinary map context:
40 / 48 / 512; layered context: 40 / 48 / 512. This accommodates the observed
33–40-path scenes without omitting roads. Exact degree-two same-level context endpoints may be joined
on overflow, preserving every segment; selected paths are never compacted this way.
The pinned SDK serializes the maximum layered UTF-8 stress envelope to 15440 bytes,
below its 16384-byte limit. A normal fr970 simulator application decodes/renders
40 paths / 512 points. These do not certify Bluetooth or physical-watch behavior.
Coordinates must lie within the circle.
Inactive/unavailable geometry clears all paths and anchors. Overflow never silently
drops competing roads while claiming complete context.

Drawing levels use explicit integer `layer` when available, otherwise bridge +1,
tunnel −1, ordinary 0. `tunnel=building_passage` alone remains 0: a passage through
a building does not establish a road-under-road crossing. Unsupported levels
fall back explicitly rather than silently flattening a crossing. See OSM's
[layer definition](https://wiki.openstreetmap.org/wiki/Key:layer) and
[building passage definition](https://wiki.openstreetmap.org/wiki/Tag:tunnel%3Dbuilding_passage).
`layer_context` is a new mode within scene version 1: older strict decoders reject
it safely instead of drawing its roads without their required level metadata.

The live watch requests one 300 ms vibration pulse when a fresh, drawable native
junction appears. Its identity uses the session, first anchor route index and
maneuver; distance/sequence changes and temporary transport loss do not repeat it.
Idle or native arrival clears the identity. On the Forerunner the SDK controls
motor strength; physical feel and device settings are unverified. A reroute to a
different junction with the same session/index/maneuver could share this identity;
no additional route identity is currently carried by the wire protocol.

For native roundabouts, the geometry window extends through the native end offset
and a short segment after the selected exit. It expands the displayed radius only
when needed, within the existing 200 m wire limit; scenes too large for that limit
remain explicitly unavailable. Other junctions keep their previous scale. Before
entry, distance refers to the entry anchor; after OsmAnd passes entry and while it
retains the roundabout, distance refers to the native end/exit. The distance can
therefore change target at entry. No local timer selects or advances a direction.

Ordinary `map_context` now permits up to 40 paths (the existing layered limit),
still with at most 48 points per path and 512 total. Watch and bridge must both
be updated: older strict decoders safely reject ordinary scenes above 32 paths.
The compact transport's 8192-byte payload bound and SDK limits remain unchanged.

No moving rider marker or map scrolling. Production scene identity should be
session + navigation generation + original next-junction index; freeze geometry
until OsmAnd changes that junction/route. `JunctionSnapshotCache` and the Kotlin
provider implement this with one worker and at most two Android scenes: current
and the immediately following native direction. Current geometry is built first;
only then may the same window/OBF reader/compiler prepare the next one. A forward
native observation can promote that scene without a new geometry build. Preparation
never changes generation, distance or turn selection by itself. Heartbeats still
use freshly observed distance, fix/progress ages and matched speed; preparing a
scene early does not make a stale fix fresh. The watch receives only the current
scene through the existing protocol and retains no upcoming-turn queue.

Route identity replacement, recalculation, pause, deviation, unavailable state,
arrival/cancel and backward turn movement discard prepared scenes. One in-flight
worker retains its slot until completion; obsolete results cannot restore guidance.
Forward skips evict out-of-window scenes. First scene, cache misses or an unfinished
next build may still show loading. This does not fix context-capacity fallbacks,
change native crossing/advancement decisions or establish physical-watch stability.
The Android observation/lifecycle path still requires physical verification.

`distanceM` MUST refer to an UNEXTRAPOLATED route-matched sample. Anticipation
subtracts speed × min(progress sample age + local elapsed, 1 second), clamped at
zero. Never compensate an already estimated position twice. Zero speed and missing
progress fields disable anticipation. No watch timer advances the junction.
Pause freezes the replay clock. Live pause/off-route/recalculation clear geometry;
disconnect clears the watch state. The live exporter sends speed only when the fix
and progress projection have the same positive timestamp and the fix has a finite,
nonnegative speed at most 70 m/s; otherwise it sends zero. The phone's simulated
route produced 35/35 matching fix/projection timestamps. Physical GPS timestamp
and speed behavior still requires testing; the one-second cap is unchanged.

Normal replay updates at 1 Hz; selectable speed scales its clock. Waydroid native
simulation fixes were measured around 1500 ms, with actual API sampling at 1 Hz;
physical GPS fix cadence remains unverified. Physical Garmin transport has delivered
and acknowledged active scenes during indoor simulation; recent sends took about
one second each, not a comprehensive throughput measurement. The live target is
1 Hz with fresh progress correcting estimates. Age >5 s (source/fix/progress) or
accepted-message silence >3 s expires active guidance. Clock rollback/wrap expires
it too. Invalid/older packets do not refresh freshness. `NavigationRequestGate`
adds the watch's full request round trip to source/fix/progress age conservatively;
no phone/watch wall-clock synchronization is used. Host/watch tests establish the
logic, not real Bluetooth timing.

Python geometry conversion remains diagnostic. Android-independent Java geometry
is under `OsmAnd-java/.../router/junction/`; the saved-capture runner calls that
same compiler/reader. Monkey C
tests run in the real SDK. `JUNCTION_DRAW` proves drawing-code execution, not pixel
correctness. `preview.py` uses the same geometry, transform, colors and strokes,
with approximate fonts: its SVG/PNG outputs are NOT simulator screenshots. The
user compares them with coordinate links; map screenshots are unnecessary.

User-approved display filter: omit footway/cycleway/path/pedestrian/steps/bridleway/
corridor/platform defaults and explicit non-motor access. Resolve known access tags
from specific to general: motorcycle → motor_vehicle → vehicle → access. Explicit
motor permission can retain otherwise non-motor classes; restricted motor access
(private/destination/etc.) and ordinary tracks/service roads remain visible.
Always retain the calculated selected route. Unknown/conditional/country defaults
are not resolved into a legal-access claim. Extracts require `accessTagsVersion:1`
so old captures without access tags cannot silently drive this filter. Omission
reasons are retained in generated provenance. See OSM's
[access hierarchy](https://wiki.openstreetmap.org/wiki/Tag:motor_vehicle%3Dyes).
Traffic-light and stop-sign landmarks were discussed, but explicitly deferred.

## API wrapper and wire envelope

`AppInfoParams.navigationSnapshot` is optional and preserves constructors and old
keys. A supported ready wrapper has version 1, sceneJson (the scene above),
capturedElapsedMs (phone monotonic Long) and exportAgeMs (0…60,000). A supported
busy/unavailable wrapper instead has version 1 and status `unavailable`; an absent
wrapper denotes an old/unsupported exporter. Phone-to-phone Binder transfer shares
the same boot clock: the bridge adds max(exportAgeMs, now-capturedElapsedMs) to all
ages, rejecting future/negative clocks. Clock Longs never go onto the watch wire.
Busy UI observations time out at 200 ms and never return an old cached scene.

Watch request: version 1, kind `junction_request`, epoch (nonempty string ≤64),
requestId (integer 1…1,000,000). Optional drawing acknowledgement is the COMPLETE
set displayedSession / displayedGeneration / displayedSeq / displayedState. The
ack identifies a drawing callback and status, not pixel correctness.

Phone reply echoes epoch/requestId and has kind `junction_snapshot` plus scene,
or kind `junction_unavailable` plus reason ≤80 and NO scene. Negative replies
clear geometry without refreshing/replacing source session/order tracking.
Unknown source data is never turned into synthetic guidance.

At normal speed the watch attempts one request per second, with one outstanding
request and a strict <3 s response deadline. An expired, superseded, wrong-epoch,
malformed or older-generation response cannot refresh state. Clock rollback or
phone connection changes reset the request epoch and clear guidance. Android also
has one source-read/send slot; connection changes invalidate old work, and an old
callback cannot release a newer slot. No snapshot history queue is maintained.
SDK send-success alone is never a rendering acknowledgement.

The standalone navigation watch factory is `navigation.jungle`. The bounded
`navigation-smoke.jungle` uses the SAME input initialization and renderer but
disables its transport timer and exits through the SDK after the first frame.
This prevents a no-phone simulator session from hanging on unavailable transport;
it certifies startup/drawing only. Recorded replay retains TEST labels. Physical
Bluetooth, SDK callbacks under interruption and repeated real deployment remain
open checks.

## Compact physical encoding

The live SDK boundary now sends a JC1 ByteArray and restores this SAME logical
envelope before request/scene validation. See [wire.md](wire.md) for the exact
format, measured tethered throttling, compatibility, alternatives and limits.
No deadline or freshness threshold is relaxed. Wire-size-only passes above do not
establish navigation latency; use actual live request/draw/ACK evidence.
