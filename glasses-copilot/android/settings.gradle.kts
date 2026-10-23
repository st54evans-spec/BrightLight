pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}
dependencyResolutionManagement {
    repositories {
        google()
        mavenCentral()
        // Add Meta's Maven repo here if the DAT SDK requires it (see DAT docs).
    }
}

rootProject.name = "glasses-copilot-android"
include(":app")
