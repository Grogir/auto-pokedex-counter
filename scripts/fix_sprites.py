from pathlib import Path

import cv2
import numpy as np

from pokedex_counter.vision.image_io import load_unchanged

ROOT = Path(__file__).resolve().parent.parent
PATH = ROOT / "src" / "pokedex_counter" / "resources" / "sprites_1"
# PATH = ROOT / "tests" / "fixtures" / "detection"
input_folder = PATH
output_folder = PATH / "out"
def main(): for_each_image(remove_all_transparent_border)


def measure(path: Path, image: np.array) -> None:
    height, width = image.shape[:2]
    if height > 41:
        print(f"Too tall : {path} ({width}x{height})")
    elif width > 47:
        print(f"Too wide : {path} ({width}x{height})")


def crop_border(path: Path, image: np.array):
    return image[1:-1, 1:-1]


def check_transparent_border(path: Path, image: np.array):
    if image.ndim < 3 or image.shape[2] < 4:
        print(path.stem, "invalid")
        return
    alpha = image[:, :, 3]
    count = (
        np.count_nonzero(alpha[0, :])
        + np.count_nonzero(alpha[-1, :])
        + np.count_nonzero(alpha[1:-1, 0])
        + np.count_nonzero(alpha[1:-1, -1])
    )
    if count > 0:
        print(path.name, count)
        # return image[2:, 1:-1]
    else:
        return image[1:-1, 1:-1]


def remove_all_transparent_border(path, image):
    if image.ndim < 3 or image.shape[2] < 4:
        print(path.stem, "invalid")
        return
    while np.all(image[0, :, 3] == 0):
        image = image[1:, :]
    while np.all(image[-1, :, 3] == 0):
        image = image[:-1, :]
    while np.all(image[:, 0, 3] == 0):
        image = image[:, 1:]
    while np.all(image[:, -1, 3] == 0):
        image = image[:, :-1]
    return image


def flip_template(path: Path, image: np.array):
    fixed = cv2.flip(image, 1)
    if fixed.shape[1] > 100: fixed = cv2.resize(fixed, (62, 22))
    return fixed


def for_each_image(func) -> None:
    for path in input_folder.glob("*.png"):
        image = load_unchanged(path)
        if image is None:
            print(f"Impossible to load : {path}")
            continue
        height, width = image.shape[:2]
        if height < 3 or width < 3:
            print(f"Too small : {path}")
            continue


        fixed = func(path, image)


        if fixed is not None:
            if fixed is image:
                print(f"{path.name}: no change")
            success, encoded = cv2.imencode(".png", fixed)
            if not success:
                print(f"Impossible to encode : {path}")
                continue
            output_folder.mkdir(parents=True, exist_ok=True)
            output_path = output_folder / path.name
            encoded.tofile(output_path)
            print(
                f"{path.name}: "
                f"{width}x{height} -> "
                f"{fixed.shape[1]}x{fixed.shape[0]}"
            )


if __name__ == "__main__":
    main()
