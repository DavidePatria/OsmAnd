# Start here: implement the Garmin junction companion

This is the entry point for a fresh implementation model. Read repository [AGENTS.md](../AGENTS.md), then [plan.md](plan.md) and [todo.md](todo.md). The plan is authoritative; `research/` contains earlier feasibility notes and alternatives, not a competing execution plan.

The relevant upstream Android repository is already cloned here from upstream base `f22eeb0c1322a9f5784eed6e4d0addb43a0c2e32`, with local checkpoint commits on branch `garmin-junction-plan`. Reuse it. Android/SDK setup and minimal watch implementation have progressed: T00 passes, the separate Android build installs and calculates a real offline route, and the watch builds/starts in the actual 970 simulator. Read [verification.md](verification.md) for evidence and limitations. Navigation export and live navigation delivery are not implemented.

**Current priority: T06 data usefulness before further watch integration.** The debug route probe now builds and has captured/validated a real motorcycle-mode route: 946 points, 99 selected segments, 20 maneuvers and 252 attached-branch entries. Start with `JUNCTION.md` and the T06 section of [verification.md](verification.md); use `integrations/garmin/route_probe.py` to reproduce the capture and its HTML reviewer. Review close turns 5/6 and fork candidate 10 against the actual map before claiming geometry usability.

T00 setup passes. T01 still needs active-navigation/simulation evidence. T02 has simulator evidence but no physical sideload. T03 has one actual tethered echo/ACK pass, followed by a failed repeat launch and intermittent ADB loss; it is deferred. The original T03-before-T06 sequence is superseded by the user's explicit data-first priority. Keep the remaining acceptance criteria open. Human supervision is available; automate builds, update install, route setup and capture rather than repeatedly asking the user to navigate menus.

Work locally. The user will fork and push after building/testing. Do not set up GitHub access, create a fork, change remote destinations or push. The user subsequently authorized focused local commits and requested a clean index at this checkpoint. Stage intended changes as AGENTS.md requires. Preserve the user's existing F-Droid installation and test only the separate development app identity.

Every completed task needs actual evidence. Record blocked/not-run checks honestly. Follow the plan's boundaries: read-only export, actual OsmAnd-calculated routes, separate bridge and standalone watch app. Do not alter native routing or build a separate map-data engine to bypass a failed geometry gate. Do not substitute synthetic geometry for evidence from the real route adapter.

At each checkpoint, produce the defined summary. After implementation, the original reviewing agent will examine the patch, recorded commands/results, actual junction geometry, API/thread/lifecycle correctness and automation usability. Read `tasks/verification.md` for the actual evidence and unresolved limitations.

Suggested skills: use focused testing/TDD for new geometry and protocol behavior, following the local skill setup instructions if invoked; use diagnosis for reproducible difficult failures; use handoff to leave an evidence-based continuation when stopping. Do not initialize issue-tracker workflows or spawn other agents merely to implement this plan.
