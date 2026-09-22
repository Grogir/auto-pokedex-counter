import cv2
import numpy as np

from pokedex_counter.vision.template_matching import canonicalize_shades
from pokedex_counter.vision.template_matching import find_best_match


def _render(shade_grid, levels):
    levels_arr = np.array(levels, dtype=np.uint8)
    return levels_arr[shade_grid]


# A small grid using all 4 shade indices with a real spatial pattern, sized
# generously enough that k-means reliably finds 4 separated clusters.
_SHADE_GRID = np.array(
    [
        [0, 0, 1, 1, 2, 2, 3, 3],
        [0, 0, 1, 1, 2, 2, 3, 3],
        [1, 1, 2, 2, 3, 3, 0, 0],
        [1, 1, 2, 2, 3, 3, 0, 0],
    ],
    dtype=np.int64,
)


def test_identical_output_across_two_non_inverted_palettes():
    a = _render(_SHADE_GRID, (0, 85, 170, 255))
    b = _render(_SHADE_GRID, (10, 60, 200, 250))  # different palette, same relative order

    canon_a = canonicalize_shades(a)
    canon_b = canonicalize_shades(b)

    assert canon_a is not None
    assert canon_b is not None
    np.testing.assert_array_equal(canon_a, canon_b)


def test_inverted_palette_produces_bitwise_complement():
    normal = _render(_SHADE_GRID, (0, 85, 170, 255))
    inverted = _render(_SHADE_GRID, (255, 170, 85, 0))  # Negative-style: order reversed

    canon_normal = canonicalize_shades(normal)
    canon_inverted = canonicalize_shades(inverted)

    assert canon_normal is not None
    assert canon_inverted is not None
    np.testing.assert_array_equal(canon_inverted, 255 - canon_normal)


def test_returns_none_on_flat_input():
    flat = np.full((20, 20), 128, dtype=np.uint8)
    assert canonicalize_shades(flat) is None


def test_returns_none_on_near_flat_noisy_input():
    rng = np.random.RandomState(0)
    near_flat = (128 + rng.randint(-3, 4, size=(20, 20))).astype(np.uint8)
    assert canonicalize_shades(near_flat) is None


def test_output_dtype_and_levels():
    img = _render(_SHADE_GRID, (0, 85, 170, 255))
    canon = canonicalize_shades(img)

    assert canon is not None
    assert canon.dtype == np.uint8
    assert set(np.unique(canon).tolist()) <= {0, 85, 170, 255}


def test_degenerate_input_with_fewer_than_k_distinct_values_returns_none():
    two_shade_grid = np.array([[0, 0, 1, 1]] * 4, dtype=np.int64)
    img = _render(two_shade_grid, (0, 85, 170, 255))  # only 2 of the 4 levels actually appear

    assert canonicalize_shades(img) is None


def test_find_best_match_refines_to_exact_pixel_height():
    rng = np.random.RandomState(7)
    template = rng.randint(0, 256, size=(20, 16), dtype=np.uint8)
    target_height = 73
    target_width = round(template.shape[1] * target_height / template.shape[0])
    rendered = cv2.resize(template, (target_width, target_height), interpolation=cv2.INTER_LINEAR)
    frame = rng.randint(0, 256, size=(200, 240), dtype=np.uint8)
    frame[61:61 + target_height, 83:83 + target_width] = rendered

    _, box = find_best_match(frame, template, np.array([0.1, 1.0]))

    assert box == (83, 61, target_width, target_height)
