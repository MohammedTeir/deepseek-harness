# Optional Termux investigation

## Summary

NOT STARTED as an implementation. Termux is not an acceptable dependency for the embedded agent and cannot make a blocked core runtime gate pass.

The official [RUN_COMMAND documentation](https://github.com/termux/termux-app/wiki/RUN_COMMAND-Intent) must govern any later provider. Validate installation source/version, package visibility, exported service behavior, `com.termux.permission.RUN_COMMAND`, `allow-external-apps`, explicit intents and authenticated result delivery. Do not assume access to Termux private files or binaries. Test returned output/status and supported cancellation; do not promise PTY or interactive streaming where the interface does not provide it.

Keep capability and filesystem reporting provider-specific, require explicit provider selection, and never silently offload failed embedded commands. Review distribution licenses before bundling any related component; inter-app integration is not permission to redistribute binaries.
