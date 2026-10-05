"""Build images/pipeline/blending.gif: two overlapping pieces of the same scene
slide together and merge into one seamless image (pipeline step 5).

Input: images/houses/baku_houses_2025.png. Requires Pillow. Run from anywhere:
    python3 images/make_blending_gif.py
"""
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "images" / "houses" / "baku_houses_2025.png"
OUT = ROOT / "images" / "pipeline" / "blending.gif"

BG = (255, 255, 255)
C_A, C_B, C_ONE = (76, 123, 244), (240, 138, 36), (27, 44, 79)
W, H = 520, 260           # merged image
PIECE = 310               # width of each piece; they share 2 * PIECE - W px
PAD, GAP = 14, 16
CW, CH = 2 * PIECE + GAP + 2 * PAD, H + 2 * PAD
TINT, LINE = 0.22, 4
DT, SLIDE, MERGE = 80, 1200, 1000          # frame step, slide in, merge (ms)
HOLD_APART, HOLD_OVER, HOLD_ONE = 1000, 900, 2800


def scene():
    im = Image.open(SRC).convert("RGB")
    w, h = im.size
    cw = h * W // H
    return im.crop(((w - cw) // 2, 0, (w + cw) // 2, h)).resize((W, H), Image.LANCZOS)


def piece(im, colour, tint):
    return Image.blend(im, Image.new("RGB", im.size, colour), TINT * tint)


def frame(a, b, slide, merge):
    """slide: 0 apart -> 1 in place; merge: 0 two pieces -> 1 one image."""
    x0 = (CW - W) // 2
    ax = round(PAD + (x0 - PAD) * slide)
    bx = round(CW - PAD - PIECE + (x0 + W - PIECE - (CW - PAD - PIECE)) * slide)
    tint = 1 - merge
    out = Image.new("RGB", (CW, CH), BG)
    out.paste(piece(a, C_A, tint), (ax, PAD))
    pb = piece(b, C_B, tint)
    mask = Image.new("L", pb.size, 255)
    over = ax + PIECE - bx
    if over > 0:  # where the pieces overlap, both show through equally
        mask.paste(128, (0, 0, over, H))
    out.paste(pb, (bx, PAD), mask)

    lines = Image.new("RGBA", out.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lines)
    alpha = round(255 * tint)
    for x, c in ((ax, C_A), (bx, C_B)):
        d.rectangle((x, PAD, x + PIECE - 1, PAD + H - 1), outline=c + (alpha,), width=LINE)
    out = Image.alpha_composite(out.convert("RGBA"), lines)
    one = Image.new("RGBA", out.size, (0, 0, 0, 0))
    ImageDraw.Draw(one).rectangle((x0, PAD, x0 + W - 1, PAD + H - 1), outline=C_ONE + (255 - alpha,), width=LINE)
    return Image.alpha_composite(out, one).convert("RGB")


def main():
    im = scene()
    a, b = im.crop((0, 0, PIECE, H)), im.crop((W - PIECE, 0, W, H))
    ease = lambda t: t * t * (3 - 2 * t)
    frames, durations = [frame(a, b, 0, 0)], [HOLD_APART]
    for i in range(1, SLIDE // DT + 1):
        frames.append(frame(a, b, ease(i / (SLIDE // DT)), 0)); durations.append(DT)
    durations[-1] = HOLD_OVER
    for i in range(1, MERGE // DT + 1):
        frames.append(frame(a, b, 1, ease(i / (MERGE // DT)))); durations.append(DT)
    durations[-1] = HOLD_ONE

    # one shared palette, taken from the tinted and the final frame
    ref = Image.new("RGB", (CW, CH * 2))
    ref.paste(frames[0], (0, 0)); ref.paste(frames[-1], (0, CH))
    pal = ref.quantize(256, method=Image.Quantize.MEDIANCUT)
    frames = [f.quantize(palette=pal, dither=Image.Dither.NONE) for f in frames]
    frames[0].save(OUT, save_all=True, append_images=frames[1:], duration=durations, loop=0, optimize=False)
    print(OUT, f"{OUT.stat().st_size / 1e6:.2f} MB", len(frames), "frames", (CW, CH))


if __name__ == "__main__":
    main()
