from pathlib import Path
import cv2

from pokedex_counter.vision.image_io import load_color

ROOT = Path(__file__).resolve().parent.parent
# PATH = ROOT / "src" / "pokedex_counter" / "resources" / "sprites_background"
PATH = ROOT / "tests" / "fixtures" / "detection"
input_folder = Path(PATH)
output_folder = Path(PATH / "out")

def measure() -> None:
    for path in input_folder.glob("*.png"):
        image = load_color(path)
        height, width = image.shape[:2]
        if height > 41:
            print(f"Too tall : {path} ({width}x{height})")
        elif width > 47:
            print(f"Too wide : {path} ({width}x{height})")

def main() -> None:
    for path in input_folder.glob("*.png"):
        image = load_color(path)
        if image is None:
            print(f"Impossible to load : {path}")
            continue
        height, width = image.shape[:2]
        if height < 3 or width < 3:
            print(f"Too small : {path}")
            continue


        # fixed = image[1:-1, 1:-1]
        fixed = cv2.flip(image, 1)
        # if fixed.shape[1] > 100: fixed = cv2.resize(fixed, (62, 22))


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
