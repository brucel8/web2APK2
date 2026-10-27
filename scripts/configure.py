#!/usr/bin/env python3
"""Resolve build settings and generate the app's name, colors and icons.

Inputs (lowest to highest priority):
  1. config.json                      - defaults committed in the repo
  2. INPUT_<KEY> environment variables - set by the GitHub workflow form

Outputs:
  build-config.json                   - read by app/build.gradle
  app/src/generated/res/...           - strings, colors, launcher icon, TV banner
  $GITHUB_OUTPUT (if set)             - slug, version, build_tv, build_phone
"""
import io
import json
import os
import re
import sys
import urllib.request
from pathlib import Path
from urllib.parse import urlparse
from xml.sax.saxutils import escape

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
GEN = ROOT / "app" / "src" / "generated" / "res"

KEYS = [
    "app_url", "app_name", "package_name", "build_target", "icon_url", "theme_color",
    "phone_orientation", "user_agent", "custom_user_agent", "fullscreen_phone",
    "version_name", "version_code",
]

FONT_CANDIDATES = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]


def fail(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def to_bool(v):
    return v if isinstance(v, bool) else str(v).strip().lower() in ("1", "true", "yes", "y", "on")


# ---------------------------------------------------------------- settings
def load_settings():
    cfg = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    for key in KEYS:
        val = os.environ.get("INPUT_" + key.upper(), "").strip()
        if val != "":
            cfg[key] = val

    url = str(cfg.get("app_url", "")).strip()
    if not url:
        fail("app_url is required")
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", url):
        url = "https://" + url
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        fail(f"app_url must be a valid http(s) URL, got: {url}")
    host = (parsed.hostname or "site").lower()
    host_nowww = re.sub(r"^www\.", "", host)

    name = str(cfg.get("app_name", "")).strip()
    if not name:
        first = host_nowww.split(".")[0] if not re.match(r"^[\d.]+$", host_nowww) else host_nowww
        name = first.capitalize() or "WebApp"

    pkg = str(cfg.get("package_name", "")).strip()
    if not pkg:
        labels = [re.sub(r"[^a-z0-9]", "", p) for p in reversed(host_nowww.split("."))]
        labels = [("a" + p) if (p and p[0].isdigit()) else p for p in labels if p]
        pkg = "io.webapp." + ".".join(labels or ["site"])
    if not re.match(r"^[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z][A-Za-z0-9_]*)+$", pkg):
        fail(f"package_name '{pkg}' is not valid (example: com.mycompany.myapp)")

    target = str(cfg.get("build_target", "both")).lower()
    if target not in ("tv", "phone", "both"):
        fail("build_target must be tv, phone or both")

    color = str(cfg.get("theme_color", "#1f2937")).strip()
    if not re.match(r"^#[0-9a-fA-F]{6}$", color):
        fail("theme_color must look like #1f2937")

    orient = str(cfg.get("phone_orientation", "system")).lower()
    if orient not in ("system", "sensor", "portrait", "landscape"):
        fail("phone_orientation must be system, sensor, portrait or landscape")

    ua = str(cfg.get("user_agent", "auto")).lower()
    if ua not in ("auto", "desktop", "custom"):
        fail("user_agent must be auto, desktop or custom")

    try:
        version_code = int(cfg.get("version_code", 1))
    except ValueError:
        fail("version_code must be an integer")

    ascii_name = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    slug = ascii_name or re.sub(r"[^a-z0-9]+", "-", host_nowww).strip("-") or "webapp"

    return {
        "appUrl": url,
        "appName": name,
        "packageName": pkg,
        "buildTarget": target,
        "iconUrl": str(cfg.get("icon_url", "")).strip(),
        "themeColor": color.lower(),
        "phoneOrientation": orient,
        "userAgentMode": ua,
        "customUserAgent": str(cfg.get("custom_user_agent", "")).strip(),
        "fullscreenPhone": to_bool(cfg.get("fullscreen_phone", False)),
        "versionName": str(cfg.get("version_name", "1.0.0")).strip() or "1.0.0",
        "versionCode": version_code,
        "slug": slug,
    }


# ---------------------------------------------------------------- resources
def xml_text(s):
    """Escape a string for an Android <string> resource."""
    s = s.replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"')
    s = escape(s.replace("\n", " "))
    if s.startswith(("@", "?")):
        s = "\\" + s
    return s


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def luminance(rgb):
    r, g, b = rgb
    return 0.299 * r + 0.587 * g + 0.114 * b


def contrast_on(rgb):
    return (255, 255, 255) if luminance(rgb) < 150 else (24, 24, 24)


def load_font(size):
    for path in FONT_CANDIDATES:
        if not os.path.exists(path):
            continue
        for index in (2, 0):  # index 2 = Simplified Chinese face in Noto CJK collections
            try:
                return ImageFont.truetype(path, size, index=index)
            except OSError:
                continue
    return ImageFont.load_default()


def draw_centered(draw, box, text, font, fill):
    x0, y0, x1, y1 = box
    l, t, r, b = draw.textbbox((0, 0), text, font=font)
    draw.text((x0 + (x1 - x0 - (r - l)) / 2 - l, y0 + (y1 - y0 - (b - t)) / 2 - t), text, font=font, fill=fill)


def fetch_logo(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read(10 * 1024 * 1024)
        return Image.open(io.BytesIO(data)).convert("RGBA")
    except Exception as exc:  # network error, SVG, unsupported format...
        print(f"WARNING: could not use icon_url ({exc}); generating a letter icon instead. "
              f"Use a direct link to a PNG/JPG/WebP image.")
        return None


def fit(img, box):
    img = img.copy()
    img.thumbnail((box, box), Image.LANCZOS)
    return img


def make_tile(size, bg, logo, letter, radius_ratio=0.22):
    """Rounded square launcher icon: logo (or letter) on a solid color."""
    tile = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(tile).rounded_rectangle([0, 0, size - 1, size - 1], radius=int(size * radius_ratio), fill=bg + (255,))
    if logo is not None:
        small = fit(logo, int(size * 0.72))
        tile.alpha_composite(small, ((size - small.width) // 2, (size - small.height) // 2))
    else:
        d = ImageDraw.Draw(tile)
        draw_centered(d, (0, 0, size, size), letter, load_font(int(size * 0.55)), contrast_on(bg) + (255,))
    return tile


def make_foreground(size, bg, logo, letter):
    """Adaptive-icon foreground: content kept inside the 66% safe zone."""
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    if logo is not None:
        small = fit(logo, int(size * 0.62))
        layer.alpha_composite(small, ((size - small.width) // 2, (size - small.height) // 2))
    else:
        d = ImageDraw.Draw(layer)
        draw_centered(d, (0, 0, size, size), letter, load_font(int(size * 0.40)), contrast_on(bg) + (255,))
    return layer


def make_banner(bg, tile, name):
    w, h = 640, 360  # xhdpi -> 320x180dp, the Android TV banner size
    banner = Image.new("RGBA", (w, h), bg + (255,))
    icon = tile.resize((200, 200), Image.LANCZOS)
    banner.alpha_composite(icon, (48, (h - 200) // 2))
    d = ImageDraw.Draw(banner)
    text = name
    size = 64
    area = w - 280 - 40
    font = load_font(size)
    while size > 26 and d.textbbox((0, 0), text, font=font)[2] > area:
        size -= 4
        font = load_font(size)
    while len(text) > 3 and d.textbbox((0, 0), text, font=font)[2] > area:
        text = text.rstrip("…")[:-1] + "…"
    draw_centered(d, (280, 0, w - 40, h), text, font, contrast_on(bg) + (255,))
    return banner.convert("RGB")


def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def generate_resources(s):
    if GEN.exists():
        for p in sorted(GEN.rglob("*"), reverse=True):
            p.unlink() if p.is_file() else p.rmdir()

    theme = hex_rgb(s["themeColor"])
    logo = fetch_logo(s["iconUrl"]) if s["iconUrl"] else None
    icon_bg = theme
    if logo is not None and logo.getchannel("A").getextrema()[0] == 255:
        # Opaque logo (e.g. a JPG): reuse its corner color as the icon background.
        icon_bg = logo.getpixel((0, 0))[:3]
    letter = (s["appName"].strip()[:1] or "W").upper()

    write(GEN / "values" / "strings.xml",
          f'<?xml version="1.0" encoding="utf-8"?>\n<resources>\n'
          f'    <string name="app_name">{xml_text(s["appName"])}</string>\n</resources>\n')
    write(GEN / "values" / "colors.xml",
          '<?xml version="1.0" encoding="utf-8"?>\n<resources>\n'
          f'    <color name="app_theme">{s["themeColor"]}</color>\n'
          f'    <color name="icon_bg">#{icon_bg[0]:02x}{icon_bg[1]:02x}{icon_bg[2]:02x}</color>\n</resources>\n')

    # Legacy launcher icons (Android 6-7 / TV)
    for folder, px in (("mdpi", 48), ("hdpi", 72), ("xhdpi", 96), ("xxhdpi", 144), ("xxxhdpi", 192)):
        out = GEN / f"mipmap-{folder}" / "ic_launcher.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        make_tile(px * 4, icon_bg, logo, letter).resize((px, px), Image.LANCZOS).save(out)

    # Adaptive icon (Android 8+, incl. Android 13 phones)
    fg = GEN / "mipmap-xxxhdpi" / "ic_launcher_foreground.png"
    make_foreground(432, icon_bg, logo, letter).save(fg)
    write(GEN / "mipmap-anydpi-v26" / "ic_launcher.xml",
          '<?xml version="1.0" encoding="utf-8"?>\n'
          '<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">\n'
          '    <background android:drawable="@color/icon_bg"/>\n'
          '    <foreground android:drawable="@mipmap/ic_launcher_foreground"/>\n'
          '</adaptive-icon>\n')

    # Android TV home-screen banner
    banner_path = GEN / "drawable-xhdpi" / "banner.png"
    banner_path.parent.mkdir(parents=True, exist_ok=True)
    # Tile is shaded slightly darker than the banner so it stays visible when icon color == theme color.
    tile_bg = tuple(int(c * 0.78) for c in icon_bg) if icon_bg == theme else icon_bg
    make_banner(theme, make_tile(256, tile_bg, logo, letter), s["appName"]).save(banner_path)


def main():
    s = load_settings()
    (ROOT / "build-config.json").write_text(json.dumps(s, indent=2, ensure_ascii=False), encoding="utf-8")
    generate_resources(s)

    print(f"App name   : {s['appName']}")
    print(f"URL        : {s['appUrl']}")
    print(f"Package    : {s['packageName']}")
    print(f"Build      : {s['buildTarget']}  (v{s['versionName']} / code {s['versionCode']})")

    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as f:
            f.write(f"slug={s['slug']}\n")
            f.write(f"version={s['versionName']}\n")
            f.write(f"build_tv={'true' if s['buildTarget'] in ('tv', 'both') else 'false'}\n")
            f.write(f"build_phone={'true' if s['buildTarget'] in ('phone', 'both') else 'false'}\n")


if __name__ == "__main__":
    main()
