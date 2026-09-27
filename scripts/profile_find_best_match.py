import cProfile
import io
import pstats
from contextlib import redirect_stdout
from pathlib import Path

from pokedex_counter.config import CALIBRATION_DIR, CALIBRATION_FILENAMES
from pokedex_counter.vision.image_io import load_gray
from pokedex_counter.vision.template_matching import find_best_match

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = CALIBRATION_DIR / CALIBRATION_FILENAMES["GAME_AREA"]
FRAME_PATH = ROOT / "tests" / "fixtures" / "calibration" / "calibration_03.png"
ITERATIONS = 1


def main() -> None:
    template = load_gray(TEMPLATE_PATH)
    frame = load_gray(FRAME_PATH)

    def run() -> None:
        for _ in range(ITERATIONS):
            find_best_match(frame, template)

    profiler = cProfile.Profile()
    with redirect_stdout(io.StringIO()):
        profiler.runcall(run)

    score, box = find_best_match(frame, template)
    print(f"template: {TEMPLATE_PATH} ({template.shape[1]}x{template.shape[0]})")
    print(f"frame:    {FRAME_PATH} ({frame.shape[1]}x{frame.shape[0]})")
    print(f"result:   score={score:.4f}, box={box}")
    print(f"profile:  {ITERATIONS} iterations")
    pstats.Stats(profiler).strip_dirs().sort_stats("cumulative").print_stats(15)


if __name__ == "__main__":
    main()
