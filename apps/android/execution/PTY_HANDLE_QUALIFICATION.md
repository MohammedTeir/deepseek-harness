# Original terminal handle: fixed host qualification

Status: IMPLEMENTED and VERIFIED on the Linux host only. The separate original node-pty source/addon phone suite is now VERIFIED for the submitted Android 11 ARM64 run; see [the review](../../../ANDROID_GATE3_REVIEW.md). That does not verify this new handle adapter on Android.

## Original contract and authority boundary

terminal-handle.ts implements the unchanged SubprocessTerminalHandle interface from packages/subprocess/subprocess/src/types.ts. A focused strict TypeScript check uses that actual interface and the actual node-pty type declarations. The wrapper reuses original node-pty I/O and exit events; it does not introduce another process engine.

This prototype accepts only known benign fixture roles and fixed input. It has an explicit Linux-host guard and is not copied into APK #6 assets, mounted into the Android profile or registered as an agent tool. Its executable configuration comes from reviewed host test code; it is not a native execution authorization service. No production permission boundary is claimed. The existing original-tool/native-grant proof remains unchanged.

The owner's signal is deliberately named ownerSignal. It controls fixture lifetime and is not the original spawnTerminal allocation signal. That future async allocation/rollback contract remains to be implemented with native authorization and actual Agent ownership.

## Verified behavior

- Live Readable output and native PTY input/resize; queued output ends after the original exit event.
- Actual normal exit 7 maps to exitCode=7 and signal=null.
- Actual Ctrl-C maps to exitCode=null and signal=SIGINT; a killed process is never reported as successful exit 0.
- Concurrent termination shares one TERM-to-KILL procedure, waits for the original exit observation and confirms ESRCH for the fixed child.
- Owner cancellation terminates and awaits the same fixed direct-child range.
- Pre-abort, invalid fixture options, unsupported input and invalid dimensions reject before the relevant operation.
- Closing/exited handles reject further write, resize and inspection calls.
- Foreground inspection returns undefined and activity is unknown. Foreground signalling rejects with the original unsupported-capability error because no process-group identity has been established.

The benign fixture cannot spawn descendants. This does not prove whole-session cleanup for a general shell, inherited-descriptor safety, stopped jobs, arbitrary descendants, Android cancellation or OS process death. Bounded output is qualification-only and is not a spill-capable general terminal implementation.

## Executed checks

The original source-addon host test now additionally runs terminal-handle-reference.mjs using real original node-pty, actual fixed processes, readiness events, stream consumption, output assertions and concurrent cleanup. It saves [the host-only report](../evidence/pty-handle-host-reference.json). The original node-pty phone result is stored separately; no host output is relabelled as Android evidence.

```sh
pnpm exec tsc --ignoreConfig --noEmit --strict --target ES2022 --module NodeNext --moduleResolution NodeNext --skipLibCheck --allowImportingTsExtensions --types node apps/android/runtime/node-pty-proof/terminal-handle.ts
python3 -m unittest discover -s apps/android/tests -p 'test_node_pty_original.py' -v
```

The compiler's ignoreConfig flag selects an explicit standalone strict check; it does not relax the original interface. The initial command without it was rejected by the installed TypeScript CLI before checking files, so the explicit-file invocation was corrected. Dependency declarations are skipped, not the new source. No repository TypeScript configuration was weakened.

## Next engineering milestone

Connect a bounded terminal allocation to trusted native exact-request authorization and the existing original owner-scoped terminal registry. Qualify allocation cancellation/rollback, foreground group identity, cleanup failures and owner disposal before exposing broader operations. The host factory remains disabled on Android until that integration has its own APK and physical evidence. Existing Linux process-inspection/Bash assumptions remain unadapted; no custom multiplexer, Termux or Root fallback is introduced.
