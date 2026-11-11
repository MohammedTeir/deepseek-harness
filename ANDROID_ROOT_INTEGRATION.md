# Optional root integration

Reference. Status: NOT STARTED. No root detection, su invocation, authorization request or privilege escalation occurs in the prototype.

An optional provider must distinguish unavailable, not authorized, authorized, denied, revoked and error. Each operation requires separate trusted user consent for exact command, effective identity, scope, expiry and known affected resources; shell side effects cannot be fully predicted. Grants cannot originate from models/plugins or be reused by other providers. Backend destructive/persistent-operation policy is independent from the dialog. Revoke on expiry, runtime death or explicit action, redact audit records, and test only on a voluntarily supplied suitable rooted device. Never root the device or silently escalate a failed unprivileged command.
