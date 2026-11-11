# Optional Termux integration

Reference. Status: NOT STARTED. Termux is neither installed nor required by the prototype; no private Termux paths, binaries or intents are used.

Before implementation, review the installed version and official RUN_COMMAND/Tasker API documentation, caller permission and allow-external-apps requirements, package visibility, result PendingIntent security and current Android background restrictions. Record exact supported stdout/stderr/exit behavior; do not assume PTY, streaming or cancellation. Capability reporting must distinguish absent, setup-required, denied, disconnected and unsupported operations. Dispatch requires a provider-bound trusted approval and must never fall back to root. Validate on an actual supported Termux installation and retain license notices for anything distributed. Embedded core readiness is an independent prerequisite.
