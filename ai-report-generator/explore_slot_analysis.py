"""Quick exploration script to discover the Slot Analysis page structure."""
import json
from playwright.sync_api import sync_playwright

def main():
    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.set_default_timeout(60000)

    # Login
    page.goto("http://localhost:8085/", wait_until="domcontentloaded")
    page.wait_for_timeout(2000)
    page.fill("input#username", "admin")
    page.fill("input#password", "#Nullaxis93820")
    page.click("button[type='submit']")
    page.wait_for_timeout(5000)

    # Navigate to Key Insights → Slot Analysis
    page.get_by_text("Key Insights").first.click()
    page.wait_for_timeout(2000)
    page.get_by_text("Slot Analysis").first.click()
    page.wait_for_timeout(15000)  # Let data load

    # Take screenshot of top
    page.screenshot(path="screenshots/explore_slot_top.png")

    # Extract page structure
    structure = page.evaluate("""
        (() => {
            const result = {
                filters: [],
                charts: [],
                dropdowns: [],
                buttons: [],
                toggles: []
            };

            // Find all select elements
            document.querySelectorAll('select').forEach(el => {
                const label = el.closest('label')?.textContent?.trim() ||
                              el.getAttribute('aria-label') || '';
                const options = Array.from(el.options).map(o => o.text);
                result.dropdowns.push({
                    type: 'select',
                    label: label,
                    value: el.value,
                    options: options.slice(0, 20)
                });
            });

            // Find MUI/custom dropdowns (divs with role=combobox or button-like selects)
            document.querySelectorAll('[role="combobox"], [role="listbox"]').forEach(el => {
                result.dropdowns.push({
                    type: 'combobox',
                    text: el.textContent?.trim().substring(0, 100),
                    ariaLabel: el.getAttribute('aria-label') || ''
                });
            });

            // Find clickable filter-like buttons/chips
            document.querySelectorAll('button, [role="button"]').forEach(el => {
                const text = el.textContent?.trim();
                if (text && text.length < 60 && el.offsetParent !== null) {
                    result.buttons.push(text);
                }
            });

            // Find headings / chart titles
            document.querySelectorAll('h1, h2, h3, h4, h5, h6').forEach(el => {
                if (el.offsetParent !== null) {
                    result.charts.push(el.textContent.trim().substring(0, 120));
                }
            });

            // Find text content that looks like labels/titles for charts
            document.querySelectorAll('[class*="title"], [class*="Title"], [class*="header"], [class*="Header"]').forEach(el => {
                if (el.offsetParent !== null && el.textContent.trim().length > 3) {
                    result.charts.push('title-class: ' + el.textContent.trim().substring(0, 120));
                }
            });

            // Find any toggle/switch elements
            document.querySelectorAll('[role="switch"], input[type="checkbox"], .MuiSwitch-root').forEach(el => {
                result.toggles.push({
                    checked: el.checked || el.getAttribute('aria-checked'),
                    label: el.getAttribute('aria-label') || el.closest('label')?.textContent?.trim() || ''
                });
            });

            // Find input fields
            document.querySelectorAll('input[type="text"], input[type="search"], input:not([type])').forEach(el => {
                if (el.offsetParent !== null && el.id !== 'username' && el.id !== 'password') {
                    result.filters.push({
                        type: 'input',
                        id: el.id,
                        placeholder: el.placeholder,
                        value: el.value,
                        ariaLabel: el.getAttribute('aria-label') || ''
                    });
                }
            });

            // Get visible text containing "Airport", "Month", "Market" etc. — filter labels
            const allText = document.body.innerText;
            const filterPatterns = ['Airport', 'Month', 'Market', 'Airline', 'Period', 'Season',
                                    'Domestic', 'International', 'Annual', 'Seasonal'];
            result.foundFilterKeywords = filterPatterns.filter(p => allText.includes(p));

            return result;
        })()
    """)

    print("=== PAGE STRUCTURE ===")
    print(json.dumps(structure, indent=2))

    # Scroll down and take more screenshots
    page.evaluate("window.scrollBy(0, 800)")
    page.wait_for_timeout(1000)
    page.screenshot(path="screenshots/explore_slot_mid.png")

    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    page.wait_for_timeout(1000)
    page.screenshot(path="screenshots/explore_slot_bottom.png")

    # Also get the full-page scroll screenshot
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(500)
    page.screenshot(path="screenshots/explore_slot_full.png", full_page=True)

    browser.close()
    pw.stop()
    print("Done! Check screenshots/explore_slot_*.png")

if __name__ == "__main__":
    main()
