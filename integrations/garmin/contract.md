# Implemented junction scene draft

Executable validators: `protocol/scene.py`, `watch/source/NavigationState.mc`.
Public real-route-derived examples: `fixtures/recorded/`. Personal route output
stays under ignored `build/garmin-review/`. T04 is partial: the complete live
request/epoch/AIDL delivery schema is NOT implemented.

| Field | Type / meaning |
| --- | --- |
| `version` | Integer 1; reject unknown versions |
| `session` | Nonempty string ≤64 |
| `generation`, `seq` | Integers 0…1,000,000. Reject older generations and duplicate/older sequences in the same session. Live session authorization remains the input adapter's job. |
| `state` | `active`, `idle`, `recalculating`, `unavailable` |
| `geometryMode` | `routing_branches` (filtered), `map_context` (unfiltered OBF road context), `route_only` (partial), `unavailable` |
| `reason`, `roadName`, `maneuver` | Strings ≤80 |
| `distanceM` | Integer 0…1,000,000; along-route distance to FIRST decision anchor |
| `sourceAgeMs`, `fixAgeMs` | Integers 0…60,000 |
| `progressAgeMs`, `speedDmps` | Optional PAIR: route-matched progress age 0…60,000 ms; forward speed 0…700 decimeters/second. Both absent disables anticipation. |
| `radiusDm` | Integer 1…2,000 |
| `anchors` | ≤4 unique `id` strings ≤32, `point:[x,y]`, original integer `routeIndex` 0…1,000,000 |
| `paths` | Unique `id` ≤32, `role`, `points:[[x,y],…]`, `anchorRefs:[[anchorId,pointIndex],…]` |

Coordinates are integer decimeters in a circle about the first decision: positive
x rider-right, positive y forward. Approach-up orientation and scale stay FIXED
for that junction. Only the renderer inverts screen y. Equal coordinates alone
do not establish connectivity. `selected` references every decision anchor;
`branch` has explicit anchor references. `context` is allowed only in map context,
has EMPTY anchor references and makes no connectivity claim. Shared OBF vertices
are retained during simplification. Grade separation currently causes an explicit
limited view, not a claimed full layout.

Legacy bounds: 8 paths / 24 points per path / 96 total. Map context: 32 / 48 / 512,
motivated by measured 29–30-path, 88–113-point scenes. These are engineering bounds,
NOT certified Bluetooth/heap capacities. Coordinates must lie within the circle.
Inactive/unavailable geometry clears all paths and anchors. Overflow never silently
drops competing roads while claiming complete context.

No moving rider marker or map scrolling. Production scene identity should be
session + navigation generation + original next-junction index; freeze geometry
until OsmAnd changes that junction/route. Current replay uses fixed scenes;
production exporter and lifecycle handling are pending.

`distanceM` MUST refer to an UNEXTRAPOLATED route-matched sample. Anticipation
subtracts speed × min(progress sample age + local elapsed, 1 second), clamped at
zero. Never compensate an already estimated position twice. Zero speed and missing
progress fields disable anticipation. No watch timer advances the junction.
Pause freezes the replay clock. The future live adapter must disable prediction
on navigation pause, off-route and disconnect.

Normal replay updates at 1 Hz; selectable speed scales its clock. Real fix/progress
cadence and live transport latency have NOT been measured. The live target is
1 Hz with fresh progress correcting estimates. Age >5 s (source/fix/progress) or
accepted-message silence >3 s expires active guidance. Clock rollback/wrap expires
it too. Invalid/older packets do not refresh freshness. The live adapter must add
a conservative transport-age bound using the plan's request/deadline mechanism;
replay reception timing is not proof of this.

Python geometry conversion is diagnostic, not production Java geometry. Monkey C
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
