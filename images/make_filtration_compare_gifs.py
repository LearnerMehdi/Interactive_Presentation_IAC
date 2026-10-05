"""Build the refinement-comparison GIFs in animations/filtration/: one per pair of
refinement cases, each flipping between the two warped mosaics of the same area.

  none_vs_ransac.gif   : no refinement vs RANSAC
  none_vs_median.gif   : no refinement vs median filtration
  ransac_vs_median.gif : RANSAC        vs median filtration

Inputs (all in filtration/): crop_none.tif, crop_ransac.tif, crop_median.tif.
Requires Pillow. Run from anywhere:
    python3 images/make_filtration_compare_gifs.py
"""
from pathlib import Path

from PIL import Image, ImageDraw

from make_houses_stacked_pair_gif import BG, FG, PAD, font, to_gif

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "filtration"
OUT = ROOT / "animations" / "filtration"

# key: (file, caption)
CASES = {
    "none": ("crop_none.tif", "No refinement"),
    "ransac": ("crop_ransac.tif", "RANSAC"),
    "median": ("crop_median.tif", "Median filtration (k = 7)"),
}
PAIRS = [("none", "ransac"), ("none", "median"), ("ransac", "median")]
TOP = 92
HOLD_MS = 1500


def main():
    shots = {key: (Image.open(SRC / name).convert("RGB"), caption) for key, (name, caption) in CASES.items()}
    f_h, f_t = font(26), font(22)
    OUT.mkdir(parents=True, exist_ok=True)
    for a, b in PAIRS:
        w, h = shots[a][0].size
        cw, ch = PAD * 2 + w, TOP + h + PAD
        title = f"{shots[a][1]} vs {shots[b][1]}"

        def frame(key):
            img, caption = shots[key]
            im = Image.new("RGB", (cw, ch), BG)
            d = ImageDraw.Draw(im)
            im.paste(img, (PAD, TOP))
            d.text((PAD + w / 2, 14), title, font=f_h, anchor="ma", fill=FG)
            d.text((PAD, 56), caption, font=f_t, fill=FG)
            return im

        q = to_gif([frame(a), frame(b)], [(PAD, TOP, PAD + w, TOP + h)], (FG, BG))
        out = OUT / f"{a}_vs_{b}.gif"
        q[0].save(out, save_all=True, append_images=q[1:], duration=HOLD_MS, loop=0, transparency=255, disposal=2)
        print(f"Wrote {out.relative_to(ROOT)} ({cw}x{ch}, {len(q)} frames, {out.stat().st_size / 1e6:.2f} MB)")


if __name__ == "__main__":
    main()
