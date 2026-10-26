import org.jetbrains.kotlin.gradle.dsl.JvmTarget

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.brightlight.glasses"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.brightlight.glasses"
        minSdk = 29          // DAT requires Android 10+
        targetSdk = 35
        versionCode = 1
        versionName = "0.1"

        // Your brain bridge URL (npm run serve). Use your LAN IP on a real phone,
        // e.g. http://192.168.1.20:3200 — localhost points at the phone itself.
        buildConfigField("String", "BRIDGE_URL", "\"http://10.0.2.2:3200\"")
        // Must match the package you register in the Wearables Developers Center.
        buildConfigField("String", "META_PACKAGE_NAME", "\"com.brightlight.glasses\"")
    }

    buildFeatures { buildConfig = true }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

kotlin {
    compilerOptions {
        jvmTarget.set(JvmTarget.JVM_17)
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.activity:activity-ktx:1.9.3")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.7")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.1")

    // Meta Wearables Device Access Toolkit (Android). Add per the current setup
    // docs — Kotlin 2.2+ is required because the toolkit is compiled with it.
    //   implementation("com.meta.wearables.dat:core:1.0.1")
    //   implementation("com.meta.wearables.dat:camera:1.0.1")
}
