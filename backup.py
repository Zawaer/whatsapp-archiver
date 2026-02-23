#!/usr/bin/env python3
"""
WhatsApp Backup Exporter

Decrypts a WhatsApp database backup, merges contact names from a VCF export,
and writes the complete chat history to a single JSON archive.

Required files in db/:
    msgstore.db.crypt15   (encrypted WhatsApp backup)
    contacts.vcf          (exported from Android Contacts app)
"""

import json
import subprocess
import sys
from pathlib import Path

from src.key_setup import create_key
from src.decryption import decrypt_databases
from src.vcf_to_contacts import parse_vcard_file
from src.parse_db import parse

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "output"
KEY_FILE = ROOT / "encrypted_backup.key"
VCF_FILE = DATA_DIR / "contacts.vcf"


def check_wadecrypt() -> None:
    """Ensure wa-crypt-tools is installed."""
    try:
        subprocess.run(
            ["wadecrypt", "--version"], capture_output=True, check=True
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        sys.exit(
            "Error: wadecrypt not found.\n"
            "  Install with: pip install wa-crypt-tools"
        )


def main() -> None:
    print("WhatsApp Backup Exporter")
    print("=" * 40)

    check_wadecrypt()
    DATA_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Key setup — runs automatically on first use
    if not KEY_FILE.exists():
        print(
            "\nNo encryption key found — running first-time setup.\n"
            "Find your key in WhatsApp:\n"
            "  Settings → Chats → Chat backup → Encryption key\n"
        )
        create_key()
        print()

    # Validate required input files
    crypt_files = sorted(DATA_DIR.glob("*.crypt15"))
    if not crypt_files:
        sys.exit(
            f"Error: No .crypt15 files found in {DATA_DIR}/\n"
            f"  Copy msgstore.db.crypt15 from your phone to {DATA_DIR}/"
        )

    if not VCF_FILE.exists():
        sys.exit(
            f"Error: contacts.vcf not found in {DATA_DIR}/\n"
            f"  Export contacts from your phone's Contacts app and copy to {DATA_DIR}/"
        )

    # Step 1 — Decrypt
    print("\nDecrypting database...")
    decrypted = decrypt_databases(KEY_FILE, DATA_DIR)
    db_path = next(
        (p for p in decrypted if p.name == "msgstore.db"), decrypted[0]
    )

    # Step 2 — Parse contacts
    print("\nParsing contacts...")
    contacts = parse_vcard_file(str(VCF_FILE))
    print(f"  {len(contacts)} contact mappings loaded.")

    # Step 3 — Parse database
    print("\nParsing database...")
    archive = parse(str(db_path), contacts)

    # Step 4 — Write output
    output_path = OUTPUT_DIR / "archive.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(archive, f, ensure_ascii=False, indent=2, default=str)

    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(
        f"\nDone — {archive['total_messages']:,} messages "
        f"from {archive['total_chats']} chats"
    )
    print(f"  Saved to {output_path} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit("\nCancelled.")
