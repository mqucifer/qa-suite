"""crew-presentation's story-journey root page fits a phone.

The story-journey root page (no card argument) shows a list of story links,
one per card in the package. Each link's text is 'repo#number - title'. With
long titles, the anchors reached 402-631px in a 375px viewport, forcing
horizontal scroll (mqucifer/crew-presentation#227).

The test renders the page from QA_BASE_URL in Chromium and measures it.
"""

from __future__ import annotations


def test_story_journey_fits_at_phone_width(rendered):
    """AC1: story-journey.html, rendered at 375x812, doesn't scroll sideways.

    document.documentElement.scrollWidth must be 375 or less (WCAG 2.2 1.4.10 Reflow).
    """
    journey = rendered("/story-journey.html", width=375, height=812)

    # A page without its long titles would fit too, and prove nothing.
    links = journey.locator("section li a").count()
    assert links, "story-journey.html rendered no story links"

    scroll_width = journey.evaluate("document.documentElement.scrollWidth")
    assert scroll_width <= 375, (
        f"story-journey.html is {scroll_width}px wide in a 375px viewport, so it scrolls "
        "sideways (mqucifer/crew-presentation#227: long card titles didn't wrap)"
    )
