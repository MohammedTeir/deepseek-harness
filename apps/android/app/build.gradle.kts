plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}
android {
    namespace = "ai.deepseek.harness.android"
    compileSdk = 35
    defaultConfig {
        applicationId = "ai.deepseek.harness.android"
        minSdk = 29
        targetSdk = 35
        versionCode = 1
        versionName = "0.1.0-prototype"
        ndk { abiFilters += "arm64-v8a" }
    }
    buildFeatures { buildConfig = true }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
    sourceSets["main"].assets.srcDir(layout.buildDirectory.dir("generated/harnessAssets"))
}
val bundleHarnessWeb by tasks.registering(Sync::class) {
    val web = rootProject.file("../web/dist")
    from(web) { exclude("**/*.map", "preview/**", "preview.html") }
    from(rootProject.file("../../LICENSE")) { into("licenses/harness") }
    into(layout.buildDirectory.dir("generated/harnessAssets/web"))
    doFirst { check(web.resolve("index.html").isFile) { "Build the original frontend: pnpm run build:web" } }
}
tasks.named("preBuild") { dependsOn(bundleHarnessWeb) }
dependencies {
    implementation("androidx.webkit:webkit:1.12.1")
    testImplementation("junit:junit:4.13.2")
}
