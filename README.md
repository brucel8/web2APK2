# Web2APK — turn any website into an Android app with GitHub Actions

Enter a URL, click **Run workflow**, get an installable APK. No Android Studio, no local setup.

| Build | Android version | Notes |
|-------|-----------------|-------|
| **TV** | 6.0 (API 23) and up | Landscape, fullscreen, D-pad/remote friendly, shows in the Android TV launcher with a banner (also in the regular launcher for TV boxes that only list normal apps) |
| **Phone** | 13 (API 33) and up | Adaptive icon, configurable rotation, optional fullscreen |

You can build **TV only, phone only, or both** (two separate APKs).

## Quick start

1. Click **Use this template** (or **Fork**) to copy this repo to your own GitHub account.
2. Open the **Actions** tab → **Build Android app from a website URL** → **Run workflow**.
   (If Actions is disabled on your copy, click the green "enable workflows" button first.)
3. Fill in the form (only the URL is required) and run it. It takes about 3–6 minutes.
4. Download the APK(s) from the repo's **Releases** page (or from *Artifacts* on the run page).

## Form options

| Option | Meaning |
|--------|---------|
| `app_url` | Website to wrap. `https://` is added if you leave it out. |
| `build_target` | `both`, `tv` or `phone`. |
| `app_name` | Name under the icon. Default: taken from the URL. Chinese and other Unicode names work. |
| `icon_url` | Direct link to a PNG/JPG/WebP image. Default: a letter icon in the theme color. |
| `theme_color` | Hex color for status bar, icon background and TV banner. |
| `package_name` | Android package id, e.g. `com.mycompany.myapp`. Default: derived from the URL. |
| `phone_orientation` | `system` follows the phone's auto-rotate switch · `sensor` rotates even if auto-rotate is locked · `portrait` · `landscape`. |
| `user_agent` | `auto` (looks like Chrome; on TV also drops the "Mobile" token so sites serve their big-screen layout) · `desktop` · `custom` (+ `custom_user_agent`). |
| `fullscreen_phone` | Hide status/navigation bars on the phone app. TV is always fullscreen. |
| `version_name` | Shown to users. The internal version code is the workflow run number, so each build can update the previous one. |
| `publish_release` | Attach the APKs to a GitHub Release for an easy download link. |

## Installing

- **Phone:** download the `-phone` APK, open it, allow "install unknown apps" for your browser/file manager.
- **Android TV / TV box:** download the `-tv` APK on a computer or phone, then copy it with a USB drive, `adb install file.apk`, or an app such as *Send Files to TV* / *Downloader* (paste the Release download link).

## Keep updates installable (optional, recommended)

Without a signing key, every build is signed with a fresh temporary key, so Android refuses to update the old install (uninstall first). To fix that, create one key and store it as repository secrets (**Settings → Secrets and variables → Actions**):

```bash
keytool -genkeypair -v -keystore release.jks -alias myapp -keyalg RSA -keysize 2048 -validity 10000
base64 -w0 release.jks      # macOS: base64 -i release.jks
```

| Secret | Value |
|--------|-------|
| `KEYSTORE_BASE64` | output of the base64 command |
| `KEYSTORE_PASSWORD` | keystore password |
| `KEY_ALIAS` | `myapp` (the alias you chose) |
| `KEY_PASSWORD` | key password |

Keep `release.jks` backed up; if you lose it you can't publish updates under the same signature.

## Using the app

- **Back** goes back in the site; at the first page, press twice to exit.
- **Menu** key (or the equivalent on your remote) opens Reload / Home / Exit.
- HTML5 video fullscreen, file uploads, cookies/logins and external links (`tel:`, `mailto:`, `intent:`) are handled.
- If the page can't load, an offline page with a **Retry** button is shown.

## Local build (optional)

Requires JDK 17, the Android SDK, Gradle 8.7 and Python 3 with Pillow.

```bash
pip install pillow
INPUT_APP_URL=https://www.example.com python3 scripts/configure.py   # or edit config.json
gradle assembleTvRelease assemblePhoneRelease
# APKs: app/build/outputs/apk/{tv,phone}/release/
```

## Limits to know about

- It is a WebView wrapper: the website must work in a Chromium-based WebView. DRM-protected streaming (Netflix, etc.) generally won't play.
- Sites that need a mouse pointer are awkward with a TV remote; the site itself should be focusable with arrow keys.
- Only wrap websites you own or have permission to package.
