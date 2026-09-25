# Pokedex Counter

A small [PySide6](https://doc.qt.io/qtforpython-6/) overlay window for tracking your Pokédex progress live while streaming a Pokémon Red/Blue/Yellow playthrough from a Game Boy capture feed. It watches the video feed, recognizes catch, evolution and "give a nickname?" screens, and keeps a running count of the 151 Pokémon you've found — handy as an OBS window/source capture.

## Download (no Python required)

Grab the latest `PokedexCounter.exe` from the [Releases page](https://github.com/Sidosh/auto-pokedex-counter/releases) and run it. Windows only.

It looks for a device named **"OBS Virtual Camera"** and uses that automatically — so start the OBS Virtual Camera before launching the app. If it can't find one (e.g. it's not running yet, or you renamed it), it falls back to camera index 2.

### What happens on launch: calibration

Every time the app starts, it calibrates itself before the counter window opens:

1. You need to launch the OBS Virtual Camera
2. A small "Calibration" preview window pops up showing your camera feed.
3. Point the feed at the **Pokémon title screen** (the "Pokémon Blue Version" boot screen) — the app matches against that screen to figure out exactly where on your camera frame the catch/evolution/nickname regions are. This is necessary because everyone's camera framing and streaming layout is different.
4. Colored boxes on the preview show live match confidence for the three regions it's searching for. Once all three are found confidently and held steady for a moment, the preview closes automatically and the counter window opens.
5. Press `Esc` at any point to skip calibration — the app falls back to whatever positions worked last time instead.

A successful calibration is remembered for next launch (saved as a `roi_calibration.py` file next to the `.exe`), so you typically only need to re-do it if your camera framing changes. You can also re-run it at any time with the **Calibrate** button, without restarting the app.

## Using the app

Two windows open side by side: the **counter window**, which is the one to capture in OBS, and a **settings window** holding every control — so nothing but the sprite grid and the count ever ends up on stream.

### The counter window

All 151 sprites plus a running "N caught". Catching a Pokémon highlights its sprite and bumps the count.

**Clicking a sprite marks or unmarks it by hand**, for when the detector misses a catch or flags one it shouldn't. Unmarking also lets that Pokémon be detected again later.

Right-clicking a sprite toggles **ignored** (gray). An ignored Pokémon
completes a route section but is not added to the global count or the boxes.
Left-clicking an ignored sprite catches it normally in black; pressing the
right button again simply removes the ignored state. Press **Backspace** to
force-detect every required Pokémon in the current section, even when the app
is not focused.

Until at least one region has been calibrated, the count is replaced by a prompt to calibrate — detection can't run at all in that state, so showing "0 caught" would look like it was working.

### The settings window

| Control | What it does |
| --- | --- |
| Sprites per row | Grid width; the counter window resizes itself to fit |
| Counter font size | Size of the "N caught" text |
| Compare to WR? | Color-codes the grid against the bundled world-record route |
| Highlight bonuses | Colors bonus catches red (see below) |
| Reset counter | Clears the run and starts fresh |
| Calibrate | Re-runs calibration mid-session |

The four settings above the buttons are remembered between launches.

### Route and sprite colors

The section route is read from `resources/route/route.txt`.

The current section colors uncaught icons as follows:

- **Light blue** — required to complete the current section.
- **Light red** — an optional bonus for the current section. It only becomes
  a red caught Pokémon when it is also present in the global `BONUSES` list.
- **Gray** — ignored with the right mouse button.
- **Black** — obtained normally.

The first list must be entirely obtained (or ignored) before the next section
becomes active. The existing WR comparison can still add its own colors:

- **Blue** — on the WR route for a section you've already reached, but not caught yet. In other words, the WR run would have it by now and you don't. These accumulate as the run progresses, so one missed in its own section stays flagged.
- **Black** — caught, and on the WR route.
- **Green** — caught, but not on the WR route in any section reached so far.
- **Red** — caught in the wild and listed as a bonus. This wins over black and green, so a bonus stands out whether or not it's on the route. Every bonus is an evolved form, so *evolving* into one is the ordinary path and doesn't count — only the wild catch turns it red.

Resetting the counter clears the accumulated blue marks so the next run re-earns them section by section. Bonus highlighting is a fixed list, so it just stays on.

The WR route is bundled as `resources/comparison/WR.json`; if it's missing or unreadable, "Compare to WR?" simply has nothing to mark. The route file, rather than `roi_config.py`, is the source of section and
bonus data.

### Personal best

When a run reaches all 151, resetting the counter or closing the app asks whether to save it as your personal best. Saving writes `comparison/PB.json` — next to the `.exe` when running the packaged build — recording which Pokémon were caught in which section, in the same shape as the bundled `WR.json`.

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
  app.py                      QApplication bootstrap and service wiring
  calibration_runner.py       Runs calibration on startup, persists locked ROIs
  camera.py                   Finds the OBS Virtual Camera's device index
  roi_config.py               Catch route, bonus list, detection entry building
  roi_calibration.py          GAME_AREA for this machine (gitignored)
  roi_writer.py               Rewrites roi_calibration.py's ROI_* constants on disk
  config.py                   App-wide constants, resource paths
  main_window.py              Counter window UI (sprite grid + counter)
  settings_window.py          Settings window UI (all controls live here)
  controllers/game_controller.py   Tracks which Pokemon have been found
  services/
    capture_service.py        Camera capture thread
    calibration_service.py    Live ROI calibration against the title screen
    detection_service.py      Per-frame catch/evolve/text detection
    route_service.py          Loads and validates route.json or route.txt
    template_service.py       Loads sprite template images
    wr_service.py             Loads the world-record route from WR.json
    pb_service.py             Saves a completed run to PB.json
  vision/template_matching.py Multi-scale template matching helper
  ui/widgets/
    sprite_strip.py           The sprite grid, and all catch-coloring rules
    clickable_label.py        One sprite: click to toggle, paints its highlight
    flow_layout.py            Wrapping grid layout the strip is built on
  resources/
    sprites/, sprites_background/   Per-Pokemon template images
    calibration/                    Title-screen reference crops
    comparison/WR.json              World-record route, by section
    fonts/                          Pokemon display fonts for the counter
tests/                        pytest + pytest-qt tests
scripts/build.py              PyInstaller packaging script
```
