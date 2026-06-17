[app]
title = Urdu News Daily
package.name = urdunewsdaily
package.domain = pk.neo.urdunews
source.dir = .
source.include_exts = py,png,jpg,ttf,json,atlas
version = 2.1
requirements = python3,kivy==2.3.0,requests,feedparser==6.0.11,urllib3,certifi,chardet,idna
orientation = portrait
fullscreen = 0

# ---------- Android ----------
android.permissions = INTERNET, ACCESS_NETWORK_STATE
android.api = 34
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a
android.allow_backup = 1
android.accept_sdk_license = True

# CRITICAL: pin p4a to the v2024.1.21 git tag (Python 3.11 era).
# Without this, buildozer 1.5.0 clones p4a master, which forces
# Python 3.14 and breaks pyjnius/kivy (no 3.14 wheels exist).
p4a.branch = v2024.01.21

# ---------- iOS ----------
ios.kivy_ios_url = https://github.com/kivy/kivy-ios
ios.kivy_ios_branch = master
ios.ios_deploy_url = https://github.com/phonegap/ios-deploy
ios.ios_deploy_branch = 1.10.0
ios.codesign.allowed = false

[buildozer]
log_level = 2
warn_on_root = 0
