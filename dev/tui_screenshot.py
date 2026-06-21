"""Screenshot helper for TUI review passes.

Textual can export an exact-render SVG of the current screen via
App.save_screenshot(), but the Read tool can't view SVGs directly. This
converts one to a PNG using a headless Chromium, which is already present
in this environment. Usage from a throwaway driver script:

    from dev.tui_screenshot import svg_to_png
    app.save_screenshot("/tmp/ui_pass/01_dashboard.svg")
    svg_to_png("/tmp/ui_pass/01_dashboard.svg")  # -> 01_dashboard.png next to it

See ROADMAP.md's "TUI Review Passes" section and CLAUDE.md for when/why to
run a full pass, and tests/test_ui_*.py for the app-driving pattern (boot
DMApp via app.run_test(), navigate with pilot.press()/action_*() calls).
"""
import subprocess
from pathlib import Path

CHROMIUM = "chromium-browser"


def svg_to_png(svg_path: str, png_path: str | None = None, window_size: str = "1400,800") -> str:
    svg_path = Path(svg_path)
    png_path = Path(png_path) if png_path else svg_path.with_suffix(".png")
    subprocess.run(
        [
            CHROMIUM, "--headless", "--disable-gpu", "--no-sandbox",
            f"--screenshot={png_path}", f"--window-size={window_size}",
            f"file://{svg_path.resolve()}",
        ],
        check=True, capture_output=True, timeout=30,
    )
    return str(png_path)
