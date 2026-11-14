"""Tray icon drawing (no image assets needed)."""
from PIL import Image, ImageDraw, ImageFont

from . import protocol as P

COLORS = {
    P.MODE_OFFICE: (64, 160, 255),
    P.MODE_GAMING: (60, 200, 120),
    P.MODE_TURBO: (235, 64, 52),
    P.MODE_CUSTOM: (170, 70, 255),
}
LETTERS = {P.MODE_OFFICE: "S", P.MODE_GAMING: "E", P.MODE_TURBO: "O", P.MODE_CUSTOM: "P"}
GREY = (120, 120, 130)


def _font(size):
    for name in ("seguisb.ttf", "segoeuib.ttf", "arialbd.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def make_icon(mode, online: bool, boost: bool = False) -> Image.Image:
    color = COLORS.get(mode, GREY) if online else GREY
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((2, 2, 62, 62), fill=color + (255,))
    if boost and online:
        d.ellipse((2, 2, 62, 62), outline=(255, 255, 255, 255), width=4)
    # water drop
    d.polygon([(32, 10), (18, 34), (46, 34)], fill=(255, 255, 255, 235))
    d.ellipse((17, 24, 47, 54), fill=(255, 255, 255, 235))
    d.text((32, 40), LETTERS.get(mode, "?"), fill=color + (255,), font=_font(22), anchor="mm")
    return img
