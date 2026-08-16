#!/usr/bin/env python3
"""Generate assets/social-preview.png, the card GitHub shows when the repository
is shared on social media, in Slack, or in a chat that unfurls links.

GitHub asks for a 1280x640 image and crops nothing. Upload the result under
Settings -> General -> Social preview.

That upload is manual -- GitHub exposes no API for it -- so the card says
nothing that goes out of date. It names what the directory covers rather than
how many entries it holds, and the live count stays where it can be regenerated:
the README badge. Pass --with-counts if you want a milestone card instead, and
remember it is a snapshot from the day you made it.

    python3 -m pip install pillow pyyaml
    python3 scripts/social_preview.py
"""

from __future__ import annotations

import os
import sys

try:
    import yaml
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("This tool needs Pillow and PyYAML: python3 -m pip install pillow pyyaml",
          file=sys.stderr)
    raise SystemExit(2)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "social-preview.png")

WIDTH, HEIGHT = 1280, 640
BACKGROUND = "#0d1117"        # GitHub's dark canvas, so the card sits on the page
TEXT = "#e6edf3"
MUTED = "#8b949e"
ACCENT = "#1f6feb"

# The flag of Yemen: red, white, black.
STRIPES = ("#ce1126", "#ffffff", "#000000")

FONTS = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
)


def font(path: str, size: int):
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


def main() -> int:
    with open(os.path.join(ROOT, "data", "projects.yml"), encoding="utf-8") as handle:
        projects = yaml.safe_load(handle) or []
    with open(os.path.join(ROOT, "data", "categories.yml"), encoding="utf-8") as handle:
        categories = yaml.safe_load(handle) or []

    bold, regular = FONTS
    image = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
    draw = ImageDraw.Draw(image)

    # A flag-coloured band down the left edge.
    band, height = 18, HEIGHT // 3
    for i, colour in enumerate(STRIPES):
        draw.rectangle([0, i * height, band, (i + 1) * height], fill=colour)

    # The flag itself, level with the numbers so it never collides with the
    # title, with a hairline so its black stripe reads against the dark canvas.
    flag_path = os.path.join(ROOT, "assets", "flag-of-yemen.png")
    if os.path.exists(flag_path):
        flag_x, flag_y = WIDTH - 240 - 96, 372
        flag = Image.open(flag_path).convert("RGB").resize((240, 160), Image.LANCZOS)
        image.paste(flag, (flag_x, flag_y))
        draw.rectangle([flag_x, flag_y, flag_x + 240, flag_y + 160],
                       outline="#30363d", width=2)

    left = 96
    draw.text((left, 132), "Yemeni Open Source", font=font(bold, 82), fill=TEXT)
    draw.text((left, 246), "A curated directory of open-source projects",
              font=font(regular, 38), fill=MUTED)
    draw.text((left, 296), "built by Yemeni developers", font=font(regular, 38), fill=MUTED)

    if "--with-counts" in sys.argv:
        # A milestone card: accurate the day it is made, and a snapshot after.
        stats = ((f"{len(projects)}", "projects"), (f"{len(categories)}", "categories"),
                 (f"{sum(1 for p in projects if p.get('featured'))}", "featured"))
        x = left
        for value, label in stats:
            draw.text((x, 396), value, font=font(bold, 64), fill=ACCENT)
            draw.text((x, 470), label.upper(), font=font(regular, 26), fill=MUTED)
            x += max(draw.textlength(value, font=font(bold, 64)),
                     draw.textlength(label.upper(), font=font(regular, 26))) + 88
    else:
        # What the directory covers, which does not go stale between uploads.
        # Short labels so the row of chips always fits above the footer rule.
        SHORT = {"ai-ml": "AI & ML", "web": "Web", "mobile": "Mobile",
                 "payments": "Payments", "arabic": "Arabic & RTL",
                 "devtools": "Dev Tools"}
        chips = [SHORT.get(c["slug"], c["title"]) for c in categories
                 if c["slug"] in SHORT]
        x, y = left, 404
        chip_font = font(regular, 27)
        for label in chips:
            width = draw.textlength(label, font=chip_font) + 44
            if x + width > WIDTH - 384:          # keep clear of the flag
                x, y = left, y + 62
            draw.rounded_rectangle([x, y, x + width, y + 50], radius=25,
                                   fill="#161b22", outline="#30363d", width=2)
            draw.text((x + 22, y + 11), label, font=chip_font, fill=TEXT)
            x += width + 16

    draw.line([(left, 552), (WIDTH - left, 552)], fill="#21262d", width=2)
    draw.text((left, 578), "Yemen Tech Collective · yementc.org",
              font=font(regular, 28), fill=MUTED)

    image.save(OUT, "PNG", optimize=True)
    print(f"Wrote {os.path.relpath(OUT, ROOT)} ({WIDTH}x{HEIGHT}, "
          f"{os.path.getsize(OUT) // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
