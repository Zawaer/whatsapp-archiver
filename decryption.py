import glob
import os
import subprocess
import sys


KEY_FILE = "encrypted_backup.key"


def main():
  if not os.path.isfile(KEY_FILE):
    raise FileNotFoundError(
      f"Missing {KEY_FILE}. Run key_setup.py first to create it."
    )

  # Decrypt WhatsApp database
  crypt15_files = glob.glob("db/*.crypt15")
  if not crypt15_files:
    print("Warning: No .crypt15 files found in the db directory.")
  
  for encrypted_file in crypt15_files:
    decrypted_file = os.path.splitext(encrypted_file)[0]
    print(f"Decrypting {encrypted_file} to {decrypted_file}")
    subprocess.run(
      ["wadecrypt", KEY_FILE, encrypted_file, decrypted_file],
      check=True,
    )
    print(f"Finished decrypting {encrypted_file}")

  # Contacts database is typically not encrypted, but copy if it exists
  contacts_source = "db/contacts2.db"
  if os.path.isfile(contacts_source):
    print(f"\n✅ Contacts database found at {contacts_source} (not encrypted)")


if __name__ == "__main__":
  try:
    main()
  except Exception as error:
    print(f"Error: {error}")
    sys.exit(1)
