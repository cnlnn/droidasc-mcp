# ASC acceptance APK

An original, Apache-2.0 test app under this repository's license. It has no external
application dependencies, network permissions, credentials, or business data. The one
screen displays a fixed marker. CI analyzes the APK statically; no emulator is needed.

## Build

Use JDK 17, Gradle 8.13, Android SDK platform 35, and Build Tools 35.0.0.
The Android Gradle Plugin version is pinned to 8.9.2 in `build.gradle`.
Set `ANDROID_HOME` to your SDK installation, then run from the repository root:

```bash
sdkmanager "platforms;android-35" "build-tools;35.0.0"
gradle --no-daemon -p tests/fixtures/android :app:assembleDebug :complex:assembleRelease
ASC_TEST_EXPECT_FIXTURE=1 \
  ASC_TEST_APK="$PWD/tests/fixtures/android/app/build/outputs/apk/debug/app-debug.apk" \
  ASC_TEST_COMPLEX_APK="$PWD/tests/fixtures/android/complex/build/outputs/apk/release/complex-release-unsigned.apk" \
  ASC_TEST_COMPLEX_MAPPING="$PWD/tests/fixtures/android/complex/build/outputs/mapping/release/mapping.txt" \
  uv run pytest -q -s
```

In PowerShell, set `$env:ASC_TEST_EXPECT_FIXTURE = "1"` and `$env:ASC_TEST_APK` to
the absolute APK path before running pytest. Set the two complex fixture variables as well.
Full acceptance also requires the pinned JADX backend described in `docs/VALIDATION.md`.

The APK is generated, not committed or bundled into the Python distributions. CI uploads
only this public-source APK as `acceptance-apk` and passes the same artifact to Linux and
Windows. Debug signing keys and ZIP timestamps can differ between builds; tests verify
the analyzed artifact's SHA-256 rather than requiring byte-identical APK rebuilds.

## Expected evidence

- Manifest package: `org.example.droidascfixture`; no requested permissions.
- DEX classes: `MainActivity`, `Probe`, and the Android-generated `R` in that package,
  plus default-package `Login` and hierarchy classes for exact-name and direct-relation checks.
- Pinned debug build layout: generated `R` in `classes.dex`; app classes in `classes2.dex`.
- Decompiled `Probe`: `marker`, `visits`, and `ASC_FIXTURE_MARKER_v1`.
- String reference: the marker in `Probe.marker`.
- Type reference: `Probe` in `MainActivity.onCreate`.
- Method reference: `Probe.marker` called by `Probe.describe`.
- Field reference: `Probe.visits` accessed by `Probe.marker`.
- Default-package method/field queries: `Login` and `LLogin;` return the same nonempty hits;
  a fuzzy `Log` pattern still matches them.
- Direct hierarchy: `HierarchyBase` has `HierarchyChild`, not `HierarchyGrandchild`, as a
  direct subclass; `InterfaceBase` has `InterfaceChild` and `HierarchyDirect`, not indirect
  implementors. `Login` and `LLogin;` both find `LoginChild`.
- String/type/method/field refs match fixture-source caller sets both before and after class
  decompilation, using fresh analyses rather than an identical-query cache hit, for APK and DEX.
- Option-shaped query values preserve a disposable sentinel outside the APK root, return literal
  search results rather than CLI help, and leave the session usable after a reserved-token error.

The tests check these semantics over stdio and HTTP, including pagination, rather than
requiring a particular decompiler formatting style. `ASC_TEST_EXPECT_FIXTURE=1` makes a
missing APK an error. It is only for this fixture; arbitrary local APKs can still use
`ASC_TEST_APK` alone for the generic smoke checks.

## Complex method fixtures

The separate `complex` module pins Kotlin 2.1.0 and builds a minified release with R8.
It uses the Kotlin standard library, two suspend points, generated continuation state and two
overloads. Rules retain the test classes/methods while allowing obfuscation and disabling
optimization, so this is an obfuscation/coroutine identity test, not an R8 optimization benchmark.
Tests require renamed classes, derive exact descriptors from the generated R8 mapping and check
both overload bodies and the continuation's call back to its workflow. Only the DEX goes to the
MCP tool; mapping data remains an independent acceptance oracle. CI uploads this fixture and
mapping separately as `complex-fixture`. No application execution or network permission is needed.

`../xrefs` contains independent Smali source assembled with the pinned backend on each test OS.
Its two DEX files establish exact call offsets 1, 6 and 9 code units, overload separation,
external references, a polymorphic call, native parameters, debug information and a catch handler.
ASC output is reassembled, and a checksum-valid unknown-opcode mutation must fail without partial
success. Large multidex performance, native execution and Android UI execution are not covered by
these fixtures. Supervisor integration tests separately check resource limits and cancellation.
