import java.util.Properties

plugins {
    id("com.android.application")
    id("kotlin-android")
    // The Flutter Gradle Plugin must be applied after the Android and Kotlin Gradle plugins.
    id("dev.flutter.flutter-gradle-plugin")
    // Firebase — must come after com.android.application
    id("com.google.gms.google-services")
    id("com.google.firebase.appdistribution")
}

// ── Signing config ────────────────────────────────────────────────────────────
// Loaded from android/key.properties (gitignored) for local builds.
// CI overrides via environment variables (STORE_PASSWORD, KEY_PASSWORD, etc.)
val keystoreProps = Properties()
val keystorePropsFile = rootProject.file("key.properties")
if (keystorePropsFile.exists()) {
    keystoreProps.load(keystorePropsFile.inputStream())
}

fun keystoreProp(name: String): String? =
    (keystoreProps[name] as String?)?.takeIf { it.isNotBlank() }
        ?: System.getenv(name.uppercase().replace(".", "_"))

val firebaseSvcAccount: String =
    keystoreProp("firebaseServiceAccountFile")
        ?: System.getenv("FIREBASE_SERVICE_ACCOUNT_FILE")
        ?: ""

android {
    namespace = "in.clearsettle.mobile"
    compileSdk = flutter.compileSdkVersion
    ndkVersion = flutter.ndkVersion

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    // ── Release keystore ───────────────────────────────────────────────────────
    signingConfigs {
        create("release") {
            keyAlias      = keystoreProp("keyAlias")      ?: error("keyAlias not set")
            keyPassword   = keystoreProp("keyPassword")   ?: error("keyPassword not set")
            storePassword = keystoreProp("storePassword") ?: error("storePassword not set")
            val sfProp    = keystoreProp("storeFile")     ?: error("storeFile not set")
            storeFile     = keystorePropsFile.parentFile.resolve(sfProp)
        }
    }

    defaultConfig {
        applicationId = "com.clearsettle.mobile"
        minSdk        = flutter.minSdkVersion
        targetSdk     = flutter.targetSdkVersion
        versionCode   = flutter.versionCode
        versionName   = flutter.versionName
    }

    buildTypes {
        release {
            signingConfig = signingConfigs.getByName("release")

            if (firebaseSvcAccount.isNotBlank()) {
                firebaseAppDistribution {
                    serviceCredentialsFile = firebaseSvcAccount
                    testers      = "sudo.ranjith@gmail.com"
                    releaseNotes = "v1.0.5 — BUG014/015/016 fixes, Firebase FCM, release signing, App Distribution"
                }
            }
        }
        debug {
            // Debug builds also uploadable for quick tester feedback
            if (firebaseSvcAccount.isNotBlank()) {
                firebaseAppDistribution {
                    serviceCredentialsFile = firebaseSvcAccount
                    testers      = "sudo.ranjith@gmail.com"
                    releaseNotes = "Debug build"
                }
            }
        }
    }
}

flutter {
    source = "../.."
}
