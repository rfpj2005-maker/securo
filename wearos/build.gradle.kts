// Root build file — no top-level dependencies, just the plugin versions
// modules opt into. Keep in sync with app/build.gradle.kts and
// watchface/build.gradle.kts when bumping.
plugins {
    id("com.android.application") version "8.6.0" apply false
    id("org.jetbrains.kotlin.android") version "2.0.20" apply false
    id("org.jetbrains.kotlin.plugin.compose") version "2.0.20" apply false
    id("org.jetbrains.kotlin.plugin.serialization") version "2.0.20" apply false
}
