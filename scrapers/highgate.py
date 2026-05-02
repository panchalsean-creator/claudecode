"""Highgate Group scraper."""

import os
import time
from playwright.sync_api import Page, TimeoutError as PWTimeout
from .base import AccountData, prompt_mfa

LOGIN_URL = "https://highgategroup.ca/"


def scrape(page: Page) -> AccountData:
    data = AccountData(source="Highgate Group")
    username = os.getenv("HIGHGATE_USERNAME", "")
    password = os.getenv("HIGHGATE_PASSWORD", "")

    if not username or not password:
        data.error = "HIGHGATE_USERNAME / HIGHGATE_PASSWORD not set in .env"
        return data

    try:
        print("[Highgate] Navigating to login page...")
        page.goto(LOGIN_URL, wait_until="networkidle", timeout=30000)
        time.sleep(1)

        # Find login link/button if homepage is a marketing page
        login_link = page.get_by_role("link", name=lambda t: "login" in t.lower() or "sign in" in t.lower() or "client" in t.lower() or "portal" in t.lower())
        if login_link.count() > 0:
            login_link.first.click()
            page.wait_for_load_state("networkidle")
            time.sleep(1)

        # Username / email
        user_input = page.locator("input[type='email'], input[type='text'][name*='user' i], input[placeholder*='email' i], input[placeholder*='username' i]").first
        user_input.wait_for(timeout=10000)
        user_input.fill(username)

        # Password
        pass_input = page.locator("input[type='password']").first
        pass_input.fill(password)

        page.get_by_role("button", name=lambda t: "login" in t.lower() or "sign in" in t.lower() or "submit" in t.lower()).first.click()
        page.wait_for_load_state("networkidle")
        time.sleep(2)

        # MFA if prompted
        mfa_input = page.locator("input[placeholder*='code' i], input[placeholder*='verification' i], input[name*='otp' i]")
        if mfa_input.count() > 0:
            code = prompt_mfa("Highgate Group")
            mfa_input.first.fill(code)
            page.keyboard.press("Enter")
            page.wait_for_load_state("networkidle")
            time.sleep(2)

        print("[Highgate] Logged in. Extracting data...")
        _extract_balances(page, data)
        _extract_transactions(page, data)

    except PWTimeout as e:
        data.error = f"Timeout: {e}"
    except Exception as e:
        data.error = str(e)

    return data


def _extract_balances(page: Page, data: AccountData):
    balance_els = page.locator("[class*='balance'], [class*='account'], [class*='portfolio'], [class*='summary']")
    for i in range(balance_els.count()):
        text = balance_els.nth(i).inner_text().strip()
        if text:
            lines = [l.strip() for l in text.splitlines() if l.strip()]
            data.balances.append({
                "Account": lines[0] if lines else "",
                "Balance": lines[1] if len(lines) > 1 else "",
            })

    if not data.balances:
        # Grab any dollar figures visible on the page
        all_text = page.locator("body").inner_text()
        data.balances.append({"Account": "Page content", "Balance": all_text[:2000]})


def _extract_transactions(page: Page, data: AccountData):
    tx_link = page.get_by_role("link", name=lambda t: "transaction" in t.lower() or "activity" in t.lower() or "history" in t.lower() or "statement" in t.lower())
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
