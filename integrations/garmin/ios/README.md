# Junction on iOS

Work in progress. This directory adapts the native OsmAnd iOS application and
builds a separate Garmin companion. Compilation, device signing, navigation,
Bluetooth delivery and watch drawing are separate verification gates.

## Architecture

- OsmAnd iOS owns route calculation, progress, decision selection and arrival.
  The opt-in exporter reads native route offsets and point-aligned road layers.
  It caches only the current and next fixed diagram, invalidates on route and
  lifecycle changes, and never advances a junction itself. Roundabouts retain
  their native end offset; the distance target becomes the exit while inside.
- `OsmAnd-shared` compiles bounded geometry from native route facts and the
  existing OBF files. Its readers belong to a single background worker. It uses
  the accepted gray context/yellow route contract and reports capacity or map
  failures honestly. It does not create another map database or routing engine.
- `Junction Bridge` selects an authorized Garmin device through Garmin Connect,
  waits for SDK characteristic discovery, then answers the existing standalone
  watch app or activity field's requests. It has one bounded request at a time,
  carries source/fix/progress ages and rejects late replies. SDK send completion
  is not proof that the watch accepted or drew a scene.
- Source and bridge communicate over authenticated TCP bound only to
  `127.0.0.1:38765`. A random credential is stored separately in each app's
  Keychain. Connecting from OsmAnd asks the user before replacing the bridge's
  credential. This avoids requiring an App Group entitlement, but does **not**
  wake a suspended OsmAnd process. Navigation/background and locked-screen
  behavior require physical iPhone testing.

The Garmin SDK is pinned in `bridge/project.yml`. It sends supported dictionary
messages; the Android bridge's compact ByteArray encoding is not assumed to be
supported by the iOS SDK. Maximum-size dictionary delivery, data-field heap use
and real BLE throughput remain unverified.

## Hosted build from Linux

The `Build Junction iOS` workflow runs on pushes to `codex/ios-garmin`, and can
also be dispatched with `destination=device` or `destination=simulator`:

```sh
gh workflow run build-junction-ios.yml --ref codex/ios-garmin -f destination=device
gh run list --branch codex/ios-garmin
gh run view RUN_ID --log-failed
gh run download RUN_ID --dir build/garmin-review/ios-ci/download
```

Linux can edit the complete adaptation, run the shared JVM tests, trigger builds
and retrieve artifacts. Xcode and the Apple SDK run on the hosted Mac. A hosted
simulator artifact targets Apple Silicon Macs; it does not run directly on Linux.
Neither the local Android/Garmin desk bench nor a hosted iPhone Simulator proves
physical iPhone-to-Garmin Bluetooth operation.

The workflow checks out this repository as `android` and exact native sibling
revisions from `workspace.lock.json`. `ci.py bootstrap` refuses existing dirty or
mismatched checkouts. `ci.py prepare` adapts only that isolated workspace:

- separate app identity `net.osmand.junction.ios` and URL scheme;
- removal of OsmAnd's signing identities and privileged upstream entitlements;
- explicit source/project registration and localized settings entry;
- repair of the pinned OsmAnd-build CMake condition's stray `OR` token;
- HTTPS resource downloads and fail-fast native preparation.

Upstream prebuilt Qt/ANGLE/resource URLs are mutable. Source revisions are pinned;
this is not yet a fully reproducible build from source. Native compiler logs and
actual output hashes are retained with each build. Build artifacts expire after
seven days. No upstream repository or sibling checkout is overwritten.

## Signing and installation

The compilation workflow produces **unsigned** device IPAs for both applications,
or simulator app archives. Unsigned IPAs are not installable signed iPhone apps.
No Apple certificate/profile is currently configured, and signing has not been
executed. The user currently has no Apple Developer Program membership.

Apple permits personal device development with a free Apple Account/Personal
Team, but its device provisioning profiles expire after seven days. The account
must first obtain the device-specific signing assets; GitHub login does not
create them. See [Apple's account overview](https://developer.apple.com/help/account/basics/about-your-developer-account).

For existing development/ad hoc signing assets, `Sign Junction iPhone apps` is a
manual workflow. Configure repository Actions secrets, never files in Git:

| Secret | Value |
| --- | --- |
| `IOS_CERTIFICATE_BASE64` | Base64 of an exported Apple signing certificate **and private key** (`.p12`) |
| `IOS_CERTIFICATE_PASSWORD` | Password of that `.p12` |
| `IOS_OSMAND_PROFILE_BASE64` | Base64 of a valid device profile for `net.osmand.junction.ios` |
| `IOS_BRIDGE_PROFILE_BASE64` | Base64 of a valid device profile for `net.osmand.junction.bridge.ios` |

Both profiles must authorize the same team and imported identity and include the
intended device. The workflow downloads a successful device build, verifies its
artifact hashes, imports credentials into a temporary keychain, signs embedded
frameworks and both apps, verifies signatures, and removes the keychain. It
rejects expired/mismatched profiles and unsupported embedded extensions. It does
not renew profiles, log into Apple, upload to TestFlight or install on a phone.
Signed artifacts contain device provisioning information and expire after three
days in Actions. This optional signing path is prepared but unexecuted.

This follows GitHub's [macOS runner signing guidance](https://docs.github.com/en/actions/how-tos/deploy/deploy-to-third-party-platforms/sign-xcode-applications).
Do not paste Apple passwords, certificate contents or profiles into chat.

After actual signing and installation, install Garmin Connect, pair the watch,
enable Junction sharing in OsmAnd Settings, connect the source to Junction
Bridge, select the watch and standalone app/activity field, and explicitly start
the bridge. Launch resumption is separately opt-in. Opening the standalone watch
app is an explicit foreground action after SDK readiness; there are no reconnect
prompt loops. The first Bluetooth/device-selection permissions require user
interaction.

## Verification

The shared JVM suite reuses the existing recorded native fork/double-turn
fixtures and checks filtering/layer facts. The Swift protocol executable tests
freshness, invalid scalar values, expiry, duplicates, epochs and stale callbacks.
These are unit regressions, not live native route or Garmin transport tests.

Current measured outcomes and failed attempts are recorded in
`tasks/verification.md`; remaining work is in `tasks/todo.md`. Full native app
compilation, signing, native realistic simulation, maximum-context transport,
watch drawing, haptics, arrival/cancellation and background behavior must be
reported individually. No physical iPhone/watch proof has been obtained here.
