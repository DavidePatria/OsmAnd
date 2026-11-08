# AGENTS.md - AI Agent Guide for OsmAnd Development

This document provides essential information for AI agents working on the OsmAnd Android project.

## 1. Project Overview
OsmAnd (OSM Automated Navigation Directions) is a powerful, open-source map and navigation application based on OpenStreetMap (OSM) data. It supports offline maps, routing, and a wide range of features for travel and outdoor activities.

- **Main Repository:** Multi-module Gradle project.
- **Languages:** Mix of **Java** and **Kotlin**.
- **Native Core:** `OsmAndCore` (C++) providing high-performance rendering and routing via JNI.

## 2. Project Structure
The project is divided into several sub-projects:

- `:OsmAnd`: The main Android application module.
  - `src/`: Java/Kotlin source code.
  - `res/`: Android resources.
  - `assets/`: App assets.
  - `test/`: Instrumentation and Unit tests.
- `:OsmAnd-java`: Core logic in pure Java. Contains data models, rendering logic, routing, and search. Independent of Android APIs.
- `:OsmAnd-api`: API for external applications to interact with OsmAnd.
- `:OsmAnd-shared`: Kotlin Multiplatform (KMP) library shared between Android, iOS, and server (JVM).
- `:plugins`: Contains various plugin sub-projects (e.g., `:plugins:Osmand-Nautical`, `:plugins:Osmand-Skimaps`).

## 3. Shared Code (Kotlin Multiplatform)
The `:OsmAnd-shared` module is a **Kotlin Multiplatform (KMP)** library designed to share logic across Android, iOS, and JVM platforms.

- **Targets:**
  - `androidTarget`: Android-specific implementations.
  - `iosX64`, `iosArm64`, `iosSimulatorArm64`: iOS-specific implementations.
  - `jvm`: Pure Java/Desktop implementations.
- **Source Sets:**
  - `commonMain`: Contains platform-independent logic (serialization, coroutines, data models).
  - `androidMain`, `iosMain`, `jvmMain`: Contain platform-specific implementations (e.g., SQLite drivers, I/O).
- **Key KMP Technologies:**
  - `kotlinx-serialization`: For JSON handling.
  - `kotlinx-coroutines`: For asynchronous programming.
  - `kotlinx-datetime`: For date and time operations.
  - `okio`: For cross-platform I/O.
  - `stately`: For concurrent collections.
- **Editing rules:** `OsmAnd-shared` is also compiled by the iOS app and by the standalone JVM build. Keep both compiling: an `actual` for every `expect` in each platform source set, no JVM-only imports in `commonMain`, and no removal of overloads or `@Jvm*`/`@Throws` annotations that Swift or Java callers use. When a change has to break compatibility anyway, name the affected declarations and consumers in the reply and in the pull request.

## 4. Architecture & Key Components
### Plugin Architecture
OsmAnd uses an internal plugin system to modularize features. 
- **Base Class:** `net.osmand.plus.plugins.OsmandPlugin`.
- **Location:** `OsmAnd/src/net/osmand/plus/plugins`.
- Plugins can hook into:
  - Map layers (`registerLayers`)
  - Widgets (`createWidgets`)
  - Context menus (`registerMapContextMenuActions`)
  - Settings (`getPreferences`, `getSettingsScreenType`)

### Main Classes
- **Application:** `net.osmand.plus.OsmandApplication` - central entry point, provides access to managers and settings.
- **Main Activity:** `net.osmand.plus.activities.MapActivity` - the main map view.
- **Settings:** `net.osmand.plus.settings.backend.OsmandSettings` - central point for managing preferences.
- **Base Fragment:** `net.osmand.plus.base.BaseOsmAndFragment` - the mandatory base class for new fragments.

### Core Services
- `NavigationService`: Handles background navigation.
- `DownloadService`: Manages map and resource downloads.
- `OsmandAidlService`: Provides an AIDL interface for external apps.

## 5. Key Technologies
- **Target SDK:** 36 (Compile SDK: 36, Min SDK: 24).
- **Kotlin 2.1.20**, Java bytecode target 17; the verified local build uses JDK 21.
- **AGP 8.10.1**.
- **UI Framework:** Primarily **standard Android Views** (XML layouts).
- **Logging:** `org.apache.commons.logging` via `PlatformUtil`.
- **SQLDelight:** Used for some database operations.
- **Rhino (JavaScript engine):** Used for voice guidance and other scripts.
- **JTS (JTS Topology Suite):** Used for geometric operations.
- **Picasso:** For image loading.
- **MPAndroidChart:** Custom version used for various charts (e.g., elevation).

## 6. Development Workflow
### Building the Project
Use Gradle to build the project.
- Build Debug APK: `./gradlew :OsmAnd:assembleDebug`
- List of Flavors: `nightlyFree`, `androidFull`, `gplayFree`, `gplayFull`, `huawei`.
- ABI Dimensions: `armv7`, `arm64`, `x86`, `fat`.
- Core Dimensions: `legacy` (no OpenGL), `opengl`.

### Testing
- **Unit & Instrumentation Tests:** Located in `OsmAnd/test/java`.
- Run tests: `./gradlew :OsmAnd:connectedDebugAndroidTest`

### External Resources
Many resources (icons, fonts, voice files) are not in the main `res` folder but are collected from `../../resources` during the build process via the `collectExternalResources` task.

## 7. Coding Standards & Best Practices
- **UI Design:** For new Material 3 UI, follow `OsmAnd/ui-guidelines/README.md`, then Google Material 3 and Android development guidelines.
- **Logging:** Use `PlatformUtil.getLog(YourClass.class)` for logging. Do not use `android.util.Log` directly in core classes to maintain portability.
- **Dependency Injection:** The project uses manual dependency injection. Key services and helpers are accessible via `OsmandApplication`.
- **Theming & Resources:** When creating or modifying UI, ensure consistency by utilizing and updating existing resource files:
  - `dimens.xml` and `sizes.xml` for dimensions and spacing.
  - `colors.xml` for application colors and palette.
  - `attrs.xml` for custom theme attributes.
- **Fragments:** All new fragments must extend `net.osmand.plus.base.BaseOsmAndFragment` (or its specialized subclasses like `BaseFullScreenFragment` or `BaseNestedFragment`) to ensure proper theming, application service access, and consistent lifecycle handling.
- **Strings:** All new user-visible strings must be added to the **beginning** of `OsmAnd/res/values/strings.xml` to support localization and simplify translation management. Avoid hardcoding strings in code or layouts.
- **Prefer Kotlin** for new UI code and modern components.
- **Keep core logic** in `OsmAnd-shared` (KMP) or `OsmAnd-java` where possible to maintain platform independence.
- **Use the Plugin system** for new optional features.
- **Follow existing style:** OsmAnd has a long history, so consistency with existing code is crucial.
- **Resource handling:** Be aware that many resources are dynamically collected; check `OsmAnd/build-common.gradle` for details.
- **Android API compatibility** The app must work on every supported Android version starting from minSdk. Do not call newer platform APIs unless they are guarded by an SDK-version check or accessed through a compatible AndroidX/helper API.

## 8. Common Tasks for Agents
- **Adding a new Setting:** Register it in `OsmandSettings` and add it to the relevant settings fragment.
- **Creating a new Fragment:** Extend `BaseOsmAndFragment` and implement required UI logic using Material Design principles.
- **Modifying Map UI:** Look into `net.osmand.plus.views.OsmandMapTileView` and its layers.
- **Extending Search:** Check `net.osmand.plus.search` and `net.osmand.search.core`.
- **Updating Plugins:** Most plugin-specific code is in `net.osmand.plus.plugins`.

## 9. Restrictions
- **Building Gradle project:** You may run Gradle build tasks to verify that a change compiles (see section 6). Prefer the narrowest task that proves the point (a module `assembleDebug` or a targeted `compile*` task over a full build), and when a build is not needed use fast checks instead - `git diff --check`, XML/resource syntax validation, or an isolated test with an already-available runtime.
- **New files for git** When creating source, resource, or documentation files intended for the change, add them to VCS. Do not add temporary, generated, local, or diagnostic files. Never change .gitignore file unless explicitly requested. Do not commit unless explicitly requested.

## 10. Language Preference
- **Java / Kotlin / Compose usage**
  - Prefer Kotlin for new Android code: In Kotlin-enabled Android modules such as :OsmAnd, :OsmAnd-shared, and plugin modules, generate new classes, functions, UI components, and Compose-related code in Kotlin by default.
  - Use Java in Java-only modules: In :OsmAnd-java, :OsmAnd-api, and other Java-only/core modules, write new code in Java unless the module is explicitly being migrated to Kotlin.
  - Preserve existing file language: When modifying existing .java files, keep the change in Java unless the PR explicitly migrates that file/class to Kotlin.
  - Follow local architecture: Prefer Kotlin/Compose for future Android UI migration work, but do not introduce Kotlin into Java-only modules just to satisfy the default language preference.

## 11. AI Disclosure in Pull Requests
Every pull request produced with the help of an AI agent MUST end with an **AI disclaimer** section. Do not wait to be asked for it - write it into the PR body when the PR is created.

The disclaimer must contain:
- **Tool and model** that produced the change (e.g. `Claude Code (Opus 5)`).
- **Prompt summary** - a short, faithful summary of the prompts the user actually gave, in order. Summarise the intent and do not invent requirements that were never asked for. Never mention which language the prompt was written in.
- **What the agent decided on its own** - anything not covered by the prompts (design choices, extra files, workarounds), so reviewers can tell human intent from model inference.

The same applies to AI-generated issue comments: mark them `(gen by AI)`.

Rules for the whole PR, not just the disclaimer:
- **English only.** Source code, code comments, commit messages, PR titles and bodies, and issue comments are always written in English, whatever language the conversation with the user happened in. Never note the language of the conversation.
- **No tool advertising.** Do not append "Generated with Claude Code" banners, agent session links, or similar footers to PR bodies or issue comments. The AI disclaimer section above is the only provenance note needed.

Template:

```markdown
## AI disclaimer

Produced with <tool / model>.

Prompts used (summarised):
1. ...
2. ...

Decided by the agent, not requested explicitly: ...
```

*Note: This file is a living document and should be updated as the project evolves.*

## 12. Junction companion project instructions

These are the user's current requirements for this local project. For current
status, evidence, unfinished checks and next steps, read `tasks/START_HERE.md`,
`tasks/todo.md` and `tasks/verification.md`. Keep observed results separate from
assumptions and unexecuted checks; preserve the historical record in those files.

- **Product:** OsmAnd on Android calculates motorcycle routes; a separate Android
  bridge delivers them to a standalone Garmin Forerunner 970 app. Wrist and mounted
  views share data. Keep the bridge separate. Avoid a second map database, changes
  to native routing decisions or a second navigation state machine.
- **Watch display:** Show a stable diagram, not a moving map or rider marker. Use
  the full round screen, prominent roads, all available relevant motor-road arms
  in gray and the selected route in yellow. Preserve junction shape, nearby
  decisions and bridge/tunnel drawing levels. Do not silently omit alternatives,
  invent branches or treat a yellow-only fallback as a full-context success.
- **Road relevance:** Footways, cycleways and other non-motor roads may be omitted
  using road type and access hierarchy, not dashed styling. Retain motor-access
  overrides, ordinary tracks/service roads and the calculated route. This is a
  display filter, not a legal-access engine. Traffic-light/stop-sign symbols were
  explicitly deferred; do not implement them without a new request.
- **Progress and cache:** OsmAnd alone chooses when a junction advances. Update
  distance about once per second. Compensate only known route-matched progress age,
  capped at one second; never extrapolate indefinitely or compensate twice. The
  Android cache holds current and next geometry, invalidates on route/lifecycle
  changes and never advances independently. Keep freshness checks strict.
- **Roundabouts:** The user observed the watch stuck at zero inside Piazza dei Re
  di Roma and unable to see the exit. Preserve the actual native entry/end offsets,
  selected exit and mapped road context. The user prefers one full roundabout
  diagram and distance to the exit while inside. Use native end offsets, keep
  ordinary junction scale, and retain the saved real route for regression. Do not
  present simulator callbacks as visual or physical-device proof; see task docs.
- **Haptics:** A short pulse is requested when a new junction is displayed, not for
  each distance update, loading frame or reconnection to the same junction. The
  actual vibration strength and feel require a physical Forerunner check.
- **Arrival and startup:** Use native finished-route state for the distinct arrival
  screen and actual routed destination for its checkered marker; cancellation and
  zero distance are not arrival. Automatic bridge startup is opt-in and must be
  authenticated/foreground-safe. Request watch opening only after SDK/device
  readiness without reconnect prompt loops; document first-permission limitations.
- **Testing:** Prefer short, fixed, meaningful scenarios using native OsmAnd
  motorcycle route calculation and REALISTIC simulation in Waydroid plus the live
  Garmin simulator/SDK. Do not replace this with a custom motion engine, synthetic
  roads or scripted fixture injection without authorization. The five short dense
  routes run once by default; a focused smoke takes a few minutes and endurance is
  explicit. The user deferred precisely scripted stops/speed spikes; native random
  stops/noise are opportunistic, not deterministic edge-case coverage.
- **Investigations:** The physical watch returning to its watch face remains
  unexplained unless new evidence establishes a cause. The former 32-path
  yellow-only limit affected two saved cases and the Piazza; a 40-path budget
  covers those tested cases, but more complex scenes can still fall back. Preserve
  the Piazza roundabout reproduction and original route inputs. Simulated stability is not
  evidence of physical Bluetooth/GPS, watch firmware, API 34+ foreground policy,
  OEM battery behavior or riding readability.
- **Waydroid and devices:** The user authorized isolated Waydroid development-app
  installs and testing without the phone. Every ADB command must use an explicit,
  verified Waydroid target; never reuse the physical-phone target from private
  configuration or perform device-wide resets. Preserve the personal F-Droid app,
  phone data and route. Physical watch/phone testing or transfer requires the
  corresponding device and user coordination; do not assume it occurred.
- **Visible desk demo:** Show Waydroid full UI and the actual Garmin simulator;
  distinguish live SDK delivery, recorded replay, approximate previews, drawing
  callbacks and actual visual review. Restore Waydroid with `show-full-ui` before
  ADB after a desktop restart, verify the exact task-owned forward and live SDK
  CONNECTED state before sending. The SDK may require one manual Connection → Start;
  ask only if it is disconnected. Preserve simulator failures and do not silently
  relaunch in a loop or call an incomplete/interrupted run a pass.
- **Privacy and scope:** Personal coordinates, captures, device IDs, logs, keys,
  SDKs, generated images, binary artifacts and local runtime configuration stay
  outside Git (normally under ignored `build/garmin-review/`). Default route capture
  is read-only; replace a route or update-install only for an authorized task and
  only in the separate development identity. Debug controls must remain debug-only
  and protected. Bounded read-only queries of the existing OBF are in scope.
- **Evidence and review:** Record actual route, app/map hashes, timing, failure
  boundaries, tests and open hardware gates in the task docs. Provide coordinate-
  linked previews when useful; a drawing callback alone does not prove pixel
  correctness. Preserve the user's accepted gray/yellow style and existing review
  numbering. Do not ask repeatedly for screenshots.
- **Workarounds:** Document observed cause, evidence, implementation, constraints,
  alternatives and remaining verification. Explain simulated SDK throttling and
  compact wire encoding honestly; never present simulator timing as physical BLE
  throughput. Preserve `JUNCTION.md` and `workspace.lock.json` portable setup; never
  automatically overwrite or reset sibling checkouts.
- **Communication:** Give concise progress updates normally within 60 seconds;
  identify failures promptly and describe the next useful check. Minimize manual
  steps and retain evidence. Keep docs current after important checkpoints.
- **Git and versions:** The user authorized cohesive validated local commits and
  version tags as work progresses. Start pre-release versioning in the `v0.x.y`
  range; 1.0.0 is not reached. Keep private/generated artifacts out of Git, do
  not alter `.gitignore`, and do not push, modify remotes or create public repos
  without explicit authorization. Scope commits carefully and retain other work.
