plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
    id("org.jetbrains.kotlin.plugin.serialization")
}

android {
    namespace = "br.com.securo.wear"
    compileSdk = 34

    defaultConfig {
        applicationId = "br.com.securo.wear"
        // minSdk 30 = Wear OS 3, the floor for Galaxy Watch 4 and newer
        // (Watch Face Format / modern Compose-for-Wear APIs assume it).
        minSdk = 30
        targetSdk = 34
        versionCode = 1
        versionName = "0.1.0"

        // Pre-fills the server field on first run — the same Tailscale
        // hostname the web app is reached at (see root .env FRONTEND_URL).
        // Editable in-app afterwards (data/ServerSettings.kt), since this
        // will differ per install if you ever run this against another
        // Securo instance.
        buildConfigField("String", "DEFAULT_BASE_URL", "\"https://desktop-s200k6m.tail50b52d.ts.net\"")
    }

    buildTypes {
        release {
            isMinifyEnabled = false
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.4")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.4")
    implementation("androidx.activity:activity-compose:1.9.1")

    // Compose for Wear OS — round-screen-aware components (curved text,
    // ScalingLazyColumn, Picker, PositionIndicator) rather than the phone
    // Material3 toolkit.
    implementation("androidx.wear.compose:compose-material:1.4.0")
    implementation("androidx.wear.compose:compose-foundation:1.4.0")
    implementation("androidx.wear.compose:compose-navigation:1.4.0")
    implementation("androidx.wear:wear-tooling-preview:1.0.0")
    // RemoteInputIntentHelper — the standard Wear OS "type or speak text"
    // system flow (same one Messages/Gmail replies use), for the pairing
    // code entry. Distinct from wear-remote-interactions (phone/Play
    // Store handoff), which this app doesn't need in Phase 1.
    implementation("androidx.wear:wear-input:1.1.0")

    // Networking — the watch talks to the same FastAPI backend the web
    // app does. Bearer token attached via AuthInterceptor (see
    // network/AuthInterceptor.kt).
    implementation("com.squareup.retrofit2:retrofit:2.11.0")
    implementation("com.squareup.retrofit2:converter-kotlinx-serialization:2.11.0")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("com.squareup.okhttp3:logging-interceptor:4.12.0")
    implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.7.1")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.1")

    // Encrypted at-rest storage for the access token — never plain
    // SharedPreferences for a bearer token.
    implementation("androidx.security:security-crypto:1.1.0-alpha06")

    implementation("androidx.datastore:datastore-preferences:1.1.1")
}
