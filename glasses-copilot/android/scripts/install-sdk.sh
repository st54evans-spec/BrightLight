#!/usr/bin/env bash
# Installs the Android command-line SDK this app compiles against.
# Android Studio does this for you; this script is for a machine that only
# has Java (17+) and needs to run ./gradlew.
set -euo pipefail

SDK="${ANDROID_HOME:-/opt/android-sdk}"
CMDLINE_URL="https://dl.google.com/android/repository/commandlinetools-linux-13114758_latest.zip"

if [[ ! -x "$SDK/cmdline-tools/latest/bin/sdkmanager" ]]; then
  tmp=$(mktemp -d)
  curl -fsSL -o "$tmp/cmdtools.zip" "$CMDLINE_URL"
  unzip -q "$tmp/cmdtools.zip" -d "$tmp/extract"
  mkdir -p "$SDK/cmdline-tools"
  rm -rf "$SDK/cmdline-tools/latest"
  mv "$tmp/extract/cmdline-tools" "$SDK/cmdline-tools/latest"
  rm -rf "$tmp"
fi

export ANDROID_HOME="$SDK"
yes | "$SDK/cmdline-tools/latest/bin/sdkmanager" --sdk_root="$SDK" --licenses >/dev/null || true
"$SDK/cmdline-tools/latest/bin/sdkmanager" --sdk_root="$SDK" \
  "platforms;android-35" \
  "build-tools;35.0.0" \
  "platform-tools"

echo "Android SDK ready at $SDK"
echo "export ANDROID_HOME=$SDK"
