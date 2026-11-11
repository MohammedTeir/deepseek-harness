# Android security model

Reference. The upstream [SAFETY.md](SAFETY.md) warning applies unchanged. No security audit or secure sandbox is claimed.

The current host grants no Internet, shared-storage, root or inter-app command permissions. Only the launcher Activity is exported. WebView navigation and subresource requests admit exactly the packaged HTTPS host on the default TLS port, with no URL userinfo; other requests receive denial. File/content access, mixed content, popups and release debugging are disabled. There is no JavaScript/native execution bridge. Packaged assets are trusted build inputs; this does not establish their supply-chain security.

Native diagnostic authorization is private to the Activity/provider. A trusted dialog displays the fixed command, application identity, cwd and one-use scope. Approvals expire in 30 seconds, are replaced on new approval and revoked on Activity destruction or denial. There is no caller-selected command/provider/root flag. The fixed diagnostic does not constitute the Harness authorization pipeline. Origin and authorization unit tests cover foreign URLs, invented/expired/replayed/replaced/revoked grants.

Before general execution is enabled, trusted enforcement must bind user-reviewed argv, cwd, environment, provider, identity, request id, resource scope and expiry to an unforgeable one-use grant; altered requests and plugin self-approval fail closed. Arbitrary plugins in the same Node process can use Node APIs directly: JavaScript tool hooks alone do not isolate them. Do not expose secrets to plugins without a separate threat assessment.

Future local RPC must authenticate every HTTP/stream/WebSocket path, preserve upstream Host/Origin admission, rotate tokens with runtime lifetime and prevent token leakage in logs, exports and untrusted navigation. Loopback alone does not prevent other apps from connecting. Cross-origin WebView behavior is not yet validated. Keystore-backed credentials, SAF grants, bounded audit retention, root isolation and revocation are NOT IMPLEMENTED. No keys should be entered into this prototype.
