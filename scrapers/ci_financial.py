"""CI Financial / CI GAM scraper."""

import os
import time
from playwright.sync_api import Page, TimeoutError as PWTimeout
from .base import AccountData, prompt_mfa

LOGIN_URL = "https://www.cifinancial.com/ci-gam/ca/en/index.html"


def _safe_text(page: Page, selector: str, default: str = "") -> str:
    try:
        el = page.locator(selector).first
        el.wait_for(timeout=4000)
        return el.inner_text().strip()
    except Exception:
        return default


def scrape(page: Page) -> AccountData:
    data = AccountData(source="CI Financial")
    username = os.getenv("CI_USERNAME", "")
    password = os.getenv("CI_PASSWORD", "")

    if not username or not password:
        data.error = "CI_USERNAME / CI_PASSWORD not set in .env"
        return data

    try:
        print("[CI Financial] Navigating to login page...")
        page.goto(LOGIN_URL, wait_until="networkidle", timeout=30000)
        time.sleep(1)

        # Look for login / sign-in link on the page
        sign_in = page.get_by_role("link", name=lambda t: "sign in" in t.lower() or "login" in t.lower())
        if sign_in.count() > 0:
            sign_in.first.click()
            page.wait_for_load_state("networkidle")

        # Username
        page.get_by_label("username", exact=False).fill(username)
        # Password
        page.get_by_label("password", exact=False).fill(password)
        page.keyboard.press("Enter")
        page.wait_for_load_state("networkidle")
        time.sleep(2)

        # MFA check — look for a code input
        mfa_input = page.locator("input[type='text'][name*='code'], input[placeholder*='code' i], input[placeholder*='verification' i]")
        if mfa_input.count() > 0:
            code = prompt_mfa("CI Financial")
            mfa_input.first.fill(code)
            page.keyboard.press("Enter")
            page.wait_for_load_state("networkidle")
            time.sleep(2)

        print("[CI Financial] Logged in. Extracting balances...")
        _extract_balances(page, data)
        _extract_transactions(page, data)

    except PWTimeout as e:
        data.error = f"Timeout: {e}"
    except Exception as e:
        data.error = str(e)

    return data


def _extract_balances(page: Page, data: AccountData):
    # Try common balance patterns — adjust selectors after inspecting the live portal
    rows = page.locator("[class*='account'], [class*='balance'], [class*='portfolio']")
    for i in range(rows.count()):
        row = rows.nth(i)
        label = row.locator("[class*='name'], [class*='label'], [class*='title']").first
        value = row.locator("[class*='value'], [class*='amount'], [class*='balance']").first
        name = label.inner_text().strip() if label.count() else row.inner_text()[:60]
        amount = value.inner_text().strip() if value.count() else ""
        if name:
            data.balances.append({"Account": name, "Balance": amount})

    if not data.balances:
        # Fallback: grab all dollar-formatted text pairs visible on screen
        all_text = page.locator("body").inner_text()
        data.balances.append({"Account": "Raw page text", "Balance": all_text[:2000]})


def _extract_transactions(page: Page, data: AccountData):
    # Navigate to transactions / activity section if available
    tx_link = page.get_by_role("link", name=lambda t: "transaction" in t.lower() or "activity" in t.lower() or "history" in t.lower())
    if tx_link.count() == 0:
        return

    tx_link.first.click()
    page.wait_for_load_state("networkidle")
    time.sleep(1)

    rows = page.locator("table tbody tr")
    for i in range(min(rows.count(), 100)):
        cells = rows.nth(i).locator("td")
        row_data = [cells.nth(j).inner_text().strip() for j in range(cells.count())]
        if row_data:
            data.transactions.append({"Row": row_data})
