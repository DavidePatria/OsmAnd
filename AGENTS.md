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

These instructions capture the user's current requirements for this local project.

- **Current priority:** verify actual junction layouts with the Garmin simulator in the loop, before further live transport work. Read `tasks/START_HERE.md`, `tasks/todo.md`, and `tasks/verification.md`; keep observed results separate from assumptions and unexecuted checks.
- **Current continuation:** the user authorized completing useful work WITHOUT the phone attached. Use saved captures/maps, host tests, Android builds and the Garmin simulator. Do not access ADB, install on the phone or replace its route during this phase. Implement geometry/export/delivery pieces in dependency order, retaining explicit hardware-only verification gates. Commit `0c6b7f8` is the last user-authorized commit; later edits need a new commit request.
- **Waydroid continuation (2026-11-06):** the user installed Waydroid and approved its one-time Android debugging trust dialog. Waydroid access, isolated test-app installs and desk testing are now authorized. Use an explicit verified Waydroid ADB target for EVERY command; never reuse the physical-phone target from the default private configuration or issue device-wide resets. Keep runtime addresses in ignored local configuration. Existing physical phone and personal app data remain untouched.
- **Unattended validation:** the user authorized completing the Waydroid map/simulation/live-export work alone, leaving coordinate-linked watch previews for later judgment, and minimizing work deferred to physical testing. Reuse the saved meaningful route for reviews; label extra public scenarios separately. Automate software lifecycle/failure checks and measure real timings. Do not infer physical Bluetooth/GPS, API 34+ foreground policy, OEM sleep/battery or riding readability from Waydroid API 33 or recorded simulator replay. Ordinary test-app runtime permissions may be configured; no Waydroid root/system permission changes are needed.
- **Target:** Android phone navigation, motorcycle routes calculated by OsmAnd, standalone Garmin Forerunner 970 app. Wrist and mounted layouts share the same data. Preserve junction shape, selected branches and nearby decision points; never present synthetic branches as extracted road data.
- **Display:** show a stable diagram of the next junction with ALL available mapped road arms, selected route yellow, plus distance updated once per second. Do not build a moving map or moving rider marker. OsmAnd owns junction advancement. Optional anticipation compensates only known delay of route-matched progress, capped at one second; never extrapolate indefinitely or compensate twice.
- **Road relevance:** the user explicitly permits omitting footpaths/cycleways and other non-motor roads that otherwise appear misleadingly as solid roads. Filter by road type and access hierarchy, not dashed map styling; preserve motor-access overrides, ordinary tracks/service roads and the calculated yellow route. This is a display filter, not a new routing/legal-access engine. Traffic-light landmarks may be useful; stop signs require approach-specific care. The user explicitly deferred both symbols: do not implement them yet.
- **Accepted visual style (2026-11-06):** the user approved review examples 1–5 and rejected the yellow-only limited views in 6–9. Preserve all surrounding motor roads in gray and the selected route in yellow. Bridge/tunnel handling must retain alternatives and distinguish drawing levels; do not solve grade separation by dropping roads. Preserve example numbering and approved geometry while iterating.
- **Next user demonstration:** the user wants a full desk demonstration with OsmAnd in Waydroid and the actual Garmin simulator producing the diagrams. They will supply both a more challenging start and destination; keep the existing route as comparison evidence. Label actual live SDK delivery separately from recorded-packet replay; do not present synchronized replay or browser previews as live transport.
- **Live demo correction:** the user supplied a new Rome start/destination and explicitly prefers a WORKING connection between both simulators. Use those coordinates from ignored local captures; do not put them in tracked documentation. Explain when the watch is displaying old comparison data or running tests. Establish the SDK connection before launching a sending watch app. Do not relax freshness limits or suppress relevant road arms merely to make a demo appear successful.
- **Workaround accountability:** the user requires shortcuts/workarounds to be documented so a later agent can reconsider them. Record the observed cause, evidence, implementation choice, constraints, alternatives and remaining verification. SDK 2.4.0 tethered throttling and compact wire encoding belong in the contract/verification notes; do not present simulator timing as measured physical BLE throughput.
- **Meaningful routes:** the user may choose endpoints/profile on the phone. Default capture is read-only. Never replace that route with the public baseline, reinstall/reset the app, or change endpoints without a task reason and authorization. Personal captures, coordinates and generated review images stay out of Git.
- **Geometry review:** provide watch-layout previews with coordinate links to OpenStreetMap for the user's own comparison; map screenshots are unnecessary. Distinguish previews (approximate fonts), real simulator drawing callbacks and actual simulator screenshots. Filtered routing alternatives do not prove complete road coverage. A bounded read-only query of the existing OBF with OsmAnd's reader is in scope; no second map database or native routing changes.
- **Scope:** contained read-only integration, independent companion project, no changes to native routing decisions or a second map database. Keep diagnostics in explicitly debug-only sources and protect exported test controls. Preserve the user's F-Droid app and data; install only the separate development identities.
- **Desk iteration:** automate incremental builds, update installation, launch, scenario setup and evidence collection. Connected devices and human supervision are available. Avoid repeated manual installation/menu/route setup; report measured unavoidable actions honestly. Simulator success does not establish physical Garmin/Bluetooth behavior.
- **Communication:** keep the user informed during work, normally within 60 seconds. Include concrete commands, observed states, failure boundaries and the next discriminating check so the user can spot low-level mistakes and help. Report failures promptly; do not quietly repeat attempts or turn uncertain results into passes.
- **Visual review:** the user supplies screenshots when useful. Do not repeatedly request them. A drawing callback proves code execution, not pixel correctness. Respect the available UI tooling and approval restrictions.
- **Handoff readiness:** after each important checkpoint, update concise status/evidence/next-step documentation. Reference existing plans instead of duplicating them. Development remains the priority. Keep an optional temporary handoff free of private device identifiers, credentials and signing material.
- **Portable repository:** this Git repository contains the Android customization, `integrations/garmin/` companion/tooling and `tasks/` documentation. Recreate required sibling build inputs using `integrations/garmin/workspace.lock.json` and `bootstrap.py`; never overwrite/reset an existing checkout automatically. Private local configuration and keys stay outside Git. See `JUNCTION.md` for a fresh-machine workflow.
- **Git:** the user has explicitly requested focused local commits for the current checkpoint and a clean index. Commit cohesive validated changes with accurate documentation; do not include SDKs, binaries, caches, raw device logs or private configuration. Future commits require user authorization. GitHub account/repository creation, remote changes and pushing remain manual unless explicitly requested. Do not install GitHub CLI/connectors for this workflow.

- **Destination/startup continuation (2026-11-06):** the user requested a checkered routed-destination marker, a distinct native-arrival watch screen, and opt-in automatic bridge startup. They chose KEEPING THE BRIDGE SEPARATE. Use the existing native finished-route flag, never cancellation/zero junction distance. Keep automatic startup authenticated and foreground-safe; request watch opening once after SDK/device readiness, with no reconnect prompt loops. Document physical prompt/first-permission/background-start limits separately.
- **Desktop restart / Android visibility:** the user restarted after a desktop crash and explicitly wants to SEE the Android UI alongside Garmin. Restore Waydroid with show-full-ui before relying on ADB: the observed no-window container was FROZEN until that command resumed it. Recreate only the exact task-owned forward and verify CONNECTED before starting watch sends. Reuse saved routes/apps/maps; no reinstall/reset is needed just for a reboot. Code/build/test evidence survived the observed restart.
