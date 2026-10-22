#!/usr/bin/env python3
"""Generate 1200x630 Open Graph PNGs into static/og/ (run locally when games/art change; needs Pillow).

Images deliberately carry no verdict text, so they never go stale between rebuilds.
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from games import GAMES  # noqa: E402

W, H = 1200, 630
FONT = str(ROOT / "tools" / "ChakraPetch-Bold.ttf")
OUT = ROOT / "static" / "og"


def cover(img: Image.Image) -> Image.Image:
    r = max(W / img.width, H / img.height)
    img = img.resize((int(img.width * r + 1), int(img.height * r + 1)), Image.LANCZOS)
    x, y = (img.width - W) // 2, (img.height - H) // 2
    return img.crop((x, y, x + W, y + H))


def gradient(base: Image.Image) -> Image.Image:
    ov = Image.new("RGBA", (W, H))
    d = ImageDraw.Draw(ov)
    for x in range(W):
        a = int(235 * max(0.0, 1 - x / (W * 0.85)) + 40)
        d.line([(x, 0), (x, H)], fill=(7, 9, 15, min(a, 245)))
    return Image.alpha_composite(base.convert("RGBA"), ov)


def wrap(draw, text, font, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=font) <= width:
            cur = t
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


def render(bg: Image.Image | None, title: str, sub: str, path: Path):
    base = cover(bg) if bg else Image.new("RGB", (W, H), (7, 9, 15))
    img = gradient(base)
    d = ImageDraw.Draw(img)
    logo = Image.open(ROOT / "brand" / "avatar.png").convert("RGBA").resize((84, 84), Image.LANCZOS) \
        if (ROOT / "brand" / "avatar.png").exists() else Image.open(ROOT / "static/img/logo.png").convert("RGBA").resize((84, 84))
    img.alpha_composite(logo, (72, 64))
    d.text((172, 82), "ModSafe", font=ImageFont.truetype(FONT, 46), fill=(0, 240, 255))
    big = ImageFont.truetype(FONT, 78)
    y = 210
    for line in wrap(d, title.upper(), big, 760)[:3]:
        d.text((72, y), line, font=big, fill=(238, 243, 255))
        y += 86
    d.text((72, y + 16), sub, font=ImageFont.truetype(FONT, 34), fill=(163, 177, 201))
    d.rectangle([0, H - 8, W, H], fill=(0, 240, 255))
    d.rectangle([W // 2, H - 8, W, H], fill=(255, 42, 109))
    path.parent.mkdir(parents=True, exist_ok=True)
    # Palette PNG keeps files ~150-250 KB (crawlers like < 300 KB) while staying a real PNG.
    img.convert("RGB").quantize(colors=200, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.FLOYDSTEINBERG).save(path, "PNG", optimize=True)
    print(path.relative_to(ROOT), path.stat().st_size)


def main():
    hero = ROOT / "static/img/cyberpunk-2077-hero.webp"
    render(Image.open(hero) if hero.exists() else None, "Did your mods survive the patch?",
           f"Mod framework status for {sum(1 for g in GAMES if g.get('genre') != 'Platform')} PC games + Steam Deck", OUT / "default.png")
    for g in GAMES:
        f = ROOT / f"static/img/{g['slug']}-hero.webp"
        bg = Image.open(f) if f.exists() else None
        render(bg, f"Is it safe to update {g['name']}?", "Live mod framework status after every patch", OUT / f"{g['slug']}.png")
    deck = ROOT / "static/img/steam-deck-hero.webp"
    render(Image.open(deck) if deck.exists() else None, "Stop Steam auto-updating your game",
           "What still works in 2026: settings, offline, rollbacks", OUT / "guide-stop-steam-auto-updates.png")
    sky = ROOT / "static/img/fallout-4-hero.webp"
    render(Image.open(sky) if sky.exists() else None, "Modding guides",
           "Hold updates, roll back patches, install mods", OUT / "guides.png")


if __name__ == "__main__":
    main()
