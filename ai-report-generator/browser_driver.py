"""
browser_driver.py — Playwright-based browser automation for dashboard navigation.

Handles login, element interaction, scrolling, and screenshot capture.
Uses a hybrid dynamic wait strategy matching Maestro's core philosophy:
  - Phase 1: DOM Loading Detection. Wait for all spinners, CircularProgress,
    and "Loading...", "Calculating...", "Fetching..." text elements to disappear.
  - Phase 2: Visual Stabilization (Pixel Diff). Take consecutive screenshots 1s
    apart and compute pixel differences via PIL's fast histogram comparison.
    Only proceed once the page is visually static (diff <= 0.5%).
"""

import io
import os
import time

from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright, Page, Browser


class BrowserDriver:
    """Drives a Chromium browser through the dashboard, capturing screenshots."""

    def __init__(self, headless: bool = True, viewport_width: int = 1440, viewport_height: int = 900):
        self.headless = headless
        self.viewport = {"width": viewport_width, "height": viewport_height}
        self._playwright = None
        self._browser: Browser | None = None
        self._page: Page | None = None

    def launch(self):
        """Start Playwright and open a Chromium browser."""
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(
            headless=self.headless,
            args=[
                f"--window-size={self.viewport['width']},{self.viewport['height']}",
                "--disable-gpu",
                "--no-sandbox",
            ],
        )
        self._page = self._browser.new_page(viewport=self.viewport)
        self._page.set_default_timeout(60000)
        print(f"  Browser launched ({'headless' if self.headless else 'headed'}, {self.viewport['width']}x{self.viewport['height']})")

    def navigate(self, url: str):
        """Navigate to a URL. Uses 'domcontentloaded' to avoid hanging on SPAs."""
        self._page.goto(url, wait_until="domcontentloaded", timeout=30000)
        self._page.wait_for_timeout(1000)
        print(f"  Navigated to {url}")

    def login(self, config: dict):
        """Perform login using selectors and credentials from config."""
        username_sel = config["username_selector"]
        password_sel = config["password_selector"]
        submit_sel = config["submit_selector"]

        self._page.wait_for_selector(username_sel, timeout=15000)
        self._page.fill(username_sel, "")
        self._page.fill(password_sel, "")
        self._page.fill(username_sel, config["username"])
        self._page.fill(password_sel, config["password"])
        self._page.click(submit_sel)

        # Wait for post-login page to settle
        wait_ms = config.get("wait_after_login", 15000)
        self.wait_until_screen_is_static(timeout_ms=wait_ms)
        print(f"  Logged in as {config['username']}")

    def execute_actions(self, actions: list):
        """Execute a list of navigation actions."""
        for action in actions:
            if isinstance(action, dict):
                action_type = list(action.keys())[0]
                value = action[action_type]

                if action_type == "tapOn":
                    self._tap_on(value)
                elif action_type == "waitFor":
                    self._wait_for_text(value)
                elif action_type == "waitUntilStatic":
                    self.wait_until_screen_is_static(timeout_ms=value)
                elif action_type == "sleep":
                    self._sleep(value)
                elif action_type == "scrollIntoView":
                    self._scroll_into_view(value)
                elif action_type == "scrollToTop":
                    self._scroll_to_top()
                elif action_type == "scrollToBottom":
                    self._scroll_to_bottom()
                elif action_type == "click":
                    self._page.click(value)
                elif action_type == "selectOption":
                    # Native <select> element: {selectOption: {selector: "select...", value: "BOM"}}
                    self._select_option(value["selector"], value.get("value"), value.get("label"))
                elif action_type == "selectDropdown":
                    # Custom dropdown: {selectDropdown: {label: "Comparing: AIG", option: "6E"}}
                    self._select_dropdown(value["label"], value["option"])
                elif action_type == "fillInput":
                    # Text input: {fillInput: {placeholder: "Sector (e.g. DEL-BOM)", text: "DEL-BOM"}}
                    self._fill_input(value["placeholder"], value["text"])
                else:
                    print(f"    ⚠ Unknown action: {action_type}")
            elif isinstance(action, str):
                if action == "scrollToTop":
                    self._scroll_to_top()
                elif action == "scrollToBottom":
                    self._scroll_to_bottom()

    def wait_until_screen_is_static(
        self,
        timeout_ms: int = 45000,
        threshold: float = 0.5,
        poll_interval_ms: int = 1000,
    ) -> bool:
        """
        Robust hybrid wait:
        1. Poll the DOM until no visible loading text/spinners remain (up to timeout_ms).
        2. Perform visual pixel-diff stabilization to verify layout is fully static.
        """
        print(f"    ⏳ Checking page state (max {timeout_ms // 1000}s, visual threshold {threshold}%)...")
        start = time.time()
        timeout_s = timeout_ms / 1000.0

        # Phase 1: Wait for DOM loading indicators to clear
        while (time.time() - start) < timeout_s:
            is_loading = self._page.evaluate("""
                (() => {
                    // 1. Check for any visible text indicating active loading/fetching/calculating/processing
                    const elements = document.querySelectorAll('*');
                    for (const el of elements) {
                        if (el.children.length === 0 && el.innerText && el.offsetParent !== null) {
                            const txt = el.innerText.trim();
                            if (txt.match(/^(loading|calculating|fetching|processing)/i)) {
                                return true;
                            }
                            if (txt.includes("Generating AI insights")) {
                                return true;
                            }
                            if (txt.includes("No slot distribution data available")) {
                                return true;
                            }
                        }
                    }
                    // 2. Check for spinner elements, circular progress bars, Mui progress
                    const spinners = document.querySelectorAll(
                        '.spinner, .loading, [class*="spinner"], [class*="loading"], ' +
                        '.MuiCircularProgress-root, .ant-spin, [role="progressbar"]'
                    );
                    for (const s of spinners) {
                        if (s.offsetParent !== null) return true;
                    }
                    return false;
                })()
            """)

            if not is_loading:
                break

            self._page.wait_for_timeout(poll_interval_ms)

        # Phase 2: Wait for visual pixel changes to settle
        prev_screenshot = self._take_pil_screenshot()

        while (time.time() - start) < timeout_s:
            self._page.wait_for_timeout(poll_interval_ms)
            curr_screenshot = self._take_pil_screenshot()

            diff_pct = self._image_diff_percent(prev_screenshot, curr_screenshot)

            if diff_pct <= threshold:
                elapsed = int((time.time() - start) * 1000)
                print(f"    ✅ Page settled fully ({elapsed}ms, visual diff: {diff_pct:.2f}%)")
                return True

            prev_screenshot = curr_screenshot

        elapsed = int((time.time() - start) * 1000)
        print(f"    ⚠ Page did not fully settle in {elapsed}ms (last diff: {diff_pct:.2f}%), continuing")
        return False

    def capture_screenshot(self, filepath: str, mode: str = "full_page") -> str:
        """Capture a screenshot and save to filepath. Returns the absolute path."""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        if mode == "full_scroll":
            self._page.screenshot(path=filepath, full_page=True)
        else:
            self._page.screenshot(path=filepath, full_page=False)

        print(f"    📸 Screenshot saved: {os.path.basename(filepath)}")
        return filepath

    def close(self):
        """Shut down browser and Playwright."""
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()
        print("  Browser closed.")

    # ─── Screenshot comparison (Maestro-style) ────────────────────────

    def _take_pil_screenshot(self) -> Image.Image:
        """Take a viewport screenshot and return as a PIL Image."""
        png_bytes = self._page.screenshot(full_page=False)
        return Image.open(io.BytesIO(png_bytes))

    @staticmethod
    def _image_diff_percent(img1: Image.Image, img2: Image.Image) -> float:
        """
        Calculate the percentage of pixels that differ between two images.
        Uses PIL histogram counting to filter out sub-pixel noise.
        """
        if img1.size != img2.size:
            return 100.0

        diff = ImageChops.difference(img1.convert("RGB"), img2.convert("RGB"))
        gray = diff.convert("L")
        threshold = gray.point(lambda p: 255 if p > 10 else 0)
        hist = threshold.histogram()
        total = img1.size[0] * img1.size[1]
        changed = hist[255]

        return (changed / total) * 100.0

    # ─── Private helpers ──────────────────────────────────────────────

    def _tap_on(self, text: str):
        """Click an element by its visible text."""
        try:
            locator = self._page.get_by_text(text, exact=False).first
            locator.wait_for(state="visible", timeout=15000)
            locator.click()
            self._page.wait_for_timeout(500)
            print(f"    ✅ Tapped on: \"{text}\"")
        except Exception as e:
            print(f"    ❌ Failed to tap \"{text}\": {e}")

    def _wait_for_text(self, text: str, timeout: int = 30000):
        """Wait until text is visible on the page."""
        try:
            self._page.get_by_text(text, exact=False).first.wait_for(state="visible", timeout=timeout)
            print(f"    ✅ Visible: \"{text}\"")
        except Exception as e:
            print(f"    ⚠ Timeout waiting for \"{text}\": {e}")

    def _sleep(self, ms: int):
        """Explicit wait in milliseconds."""
        self._page.wait_for_timeout(ms)

    def _select_option(self, selector: str, value: str = None, label: str = None):
        """
        Select an option in a native HTML <select> element.
        Uses Playwright's select_option() which supports value or label.
        """
        try:
            if value:
                self._page.select_option(selector, value=value)
                print(f"    ✅ Selected value \"{value}\" in {selector}")
            elif label:
                self._page.select_option(selector, label=label)
                print(f"    ✅ Selected label \"{label}\" in {selector}")
        except Exception as e:
            print(f"    ❌ Failed to select in {selector}: {e}")

    def _select_dropdown(self, button_text: str, option_text: str):
        """
        Interact with a custom (non-native) dropdown:
        1. Click the dropdown trigger button (matched by button_text).
        2. Wait for the dropdown options to appear.
        3. Click the desired option (matched by option_text).
        """
        try:
            # Click the dropdown trigger
            trigger = self._page.get_by_text(button_text, exact=False).first
            trigger.wait_for(state="visible", timeout=10000)
            trigger.click()
            self._page.wait_for_timeout(500)
            # Click the option
            option = self._page.get_by_text(option_text, exact=False).first
            option.wait_for(state="visible", timeout=10000)
            option.click()
            self._page.wait_for_timeout(500)
            print(f"    ✅ Selected \"{option_text}\" from dropdown \"{button_text}\"")
        except Exception as e:
            print(f"    ❌ Failed to select \"{option_text}\" from \"{button_text}\": {e}")

    def _fill_input(self, placeholder: str, text: str):
        """Fill a text input field identified by its placeholder text."""
        try:
            locator = self._page.get_by_placeholder(placeholder).first
            locator.wait_for(state="visible", timeout=10000)
            locator.fill(text)
            self._page.wait_for_timeout(300)
            print(f"    ✅ Filled \"{placeholder}\" with \"{text}\"")
        except Exception as e:
            print(f"    ❌ Failed to fill \"{placeholder}\": {e}")

    def _scroll_into_view(self, text: str):
        """Scroll an element with matching text to the top of the viewport, adjusted for sticky headers."""
        try:
            # Find the element
            locator = self._page.get_by_text(text, exact=False).first
            locator.wait_for(state="attached", timeout=10000)

            # Use JS to scroll it to the top of the viewport
            self._page.evaluate("""
                (text) => {
                    const xpath = `//*[contains(text(), "${text}")]`;
                    const result = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
                    const el = result.singleNodeValue;
                    if (el) {
                        el.scrollIntoView({ block: 'start', behavior: 'auto' });
                    }
                }
            """, text)

            self._page.wait_for_timeout(500)
            # Scroll up slightly (e.g. 80px) to clear any sticky top navbars
            self._page.evaluate("window.scrollBy(0, -90)")
            self._page.wait_for_timeout(300)
            print(f"    ✅ Scrolled to: \"{text}\"")
        except Exception as e:
            print(f"    ❌ Failed to scroll to \"{text}\": {e}")

    def _scroll_to_top(self):
        """Scroll to the top of the page."""
        self._page.evaluate("window.scrollTo({ top: 0, behavior: 'auto' })")
        self._page.wait_for_timeout(500)
        print("    ✅ Scrolled to top")

    def _scroll_to_bottom(self):
        """Scroll to the bottom of the page."""
        self._page.evaluate(
            "window.scrollTo({ top: Math.max(document.body.scrollHeight, document.documentElement.scrollHeight), behavior: 'auto' })"
        )
        self._page.wait_for_timeout(500)
        print("    ✅ Scrolled to bottom")
