#!/usr/bin/env python3
"""
Extract contact phone number → name mapping from Android Contacts database.

Usage:
  python contacts_export.py

Outputs:
  contacts_mapping.json: {"+358401234567": "John Doe", ...}
"""

import json
import os
import sqlite3
import sys


def extract_contacts_mapping(db_path: str) -> dict[str, str]:
    """Extract phone number to contact name mapping from contacts2.db."""
    if not os.path.isfile(db_path):
        print(f"Contacts database not found at {db_path}")
        return {}

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Try to get display names and phone numbers
        # The contacts database structure varies by Android version/OEM
        mapping: dict[str, str] = {}

        try:
            # Method 1: Try the standard contacts structure
            cursor.execute("""
                SELECT DISTINCT
                    d.data1,
                    c.display_name
                FROM data d
                JOIN contacts c ON c._id = d.contact_id
                WHERE d.mimetype = 'vnd.android.cursor.item/phone_v2'
                    AND d.data1 IS NOT NULL
                    AND c.display_name IS NOT NULL
            """)
            
            for phone, name in cursor.fetchall():
                if phone and name:
                    # Normalize phone number (strip spaces, dashes, etc.)
                    normalized = phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
                    mapping[normalized] = name
                    # Also try with + prefix if not there
                    if not normalized.startswith("+"):
                        mapping["+" + normalized] = name
            
            if mapping:
                conn.close()
                return mapping

        except sqlite3.OperationalError:
            pass

        # Method 2: Try simpler query on contacts table directly
        try:
            cursor.execute("""
                SELECT _id, display_name FROM contacts
                WHERE display_name IS NOT NULL
                LIMIT 1
            """)
            cursor.fetchall()
            
            # Contacts table exists, try to get phone data
            cursor.execute("""
                SELECT display_name FROM contacts LIMIT 1
            """)
            print("  Found contacts table, but structure differs from standard Android")
        except sqlite3.OperationalError:
            pass

        conn.close()
        return mapping

    except sqlite3.DatabaseError as e:
        print(f"Error reading contacts database: {e}")
        return {}


def main() -> None:
    db_path = "db/contacts2.db"
    
    print("Extracting contacts mapping from Android Contacts database...")
    mapping = extract_contacts_mapping(db_path)

    if not mapping:
        print("⚠️  No contacts found or database structure not recognized.")
        print("   This is normal if:")
        print("   - You haven't extracted contacts2.db via ADB yet")
        print("   - Your phone uses a non-standard contacts database format")
        print("\n   Continuing without contacts mapping...")
        mapping = {}

    output_path = "contacts_mapping.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)

    print(f"✅ Exported {len(mapping)} contacts to {output_path}")
    if len(mapping) > 0:
        print(f"   Sample: {list(mapping.items())[:3]}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"Error: {error}")
        sys.exit(1)
