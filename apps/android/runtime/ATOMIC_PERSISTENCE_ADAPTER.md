# APK #2: original Harness persistence qualification

## Scope and accepted prerequisite

The [physical review](../evidence/atomic-poc-physical-review.json) accepts APK #1's fixed native same-directory publication on a user-tested Redmi Note 8 Pro, Android 11/API 30 ARM64, after two complete matching-artifact reports. This permits a narrow adapter implementation; it does not qualify the new Node-API wrapper, original Harness session persistence, API 29, newer Android versions or full Gate 2.

APK #2 is version code 9, 0.1.8-atomic-persistence, using the existing ai.deepseek.harness.android.runtimepoc package. It updates the larger Node/Harness diagnostic app and preserves its data. The small atomicpoc package remains separate. Neither app is the final original-Web-UI product.

## Implementation and retained guarantees

The [native entry](../../../native/system/packages/entry/README.md) owns publishPreparedFileExclusive and its limits. Non-Android consumers retain the original fs.link operation. Android ARM64 loads only the installer-owned libharness_atomic.so; asynchronous Node-API v8 work validates the private parent and fixed basename requirements and invokes SYS_renameat2 with RENAME_NOREPLACE. There is no ordinary-rename, check-then-rename, permission escalation or compile fallback. Unsupported kernel/filesystem/policy behavior rejects. Node's ENOTSUP name for errno 95 is the EOPNOTSUPP alias.

The original JSONL materializePosix and generation publisher call that entry. Their original file fsync, directory fsync, existing-generation verification and failure handling remain in place. Android success consumes staging; cleanup already uses force/ENOENT-tolerant removal. A visible published file is retained if a subsequent directory sync fails, and the failure remains a rejection. Historical committed generations are not moved, overwritten or deleted. Session format, original SDK, named profile, Cordis plugin tree, model adapters and agent loop are unchanged.

The generation file-operation test interface names the operation publishExclusive instead of promising a retained hardlink. Real host consumer tests cover consumed-stage cleanup and post-publication sync failure without deleting either the historical source or current published generation. These tests are not Android syscall evidence. The new C binding follows the existing flock binding's async-work/environment-cleanup ownership pattern without modifying that binding. A real Linux Node-API qualification runs the new C wrapper, including 32 independent publishers across four rounds; separate metadata/loader fixtures are explicitly simulated and cannot pass a device gate.

Cross-directory fs-local and attachment staging are not routed through this same-directory API. The retained-source attachment alias is not equivalent to a move. Those identified callers remain separate requirements; no unrelated link operation is replaced. The helper is not a sandbox against a malicious same-UID plugin and does not expose a command provider, root or Termux integration.

## Original profile proof and result distinctions

The third action in Harness runtime proof starts the same original sdk-minimal profile with unqualified execution providers disabled. The preflight now calls the same publication entry as JSONL, requires exact inode/content identity, EEXIST without replacement and actual file/directory synchronization, then creates real working-directory session state. Shutdown must be explicitly acknowledged before runtime restart. A rejected resume of a nonexistent session must leave the existing JSONL hashes unchanged. The original session is then resumed and its nondefault directory verified. A successful repeat invocation must additionally recover the previous checkpoint's session.

The result includes the installed APK/native-binding SHA-256, actual process identity, persisted JSONL hashes, storage strategy and SDK diagnostics. The [result validator](../scripts/validate_profile_result.py) checks artifact matching, original profile/runtime identity, two shutdown acknowledgements, local publication checks and genuine runtime-restart recovery. Its optional previous-invocation requirement is separate. A new Copy complete result button copies selectable diagnostic output; actual Android rendering, copy interaction and cancellation still require phone testing.

| Observation | Status at delivery |
|---|---|
| APK #1 fixed native mechanism on the reported Android 11 phone | VERIFIED through two user-reported results |
| New C wrapper and Node-API callback on Linux | VERIFIED on host; not Android ABI proof |
| Original profile, isolated image and repeated session recovery on Linux | VERIFIED on host; not Android persistence proof |
| APK #2 build, signature, native dependencies and alignment | See [inspected artifact](../evidence/runtime-atomic-persistence-build.json) |
| APK #2 native wrapper and original JSONL on Android | BLOCKED pending phone |
| Runtime restart recovery on Android | BLOCKED pending phone |
| Previous-invocation recovery on Android | BLOCKED pending phone |
| App restart / process termination during writes | NOT YET VERIFIED; separate scenarios |
| Physical power loss, API 29 and recent Android devices | NOT YET VERIFIED |
| Trusted approved command / model request / Gate 2 | BLOCKED; no substitute result |

The proof always leaves appRestartVerified, approvedCommandExecuted, modelRequestExecuted and gate2Passed false. Repeated invocation or a new service PID alone does not establish a full application restart. A force-stop performed by the tester after acknowledged shutdown can support a separately attributed manual restart record; it does not test process death during a write or power loss. No session file is manually edited to make recovery succeed.

## Rebuild tutorial

Use the [Android toolchain environment](../../../ANDROID_BUILD_GUIDE.md). Original workspace artifacts must exist before tracing the profile. The profile packer requires a new output directory; preserve the previous ignored output outside the checkout before regenerating it.

```sh
pnpm run build
bash apps/android/runtime/build-atomic-addon.sh
python3 apps/android/scripts/package_node.py --build "$ANDROID_NODE_BUILD_DIR" --ndk "$ANDROID_NDK_HOME"
python3 apps/android/scripts/package_profile.py apps/android/runtime/out/profile-v7
./apps/android/gradlew -p apps/android :app:assembleDebug :app:assembleDebugAndroidTest :app:lintDebug --console=plain -Pkotlin.compiler.execution.strategy=in-process > /tmp/android-apk2-gradle-qualified.log 2>&1
python3 apps/android/scripts/inspect_runtime_apk.py --build-log /tmp/android-apk2-gradle-qualified.log
```

Capture the actual successful Gradle output in the build-log path passed to the inspector. The atomic build metadata pins C source, native binary and Node-library hashes. Packaging rejects a stale source/binary record or missing Node dependency; normal APK preparation does not exclude asset checks. The interpreted image contains the new original entry JavaScript, not a native executable extracted into writable app files. Two Linux bindings enter only the isolated host qualification tree. Installed ARM64 libraries remain in Android's immutable native-library directory.

## Physical-device tutorial

Install the delivered app-debug APK over the existing larger Harness runtime proof app; do not uninstall it or clear its data. Do not run this test in the small Harness atomic storage proof app. Open Harness runtime proof, select Run original Harness profile + session recovery (third action), confirm Run once and keep the app visible. Tap Copy complete result and retain the full JSON/error. Run the same third action a second time without clearing data and retain its complete output too. The second successful report must have previousRunSessionRecovered true. Missing data, native failures or rejected shutdowns remain failures.

With an authorized selected ADB device, the existing runner supports the same class:

```sh
python3 apps/android/scripts/test_device.py --adb adb --serial SERIAL --proof profile --output /tmp/android-apk2-phone-run1
python3 apps/android/scripts/validate_profile_result.py /tmp/android-apk2-phone-run1/runtime-result.json --build-record apps/android/evidence/runtime-atomic-persistence-build.json
python3 apps/android/scripts/test_device.py --adb adb --serial SERIAL --proof profile --output /tmp/android-apk2-phone-run2
python3 apps/android/scripts/validate_profile_result.py /tmp/android-apk2-phone-run2/runtime-result.json --build-record apps/android/evidence/runtime-atomic-persistence-build.json --require-previous-invocation
```

Manual results can be saved as JSON and passed to the same validator. A validator fixture is not device evidence; review actual device identity, artifacts and tester actions. After those two reports pass review, test a separately documented app force-stop/reopen, migration and active-process interruption before broader lifecycle claims. Approved harmless-command integration follows authentic persistence acceptance; optional root/Termux, broad PTY and original Web UI remain later milestones.
