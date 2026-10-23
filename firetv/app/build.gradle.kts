plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

// Assinatura estável (para `adb install -r` atualizar sem desinstalar):
// o CI lê o keystore dos secrets FIRETV_KEYSTORE_*. Sem eles, usa a chave de debug.
val releaseKeystore = System.getenv("FIRETV_KEYSTORE_FILE")?.let { file(it) }?.takeIf { it.exists() }

android {
    namespace = "br.com.amparar.cameras"
    compileSdk = 35

    defaultConfig {
        applicationId = "br.com.amparar.cameras"
        minSdk = 22 // Fire OS 5 (Fire TV Stick 2ª geração) em diante
        targetSdk = 35
        versionCode = (System.getenv("GITHUB_RUN_NUMBER")?.toIntOrNull() ?: 1)
        versionName = "1.0.${System.getenv("GITHUB_RUN_NUMBER") ?: "0"}"
    }

    signingConfigs {
        if (releaseKeystore != null) {
            create("release") {
                storeFile = releaseKeystore
                storePassword = System.getenv("FIRETV_KEYSTORE_PASSWORD")
                keyAlias = System.getenv("FIRETV_KEY_ALIAS") ?: "amparar"
                keyPassword = System.getenv("FIRETV_KEY_PASSWORD") ?: System.getenv("FIRETV_KEYSTORE_PASSWORD")
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
            signingConfig = signingConfigs.findByName("release") ?: signingConfigs.getByName("debug")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
    lint {
        disable += "UnsafeOptInUsageError"
        abortOnError = false
    }
}

dependencies {
    val media3 = "1.6.1"
    implementation("androidx.media3:media3-exoplayer:$media3")
    implementation("androidx.media3:media3-exoplayer-rtsp:$media3")
    implementation("androidx.media3:media3-ui:$media3")
}
