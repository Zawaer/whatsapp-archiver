#!/usr/bin/env python3
"""
Extract WhatsApp and Contacts databases from Android phone via ADB.

Usage:
  python adb_extract.py

This script pulls:
  - WhatsApp encrypted database (msgstore.db.crypt15)
  - Android Contacts database (contacts2.db)

Both are saved to the db/ directory for later processing.
"""

import os
import subprocess
import sys


def run_adb(command: list[str], description: str) -> None:
    """Run an ADB command with error handling."""
    try:
        print(f"  {description}...")
        subprocess.run(command, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        print(f"  Error: {e.stderr.decode() if e.stderr else e}")
        raise


def main() -> None:
    os.makedirs("db", exist_ok=True)

    print("Checking ADB connection...")
    try:
        subprocess.run(["adb", "devices"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: ADB not found or no device connected.")
        print("Ensure ADB is installed and your Android device is connected with USB debugging enabled.")
        sys.exit(1)

    # Pull WhatsApp database
    print("\n1. Extracting WhatsApp database...")
    run_adb(
        ["adb", "pull", "/data/data/com.whatsapp/databases/msgstore.db.crypt15", "db/msgstore.db.crypt15"],
        "Pulling msgstore.db.crypt15"
    )

    # Pull Android Contacts database
    print("\n2. Extracting Android Contacts database...")
    try:
        run_adb(
            ["adb", "pull", "/data/data/com.android.providers.contacts/databases/contacts2.db", "db/contacts2.db"],
            "Pulling contacts2.db"
        )
    except subprocess.CalledProcessError:
        print("  Warning: Could not extract contacts database. Continuing anyway...")

    print("\n✅ Extraction complete!")
    print("   Next steps:")
    print("   1. Run: python key_setup.py [to set up encryption key if not done already]")
    print("   2. Run: python decryption.py [to decrypt WhatsApp database]")
    print("   3. Run: python contacts_export.py [to export contacts mapping]")
    print("   4. Run: python parse_db.py [to generate archive.json]")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"\nFailed: {error}")
        sys.exit(1)
