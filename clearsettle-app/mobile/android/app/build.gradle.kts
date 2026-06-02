plugins {
    id("com.android.application")
    id("kotlin-android")
    // The Flutter Gradle Plugin must be applied after the Android and Kotlin Gradle plugins.
    id("dev.flutter.flutter-gradle-plugin")
    // Firebase — must come after com.android.application
    id("com.google.gms.google-services")
    id("com.google.firebase.appdistribution")
}

android {
    namespace = "in.clearsettle.mobile"
    compileSdk = flutter.compileSdkVersion
    ndkVersion = flutter.ndkVersion

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = JavaVersion.VERSION_17.toString()
    }

    defaultConfig {
        // TODO: Specify your own unique Application ID (https://developer.android.com/studio/build/application-id.html).
        applicationId = "in.clearsettle.mobile"
        // You can update the following values to match your application needs.
        // For more information, see: https://flutter.dev/to/review-gradle-config.
        minSdk = flutter.minSdkVersion
        targetSdk = flutter.targetSdkVersion
        versionCode = flutter.versionCode
        versionName = flutter.versionName
    }

    buildTypes {
        release {
            // TODO: Add your own signing config for the release build.
            // Signing with the debug keys for now, so `flutter run --release` works.
            signingConfig = signingConfigs.getByName("debug")

            firebaseAppDistribution {
                // Testers are notified automatically when a new build is uploaded.
                // Comma-separated tester emails or group aliases defined in Firebase console.
                testers = "sudo.ranjith@gmail.com"
                releaseNotes = "Internal test build"
                // Optional: set serviceCredentialsFile for CI
                // serviceCredentialsFile = "firebase-service-account.json"
            }
        }
        debug {
            firebaseAppDistribution {
                testers = "sudo.ranjith@gmail.com"
                releaseNotes = "Debug build"
            }
        }
    }
}

flutter {
    source = "../.."
}
