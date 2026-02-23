"""Create encrypted_backup.key from a WhatsApp hex key."""

import re
import subprocess
from pathlib import Path

HEX_KEY_LENGTH = 64


def create_key() -> Path:
    """Prompt for the 64-char hex key and generate encrypted_backup.key."""
    raw = input("Paste your 64-character WhatsApp hex key: ").strip()
    cleaned = re.sub(r"[^0-9a-fA-F]", "", raw)

    if not cleaned:
        raise ValueError("No hex characters found in input.")

    if len(cleaned) != HEX_KEY_LENGTH:
        raise ValueError(
            f"Expected {HEX_KEY_LENGTH} hex characters, got {len(cleaned)}."
        )

    subprocess.run(["wacreatekey", "--hex", cleaned], check=True)

    key_path = Path("encrypted_backup.key")
    if not key_path.exists():
        raise RuntimeError("wacreatekey did not produce encrypted_backup.key.")

    print("encrypted_backup.key created successfully.")
    return key_path
