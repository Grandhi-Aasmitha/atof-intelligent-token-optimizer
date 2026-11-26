plugins {
    java
    id("org.jetbrains.intellij.platform") version "2.20.1"
}
group = "dev.atof"
version = "0.9.0"
repositories {
    mavenCentral()
    intellijPlatform { defaultRepositories() }
}
dependencies {
    implementation("com.google.code.gson:gson:2.11.0")
    intellijPlatform { intellijIdea("2025.2") }
    testImplementation("org.junit.jupiter:junit-jupiter:5.11.4")
    testRuntimeOnly("org.junit.platform:junit-platform-launcher")
}
java { toolchain { languageVersion.set(JavaLanguageVersion.of(21)) } }
intellijPlatform {
    pluginConfiguration {
        ideaVersion {
            sinceBuild = "252"
            untilBuild = "252.*"
        }
    }
}
tasks.test { useJUnitPlatform() }
