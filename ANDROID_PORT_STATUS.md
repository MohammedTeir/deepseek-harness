# Android Phase 0 and Phase 1 status

## Summary

Phase 0 is VERIFIED. The [Gate 1 review](ANDROID_GATE1_REVIEW.md) accepts the reviewed audit and a bounded Phase 2 runtime experiment. Phase 2 is IN PROGRESS; Gate 2 is not passed. The branch now includes a native diagnostic host, JNI shim and pinned Android runtime build tools. The original frontend and Harness engine are preserved. No Android device execution, authentic profile readiness, session recovery or authorized tool result has been verified.

## Upstream sync: Phase 1 evidence refreshed

The fork's upstream release `0.2.2-rc.2` is merged into this audit branch with both histories retained. The [sync impact record](audit/android/upstream-sync-impact.json) identifies the old and new revisions. The master specification is unchanged. Graphs, installed payloads, registry manifests and source indexes below now describe synced master, not the earlier release candidate. The former evidence remains in Git history.

The refresh reviews structured approval/cancellation errors, PTY load failures, credential masking, the new ripgrep/terminal/Office packages and the PTC evaluator's additional Node API. Native lock platform selection and terminal-bash defaults remain blockers. The later Gate 1 decision authorizes the bounded Phase 2 experiment; synchronization alone was not runtime acceptance.

## Baseline and verification

[Exact baseline and environment](audit/android/baseline.json) records the current fork, included upstream baseline and observed upstream HEAD separately. The checkout started clean, `origin` points to the author's fork, `upstream` points to the original project, and `feature/android-port` was created from fork master before the author-synchronized source was merged. The author-synchronized upstream source is included; no separate upstream update was selected.

| Check | Executed result | Limit |
|---|---|---|
| `git status --short`, remotes, branches, log and `ls-remote` | Correct fork/remotes; clean start; baseline recorded | Remote observations are point-in-time |
| `python3 audit/android/collect.py` | 398 importers, 1,755 package identities, 1,763 snapshots, 8,836 edges; zero unresolved endpoints | Complete committed lock graph, not future dynamic downloads |
| Installed package scan | 1,426 identities; manifests/hooks/source descriptors/binary headers inspected | Linux installation; no Android execution |
| Repeated graph/index collection | Four recorded graph/index SHA-256 values reproduced exactly | Same installed tree and source baseline |
| Binary payload/ELF dependency graph | 161 inspected payload nodes and 211 DT_NEEDED edges | Loader resolution on Android remains unverified |
| Registry manifest fetch and integrity comparison | 329/329 retrieved, zero fetch errors, all distribution integrity values match lock | Archive bytes not downloaded or executed |
| `python3 audit/android/index_sources.py` | 37 Node builtin specifiers, 383 platform-sensitive sites, 17 native source/matrix paths | Static references include different product/build roles |
| `pnpm install --frozen-lockfile` | PASS, 21.6 seconds; lockfile supply-chain policies passed for 1,755 entries | Host dependency installation only |
| `DSH_GATE_CONCURRENCY=2 pnpm run build` | PASS: 10 gates, 287.78 seconds; 369 client artifacts recorded | Host native addon, compilers, bundles, Web build and aggregate checks; no Android inference |
| `pnpm run lint` | PASS, with one existing unused-disable warning in client-ui-cot-translation | Host repository lint only |
| Current `pnpm run doc-sync` | PASS: 43/43 checks in 494.61 seconds | Exact-baseline conflict repaired through strict evidence validation; original evidence retained |
| Current `pnpm run test:docs` | PASS: 21/21 gates in 82.80 seconds | Includes repaired repository-reference validation |
| Reference-checker regression file | PASS: 46 tests | Valid evidence plus wrong-path, abbreviated, unknown, malformed, duplicate, nested and forbidden-URL rejection |
| `pnpm run verify-repository-references` | PASS | Original baseline JSON unchanged |

## Blockers and recommendation

Node >=24.9 has no demonstrated supported Android runtime in this audit. Existing native lock selection rejects Android. node-pty's Linux ARM64 binary has GNU/Linux linkage, and the default persistent terminal assumes `/bin/bash` plus bash-specific control behavior. Android W^X, linker, app identity, PTY permissions and lifecycle must be qualified on devices. MCP stdio and arbitrary Node plugins can bypass a replacement central subprocess service; secure privilege mediation requires more than UI approval.

Recommend original Web UI plus the authentic profile/Cordis engine under a Kotlin supervisor, while comparing a source-built shared-library runtime with a compliant APK-packaged executable. JNI is a candidate, not a mandatory or verified decision. Preserve existing model/provider abstractions and service seams. Defer optional Termux/root, desktop-native plugins and broad package installation.

## Review boundary and next milestone

Review the [audit](ANDROID_PORT_AUDIT.md), [compatibility matrix](ANDROID_COMPATIBILITY_MATRIX.md), [architecture](ANDROID_ARCHITECTURE.md), [security risks](ANDROID_SECURITY_MODEL.md) and [roadmap](ANDROID_IMPLEMENTATION_PLAN.md). Noninstalled binary payloads, runtime-downloaded artifacts and Android execution remain unverified; these must not be represented as compatible.

After the accepted Gate 1 review, the current milestone is an Android ARM64/API 29+ runtime qualification using real Node APIs and an authentic Harness profile: persistent session create/reopen, approved harmless command with actual stdout/stderr/exit, and denied-operation evidence. Phase 2 implementation is bounded by the review decision; no later gate is bypassed. PR publication remains subject to the author's authorization.

## Phase 2 experiment evidence

- Kotlin host, JNI shim and instrumentation-test source compile passed (31 tasks, 1m32s) with runtime asset preparation excluded for code-only checks. Initial offline resolution lacked AndroidX test dependencies; the online retry fetched them and passed with in-process Kotlin compilation. This is not an Android execution test or APK result.
- The unchanged upstream flock source cross-compiled with NDK r28c for ARM64/API 29. Its runtime loading/contention tests remain unrun on Android.
- Four ELF parser rejection/acceptance tests passed; they use synthetic inspection text and are not Android compatibility evidence.
- The API probe ran on Linux x64 Node 24.22.1: SQLite, workers, ESM, crypto and result-file output passed. Native Android locking was not run. DNS returned EAI_AGAIN, so DNS/TLS are unverified. Harness was explicitly not started.
- Pinned Node ARM64 source compilation is running. The host-generator optimization was changed from the previously failing `-O0` to `-O1`; no completion is claimed yet.
- No physical device is attached and `/dev/kvm` is absent. Official emulator 37.2.13 and an API 30 x86_64 Google APIs image installed successfully. A software-acceleration-disabled boot is running, but ADB remains offline; no usable device result is claimed. Any ARM translation results must be labeled separately from native ARM64 hardware. Device/profile/session/tool acceptance remains BLOCKED. Normal APK generation requires inspected runtime libraries and notices and cannot silently package a replacement backend.

The production native lock selector still rejects Android. The runtime probe exercises the original C binding directly as a qualification step; it is not session integration. Genuine Harness profile boot, durable sessions and a native-authorized command must still be integrated and tested after runtime qualification. Optional Termux/root and original-UI integration are outside this bounded prototype.

Current validation: reference policy 46 tests passed, quick documentation 21/21, full doc-sync 43/43, TypeScript build checks 2/2, and root lint passed with one existing unused-disable warning. The first lint run found a new arrow-parentheses formatting error; it was corrected before the passing rerun. Original baseline and sync evidence JSON contents are unchanged.
