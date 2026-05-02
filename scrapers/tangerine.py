"""Tangerine bank scraper."""

import os
import time
from playwright.sync_api import Page, TimeoutError as PWTimeout
from .base import AccountData, prompt_mfa

LOGIN_URL = "https://www.tangerine.ca/app/#/login/login-id?locale=en_CA"


def scrape(page: Page) -> AccountData:
    data = AccountData(source="Tangerine")
    username = os.getenv("TANGERINE_USERNAME", "")
    password = os.getenv("TANGERINE_PASSWORD", "")
    pin = os.getenv("TANGERINE_SECURITY_PIN", "")

    if not username or not password:
        data.error = "TANGERINE_USERNAME / TANGERINE_PASSWORD not set in .env"
        return data

    try:
        print("[Tangerine] Navigating to login page...")
        page.goto(LOGIN_URL, wait_until="networkidle", timeout=30000)
        time.sleep(2)

        # Step 1: Enter client number / username
        client_input = page.locator("#login-id, input[name='loginId'], input[placeholder*='client' i], input[type='text']").first
        client_input.wait_for(timeout=10000)
        client_input.fill(username)
        page.get_by_role("button", name=lambda t: "next" in t.lower() or "continue" in t.lower() or "go" in t.lower()).first.click()
        page.wait_for_load_state("networkidle")
        time.sleep(1)

        # Step 2: Security word / PIN (Tangerine uses a security image + PIN)
        pin_input = page.locator("input[type='password'], input[placeholder*='pin' i], input[placeholder*='password' i]").first
        if pin_input.count() > 0:
            pin_input.wait_for(timeout=8000)
            pin_val = pin if pin else prompt_mfa("Tangerine", "Enter Security PIN")
            pin_input.fill(pin_val)
            page.get_by_role("button", name=lambda t: "next" in t.lower() or "sign in" in t.lower() or "login" in t.lower()).first.click()
            page.wait_for_load_state("networkidle")
            time.sleep(2)

        # Step 3: SMS / email MFA if prompted
        mfa_input = page.locator("input[placeholder*='code' i], input[placeholder*='verification' i], input[name*='otp' i], input[name*='code' i]")
        if mfa_input.count() > 0:
            code = prompt_mfa("Tangerine", "Enter the SMS/email verification code")
            mfa_input.first.fill(code)
            page.get_by_role("button", name=lambda t: "verify" in t.lower() or "confirm" in t.lower() or "next" in t.lower()).first.click()
            page.wait_for_load_state("networkidle")
            time.sleep(2)

        print("[Tangerine] Logged in. Extracting balances...")
        _extract_balances(page, data)
        _extract_transactions(page, data)

    except PWTimeout as e:
        data.error = f"Timeout: {e}"
    except Exception as e:
        data.error = str(e)

    return data


def _extract_balances(page: Page, data: AccountData):
    # Tangerine dashboard lists accounts with names and balances
    page.wait_for_selector("[class*='account'], [class*='Account'], [data-test*='account']", timeout=10000)

    account_cards = page.locator("[class*='account-card'], [class*='AccountCard'], [class*='account-summary'], li[class*='account']")
    if account_cards.count() == 0:
        # Fallback to any element containing dollar amounts
        account_cards = page.locator("[class*='account']")

    for i in range(account_cards.count()):
        card = account_cards.nth(i)
        text = card.inner_text().strip()
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        if lines:
            data.balances.append({
                "Account": lines[0] if len(lines) > 0 else "",
                "Balance": lines[1] if len(lines) > 1 else "",
                "Extra": " | ".join(lines[2:]) if len(lines) > 2 else "",
            })


def _extract_transactions(page: Page, data: AccountData):
    # Click into each account to get transactions
    account_links = page.get_by_role("link", name=lambda t: any(k in t.lower() for k in ["chequing", "savings", "rsp", "tfsa", "rrsp"]))

    for i in range(min(account_links.count(), 5)):
        try:
            link = account_links.nth(i)
            account_name = link.inner_text().strip()
            link.click()
            page.wait_for_load_state("networkidle")
            time.sleep(1)

            rows = page.locator("table tbody tr, [class*='transaction-row'], [class*='TransactionRow']")
            for j in range(min(rows.count(), 100)):
                cells = rows.nth(j).locator("td, [class*='cell'], [class*='Cell']")
                row_vals = [cells.nth(k).inner_text().strip() for k in range(cells.count())]
                if any(row_vals):
                    data.transactions.append({"Account": account_name, "Row": row_vals})

            page.go_back(wait_until="networkidle")
            time.sleep(1)
        except Exception:
            continue
