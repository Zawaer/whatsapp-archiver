#!/usr/bin/env python3
"""
WhatsApp backup exporter - all-in-one backup workflow.

This script handles:
1. Decrypting WhatsApp database (msgstore.db.crypt15)
2. Exporting contacts mapping from VCF file
3. Parsing database to JSON archive with contact names

Usage:
  python backup.py                  # Run full backup (key must be set up)
  python backup.py --init           # First-time setup (creates encryption key)
  python backup.py --help           # Show all options
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def check_requirements() -> bool:
    """Check if required tools are installed."""
    try:
        subprocess.run(["wadecrypt", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Error: wa-crypt-tools not found")
        print("   Install with: python3 -m pip install wa-crypt-tools")
        return False


def create_directories() -> None:
    """Create necessary directories."""
    Path("db").mkdir(exist_ok=True)
    Path("output").mkdir(exist_ok=True)


def setup_key() -> None:
    """One-time encryption key setup."""
    print("\n🔐 WhatsApp Encryption Key Setup")
    print("=" * 50)
    print("You need your 64-character WhatsApp backup encryption key.")
    print("Find it in: Settings → Chats → Chat backup → Encryption key")
    print()
    
    # Import and run key setup
    import key_setup as key_setup_module
    key_setup_module.main()


def decrypt_database() -> bool:
    """Decrypt WhatsApp database."""
    print("\n🔓 Decrypting WhatsApp database...")
    
    KEY_FILE = "encrypted_backup.key"
    if not os.path.isfile(KEY_FILE):
        print("❌ Encryption key not found. Run with --init first.")
        return False
    
    crypt15_files = list(Path("db").glob("*.crypt15"))
    if not crypt15_files:
        print("⚠️  No .crypt15 files found in db/ directory")
        print("   Place msgstore.db.crypt15 in db/ folder first")
        return False
    
    for encrypted_file in crypt15_files:
        decrypted_file = encrypted_file.with_suffix("")
        print(f"  Decrypting {encrypted_file.name}...")
        try:
            subprocess.run(
                ["wadecrypt", KEY_FILE, str(encrypted_file), str(decrypted_file)],
                check=True,
                capture_output=True,
            )
            print(f"  ✓ {decrypted_file.name}")
        except subprocess.CalledProcessError as e:
            print(f"  ❌ Failed: {e.stderr.decode() if e.stderr else e}")
            return False
    
    return True


def export_contacts() -> bool:
    """Export contacts from VCF file."""
    print("\n📇 Exporting contacts from VCF...")
    
    vcf_path = Path("db/contacts.vcf")
    if not vcf_path.exists():
        print("⚠️  contacts.vcf not found in db/ directory")
        print("   1. Export contacts from your phone's Contacts app")
        print("   2. Save as contacts.vcf")
        print("   3. Transfer to db/ folder")
        return True  # Continue anyway, contacts optional
    
    import vcf_to_contacts as vcf_module
    
    mapping = vcf_module.parse_vcard_file(str(vcf_path))
    if not mapping:
        print("⚠️  No contacts found in VCF file")
        return True
    
    output_path = Path("contacts_mapping.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)
    
    print(f"  ✓ {len(mapping)} contact mappings exported")
    return True


def parse_database() -> bool:
    """Parse WhatsApp database to JSON archive."""
    print("\n📦 Parsing WhatsApp database...")
    
    db_path = Path("db/msgstore.db")
    if not db_path.exists():
        print("❌ Decrypted database not found at db/msgstore.db")
        print("   Make sure decryption step completed successfully")
        return False
    
    import parse_db as parse_module
    
    try:
        archive = parse_module.parse(str(db_path))
        
        output_path = Path("output/archive.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(archive, f, ensure_ascii=False, indent=2, default=str)
        
        file_size_mb = output_path.stat().st_size / (1024 * 1024)
        print(f"\n✅ Done! {archive['total_messages']:,} messages in {archive['total_chats']} chats")
        print(f"   Saved to: {output_path} ({file_size_mb:.1f} MB)")
        return True
    except Exception as e:
        print(f"❌ Parsing failed: {e}")
        return False


def run_full_backup() -> bool:
    """Run complete backup workflow."""
    print("\n📱 WhatsApp Backup Exporter")
    print("=" * 50)
    
    # Check requirements
    if not check_requirements():
        return False
    
    create_directories()
    
    # Check for encrypted key
    if not Path("encrypted_backup.key").exists():
        print("\n❌ Encryption key not set up yet")
        print("   Run with --init to set up your key first")
        return False
    
    # Run steps
    steps = [
        ("Decrypt database", decrypt_database),
        ("Export contacts", export_contacts),
        ("Parse to JSON", parse_database),
    ]
    
    for step_name, step_func in steps:
        if not step_func():
            print(f"\n❌ {step_name} failed")
            return False
    
    print("\n✨ Backup complete!")
    print("📋 Next: Back up output/archive.json to encrypted storage")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="WhatsApp backup and export tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python backup.py --init     # First-time setup (create encryption key)
  python backup.py            # Run full backup workflow
  python backup.py --decrypt  # Only decrypt database
        """,
    )
    parser.add_argument(
        "--init",
        action="store_true",
        help="Initialize: set up encryption key (one-time only)",
    )
    parser.add_argument(
        "--decrypt",
        action="store_true",
        help="Only decrypt database files",
    )
    parser.add_argument(
        "--contacts",
        action="store_true",
        help="Only export contacts mapping",
    )
    parser.add_argument(
        "--parse",
        action="store_true",
        help="Only parse database to JSON",
    )
    
    args = parser.parse_args()
    
    # Handle individual steps
    if args.init:
        setup_key()
    elif args.decrypt:
        if not check_requirements():
            sys.exit(1)
        create_directories()
        if not decrypt_database():
            sys.exit(1)
    elif args.contacts:
        if not export_contacts():
            sys.exit(1)
    elif args.parse:
        if not parse_database():
            sys.exit(1)
    else:
        # Run full workflow
        if not run_full_backup():
            sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  Cancelled by user")
        sys.exit(1)
