# WhatsApp msgstore.db Analysis: What's Useful

## Your Requirements vs. What's Available

### ✅ MUST-HAVE (Full Coverage)

| Requirement | Table(s) | Details |
|---|---|---|
| **Full message history** | `messages` | ~300K+ rows; primary message store |
| **Timestamps** | `messages` (timestamp, received_timestamp, send_timestamp) | Millisecond precision |
| **Reactions** | `message_reaction` | Who reacted with what emoji |
| **Replies/Quotes** | `messages_quotes` (quoted_row_id) | Links replies to original messages |
| **Media references** | `mms_metadata` (direct_path, media_key) | Encrypted media URLs + keys |
| **Group metadata** | `chat` (subject, isGroup, group_type) | Group names, member info in `group_participant` |

---

## Detailed Table Breakdown

### CORE TABLES (Essential)

#### 1. **messages** (~300K rows)
- **Key columns:**
  - `key_remote_jid`: Chat ID (WhatsApp JID format)
  - `key_from_me`: 0=received, 1=sent
  - `key_id`: Message ID (unique identifier)
  - `data`: Message text (sometimes encoded)
  - `timestamp`: When message was sent (ms since epoch)
  - `received_timestamp`: When you received it
  - `send_timestamp`: Server send time
  - `status`: Delivery status (sent, delivered, read, played)
  - `quoted_row_id`: Links to replied message
  - `media_wa_type`: Image, video, audio, document, etc.
  - `latitude`, `longitude`: Location data if shared
  - `mentioned_jids`: @mentions in group chats
  - `forwarded`: Boolean flag

- **Relevance:** **CRITICAL** — backbone of your archive

---

#### 2. **message_reaction** (variable)
- Stores emoji reactions (e.g., 👍, ❤️)
- **Columns:**
  - `message_row_id`: Links to message
  - `reaction_from_jid_row_id`: Who reacted
  - `reaction`: Emoji character
  - `reaction_timestamp`: When

- **Relevance:** **HIGH** if you want full metadata

---

#### 3. **chat** (~50-100 rows)
- All conversations (1:1 + groups)
- **Columns:**
  - `subject`: Chat name / group subject
  - `isGroup`: Boolean
  - `group_type`: If group, what type
  - `last_message_table_id`: Links to latest message
  - `hidden`: Archived/hidden chats
  - `muted`: Mute settings
  - `pinned_message_row_id`: Pinned message

- **Relevance:** **HIGH** — need this to organize messages by conversation

---

#### 4. **group_participant** (if groups exist)
- Lists members in group chats
- **Columns:**
  - `group_jid_row_id`: Which group
  - `user_jid_row_id`: Which user/member
  - `admin`: Boolean, is admin

- **Relevance:** **HIGH** if archiving group conversations

---

### MEDIA & ATTACHMENTS

#### 5. **mms_metadata** (~150+ rows)
- Media file metadata
- **Columns:**
  - `message_row_id`: Links to message
  - `direct_path`: WhatsApp's CDN path (encrypted)
  - `media_key`: Encryption key (needed to decrypt)
  - `media_key_timestamp`: When key was issued
  - `thumb_hash`, `enc_thumb_hash`: Thumbnail fingerprints
  - `insert_timestamp`: When inserted locally
- **Note:** `direct_path` is temporary (expires ~24h), so media must be downloaded at backup time

- **Relevance:** **HIGH** if you want to preserve media file references + decryption keys

---

#### 6. **message_thumbnail** (~3,460 rows)
- Embedded thumbnail BLOB (small preview image)
- **Columns:**
  - `message_row_id`: Which message
  - `thumbnail`: BLOB (JPEG image data)

- **Relevance:** **MEDIUM** — useful for preview without downloading full media

---

#### 7. **message_text** (~4,300 rows)
- Metadata for link previews, shared URLs
- **Columns:**
  - `message_row_id`: Which message
  - `description`: Preview text
  - `page_title`: Website title
  - `url`: The link
  - `font_style`, `text_color`, `background_color`: Formatting

- **Relevance:** **MEDIUM** — nice to have for web previews

---

### DELIVERY & READ RECEIPTS

#### 8. **receipt_user** (~130K rows)
- Per-user read/delivery receipts
- **Columns:**
  - `message_row_id`: Which message
  - `receipt_user_jid_row_id`: User who got the receipt
  - `receipt_timestamp`: Delivered at
  - `read_timestamp`: Read at
  - `played_timestamp`: Played (voice note) at

- **Relevance:** **MEDIUM** — useful for understanding conversation flow

---

#### 9. **missed_call_logs** (~100 rows)
- Call history (missed calls)
- **Columns:**
  - `message_row_id`: Linked message
  - `timestamp`: When called
  - `video_call`: Video vs audio
  - `group_jid_row_id`: If group call

- **Relevance:** **MEDIUM** — call history often lost

---

### CONTACTS & JIDs

#### 10. **jid** (reference table)
- Maps JID row IDs to actual WhatsApp phone numbers/usernames
- **Columns:**
  - `raw_string`: The actual phone number or group ID
  - `server`: Usually "s.whatsapp.net" for users, "g.us" for groups

- **Relevance:** **CRITICAL** — need this to decode all the JID references

---

#### 11. **wa_contacts** (or similar)
- Contact names, avatars
- **Columns:**
  - `jid`: Phone number
  - `display_name`: Saved contact name
  - `nickname`: User's nickname
  - `given_name`, `family_name`: Parts of name

- **Relevance:** **HIGH** — makes messages readable (users see names, not phone numbers)

---

### LESS CRITICAL BUT INTERESTING

- **message_vcard**: Contact cards shared in chats
- **newsletter_***: WhatsApp Newsletter (Channels) data if subscribed
- **message_view_once_media**: Disappearing media tracking
- **payment_***: Payment/transaction history (if used)
- **props**: App configuration & metadata

---

## Recommended Archive Format

Based on your requirements, export as **nested JSON** per chat:

```json
{
  "chats": [
    {
      "id": "1234567890@s.whatsapp.net",
      "name": "John Doe",
      "isGroup": false,
      "created": 1609459200000,
      "archived": false,
      "messages": [
        {
          "id": "MESSAGE_ID",
          "timestamp": 1609459200000,
          "from": "1234567890@s.whatsapp.net",
          "fromName": "John Doe",
          "text": "Hello!",
          "status": "read",  // sent|delivered|read|played
          "replies_to": {    // If this is a reply
            "message_id": "PARENT_ID",
            "text": "Original message"
          },
          "reactions": [
            { "emoji": "👍", "from": "...", "timestamp": ... }
          ],
          "media": {
            "type": "image",
            "size": 102400,
            "mimetype": "image/jpeg",
            "thumbnail": "base64_encoded",
            "media_key": "hex_string",  // Keep this for potential re-download
            "direct_path": "..."
          },
          "receipts": {
            "delivered_by": ["..."],
            "read_by": ["..."]
          }
        }
      ]
    }
  ]
}
```

---

## Summary: What to Extract

| Component | Tables | Priority | Notes |
|---|---|---|---|
| Messages | `messages` | CRITICAL | Core data |
| Replies | `messages_quotes` | CRITICAL | Preserve threading |
| Reactions | `message_reaction` | HIGH | Modern WhatsApp feature |
| Chats | `chat`, `group_participant`, `jid`, `wa_contacts` | CRITICAL | Need for organization |
| Media refs | `mms_metadata`, `message_thumbnail` | HIGH | Preserve file refs + thumbs |
| Receipts | `receipt_user` | MEDIUM | Nice-to-have metadata |
| Call history | `missed_call_logs` | MEDIUM | Often lost otherwise |
| Web previews | `message_text` | MEDIUM | Optional but useful |

---

## Next Steps

1. **Create a parser** that reads `msgstore.db` and exports to the JSON structure above.
2. **Handle JID resolution** — decode phone numbers from the `jid` table.
3. **Preserve media links** — store direct_path + media_key for later re-download if needed.
4. **Timestamp conversion** — WhatsApp uses milliseconds since epoch.
5. **Test on a single chat** first, then scale to all.
