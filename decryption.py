encryptionKey = ""

import re
import os

trimmedEncryptionKey = re.sub(r'[^0-9a-fA-F]', '', encryptionKey)
if not trimmedEncryptionKey:
  raise Exception("Missing encryptionKey")

# Convert the hexadecimal key to a key file
os.system(f"wacreatekey --hex \"{encryptionKey}\"")

# Find and decrypt all .crypt15 files
import glob
import os
crypt15_files = glob.glob('db/*.crypt15')
if not crypt15_files:
  raise Exception("No .crypt15 files found in the current directory.")
else:
  for encrypted_file in crypt15_files:
    decrypted_file = os.path.splitext(encrypted_file)[0]  # Remove the .crypt15 extension
    print(f"Decrypting {encrypted_file} to {decrypted_file}")
    os.system(f"wadecrypt encrypted_backup.key {encrypted_file} {decrypted_file}")
    print(f"Finished decrypting {encrypted_file}")
