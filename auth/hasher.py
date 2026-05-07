"""
hasher.py — CLI utility to generate bcrypt password hashes.

Usage (from project root, using venv):
    .\\venv\\Scripts\\python.exe -m auth.hasher

Generates bcrypt hashes for the predefined test user passwords.
Copy the output hashes into .streamlit/secrets.toml.

This file is a standalone tool — it is NOT imported by the app.
"""

import bcrypt


def hash_password(plain_password: str) -> str:
    """Generate a bcrypt hash for the given plain text password."""
    return bcrypt.hashpw(
        plain_password.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")


import getpass

if __name__ == "__main__":
    print("=" * 60)
    print("  Bcrypt Password Hash Generator")
    print("=" * 60)
    print()

    while True:
        password = getpass.getpass("Enter password to hash (or press Enter to quit): ")
        if not password:
            break
            
        hashed = hash_password(password)
        print(f"\n  Generated Hash: {hashed}\n")
        print("  Copy this hash and paste it into the password field in .streamlit/secrets.toml")
        print("-" * 60)

