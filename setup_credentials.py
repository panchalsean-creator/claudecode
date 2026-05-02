"""
Run this once to save your login credentials securely to the .env file.
Your passwords are only stored locally and never shared.

Usage: python3 setup_credentials.py
"""

import getpass
import os

ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")

print("\n=== Financial Account Setup ===")
print("Type each value and press Enter. Passwords are hidden as you type.\n")

fields = [
    ("CI_USERNAME",           "CI Financial - Username: ",       False),
    ("CI_PASSWORD",           "CI Financial - Password: ",       True),
    ("TANGERINE_USERNAME",    "Tangerine - Username: ",          False),
    ("TANGERINE_PASSWORD",    "Tangerine - Password: ",          True),
    ("TANGERINE_SECURITY_PIN","Tangerine - Security PIN: ",      True),
    ("HIGHGATE_USERNAME",     "Highgate - Username: ",           False),
    ("HIGHGATE_PASSWORD",     "Highgate - Password: ",           True),
]

values = {}
for key, prompt, is_secret in fields:
    if is_secret:
        values[key] = getpass.getpass(prompt)
    else:
        values[key] = input(prompt)

# Read existing .env and update only the credential fields
with open(ENV_PATH, "r") as f:
    lines = f.readlines()

updated = []
for line in lines:
    replaced = False
    for key in values:
        if line.startswith(f"{key}="):
            updated.append(f"{key}={values[key]}\n")
            replaced = True
            break
    if not replaced:
        updated.append(line)

with open(ENV_PATH, "w") as f:
    f.writelines(updated)

print("\n✓ Credentials saved to .env — you're all set!\n")
