"""What crew-presentation's tests share: Chromium, to see a page as its reader gets it.

`start.sh` installs Playwright and Chromium for this folder. README.md says when a
test renders a page and when plain HTTP is enough.
"""

from __future__ import annotations

import os

import pytest


@pytest.fixture(scope="session")
def chromium():
    # Imported here so a test that only reads pages over HTTP doesn't depend on it.
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        yield browser
        browser.close()


@pytest.fixture
def rendered(chromium):
    """Opens a page of the site in Chromium, at a viewport the test chooses:

        page = rendered("/replay.html", width=375, height=812)
        page.evaluate("document.documentElement.scrollWidth")

    It's a Playwright Page, loaded. It fails if the site doesn't serve the page or a
    stylesheet doesn't load: a layout measured without its CSS proves nothing.
    """
    # Fails rather than skips without it: a skipped suite would be a green check.
    base = os.environ.get("QA_BASE_URL", "")
    if not base:
        pytest.fail("QA_BASE_URL isn't set: run start.sh first", pytrace=False)
    contexts = []

    def open_page(path: str, *, width: int, height: int):
        context = chromium.new_context(viewport={"width": width, "height": height})
        contexts.append(context)
        page = context.new_page()
        unstyled = []

        def on_response(response):
            if response.request.resource_type == "stylesheet" and not response.ok:
                unstyled.append(f"{response.url} answered {response.status}")

        def on_failed(request):
            if request.resource_type == "stylesheet":
                unstyled.append(f"{request.url} failed: {request.failure}")

        page.on("response", on_response)
        page.on("requestfailed", on_failed)
        response = page.goto(base + path, wait_until="load")
        if response is None or not response.ok:
            status = response.status if response else "nothing"
            pytest.fail(f"GET {path} answered {status}: the site has no such page", pytrace=False)
        if unstyled:
            pytest.fail(f"{path} rendered without its CSS: {'; '.join(unstyled)}", pytrace=False)
        return page

    yield open_page
    for context in contexts:
        context.close()
