# Urdu News Daily — Mobile (Android + iPhone)

This is your desktop **Urdu News Daily v2.1** rebuilt as a real mobile app.
Same brain: 16 sources, category filter, RTL Nastaliq, auto-translate, AI summary,
bookmarks. **No background polling — you tap Refresh.**

The user installs ONE file. No Python, no setup, nothing else required. ✅

---

## What's in this folder

| File | What it is |
|------|-----------|
| `main.py` | The whole app (Kivy port of your v2.1) |
| `buildozer.spec` | Build recipe — turns `main.py` into `.apk` / `.ipa` |
| `NotoNastaliqUrdu-Regular.ttf` | Bundled Urdu font (so it renders on phones with no Urdu font) |
| `.github/workflows/build-android.yml` | **Auto-builds the APK in the cloud for free** |

---

## 🟢 ANDROID — the easy, free path (recommended)

You do **not** need Android Studio or a Linux PC. GitHub builds it for you.

### Steps (10 minutes, one-time)
1. Create a free account at **github.com** (if you don't have one).
2. Make a new **public** repository, e.g. `urdu-news-daily`.
3. Upload **everything in this folder** (including the hidden `.github` folder).
   - Easiest: GitHub web → "Add file" → "Upload files" → drag all files.
   - The `.github/workflows/build-android.yml` MUST be uploaded too.
4. Go to the repo's **Actions** tab → click **"Build Android APK"** → **Run workflow**.
5. Wait ~20–30 min (first build is slow; it downloads the Android SDK).
6. When the green ✓ appears, open the run → scroll to **Artifacts** →
   download **`UrduNewsDaily-APK`**.
7. Unzip it → you get `urdunewsdaily-2.1-debug.apk`.

### Install on any Android phone
1. Copy the `.apk` to the phone (WhatsApp-to-self, email, USB, anything).
2. Tap it → Android asks to allow "Install from this source" → allow → Install.
3. Done. It's a normal app now. Share that same `.apk` with anyone.

> This is a **debug** APK — perfect for personal use and sharing directly.
> For Google Play Store you'd later make a signed "release" build, but you do
> NOT need the Play Store to install and share it.

---

## 🍎 iPhone — the honest truth

Apple does not allow free, no-setup installs. To get this on an iPhone you need:
- A **Mac** (macOS) with **Xcode**
- An **Apple Developer account** ($99/year) to install on real devices
- Build with: `pip install kivy-ios && toolchain build python3 kivy && ...`
  then open the generated Xcode project and deploy.

There is **no way around Apple's wall** — it's their policy, not a limitation
of your app. The `buildozer.spec` already has the iOS section ready for when
you have a Mac.

**Practical recommendation:** ship Android now (free, today). Do iPhone later
only if you actually need iOS users — for a personal Urdu news reader, Android
covers ~95% of your Pakistani audience.

---

## Local build (only if you have Ubuntu/WSL and want to skip GitHub)

```bash
pip install buildozer Cython==0.29.36
sudo apt install -y openjdk-17-jdk zip unzip autoconf libtool pkg-config \
  zlib1g-dev libncurses5-dev cmake libffi-dev libssl-dev
buildozer android debug      # APK lands in ./bin/
```

---

## Notes
- First launch needs internet (it fetches live RSS). News itself loads on Refresh.
- AI summaries are optional: tap **AI** on any article → paste your Anthropic key once.
- Bookmarks are stored on-device and survive restarts.
- If Urdu looks disconnected on some device, the bundled font fixes it — make
  sure `NotoNastaliqUrdu-Regular.ttf` was uploaded with the rest.
