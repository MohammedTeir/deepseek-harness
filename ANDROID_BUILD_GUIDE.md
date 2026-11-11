# Phase 1 audit reproduction

## Summary

This branch builds audit evidence and the original host frontend only. It contains no Android application build or APK target.

## Prerequisites and commands

Use the checked-out fork and its pinned Node/pnpm versions. Installed dependencies must match `pnpm-lock.yaml`; do not refresh the lockfile. The evidence collector requires Python 3, PyYAML and GNU readelf. Run `python3 audit/android/collect.py` from the repository root to reconstruct the locked graph and installed-payload inventory. It reads manifests and binary headers without running dependency install hooks and fails on unresolved graph targets or ELF-read errors. Installed payload availability varies by host; the checked-in snapshot states this host's coverage.

Run `pnpm run build:web` to compile the original frontend after the repository's built workspace artifacts are available. This verifies the host frontend build only. `apps/web/dist` is generated output and is not committed. Record node/pnpm versions, lock digest and command result in [status](ANDROID_PORT_STATUS.md).

Registry metadata for noninstalled packages and official-platform excerpts are dated investigation evidence, not a silently refreshed source of executable code. Re-fetch their recorded URLs and compare `dist.integrity` against the lockfile before updating those records. No Android SDK/NDK install, signing or packaging step is needed for this documentation phase.
