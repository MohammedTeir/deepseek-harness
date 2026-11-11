# Android architecture

Reference. Kotlin Activity + AndroidX WebViewAssetLoader hosts the original `apps/web/dist` at `https://appassets.androidplatform.net/`. A persistent native status message states that the embedded Harness backend is unavailable. No mock boot manifest or replacement chat is injected. The upstream boot page can render; actual application navigation needs backend plugin boot data.

The native diagnostic has a separate user approval dialog and one fixed app-scoped `/system/bin/sh -c pwd` operation. Its result is presented in a native dialog, not claimed as an agent tool result. No JavaScript bridge or network permission is exposed in this prototype.

The intended runtime must load a compliant APK-packaged Bionic `libnode` on an owned runtime thread/process, then use the existing `dsh` named-profile launcher and Android provider plugins. This component is BLOCKED, not implemented. Adapter work must implement existing `ctx.subprocess`, `ctx.shell`, `ctx.fs`, `ctx.terminals` and credential-provider interfaces rather than replace Harness services.

Before transport is enabled, select and test one authenticated origin design using existing connection admission/authentication. Asset-loader HTTPS origin and loopback HTTP/WebSocket have mixed-content/cookie differences: neither permissive CORS nor disabled WebView checks is an accepted integration. Readiness must follow real profile boot; crashes invalidate transport tokens and approvals. Service type/notification policy requires a supported Android execution use case, not a generic indefinite foreground service.

See [compatibility](ANDROID_COMPATIBILITY_MATRIX.md), [security](ANDROID_SECURITY_MODEL.md), and [runtime](ANDROID_RUNTIME_GUIDE.md).
