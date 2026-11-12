plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}
android {
    namespace = "io.github.mohammedteir.deepseekharness"
    compileSdk = 36
    buildToolsVersion = "36.0.0"
    defaultConfig {
        applicationId = "ai.deepseek.harness.android.runtimepoc"
        minSdk = 29
        targetSdk = 36
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        versionCode = 1
        versionName = "0.1.0-runtime-proof"
        ndk { abiFilters += "arm64-v8a" }
    }
    signingConfigs.getByName("debug").storeFile = rootProject.file(".local/debug.keystore")
    ndkVersion = "28.2.13676358"
    externalNativeBuild { cmake { path = file("../native/CMakeLists.txt"); version = "3.22.1" } }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
    sourceSets["main"].assets.srcDir(layout.buildDirectory.dir("generated/runtimeAssets"))
    sourceSets["main"].assets.srcDir(rootProject.file("licenses"))
    sourceSets["androidTest"].assets.srcDir(rootProject.file("licenses"))
}
val prepareRuntimeAssets by tasks.registering(Exec::class) {
    workingDir(rootProject.projectDir)
    commandLine("python3", "scripts/prepare_runtime_assets.py", layout.buildDirectory.dir("generated/runtimeAssets").get().asFile.absolutePath)
    outputs.upToDateWhen { false }
}
tasks.named("preBuild") { dependsOn(prepareRuntimeAssets) }

dependencies {
    androidTestImplementation("androidx.test:runner:1.6.2")
    androidTestImplementation("androidx.test.ext:junit:1.2.1")
}
