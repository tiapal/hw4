"""Make product photos with a black background (or black side bars) use a white background instead.

Reads every photo in data/products/ and writes the result to data/products_white/. The originals are
never changed. The API serves data/products_white/ when it exists.

How it works, per photo:
  1. "Background black" is pure black: the brightest colour channel is at most BG_BLACK. These photos'
     backgrounds are exactly 0, while even the darkest navy garment stays above about 35, so a very low
     cutoff keeps dark garments from being mistaken for background.
  2. A dark region counts as background if it touches the photo's edge, OR if it holds a solid patch of
     exact zero (the real background is exactly 0, which black ink or a shadow in a garment never is).
     The second rule catches the gaps between an arm and the body. Black or navy parts of a garment
     (a logo, a drawstring) are left alone.
  3. Tiny specks (JPEG noise floating in the background, under SPECK_PIXELS pixels, not joined to the
     garment) are counted as background too. Background pixels become pure white.
  4. The thin ring of edge pixels that are a blend of garment and black are un-blended
     (new = pixel + (1 - alpha) * 255), so there is no dark outline around the garment.
  5. A photo is only changed if a real share of its border is black. White photos are copied as they are.

Run from the HW 4 folder (needs: pip install pillow numpy scipy):
    backend/.venv/bin/python scripts/whiten_product_photos.py
"""

import shutil
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

DATA = Path(__file__).resolve().parent.parent / "data"
SRC, DST = DATA / "products", DATA / "products_white"

BG_BLACK = 8  # a pixel is background black if its brightest channel is at or below this
BG_CORE = 2  # an enclosed region is background only if it holds at least POCKET_CORE_PIXELS pixels this dark
POCKET_CORE_PIXELS = 40
BORDER_DARK = 48  # only used to decide whether a photo has a black border at all
BLACK_BORDER_SHARE = 0.15  # change a photo only if at least this share of its border is that dark
RING = 2.5  # px: the blended edge band next to the background
SPECK_PIXELS = 80  # a loose speck smaller than this, cut off from the garment, is noise, not part of the product
MAX_BG_SHARE = 0.92  # if more than this much of the photo would turn white, something is wrong: leave it


def border_dark_share(brightest: np.ndarray) -> float:
    ring = np.concatenate([brightest[:4].ravel(), brightest[-4:].ravel(), brightest[:, :4].ravel(), brightest[:, -4:].ravel()])
    return float((ring <= BORDER_DARK).mean())


def whiten(rgb: np.ndarray) -> tuple[np.ndarray | None, float]:
    """Return (new image, share of pixels made white), or (None, share) if the photo shouldn't be changed."""
    brightest = rgb.max(axis=2).astype(float)
    if border_dark_share(brightest) < BLACK_BORDER_SHARE:
        return None, 0.0

    dark = brightest <= BG_BLACK
    labels, _ = ndimage.label(dark, structure=np.ones((3, 3)))  # 8-connected dark regions
    edge_labels = np.unique(np.concatenate([labels[0], labels[-1], labels[:, 0], labels[:, -1]]))
    edge_labels = edge_labels[edge_labels != 0]
    core_counts = np.bincount(labels[brightest <= BG_CORE], minlength=labels.max() + 1)
    pocket_labels = np.flatnonzero(core_counts >= POCKET_CORE_PIXELS)
    pocket_labels = pocket_labels[pocket_labels != 0]
    background = np.isin(labels, np.union1d(edge_labels, pocket_labels))  # touches the edge, or is solid true black
    pieces, count = ndimage.label(~background, structure=np.ones((3, 3)))
    sizes = np.bincount(pieces.ravel(), minlength=count + 1)
    background |= (sizes[pieces] < SPECK_PIXELS) & (pieces > 0)  # remove loose specks
    share = float(background.mean())
    if share > MAX_BG_SHARE:
        return None, share

    # Edge pixels are garment blended with black: pixel = a * colour. Estimate a from the nearby garment.
    distance = ndimage.distance_transform_edt(~background)
    edge_band = ~background & (distance <= RING)
    interior = ~background & (distance > RING)
    local_max = ndimage.maximum_filter(np.where(interior, brightest, 0.0), size=9)
    alpha = np.clip(brightest / np.maximum(np.maximum(local_max, brightest), 1.0), 0.0, 1.0)
    alpha = np.where(local_max > 0, alpha, 1.0)

    out = rgb.astype(float)
    out[edge_band] = out[edge_band] + (1.0 - alpha[edge_band])[:, None] * 255.0
    out[background] = 255.0
    return np.clip(out, 0, 255).astype(np.uint8), share


def main() -> None:
    DST.mkdir(exist_ok=True)
    changed, copied, skipped = [], [], []
    for src in sorted(SRC.glob("*.jpg")):
        rgb = np.asarray(Image.open(src).convert("RGB"))
        result, share = whiten(rgb)
        if result is None:
            shutil.copyfile(src, DST / src.name)
            (skipped if share > 0 else copied).append((src.name, share))
        else:
            Image.fromarray(result).save(DST / src.name, quality=95, subsampling=0)
            changed.append((src.name, share))
    print(f"{len(changed)} photos changed to a white background")
    print(f"{len(copied)} photos already had a light background (copied as is)")
    if skipped:
        print(f"{len(skipped)} photos left alone because too much would have turned white:")
        for name, share in skipped:
            print(f"   {name}  ({share:.0%})")
    print("share of each changed photo turned white: min %.0f%%, max %.0f%%" % (100 * min(s for _, s in changed), 100 * max(s for _, s in changed)))


if __name__ == "__main__":
    sys.exit(main())
