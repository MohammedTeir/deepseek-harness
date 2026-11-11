# Android Phase 0 and Phase 1 status

## Summary

Phase 0 is VERIFIED. Phase 1 audit artifacts are IMPLEMENTED and awaiting review; Gate 1 is not declared accepted. Phase 2 is NOT STARTED. This branch contains documentation and read-only audit tooling/data only. No Android app, runtime prototype, upstream workflow, frontend redesign or replacement agent is introduced. The prior local prototype is archived separately and supplies no Android acceptance evidence here.

## Upstream sync: audit refresh required

The fork now includes upstream release `0.2.2-rc.2`. The [sync impact record](audit/android/upstream-sync-impact.json) identifies both revisions: 3,479 files changed; importers increased from 394 to 398 and resolved snapshots from 1,762 to 1,763. Eight external package identities were replaced, including LibreOffice kit, Stagehand and Zod. The master project specification is unchanged.

All graph counts and test results below belong to the previous audited revision. They are historical evidence, not validation of synced master. Refresh the dependency/payload graph, native matrix and affected source findings; reinstall from the new frozen lockfile before repeating the original frontend build and documentation checks. Review changed approval/cancellation, subprocess, credential/account, profile and frontend code. Node requirements, native lock loader and terminal-bash defaults are unchanged in the compared files, so the existing core blockers remain.

Only the impact assessment has run. The synced source has not been merged into this audit branch or revalidated, and Phase 2 remains NOT STARTED. Preserve the original evidence until replacement records have been generated against the new baseline.

## Baseline and verification

[Exact baseline and environment](audit/android/baseline.json) records the current fork, original upstream ancestor and observed upstream HEAD separately. The checkout started clean, `origin` points to the author's fork, `upstream` points to the original project, and `feature/android-port` was created from the current fork master. No source update from newer upstream was merged.

| Check | Executed result | Limit |
|---|---|---|
| `git status --short`, remotes, branches, log and `ls-remote` | Correct fork/remotes; clean start; baseline recorded | Remote observations are point-in-time |
| `python3 audit/android/collect.py` | 394 importers, 1,755 package identities, 1,762 snapshots, 8,696 edges; zero unresolved endpoints | Complete committed lock graph, not future dynamic downloads |
| Installed package scan | 1,426 identities; manifests/hooks/source descriptors/binary headers inspected | Linux installation; no Android execution |
| Repeated graph/index collection | Four recorded graph/index SHA-256 values reproduced exactly | Same installed tree and source baseline |
| Native ELF graph | 153 inspected payload nodes and 211 DT_NEEDED edges | Loader resolution on Android remains unverified |
| Registry manifest fetch and integrity comparison | 329/329 retrieved, zero fetch errors, all distribution integrity values match lock | Archive bytes not downloaded or executed |
| `python3 audit/android/index_sources.py` | 36 Node builtin specifiers, 374 platform-sensitive sites, 17 native source/matrix paths | Static references include different product/build roles |
| `pnpm run build:web` | PASS, original Vite frontend built in 7.33 seconds; chunk-size warning | Existing host workspace artifacts used; no APK or device claim |
| `pnpm run doc-sync` | 42 passed, one failed in 162.32 seconds; site build/checks, links, typecheck and graphs passed | Same exact-baseline-hash policy conflict; no checker changed |
| `pnpm run test:docs` | 20 passed, one failed | Repository-reference gate rejects exact known commit hashes in baseline JSON; retained as explicitly required by the author; checker unchanged |

## Blockers and recommendation

Node >=24.9 has no demonstrated supported Android runtime in this audit. Existing native lock selection rejects Android. node-pty's Linux ARM64 binary has GNU/Linux linkage, and the default persistent terminal assumes `/bin/bash` plus bash-specific control behavior. Android W^X, linker, app identity, PTY permissions and lifecycle must be qualified on devices. MCP stdio and arbitrary Node plugins can bypass a replacement central subprocess service; secure privilege mediation requires more than UI approval.

Recommend original Web UI plus the authentic profile/Cordis engine under a Kotlin supervisor, while comparing a source-built shared-library runtime with a compliant APK-packaged executable. JNI is a candidate, not a mandatory or verified decision. Preserve existing model/provider abstractions and service seams. Defer optional Termux/root, desktop-native plugins and broad package installation.

## Review boundary and next milestone

Review the [audit](ANDROID_PORT_AUDIT.md), [compatibility matrix](ANDROID_COMPATIBILITY_MATRIX.md), [architecture](ANDROID_ARCHITECTURE.md), [security risks](ANDROID_SECURITY_MODEL.md) and [roadmap](ANDROID_IMPLEMENTATION_PLAN.md). Noninstalled binary payloads, runtime-downloaded artifacts and Android execution remain unverified; these must not be represented as compatible.

After review only, the next milestone is an Android ARM64/API 29+ runtime qualification using real Node APIs and an authentic Harness profile: persistent session create/reopen, approved harmless command with actual stdout/stderr/exit, and denied-operation evidence. No Phase 2 implementation begins in this task. PR publication remains subject to the author's authorization.
