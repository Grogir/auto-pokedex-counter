# Pokedex Counter

A small [PySide6](https://doc.qt.io/qtforpython-6/) overlay window for tracking your Pokédex progress live while streaming a Pokémon Red/Blue/Yellow playthrough from a Game Boy capture feed. It watches the video feed, recognizes catch, evolution and "give a nickname?" screens, and keeps a running count of the 151 Pokémon you've found — handy as an OBS window/source capture.

## Download (no Python required)

Grab the latest `PokedexCounter.exe` from the [Releases page](https://github.com/Sidosh/auto-pokedex-counter/releases) and run it. Windows only.

It looks for a device named **"OBS Virtual Camera"** and uses that automatically — so start the OBS Virtual Camera before launching the app. If it can't find one (e.g. it's not running yet, or you renamed it), it falls back to camera index 0.

### Calibration

Automatic detection needs a calibrated game area. If no calibration is available, the counter shows a prompt instead of a count. Calibration does not start automatically; use the **Calibrate** button in the settings window:

1. Start the OBS Virtual Camera and open the in-game title screen with Squirtle visible.
2. Click **Calibrate**. A preview opens while the app searches for the game area.
3. Once the area is found confidently and remains steady briefly, the calibration is saved for the next launch.

In a source run, calibration is written to `saved_calibration.py`; in the packaged executable, it is written next to the `.exe`. The calibrated area is applied to the current session, but these saved files are not reliably restored on the next launch yet. Press `Esc` to abort calibration; if no new area was locked, the existing calibration is kept. Selecting **No detection** disables automatic detection and does not require calibration.

## Using the app

The app opens four windows: the **counter**, **settings**, **Pokémon Boxes**, and **AFO Prediction**. Capture the counter window in OBS; use the settings window for controls, the boxes window to track the team and PC, and the AFO window for its time estimate and comparison.

### The counter window

All 151 sprites and the current count. Automatic detection can use text or sprite matching; choose the detection mode in settings. Catching a Pokémon highlights its sprite and bumps the count.

**Clicking a sprite marks or unmarks it by hand**, for when the detector misses a catch or flags one it shouldn't. Unmarking also lets that Pokémon be detected again later.

Right-clicking a sprite toggles **ignored** (gray).
An ignored Pokémon counts toward the current route section, but is not added to the global count or the boxes. Right-clicking it again removes the ignored state.
Press **Backspace** to mark enough missing required Pokémon to pass the current section, even when the app is not focused.

Until the game area has been calibrated, the count is replaced by a calibration prompt. This is only needed for automatic detection; select **No detection** to track catches manually without calibration.

### The settings window

| Control | What it does |
| --- | --- |
| Sprites per row | Grid width; the counter window resizes itself to fit |
| Sprite width / height | Sprite dimensions in the counter window |
| Sprite padding | Spacing around sprites in the counter and boxes windows |
| Box sprite width / height | Sprite dimensions in the boxes window |
| Counter font size | Size of the "N caught" text |
| Bottom margin | Extra space below the counter window content |
| Sprite set | Selects the sprite artwork set |
| Detection type | No detection, text detection, or sprite detection |
| Compare to | Selects a comparison route, or **None** |
| AFO comparison | Reference time used to show the AFO time difference |
| AFO modifier | Adjusts the AFO estimate by a percentage |
| Highlight bonuses | Highlights wild-caught bonus Pokémon (see below) |
| Remove title bar | Hides the counter window title bar |
| Reset counter | Clears the run and starts fresh |
| Calibrate | Re-runs calibration mid-session |

Settings are remembered between launches.

### Route and sprite colors

The section route is read from `resources/route/route.txt`.
By default, every required Pokémon must be obtained or ignored to complete a section. A route line can set a lower threshold with `MIN:n`; ignored Pokémon count toward that minimum.

The icons are colored as follows:

- **Black** — obtained normally, including by evolution.
- **Red** — a wild-caught bonus when **Highlight bonuses** is enabled.
- **Gray** — ignored with the right mouse button.

The current route section colors icons as follows:

- **Blue** — required to meet the current section's minimum.
- **Light pink** — an potential bonus for the current section.

The selected comparison adds bonus-route colors:

- **Red** — a wild-caught bonus that is not on the selected comparison.
- **Yellow** — a bonus on the selected comparison, but not caught yet.
- **Orange** — a wild-caught bonus that is also on the selected comparison.

Turning off **Highlight bonuses** removes the red/orange catch highlighting.

Comparison marks accumulate as the run progresses. Resetting the counter clears them so the next run earns them section by section. The list of bonus Pokémon is fixed.
Comparison JSON files in `resources/comparison/` are listed in the settings dropdown when they contain valid section-to-Pokémon data. A packaged build also scans the `comparison/` folder next to the executable, where a same-named file is shown as a separate selectable entry.

### Personal best

When a run reaches all 151, resetting the counter or closing the app asks whether to save it as your personal best. Saving records which Pokémon were caught in which section. A source run writes `src/pokedex_counter/resources/comparison/PB.json`; a packaged build writes `comparison/PB.json` next to the `.exe`. The comparison dropdown refreshes after the save.

## Setup (for development)

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## Run

```bash
python -m pokedex_counter
```

## Test

```bash
pytest
```

## Build a standalone executable

```bash
python scripts/build.py
```

This produces `dist/PokedexCounter.exe` (bundled with `resources/`) using PyInstaller. Pushing a `v*` tag also builds and attaches this exe to a GitHub Release automatically (see `.github/workflows/release.yml`).

## Project structure

```text
src/pokedex_counter/
  __main__.py                 Entry point (`python -m pokedex_counter`)
  app.py                      QApplication bootstrap and component wiring
  config.py                   App-wide constants and resource paths
  detection_config.py         Detection settings and calibration status
  game_config.py              Pokémon data, route sections, and bonuses
  game_controller.py          Tracks found/ignored Pokémon and route progress
  saved_calibration.py        Generated calibration file (source runs; gitignored)
  services/
    calibration_runner.py     Starts calibration and saves its result
    calibration_service.py    Finds the game area in camera frames
    camera_finder.py          Finds the OBS Virtual Camera device index
    capture_service.py        Camera capture thread
    comparison_service.py     Loads and validates comparison files
    detection_service.py      Per-frame text and sprite detection
    global_hotkey.py          Registers the global Backspace hotkey
    pb_service.py             Saves a completed run to PB.json
    roi_writer.py             Persists calibrated game-area coordinates
    route_service.py          Loads and validates the route.txt format
    template_service.py       Loads detection template images
  ui/
    afo_window.py             AFO time estimate and comparison
    boxes_window.py           Team and PC box tracker
    main_window.py            Counter window and sprite grid
    settings_window.py        Detection, display, and comparison controls
    widgets/
      sprite_strip.py         Sprite grid and click handling
      clickable_label.py      Clickable sprite and its highlights
      flow_layout.py          Wrapping layout for the sprite grid
  vision/
    image_io.py               Image-loading helpers
    template_matching.py      Multi-scale template matching helper
  resources/
    calibration/              Title-screen reference image
    comparison/               Bundled comparison routes
    detection/                Per-Pokémon detection templates
    fonts/                    Counter display fonts
    route/                    Route text files, including route.txt
    sprites_1/                Sprite artwork set 1
    sprites_2/                Sprite artwork set 2
    sprites_3/                Sprite artwork set 3
    textbox/                  Text detection templates
tests/
  test_*.py                    App and controller tests
  services/                    Service tests
  ui/                          Window tests
  ui/widgets/                  Widget tests
  vision/                      Image matching tests
scripts/build.py               PyInstaller packaging script
```
