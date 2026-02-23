"""Decrypt WhatsApp .crypt15 backup files using wadecrypt."""

import subprocess
from pathlib import Path


def decrypt_databases(key_path: Path, db_dir: Path) -> list[Path]:
    """Decrypt all .crypt15 files in db_dir. Returns paths to decrypted files."""
    crypt_files = sorted(db_dir.glob("*.crypt15"))
    if not crypt_files:
        raise FileNotFoundError(f"No .crypt15 files found in {db_dir}/")

    decrypted: list[Path] = []
    for encrypted in crypt_files:
        output = encrypted.with_suffix("")
        print(f"  Decrypting {encrypted.name}...")
        subprocess.run(
            ["wadecrypt", str(key_path), str(encrypted), str(output)],
            check=True,
            capture_output=True,
        )
        print(f"  ✓ {output.name}")
        decrypted.append(output)

    return decrypted
