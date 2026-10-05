"""Co-register the synthetically shifted pairs of make_anaglyphs.py (forest, water).

For each dataset the two rasters are put on their shared grid exactly as in
make_anaglyphs.py, one of them translated by the same `shift`. That pair - the
untouched image as reference, the shifted one as source - carries no
georeference, so the Coregistration pipeline has to find the shift from the
image content alone. Per dataset folder this writes, as PNG and - cropped to
the area that has data both before and after co-registration - as JPG for
index.html:

  <name>_pair_<ref label>                  : reference
  <name>_pair_<shifted label>_shifted      : source (shifted)
  <name>_pair_<shifted label>_coregistered : pipeline output
  <name>_pair_anaglyph_coregistered.png    : the co-registered pair, coloured as in make_anaglyphs.py

A pair smaller than one detection tile (forest) is enlarged by a whole factor
for the pipeline, and its output reduced back.

Run with the pipeline's environment:
    Coregistration/.venv/bin/python images/coregister_shifted_pairs.py
"""
import math
import os
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageChops, ImageStat

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "Coregistration")]

from make_anaglyphs import DATASETS, extent, info, rgb_on_grid  # noqa: E402
from configs import CROP_HEIGHT, CROP_WIDTH  # noqa: E402
from pycore.pipeline import CoregistrationPipeline  # noqa: E402

JPG_QUALITY = 92
CROP_MARGIN = 8  # px trimmed beyond the shift, for the interpolated edge of the gaps


def save(img, stem, shift):
    img.save(stem.with_suffix(".png"))
    mx, my = (abs(v) + CROP_MARGIN for v in shift)
    img.crop((mx, my, img.width - mx, img.height - my)).save(stem.with_suffix(".jpg"), quality=JPG_QUALITY)
    return stem.with_suffix(".png")


def mean_diff(a, b):
    return ImageStat.Stat(ImageChops.difference(a.convert("L"), b.convert("L"))).mean[0]


def build_pair(name, red, cyan, shifted, shift):
    """Write the reference and the shifted source on the shared grid."""
    folder = HERE / name
    paths = {label: folder / fname for label, fname in (red, cyan)}
    ref_label = next(label for label in paths if label != shifted)

    a, b = (extent(info(p)) for p in paths.values())
    te = (max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3]))
    gt = info(paths[red[0]])["geoTransform"]
    size = (round((te[2] - te[0]) / gt[1]), round((te[3] - te[1]) / -gt[5]))

    with tempfile.TemporaryDirectory() as tmp:
        ref = rgb_on_grid(paths[ref_label], te, size, Path(tmp))
        src = rgb_on_grid(paths[shifted], te, size, Path(tmp), shift)
    for aux in folder.glob("*.tif.aux.xml"):  # stats sidecars left by gdalinfo -stats
        aux.unlink()
    return (save(ref, folder / f"{name}_pair_{ref_label}", shift),
            save(src, folder / f"{name}_pair_{shifted}_shifted", shift))


def main():
    os.chdir(HERE.parent / "Coregistration")  # the matcher loads its config relative to it
    pipeline = CoregistrationPipeline().load()
    for d in DATASETS:
        name, shifted = d["name"], d["shifted"]
        ref_png, src_png = build_pair(**d)
        ref, src = Image.open(ref_png), Image.open(src_png)

        # the pipeline needs at least one full detection tile
        k = max(1, math.ceil(CROP_WIDTH / ref.width), math.ceil(CROP_HEIGHT / ref.height))
        with tempfile.TemporaryDirectory() as tmp:
            inputs = [ref_png, src_png]
            if k > 1:
                inputs = [Path(tmp) / p.name for p in inputs]
                for img, p in zip((ref, src), inputs):
                    img.resize((img.width * k, img.height * k), Image.BICUBIC).save(p)
            result = pipeline.run(*map(str, inputs))
        out = Image.open(result["output_path"]).convert("RGB").resize(ref.size, Image.BOX)
        save(out, HERE / name / f"{name}_pair_{shifted}_coregistered", d["shift"])
        r, c = (out if d["red"][0] == shifted else ref).convert("L"), (ref if d["red"][0] == shifted else out).convert("L")
        Image.merge("RGB", (r, c, c)).save(HERE / name / f"{name}_pair_anaglyph_coregistered.png")
        print(f"{name}: {ref.size[0]}x{ref.size[1]} px  shift (right, down) = {d['shift']}  "
              f"pipeline scale = x{k}  "
              f"mode = {result['mode']}  keypoints = {result['n_keypoints']}\n"
              f"  mean |reference - source| = {mean_diff(ref, src):.1f}/255 shifted, "
              f"{mean_diff(ref, out):.1f}/255 co-registered\n"
              f"  timings (s): { {k: round(v, 1) for k, v in result['timings'].items()} }")


if __name__ == "__main__":
    main()
