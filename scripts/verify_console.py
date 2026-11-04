"""Optional real Chromium verification; install Playwright in an isolated tools env."""
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8501")
    parser.add_argument("--screenshots", type=Path, default=Path("reports/screenshots"))
    args = parser.parse_args()
    args.screenshots.mkdir(parents=True, exist_ok=True)
    results, errors = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 1000}, color_scheme="dark")
        page = context.new_page()
        page.on("pageerror", lambda error: errors.append(type(error).__name__))
        page.goto(args.url, wait_until="domcontentloaded")
        page.get_by_role("heading", name="Inspect before you send", exact=True).wait_for(timeout=30000)
        pages = [("Prompt workspace", "Inspect before you send"), ("Security analytics", "Security analytics"),
                 ("Review queue", "Human review queue"), ("ML evaluation", "Evidence, not assurances"),
                 ("System health", "Service health")]
        for index, (name, title) in enumerate(pages):
            page.locator('[data-testid="stSidebar"]').get_by_text(name, exact=True).click()
            page.get_by_role("heading", name=title, exact=True).wait_for()
            if name in ("Security analytics", "System health"):
                page.locator('[data-testid="stMetric"]').first.wait_for(timeout=20000)
            elif name == "ML evaluation":
                page.locator('[data-testid="stDataFrame"]').first.wait_for(timeout=20000)
            page.wait_for_function("document.querySelectorAll('[data-stale=\"true\"]').length === 0", timeout=30000)
            page.wait_for_timeout(500)
            page.locator('[data-testid="stMain"]').evaluate('(element) => element.scrollTo(0, 0)')
            assert page.locator('[data-testid="stException"]').count() == 0
            page.screenshot(path=str(args.screenshots / f"console-{index + 1}.png"), full_page=True)
            results.append({"section": name, "rendered": True})
        # Draft check is real API analysis, with no submission and no screenshot of the draft.
        page.locator('[data-testid="stSidebar"]').get_by_text("Prompt workspace", exact=True).click()
        page.get_by_text("Check draft on edit", exact=True).click()
        assert page.get_by_label("Check draft on edit", exact=True).is_checked()
        page.get_by_label("Prompt", exact=True).fill("api_key = fictional_nonfunctional_browser_key")
        page.get_by_label("Prompt", exact=True).press("Tab")
        page.get_by_text("Draft check: BLOCK", exact=False).wait_for(timeout=20000)
        page.get_by_label("Prompt", exact=True).fill("")
        page.get_by_label("Prompt", exact=True).press("Tab")
        # Responsive render check; screenshots retain an empty prompt only.
        page.set_viewport_size({"width": 430, "height": 900})
        page.wait_for_timeout(500)
        page.screenshot(path=str(args.screenshots / "console-mobile.png"), full_page=True)
        browser.close()
    assert not errors
    print(json.dumps({"browser": "Chromium via Playwright", "sections": results,
                      "draft_check": "BLOCK_WITHOUT_SUBMISSION", "mobile_render": "PASS", "browser_errors": errors}))


if __name__ == "__main__":
    main()
