# Optional root investigation

## Summary

NOT STARTED and not required for non-root functionality. No `su` execution, root detection probe, rooting attempt or elevated permission is performed by this audit.

Gate 5 requires a trusted native authorization/enforcement component independent of agent/plugin code. Requests carry tool identity, operation, argument vector, resource targets, unique immutable request ID and bounded scope. Consent must bind to the canonical request; mutation/replay/expiry/revocation fail before invocation. The Node runtime must not acquire a persistent root shell or invoke unmediated root subprocesses.

Distinguish unavailable, not authorized, authorized, denied, revoked and error states. Native confirmation cannot predict every shell/script side effect; prefer narrowly structured operations and default-deny destructive or persistent system changes. Validate positive and adversarial cases only on a suitable explicitly authorized test device. No silent fallback from embedded or Termux to root is acceptable.
