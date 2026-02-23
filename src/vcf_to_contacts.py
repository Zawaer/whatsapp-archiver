#!/usr/bin/env python3
"""
Parse vCard (VCF) file exported from Android Contacts app.

Usage:
  python vcf_to_contacts.py [--vcf db/contacts.vcf] [--out contacts_mapping.json]

Extracts phone number → contact name mapping and saves to JSON.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path


def decode_quoted_printable(text: str) -> str:
    """Decode quoted-printable encoded strings in vCard format."""
    if not text or "=" not in text:
        return text
    
    try:
        # Handle UTF-8 quoted-printable encoding
        # Replace =XX with chr(0xXX), then decode UTF-8
        result = ""
        i = 0
        while i < len(text):
            if text[i] == "=" and i + 2 < len(text):
                hex_str = text[i+1:i+3]
                try:
                    result += chr(int(hex_str, 16))
                    i += 3
                except ValueError:
                    result += text[i]
                    i += 1
            else:
                result += text[i]
                i += 1
        
        # Try to encode/decode as UTF-8 to handle multi-byte sequences
        return result.encode('latin-1').decode('utf-8', errors='ignore')
    except Exception:
        return text


def parse_vcard_file(vcf_path: str) -> dict[str, str]:
    """Parse a VCF file and extract phone → name mapping."""
    if not os.path.isfile(vcf_path):
        print(f"Error: VCF file not found at {vcf_path}")
        return {}
    
    mapping: dict[str, str] = {}
    
    try:
        with open(vcf_path, "r", encoding="utf-8") as f:
            content = f.read()
    except UnicodeDecodeError:
        # Try with latin-1 if UTF-8 fails
        with open(vcf_path, "r", encoding="latin-1") as f:
            content = f.read()
    
    # Split into individual vCard entries
    vcards = re.split(r"(?=BEGIN:VCARD)", content)
    
    for vcard in vcards:
        if not vcard.strip() or not vcard.startswith("BEGIN:VCARD"):
            continue
        
        lines = vcard.split("\n")
        name = None
        phones = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Parse FN (full name) field
            if line.startswith("FN"):
                # Extract the value after the colon (and any parameters)
                parts = line.split(":", 1)
                if len(parts) > 1:
                    raw_name = parts[1].strip()
                    
                    # Check if it's quoted-printable encoded
                    if "ENCODING=QUOTED-PRINTABLE" in line:
                        name = decode_quoted_printable(raw_name)
                    else:
                        name = raw_name
            
            # Parse TEL (phone) fields
            elif line.startswith("TEL"):
                # Extract the phone number after the colon
                parts = line.split(":", 1)
                if len(parts) > 1:
                    phone = parts[1].strip()
                    # Normalize: remove spaces, dashes, parentheses
                    normalized = phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
                    if normalized:
                        phones.append(normalized)
        
        # Add all phone numbers to mapping
        if name and phones:
            for phone in phones:
                # Add with + if not already present
                if not phone.startswith("+"):
                    mapping[f"+{phone}"] = name
                # Also add without + (some DBs store it this way)
                mapping[phone.lstrip("+")] = name
                # Add the phone as-is (might already have +)
                mapping[phone] = name
    
    return mapping


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse vCard contacts and export to JSON mapping.")
    parser.add_argument("--vcf", default="db/contacts.vcf", help="Path to VCF contacts file")
    parser.add_argument("--out", default="contacts_mapping.json", help="Output JSON file path")
    args = parser.parse_args()
    
    print("Parsing VCF contacts file...")
    mapping = parse_vcard_file(args.vcf)
    
    if not mapping:
        print("⚠️  No contacts found in VCF file.")
        sys.exit(1)
    
    # Write to JSON
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Exported {len(mapping)} phone number mappings to {args.out}")
    
    # Show sample
    sample_items = list(mapping.items())[:5]
    if sample_items:
        print("   Sample entries:")
        for phone, name in sample_items:
            print(f"     {phone} → {name}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"Error: {error}")
        sys.exit(1)
