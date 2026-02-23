import re
import subprocess
import sys


HEX_KEY_LENGTH = 64


def main() -> None:
  raw_key = input("Paste your 64-character WhatsApp hex key: ").strip()
  trimmed_key = re.sub(r"[^0-9a-fA-F]", "", raw_key)

  if not trimmed_key:
    raise ValueError("Missing key input.")

  if len(trimmed_key) != HEX_KEY_LENGTH:
    raise ValueError(
      f"Invalid key length: expected {HEX_KEY_LENGTH} hex characters, got {len(trimmed_key)}."
    )

  subprocess.run(["wacreatekey", "--hex", trimmed_key], check=True)
  print("encrypted_backup.key created successfully.")


if __name__ == "__main__":
  try:
    main()
  except Exception as error:
    print(f"Error: {error}")
    sys.exit(1)
