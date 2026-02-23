#!/bin/bash
# One-command WhatsApp backup workflow

set -e  # Exit on error

echo "📱 WhatsApp Backup & Archive Workflow"
echo "======================================"
echo ""

# Step 1: Extract from phone
echo "Step 1️⃣  Extracting from Android phone via ADB..."
python3 adb_extract.py || {
    echo "⚠️  ADB extraction failed. Make sure phone is connected with USB debugging enabled."
    echo "    Run manually: python3 adb_extract.py"
    exit 1
}

# Step 2: Setup key (skip if already done)
if [ ! -f "encrypted_backup.key" ]; then
    echo ""
    echo "Step 2️⃣  Setting up encryption key (one-time)..."
    python3 key_setup.py || {
        echo "❌ Key setup failed."
        exit 1
    }
else
    echo ""
    echo "Step 2️⃣  Encryption key already exists, skipping..."
fi

# Step 3: Decrypt
echo ""
echo "Step 3️⃣  Decrypting WhatsApp database..."
python3 decryption.py || {
    echo "❌ Decryption failed."
    exit 1
}

# Step 4: Export contacts from VCF
echo ""
echo "Step 4️⃣  Exporting contacts from VCF..."
if [ -f "db/contacts.vcf" ]; then
    python3 vcf_to_contacts.py || {
        echo "⚠️  Contact export failed, continuing without contact names..."
    }
else
    echo "⚠️  contacts.vcf not found. Export contacts from your phone's Contacts app first."
    echo "    (Save to db/contacts.vcf and re-run this script)"
fi

# Step 5: Generate archive
echo ""
echo "Step 5️⃣  Generating JSON archive..."
python3 parse_db.py || {
    echo "❌ Archive generation failed."
    exit 1
}

echo ""
echo "✅ Done! Archive saved to output/archive.json"
echo ""
echo "📊 Next steps:"
echo "   - Back up output/archive.json to encrypted storage"
echo "   - Run this script again monthly for fresh backup"
