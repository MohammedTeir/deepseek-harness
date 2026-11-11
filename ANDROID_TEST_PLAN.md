# Android audit and future acceptance tests

## Summary

Host graph/static/build checks establish audit reproducibility only. No mock, browser preview, Linux test or successful cross-compile passes an Android runtime gate.

## Phase 1 checks

Check every dependency edge resolves, graph counts match lockfile sections, importer manifests exist, aliases/optional/peer contexts are retained, and repeated collection is deterministic for the same installed tree. Match all noninstalled registry manifests to lockfile distribution integrity. Review actual native hooks, build descriptors, ELF linkage and source platform gates. Build the original frontend and inspect its emitted document/asset paths. Run repository documentation checks and disclose failures rather than suppressing them.

## Deferred device matrix

After review, use Android 10/API 29 ARM64 and a recent ARM64 release, including a 16 KB page-size environment when available. Record device model, OS/API/security patch, WebView version, source revision, runtime/addon digests, target SDK and test commands. Physical-device and emulator results must be separate.

Runtime cases: load/stop/restart, ESM/module paths, workers, TLS/DNS, SQLite, file locks under competing processes, app-private writes, session recovery and actual Harness profile readiness. Process cases: command discovery, stdout/stderr/exit, cwd/environment, streamed input/output, timeout, cancellation, child cleanup and PTY behavior. Transport cases: authorized/unauthorized browser/API/WebSocket, origin spoofing, token replay, missing assets, deep links, reconnection and real agent/tool streaming. Security cases: denied/expired/mutated approval, plugin spawn bypass, credential disclosure, SAF grant revocation and optional root separation.

Only after these pass should the original chat UI's real approved command result, session restart recovery and authorized provider request be claimed. Missing test credentials leave model integration unverified, not mocked into success.
