plugins {
    java
    id("org.jetbrains.intellij.platform") version "2.20.1"
}
group = "dev.atof"
version = "0.7.0"
repositories {
    mavenCentral()
    intellijPlatform { defaultRepositories() }
}
dependencies { intellijPlatform { intellijIdea("2025.2") } }
java { toolchain { languageVersion.set(JavaLanguageVersion.of(21)) } }
