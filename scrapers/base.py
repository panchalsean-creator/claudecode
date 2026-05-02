"""Shared browser context and MFA helpers."""

import sys
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AccountData:
    source: str
    balances: list[dict] = field(default_factory=list)
    transactions: list[dict] = field(default_factory=list)
    error: Optional[str] = None


def prompt_mfa(site_name: str, prompt: str = "Enter MFA / verification code") -> str:
    print(f"\n[{site_name}] {prompt}: ", end="", flush=True)
    return sys.stdin.readline().strip()


def new_browser_context(playwright, headless: bool = False):
    """Return a Playwright browser + context configured to reduce bot detection."""
    browser = playwright.chromium.launch(
        headless=headless,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
        ],
    )
    context = browser.new_context(
        viewport={"width": 1280, "height": 800},
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        locale="en-CA",
        timezone_id="America/Toronto",
    )
    # Hide webdriver flag
    context.add_init_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    return browser, context
