from __future__ import annotations

import cv2
import numpy as np

# Minimum gap (0-255 grayscale units) required between adjacent k-means
# shade-cluster centers for canonicalize_shades() to trust the clustering.
# Below this, treat the crop as having no reliable 4-shade structure
# (blank/transition frame) rather than rank-remapping noise into a
# fabricated full-contrast pattern.
MIN_SHADE_SEPARATION = 15.0

_COARSE_SAMPLES = 40
_MIN_FRAME_HEIGHT_RATIO = 0.1
_COARSE_FRAME_DIVISOR = 2
_KMEANS_CRITERIA = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)


def canonicalize_shades(gray: np.ndarray, k: int = 4, min_separation: float = MIN_SHADE_SEPARATION) -> np.ndarray | None:
    """Remap `gray` to one of `k` fixed evenly-spaced levels (0/85/170/255
    for k=4) by each pixel's cluster's brightness *rank*, not its absolute
    value. A Game Boy screen always has k=4 underlying shade classes, but
    each of the GBC's 13 hardware color palettes assigns different actual
    luminance to each - rank-based remapping makes two renders of the same
    underlying shade pattern produce an identical result regardless of the
    palette, as long as it preserves relative shade ordering (all of them
    do except "Negative", which reverses it). Since this only preserves
    *order* and discards absolute brightness, canonicalizing an inverted
    render produces the exact bitwise complement of the non-inverted
    result - callers recover Negative-style palettes by additionally
    matching against `255 - canonicalize_shades(...)`, with no need to
    know which palette is actually active.

    Returns None if the clustering isn't trustworthy - e.g. a blank or
    in-transition crop with no real 4-shade content would otherwise have
    its noise rank-remapped into a fabricated full-contrast pattern.
    """
    samples = gray.reshape(-1, 1).astype(np.float32)
    _, labels, centers = cv2.kmeans(samples, k, None, _KMEANS_CRITERIA, 3, cv2.KMEANS_PP_CENTERS)

    centers = centers.flatten()
    order = np.argsort(centers)
    if np.diff(centers[order]).min() < min_separation:
        return None

    rank_of_cluster = np.empty(k, dtype=np.int64)
    rank_of_cluster[order] = np.arange(k)
    canonical_levels = np.linspace(0, 255, k).astype(np.uint8)

    remapped = canonical_levels[rank_of_cluster[labels.flatten()]]
    return remapped.reshape(gray.shape)


def find_best_match(frame_gray: np.ndarray, template: np.ndarray):
    th, tw = template.shape[:2]
    fh, fw = frame_gray.shape[:2]

    min_height = max(8, int(np.ceil(fh * _MIN_FRAME_HEIGHT_RATIO)))
    max_height = min(fh, int(fw * th / tw))
    if min_height > max_height:
        return -1.0, None

    coarse_frame = cv2.resize(frame_gray, (fw // _COARSE_FRAME_DIVISOR, fh // _COARSE_FRAME_DIVISOR))
    coarse_heights = [
        int(height)
        for height in np.linspace(
            min_height, max_height, min(_COARSE_SAMPLES, max_height - min_height + 1)
        ).round()
    ]

    def score_at(height, target_frame=frame_gray):
        width = round(tw * height / th)
        if width < 8 or height < 8 or width > target_frame.shape[1] or height > target_frame.shape[0]:
            return None, None
        resized = cv2.resize(template, (width, height))
        result = cv2.matchTemplate(target_frame, resized, cv2.TM_CCOEFF_NORMED)
        _, score, _, max_loc = cv2.minMaxLoc(result)
        return score, (max_loc[0], max_loc[1], width, height)

    best_score = -1.0
    best_height = None

    for height in coarse_heights:
        score, _ = score_at(round(height / _COARSE_FRAME_DIVISOR), coarse_frame)
        if score is not None and score > best_score:
            best_score, best_height = score, height

    if best_height is None:
        return -1.0, None

    best_score = -1.0
    best_box = None
    coarse_step = (max_height - min_height) // _COARSE_SAMPLES
    lo = max(min_height, best_height - coarse_step)
    hi = min(max_height, best_height + coarse_step)

    for height in range(lo, hi + 1):
        score, box = score_at(height)
        if score is not None and score > best_score:
            best_score, best_box = score, box

    return best_score, best_box
