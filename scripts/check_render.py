# /// script
# requires-python = ">=3.12"
# dependencies = ["playwright"]
# ///
"""Render checks in the installed Chrome: no sideways scroll, images load, no console errors.

Run: uv run --no-project --script scripts/check_render.py
Screenshots go to docs/superpowers/screens/ (gitignored).
"""

import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
PAGES = ["index.html", "projects.html", "teaching.html", "research.html"]
WIDTHS = [1920, 1280, 768, 390]
PORT = 8765
BASE = f"http://localhost:{PORT}"
SHOTS = ROOT / "docs" / "superpowers" / "screens"

OVERFLOW_JS = "document.documentElement.scrollWidth <= window.innerWidth"
LOAD_ALL_IMAGES_JS = """Promise.all([...document.images].map(i => {
  i.loading = "eager";
  return i.complete ? 0 : new Promise(r => { i.onload = i.onerror = r; });
}))"""
BROKEN_IMAGES_JS = "[...document.images].filter(i => !i.complete || i.naturalWidth === 0).map(i => i.src)"


def wait_for_server():
    for _ in range(50):
        try:
            urllib.request.urlopen(BASE, timeout=1)
            return
        except OSError:
            time.sleep(0.1)
    raise RuntimeError("local server did not start")


def main():
    SHOTS.mkdir(parents=True, exist_ok=True)
    server = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT)], cwd=ROOT,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    results = []
    try:
        wait_for_server()
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="chrome")

            # Probe: the overflow check must catch a page that is too wide.
            page = browser.new_page(viewport={"width": 390, "height": 900})
            page.goto(f"{BASE}/index.html", wait_until="networkidle")
            page.add_style_tag(content="body { min-width: 900px; }")
            results.append(("probe overflow check detects wide page", not page.evaluate(OVERFLOW_JS), ""))
            page.close()

            for width in WIDTHS:
                for name in PAGES:
                    page = browser.new_page(viewport={"width": width, "height": 900})
                    errors = []
                    page.on("console", lambda m, errors=errors: m.type == "error" and errors.append(m.text))
                    page.on("pageerror", lambda e, errors=errors: errors.append(str(e)))
                    page.goto(f"{BASE}/{name}", wait_until="networkidle")
                    tag = f"{name} @{width}"
                    results.append((f"{tag} overflow", page.evaluate(OVERFLOW_JS),
                                    f"scrollWidth {page.evaluate('document.documentElement.scrollWidth')}"))
                    if width == 1920:
                        main_w = page.locator("main").bounding_box()["width"]
                        # On big monitors the content shouldn't sit in a narrow strip.
                        results.append((f"{tag} content fills wide screen", main_w >= 1150, f"main {main_w:.0f}px"))
                    if name == "index.html":
                        box = page.locator(".hero-photo").bounding_box()
                        natural = page.evaluate("(() => { const i = document.querySelector('.hero-photo'); return i.naturalWidth / i.naturalHeight; })()")
                        # The stage photo is chosen for the open-hand gesture: show it whole, never cropped.
                        shown = box["width"] / box["height"]
                        results.append((f"{tag} hero photo not cropped", abs(shown - natural) < 0.02,
                                        f"shown {shown:.3f} vs natural {natural:.3f}"))
                        # The photo must not become a tall, narrow strip (e.g. iPad portrait).
                        results.append((f"{tag} hero photo not a tall strip", box["height"] <= box["width"] * 1.2,
                                        f"{box['width']:.0f}x{box['height']:.0f}"))
                    # Lazy images load only near the viewport: force them to load, then wait.
                    page.evaluate(LOAD_ALL_IMAGES_JS)
                    broken = page.evaluate(BROKEN_IMAGES_JS)
                    results.append((f"{tag} images", not broken, f"broken: {broken}"))
                    results.append((f"{tag} console", not errors, f"errors: {errors}"))
                    page.screenshot(path=SHOTS / f"{name.removesuffix('.html')}-{width}.png", full_page=True)
                    page.close()
            browser.close()
    finally:
        server.terminate()
        server.wait()

    failed = 0
    for label, ok, detail in results:
        print(f"PASS {label}" if ok else f"FAIL {label}: {detail}")
        failed += not ok
    print(f"{len(results) - failed}/{len(results)} passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
