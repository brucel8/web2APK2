# Web2APK — turn any website into an Android TV or phone app with GitHub Actions

Enter a URL, click **Run workflow**, get an installable APK. No Android Studio, no local setup.

| Build | Android version | Notes |
|-------|-----------------|-------|
| **TV** | 6.0 (API 23) and up | Landscape, fullscreen, D-pad/remote friendly, shows in the Android TV launcher with a banner (also in the regular launcher for TV boxes that only list normal apps) |
| **Phone** | 13 (API 33) and up | Adaptive icon, configurable rotation, optional fullscreen |

You can build **TV only, phone only, or both** (two separate APKs).

No GitHub Actions? There is also a **[Windows portable version](#windows-portable-version-build-on-your-pc)** that builds the same apps on your own PC.

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

## Windows portable version (build on your PC)

Prefer not to use GitHub Actions? [`windows/Web2APK-Portable.zip`](windows/Web2APK-Portable.zip) does the same job on a Windows PC: enter a URL, get a TV and/or phone APK. It is portable: unzip and run, nothing is installed on your system and no Android Studio is needed.

**Requirements:** Windows 10/11 (64-bit), internet access, about 4 GB free disk space.

### Use it

1. Download the ZIP (open the file in the `windows` folder and click **Download raw file**, or grab it from the Releases page if provided) and unzip it to a **simple path** such as `C:\Web2APK`. Avoid spaces and non-English characters in the path; Android build tools can fail on them.
2. Double-click **`Web2APK.bat`**.
3. Enter the website URL (everything else is optional), choose **both / tv / phone**, and click **Build APK**.
4. A console window shows progress. When it finishes, the `output` folder opens with your APK(s), for example `site-tv-v1.0.0.apk` and `site-phone-v1.0.0.apk`.

The window has the same options as the GitHub form: app name, icon, theme color, package id, phone rotation, browser identity, phone fullscreen and version name. For the icon you can pick a local image file (PNG/JPG/GIF) or paste a link.

**First build:** it downloads about 1 GB of tools (JDK 17, Gradle 8.7, Android SDK) into a `tools` folder next to the program, then the Android Gradle plugin libraries. Allow 10-20 minutes. Later builds take about 1-3 minutes. By building you accept the [Android SDK license](https://developer.android.com/studio/terms).

### Command line (optional)

```bat
BuildFromUrl.bat https://www.example.com tv
```

or, for all options:

```bat
powershell -ExecutionPolicy Bypass -File scripts\build.ps1 -Url https://www.example.com -Target both -Name "My App" -ThemeColor "#b91c1c"
```

Options: `-Name` `-Target` `-Icon` `-ThemeColor` `-PackageName` `-PhoneOrientation` `-UserAgent` `-CustomUserAgent` `-FullscreenPhone` `-VersionName`. For non-English app names use the window (`Web2APK.bat`) rather than `BuildFromUrl.bat`.

### What is inside

| Path | Purpose |
|------|---------|
| `Web2APK.bat` | Opens the input window |
| `BuildFromUrl.bat` | Quick command-line build |
| `scripts\build.ps1` | Downloads tools, generates icons, builds the APKs |
| `scripts\gui.ps1` | The input window |
| `project\` | The same Android project used by the GitHub version |
| `tools\` *(created on first run)* | Portable JDK, Gradle and Android SDK |
| `data\` *(created on first run)* | Your signing key and last-used settings |
| `output\` *(created on first run)* | Finished APKs |

### Updates and signing

A signing key is created once in `data\` and reused for every build, so a new APK can update an older install without uninstalling. **Back up the `data` folder**: if you lose `release.jks`, you have to uninstall old apps before installing new builds. (Do not share the `data` folder; it contains your key and its password.)

### Differences from the GitHub version

| | GitHub Actions | Windows portable |
|---|---|---|
| Where it builds | GitHub's servers | Your PC |
| Setup | Fork + run workflow | Unzip + double-click |
| Signing key | Optional secrets, else a temporary key | Created automatically and reused |
| Icon source | Link to PNG/JPG/WebP | Local file or link (PNG/JPG/GIF) |
| App itself | Same | Same |

The resulting apps are identical in behavior: TV 6.0+ / phone 13+, same rotation, browser-identity and fullscreen options.

## Limits to know about

- It is a WebView wrapper: the website must work in a Chromium-based WebView. DRM-protected streaming (Netflix, etc.) generally won't play.
- Sites that need a mouse pointer are awkward with a TV remote; the site itself should be focusable with arrow keys.
- Only wrap websites you own or have permission to package.
