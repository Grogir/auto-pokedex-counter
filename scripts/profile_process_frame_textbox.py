import cProfile
import io
import pstats
from contextlib import redirect_stdout
from pathlib import Path

from pokedex_counter.services.detection_service import DetectionService
from pokedex_counter.vision.image_io import load_color

FIXTURE_NOTEXT = Path(__file__).parent.parent / "tests" / "fixtures" / "calibration" / "calibration_03.png"
FIXTURE = Path(__file__).parent.parent / "tests" / "fixtures" / "detection" / "text_03.png"


def main() -> None:
    fixture = FIXTURE
    frame = load_color(fixture)
    if frame is None:
        raise RuntimeError(f"Could not load {fixture}")

    detector = DetectionService([])

    def run() -> None:
        for _ in range(100):
            detector.process_frame_textbox(frame)

    profiler = cProfile.Profile()
    with redirect_stdout(io.StringIO()):
        profiler.runcall(run)
    pstats.Stats(profiler).strip_dirs().sort_stats("cumulative").print_stats(25)


if __name__ == "__main__":
    main()
