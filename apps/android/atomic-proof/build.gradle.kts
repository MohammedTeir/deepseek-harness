plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}
android {
    namespace = "io.github.mohammedteir.deepseekharness.atomic"
    compileSdk = 36
    buildToolsVersion = "36.0.0"
    defaultConfig {
        applicationId = "ai.deepseek.harness.android.atomicpoc"
        minSdk = 29
        targetSdk = 36
        versionCode = 1
        versionName = "0.1.0-atomic-proof"
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
    sourceSets["main"].jniLibs.srcDir(layout.buildDirectory.dir("generated/native"))
    sourceSets["main"].assets.srcDir(layout.buildDirectory.dir("generated/proofAssets"))
    sourceSets["main"].assets.srcDir(rootProject.file("licenses"))
    sourceSets["androidTest"].assets.srcDir(rootProject.file("licenses"))
}
val sdk = providers.environmentVariable("ANDROID_HOME").get()
val compiler = "$sdk/ndk/28.2.13676358/toolchains/llvm/prebuilt/linux-x86_64/bin/aarch64-linux-android29-clang++"
val nativeProof by tasks.registering(Exec::class) {
    val destination = layout.buildDirectory.file("generated/native/arm64-v8a/libatomic_poc.so").get().asFile
    inputs.file("native/atomic_poc.cpp")
    outputs.file(destination)
    doFirst { destination.parentFile.mkdirs() }
    commandLine(compiler, "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror", "-fPIE", "-pie", "-static-libstdc++",
        "-Wl,-z,max-page-size=16384", "-Wl,-z,relro,-z,now", file("native/atomic_poc.cpp"), "-o", destination)
}
val proofNotices by tasks.registering(Sync::class) {
    from(rootProject.file("../../LICENSE"))
    from(rootProject.file("../../THIRD_PARTY_NOTICES.md"))
    from("$sdk/ndk/28.2.13676358/NOTICE") { rename { "NDK_NOTICE" } }
    into(layout.buildDirectory.dir("generated/proofAssets/licenses"))
}
tasks.named("preBuild") { dependsOn(nativeProof, proofNotices) }
dependencies {
    androidTestImplementation("androidx.test:runner:1.6.2")
    androidTestImplementation("androidx.test.ext:junit:1.2.1")
}
