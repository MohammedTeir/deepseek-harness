plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}
android {
    namespace = "io.github.mohammedteir.deepseekharness.packaging"
    compileSdk = 36
    buildToolsVersion = "36.0.0"
    defaultConfig {
        applicationId = "ai.deepseek.harness.android.packagingproof"
        minSdk = 29
        targetSdk = 36
        versionCode = 1
        versionName = "0.1.0-packaging-proof"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        ndk { abiFilters += "arm64-v8a" }
    }
    signingConfigs.getByName("debug").storeFile = rootProject.file(".local/debug.keystore")
    ndkVersion = "28.2.13676358"
    packaging { jniLibs { useLegacyPackaging = true } }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
    sourceSets["main"].assets.srcDir(layout.buildDirectory.dir("generated/proofAssets"))
    sourceSets["main"].jniLibs.srcDir(layout.buildDirectory.dir("generated/fixtures"))
}
val sdk = providers.environmentVariable("ANDROID_HOME").get()
val compiler = "$sdk/ndk/28.2.13676358/toolchains/llvm/prebuilt/linux-x86_64/bin/aarch64-linux-android29-clang"
val sharedFixture by tasks.registering(Exec::class) {
    val destination = layout.buildDirectory.file("generated/fixtures/arm64-v8a/libpackaging_probe.so").get().asFile
    inputs.file("native/shared.c")
    outputs.file(destination)
    doFirst { destination.parentFile.mkdirs() }
    commandLine(compiler, "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror", "-fPIC", "-shared", "-Wl,-z,max-page-size=16384", file("native/shared.c"), "-o", destination)
}
val executableFixture by tasks.registering(Exec::class) {
    val destination = layout.buildDirectory.file("generated/fixtures/arm64-v8a/libexecution_probe.so").get().asFile
    inputs.file("native/executable.c")
    outputs.file(destination)
    doFirst { destination.parentFile.mkdirs() }
    commandLine(compiler, "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror", "-fPIE", "-pie", "-Wl,-z,max-page-size=16384", file("native/executable.c"), "-o", destination)
}
val fixtureNotices by tasks.registering(Sync::class) {
    from(rootProject.file("../../LICENSE"))
    from(rootProject.file("../../THIRD_PARTY_NOTICES.md"))
    from("$sdk/ndk/28.2.13676358/NOTICE") { rename { "NDK_NOTICE" } }
    into(layout.buildDirectory.dir("generated/proofAssets/licenses"))
}
tasks.named("preBuild") { dependsOn(sharedFixture, executableFixture, fixtureNotices) }
dependencies {
    androidTestImplementation("androidx.test:runner:1.6.2")
    androidTestImplementation("androidx.test.ext:junit:1.2.1")
}
