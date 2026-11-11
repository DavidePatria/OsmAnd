# Forerunner 265 builds

The standard Forerunner 265 uses a round 416×416 screen. These separate
device-specific builds share the existing Junction watch-app and activity-field
identities, scene renderer and phone bridge protocol. They target the `fr265`
device profile and require Connect IQ API level 5.2 or later. They are not
builds for the smaller Forerunner 265S.

Install the Garmin SDK's `fr265` device profile and simulator fonts, and use the
same local development signing key as the existing Junction builds. From the
repository root:

```sh
python3 integrations/garmin/dev.py build --target fr265 --out build/garmin-review/fr265/watch
python3 integrations/garmin/dev.py build --target fr265-datafield --out build/garmin-review/fr265/datafield
python3 integrations/garmin/dev.py check --suite fr265 --out build/garmin-review/fr265/watch-tests
python3 integrations/garmin/dev.py check --suite fr265-datafield --out build/garmin-review/fr265/field-tests
```

Each build directory contains a `Junction.prg`; use separate destination names
when transferring both to a watch. The phone bridge targets either the standalone
app or the data field according to its setting. A connected watch must be selected
in the bridge if more than one is paired.

On 2026-11-11 both 265 builds compiled and each simulator unit suite passed
34 tests. The standalone app also issued a 416×416 drawing callback in a
separate startup check. The data-field startup check timed out while the Linux
simulator displayed a black GTK/FreeType error dialog; that is not a field
startup pass. Both builds were subsequently transferred to a Forerunner 265
over MTP and read back with matching hashes. Processing after disconnection
and opening the apps have not been verified. The checks do not establish visual
readability, live Garmin Connect delivery, vibration, real activity behavior, or
physical-watch stability.
Test those on the actual 265 before relying on it during a ride. Earlier data
field unit tests run under a test heap and are not a physical memory measurement.
