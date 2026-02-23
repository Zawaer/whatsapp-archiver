# WhatsApp Backup Exporter

Export and decrypt WhatsApp Android backups into machine-readable files for long-term personal archiving.

This project is designed for people who want to preserve memories and chat history in a complete, structured format (SQLite/JSON-ready), not just plain text exports.

## Why this project?

WhatsApp’s built-in Export Chat is useful for quick sharing, but it is not archival-grade:
- Loses rich structure (replies, reactions, metadata context)
- Manual per-chat workflow
- Incomplete media handling

This project focuses on:
- Full message history snapshots
- Reply/reaction preservation (as stored in WhatsApp DB)
- Timestamps and metadata
- Media references and files
- Group/chat metadata
- Local-first workflow without device rooting

## Approach

This project uses an **ADB + local decryption** workflow:

Phone (WhatsApp data)
→ pull encrypted backup files via ADB
→ decrypt locally with your backup key
→ get readable SQLite output
→ parse to JSON / custom viewer (next step)

### Why this approach?
- No persistent high-privilege Google master token storage
- More stable long-term than undocumented cloud scraping
- Always captures your latest on-device backup state
- Better security model for personal archival

## Current project status

Current files in this repo:
- `adb-commands.txt` – ADB commands to pull backup files from Android storage
- `decryption.py` – local Python script to decrypt `.crypt15` backups

Planned:
- Parser that converts decrypted DBs into structured JSON
- Searchable local viewer/web UI for memory browsing
- One-command backup + decrypt + archive workflow

## Requirements

- Android phone with WhatsApp backups enabled
- USB cable
- USB debugging enabled on Android
- ADB installed (`platform-tools`)
- Python 3
- `wa-crypt-tools` installed

Install decryption dependency:

```bash
python3 -m pip install wa-crypt-tools
```

## Quick start

### 1) Pull backup files from phone

From project root:

```bash
adb pull /storage/emulated/0/Android/media/com.whatsapp/WhatsApp/Databases ./
adb pull /storage/emulated/0/Android/media/com.whatsapp/WhatsApp/Backups ./
```

(Equivalent commands are in `adb-commands.txt`.)

### 2) Add your backup key

Open `decryption.py` and set your backup key in `encryptionKey`.

> Expected format: 64 hex characters.

### 3) Run decryption

```bash
python3 decryption.py
```

The script scans the current directory for `.crypt15` files and attempts to decrypt each one.

## Output

Typical output artifacts:
- Decrypted SQLite database(s) (for example `msgstore.db`)
- Optional ZIP/media-related backup artifacts depending on backup contents

These files are suitable for:
- Programmatic processing
- JSON conversion
- Custom searchable archive viewers

## Security notes

- Treat the backup key and decrypted database as sensitive personal data.
- Do not commit keys or private backups to public repositories.
- Prefer encrypted storage for archive snapshots.
- This project intentionally avoids long-lived cloud auth tokens as the primary extraction method.

## Suggested archival workflow

- Run monthly (or manually when desired):
  1. Connect phone
  2. Run ADB pull
  3. Run decryption
  4. Store snapshot in encrypted archive storage

This gives high data completeness with minimal operational risk.

## Limitations

- Requires physically connecting phone when extracting data
- Depends on backup file compatibility (`.crypt15` and related tooling)
- Parser/viewer is still in progress

## Disclaimer

This tool is for lawful personal backup/archival use of your own data. You are responsible for complying with local laws, platform terms, and privacy obligations.
