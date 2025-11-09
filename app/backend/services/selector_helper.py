"""
Selector Helper - Debug tool to help find the correct CSS selectors for iFlow

Usage:
    python -m services.selector_helper

This will open a browser window and help you identify the correct selectors
for your specific iFlow instance.
"""
import os
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env.local")

URL = os.getenv("IFLOW_URL", "https://app.hriflow.ro/#/dashboard")
USERNAME = os.getenv("IFLOW_USERNAME", "")
PASSWORD = os.getenv("IFLOW_PASSWORD", "")


def find_selectors():
    """Interactive tool to help find the right selectors."""
    print("=== iFlow Selector Helper ===")
    print(f"URL: {URL}")
    print(f"Username: {USERNAME}")
    print()

    if not USERNAME or not PASSWORD:
        print("ERROR: Please set IFLOW_USERNAME and IFLOW_PASSWORD in .env.local")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Always visible
        context = browser.new_context(
            viewport={'width': 1280, 'height': 720}
        )
        page = context.new_page()

        print("Opening browser...")
        page.goto(URL)

        print("\nPlease manually inspect the page and identify the selectors:")
        print("1. Right-click on the username input field -> Inspect")
        print("2. Right-click on the element in DevTools -> Copy -> Copy selector")
        print("3. Do the same for password, login button, check-in/out buttons")
        print()

        # Try to find common elements
        print("=== Attempting to auto-detect selectors ===\n")

        # Username inputs
        username_candidates = [
            'input[name="username"]',
            'input[name="email"]',
            'input[type="email"]',
            'input#username',
            'input#email',
            'input[placeholder*="email" i]',
            'input[placeholder*="username" i]',
        ]
        print("Username input candidates:")
        for selector in username_candidates:
            try:
                if page.is_visible(selector, timeout=1000):
                    print(f"  ✓ FOUND: {selector}")
                else:
                    print(f"  ✗ NOT VISIBLE: {selector}")
            except:
                print(f"  ✗ NOT FOUND: {selector}")
        print()

        # Password inputs
        password_candidates = [
            'input[name="password"]',
            'input[type="password"]',
            'input#password',
        ]
        print("Password input candidates:")
        for selector in password_candidates:
            try:
                if page.is_visible(selector, timeout=1000):
                    print(f"  ✓ FOUND: {selector}")
                else:
                    print(f"  ✗ NOT VISIBLE: {selector}")
            except:
                print(f"  ✗ NOT FOUND: {selector}")
        print()

        # Login buttons
        login_candidates = [
            'button[type="submit"]',
            'input[type="submit"]',
            'button:has-text("Login")',
            'button:has-text("Sign in")',
            'button:has-text("Autentificare")',
            '.btn-login',
            '#login-button',
        ]
        print("Login button candidates:")
        for selector in login_candidates:
            try:
                if page.is_visible(selector, timeout=1000):
                    print(f"  ✓ FOUND: {selector}")
                else:
                    print(f"  ✗ NOT VISIBLE: {selector}")
            except:
                print(f"  ✗ NOT FOUND: {selector}")
        print()

        print("=== Manual Login ===")
        print("Please log in manually in the browser window.")
        print("Press Enter when you reach the dashboard...")
        input()

        page.wait_for_timeout(2000)

        # Check-in buttons
        checkin_candidates = [
            'button:has-text("Check In")',
            'button:has-text("Pontaj")',
            'button:has-text("Intrare")',
            '.checkin-btn',
            '#checkin',
        ]
        print("\nCheck-in button candidates:")
        for selector in checkin_candidates:
            try:
                if page.is_visible(selector, timeout=1000):
                    print(f"  ✓ FOUND: {selector}")
                else:
                    print(f"  ✗ NOT VISIBLE: {selector}")
            except:
                print(f"  ✗ NOT FOUND: {selector}")
        print()

        # Check-out buttons
        checkout_candidates = [
            'button:has-text("Check Out")',
            'button:has-text("Iesire")',
            'button:has-text("Plecare")',
            '.checkout-btn',
            '#checkout',
        ]
        print("Check-out button candidates:")
        for selector in checkout_candidates:
            try:
                if page.is_visible(selector, timeout=1000):
                    print(f"  ✓ FOUND: {selector}")
                else:
                    print(f"  ✗ NOT VISIBLE: {selector}")
            except:
                print(f"  ✗ NOT FOUND: {selector}")
        print()

        print("\n=== Summary ===")
        print("Update the SELECTORS dictionary in services/iso_task.py with the selectors marked ✓")
        print("\nPress Enter to close the browser...")
        input()

        browser.close()


if __name__ == "__main__":
    find_selectors()
