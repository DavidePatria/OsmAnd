# Public real-route inputs

These two small inputs come from the documented public Lazio scenario, NOT the
user's personal route. They retain original native route indexes and nearby OBF
road geometry/tags before the display filter. No expected drawing was generated
by the simplifier: tests assert independently known native decisions/indexes,
right/left branch direction, distinct close anchors and bounded honest context.

- Route: public baseline (41.4472,12.6286) → (41.4675,12.9030), built-in motorcycle.
- Raw capture SHA-256: `0a58cf1db4cbec158e5e24c09563c357d1e559740f67aa489133489866c86c51`.
- Map: Italy_lazio_europe.road.obf, SHA-256 `db01a72e15bdf1cb4e74660e4f88e62f27476216ab71287294ea29d2d91518a0`.
- Double turn: native decisions 5/6, original point indexes 75/82, TR/TR, ~42 m apart.
- Fork: native decision 10, original point index 219, TSLL.
- Native route windows contain 25 / 39 points; bounded raw contexts have 57 / 74
  road objects. The portable tests need neither the phone nor the full OBF.

Generated with `junctionJavaScenes -Pjunction.inputFixtures=true` using the saved
PUBLIC baseline capture. Never copy private captures into this directory.

Map data © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright),
available under the [Open Database License](https://opendatacommons.org/licenses/odbl/1-0/).
