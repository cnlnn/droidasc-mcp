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
gradle --no-daemon -p tests/fixtures/android :app:assembleDebug
ASC_TEST_EXPECT_FIXTURE=1 \
  ASC_TEST_APK="$PWD/tests/fixtures/android/app/build/outputs/apk/debug/app-debug.apk" \
  uv run pytest -q -s
```

In PowerShell, set `$env:ASC_TEST_EXPECT_FIXTURE = "1"` and `$env:ASC_TEST_APK` to
the absolute APK path before running pytest.

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

This small two-DEX debug app checks discovery beyond the first DEX. It does not cover
large multidex workloads, obfuscation, Kotlin, native libraries, malformed APKs, Android
UI execution. Process cleanup is covered by separate supervisor integration tests.
