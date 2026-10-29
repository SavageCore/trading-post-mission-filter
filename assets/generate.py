#!/usr/bin/env python3
"""Regenerate the Nexus page images from the source screenshot.

  assets/gallery-1920x1080.jpg  (all-delivery board, gallery slot)
  assets/header-1300x372.jpg     (wide crop + title overlay, banner)

The source is an in-game shot of the trading post board with every
slot offering a package delivery run: the terminal on the left, the
delivery contracts on the right. Two framings come out of it:

  gallery  the whole frame, fitted to 16:9 over a blurred fill of
           itself, showing the full all-delivery board, which is
           the point of the mod.
  header   a band cropped off the top at full source width, so the
           terminal and the first deliveries stay in frame and the
           title has the empty dark backdrop top-left to sit on.

The source screenshot is the author's own; no attribution file needed.

Usage: python3 assets/generate.py   (or: make assets)
Requires: Pillow (pip install Pillow). Typeface is vendored (see FONT).
"""

import os

from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "src", "gallery-trading-post.jpg")
GAL = os.path.join(HERE, "gallery-1920x1080.jpg")
HDR = os.path.join(HERE, "header-1300x372.jpg")

# In-game heading typeface, vendored (SIL OFL 1.1):
# https://github.com/NMSCD/No-Mans-Sky-Universal-Font
FONT = os.path.join(HERE, "fonts", "GeosansLight-NMS.ttf")

TITLE = ["TRADING POST MISSION FILTER"]
SUBTITLE = "PACKAGE DELIVERY \u2022 ASTEROID \u2022 SALVAGE \u2022 SLIME"

# Header crop, in source pixels: full source width so the terminal
# and the delivery list stay in frame. The band sits below the
# in-game gold banner so the overlaid title has no competing
# header text behind it; the dark gradient covers the terminal.
# The source is 2560x1440.
HDR_X = 0
HDR_Y = 550
HDR_W = 2560

# Header size in output pixels.
HDR_OUT_W = 1300
HDR_OUT_H = 372

# Title placement in the header. The title is long, so the small
# sizes: 42px caps white, 28px amber subtitle.
TITLE_X = 48
TITLE_Y = 48
TITLE_SIZE = 42
TITLE_GAP = 54
SUBTITLE_SIZE = 28

# Gallery size in output pixels.
GAL_W = 1920
GAL_H = 1080

AMBER = (255, 205, 130)


def text_shadowed(d, xy, s, font, fill):
    x, y = xy
    for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2), (-2, -2), (2, -2), (-2, 2), (2, 2)):
        d.text((x + dx, y + dy), s, font=font, fill=(0, 0, 0))
    d.text((x, y), s, font=font, fill=fill)


def load():
    return Image.open(SRC).convert("RGB")


def header():
    img = load()
    assert img.size[0] >= HDR_X + HDR_W, f"crop too wide for source: {img.size}"

    band_h = int(HDR_W * HDR_OUT_H / HDR_OUT_W)
    assert HDR_Y + band_h <= img.size[1], f"crop too tall for source: {img.size}"
    band = img.crop((HDR_X, HDR_Y, HDR_X + HDR_W, HDR_Y + band_h))
    band = band.resize((HDR_OUT_W, HDR_OUT_H), Image.LANCZOS)
    # Pull the whole band down a touch so white type reads over the
    # bright terminal, then the left-weighted gradient for the title.
    band = Image.blend(band, Image.new("RGB", band.size), 0.15)
    d = ImageDraw.Draw(band, "RGBA")
    for x in range(HDR_OUT_W):
        a = int(235 * max(0.0, 1 - x / (HDR_OUT_W * 0.78)) ** 1.3)
        d.rectangle([x, 0, x + 1, HDR_OUT_H], fill=(0, 0, 0, a))
    band = band.convert("RGB")
    d = ImageDraw.Draw(band)
    fb = ImageFont.truetype(FONT, TITLE_SIZE)
    fs = ImageFont.truetype(FONT, SUBTITLE_SIZE)

    for i, line in enumerate(TITLE):
        text_shadowed(d, (TITLE_X, TITLE_Y + i * TITLE_GAP), line, fb, (255, 255, 255))
    text_shadowed(
        d,
        (TITLE_X + 2, TITLE_Y + len(TITLE) * TITLE_GAP + 8),
        SUBTITLE,
        fs,
        AMBER,
    )
    band.save(HDR, quality=92)
    print(f"wrote {HDR}")


def gallery():
    src = load()
    # blurred fill: cover the frame, blur it, darken it, so the fitted
    # frame below lands on its own backdrop instead of a hard edge
    scale = max(GAL_W / src.width, GAL_H / src.height)
    bg = src.resize(
        (round(src.width * scale), round(src.height * scale)), Image.LANCZOS
    )
    left = (bg.width - GAL_W) // 2
    top = (bg.height - GAL_H) // 2
    bg = bg.crop((left, top, left + GAL_W, top + GAL_H))
    bg = bg.filter(ImageFilter.GaussianBlur(40))
    bg = Image.blend(bg, Image.new("RGB", bg.size), 0.45)
    # fitted frame: full width, so the whole board stays in frame.
    # Pasted through a mask feathered top and bottom so no hard edge
    # shows where the frame meets its blurred fill.
    fg_w = GAL_W
    fg_h = round(src.height * GAL_W / src.width)
    fg = src.resize((fg_w, fg_h), Image.LANCZOS)
    top = (GAL_H - fg_h) // 2
    layer = Image.new("RGB", (GAL_W, GAL_H))
    layer.paste(fg, (0, top))
    feather = 30
    mask_img = Image.new("L", (GAL_W, GAL_H))
    mask = ImageDraw.Draw(mask_img)
    mask.rectangle([0, top, GAL_W, top + fg_h], fill=255)
    for i in range(feather):
        a = int(255 * (i + 1) / (feather + 1))
        mask.line([(0, top + i), (GAL_W, top + i)], fill=a)
        mask.line([(0, top + fg_h - 1 - i), (GAL_W, top + fg_h - 1 - i)], fill=a)
    bg.paste(layer, (0, 0), mask_img)
    bg.save(GAL, quality=92)
    print(f"wrote {GAL}")


if __name__ == "__main__":
    header()
    gallery()
