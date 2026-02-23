"""WhatsApp msgstore.db → JSON parser.

Reads a decrypted WhatsApp SQLite database and produces a structured dict
with messages, replies, reactions, media references, group metadata, call logs,
message edit history, polls with votes, and thumbnail previews.
"""

from __future__ import annotations

import base64
import os
import sqlite3
from datetime import datetime, timezone

# ──────────────────────────────────────────────
# WhatsApp message_type mapping (from schema inspection)
# ──────────────────────────────────────────────
MESSAGE_TYPES = {
    0: "text",
    1: "image",
    2: "audio",
    3: "video",
    7: "system",
    9: "document",
    10: "missed_call",
    13: "gif",
    15: "deleted",
    16: "live_location",
    20: "sticker",
    27: "poll",
    42: "view_once_image",
    43: "view_once_video",
    64: "poll_update",
    66: "call_log",
    90: "e2e_notification",
    99: "ephemeral_notification",
    112: "community_alert",
    116: "event",
}


def ts_to_iso(ts_ms: int | None) -> str | None:
    """Convert WhatsApp millisecond timestamp to ISO 8601 string."""
    if not ts_ms or ts_ms <= 0:
        return None
    try:
        return datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).isoformat()
    except (OSError, ValueError):
        return None



def get_display_name(jid: str, contacts_mapping: dict[str, str]) -> tuple[str, bool]:
    """
    Get human-readable name for a JID.
    
    Returns: (name, found_in_contacts)
    """
    if not jid:
        return ("Unknown", False)
    
    # For group chats, use the group ID
    if jid.endswith("@g.us"):
        return (jid, False)
    
    # Extract phone number from JID (e.g., "358401234567@s.whatsapp.net" -> "358401234567")
    phone = jid.split("@")[0] if "@" in jid else jid
    
    # Try with +, then without
    for variant in [f"+{phone}", phone]:
        if variant in contacts_mapping:
            return (contacts_mapping[variant], True)
    
    # Fallback to phone number
    return (phone, False)


def build_jid_map(cursor: sqlite3.Cursor) -> dict[int, str]:
    """Build a mapping from jid row ID → raw JID string."""
    cursor.execute("SELECT _id, raw_string FROM jid")
    return {row[0]: row[1] for row in cursor.fetchall()}


def build_chat_list(cursor: sqlite3.Cursor, jid_map: dict[int, str]) -> list[dict]:
    """Load all chats with metadata."""
    cursor.execute("""
        SELECT
            _id,
            jid_row_id,
            subject,
            group_type,
            created_timestamp,
            archived,
            ephemeral_expiration
        FROM chat
        ORDER BY sort_timestamp DESC
    """)

    chats = []
    for row in cursor.fetchall():
        chat_id, jid_row_id, subject, group_type, created_ts, archived, ephemeral = row
        jid = jid_map.get(jid_row_id, "")
        is_group = jid.endswith("@g.us") if jid else False

        chats.append({
            "chat_row_id": chat_id,
            "jid": jid,
            "name": subject if subject else jid.split("@")[0] if jid else str(chat_id),
            "is_group": is_group,
            "group_type": group_type,
            "created": ts_to_iso(created_ts),
            "archived": bool(archived),
            "ephemeral_seconds": ephemeral if ephemeral else None,
            "messages": [],
        })
    return chats


def build_group_participants(cursor: sqlite3.Cursor) -> dict[str, list[dict]]:
    """Load group participants keyed by group JID."""
    cursor.execute("""
        SELECT gjid, jid, admin
        FROM group_participants
    """)
    groups: dict[str, list[dict]] = {}
    for gjid, member_jid, admin in cursor.fetchall():
        groups.setdefault(gjid, []).append({
            "jid": member_jid,
            "is_admin": bool(admin),
        })
    return groups


def build_reactions_map(cursor: sqlite3.Cursor, jid_map: dict[int, str]) -> dict[int, list[dict]]:
    """Build mapping from parent message row ID → list of reactions."""
    cursor.execute("""
        SELECT
            ao.parent_message_row_id,
            ao.sender_jid_row_id,
            ar.reaction,
            ar.sender_timestamp
        FROM message_add_on ao
        JOIN message_add_on_reaction ar ON ar.message_add_on_row_id = ao._id
        WHERE ao.message_add_on_type = 56
    """)
    reactions: dict[int, list[dict]] = {}
    for parent_id, sender_jid_row_id, emoji, ts in cursor.fetchall():
        reactions.setdefault(parent_id, []).append({
            "emoji": emoji,
            "from": jid_map.get(sender_jid_row_id, ""),
            "timestamp": ts_to_iso(ts),
        })
    return reactions


def build_quoted_map(cursor: sqlite3.Cursor) -> dict[int, dict]:
    """Build mapping from message row ID → quoted (replied-to) message info."""
    cursor.execute("""
        SELECT
            message_row_id,
            from_me,
            sender_jid_row_id,
            key_id,
            message_type,
            text_data
        FROM message_quoted
    """)
    quoted: dict[int, dict] = {}
    for msg_id, from_me, sender_jid, key_id, msg_type, text in cursor.fetchall():
        quoted[msg_id] = {
            "from_me": bool(from_me),
            "sender_jid_row_id": sender_jid,
            "key_id": key_id,
            "type": MESSAGE_TYPES.get(msg_type, f"unknown_{msg_type}"),
            "text": text,
        }
    return quoted


def build_media_map(cursor: sqlite3.Cursor) -> dict[int, dict]:
    """Build mapping from message row ID → media metadata."""
    cursor.execute("""
        SELECT
            message_row_id,
            mime_type,
            file_path,
            file_size,
            file_length,
            media_duration,
            media_caption,
            width,
            height,
            media_name,
            file_hash
        FROM message_media
    """)
    media: dict[int, dict] = {}
    for row in cursor.fetchall():
        msg_id = row[0]
        media[msg_id] = {
            "mime_type": row[1],
            "file_path": row[2],
            "file_size": row[3] or row[4],
            "duration_seconds": row[5] if row[5] else None,
            "caption": row[6],
            "width": row[7] if row[7] else None,
            "height": row[8] if row[8] else None,
            "file_name": row[9],
            "file_hash": row[10],
        }
    return media


def build_call_logs_map(cursor: sqlite3.Cursor, jid_map: dict[int, str]) -> dict[int, dict]:
    """Build mapping from chat row ID → call log entry."""
    cursor.execute("""
        SELECT
            _id,
            jid_row_id,
            from_me,
            call_id,
            timestamp,
            video_call,
            duration,
            call_result,
            bytes_transferred
        FROM call_log
    """)
    CALL_RESULTS = {
        0: "unknown",
        2: "missed",
        3: "rejected",
        4: "busy",
        5: "answered",
        7: "unavailable",
        8: "declined",
    }
    calls: dict[int, list[dict]] = {}
    for row in cursor.fetchall():
        call_id, jid_row_id, from_me, call_sid, ts, video, dur, result, bytes_tx = row
        calls.setdefault(jid_row_id, []).append({
            "call_id": call_sid,
            "timestamp": ts_to_iso(ts),
            "from_me": bool(from_me),
            "video_call": bool(video),
            "duration_seconds": dur if dur else 0,
            "result": CALL_RESULTS.get(result, f"result_{result}"),
            "bytes_transferred": bytes_tx if bytes_tx else 0,
        })
    return calls


def build_edit_history_map(cursor: sqlite3.Cursor) -> dict[int, dict]:
    """Build mapping from message row ID → edit info."""
    cursor.execute("""
        SELECT
            message_row_id,
            original_key_id,
            edited_timestamp,
            sender_timestamp
        FROM message_edit_info
    """)
    edits: dict[int, dict] = {}
    for msg_id, orig_key, edit_ts, sender_ts in cursor.fetchall():
        edits[msg_id] = {
            "original_key_id": orig_key,
            "edited_at": ts_to_iso(edit_ts),
            "sender_timestamp": ts_to_iso(sender_ts),
        }
    return edits


def build_thumbnails_map(cursor: sqlite3.Cursor) -> dict[int, str]:
    """Build mapping from message row ID → base64-encoded thumbnail."""
    cursor.execute("""
        SELECT
            message_row_id,
            thumbnail
        FROM message_thumbnail
    """)
    thumbnails: dict[int, str] = {}
    for msg_id, thumb_blob in cursor.fetchall():
        if thumb_blob:
            thumbnails[msg_id] = base64.b64encode(thumb_blob).decode("utf-8")
    return thumbnails


def build_polls_map(cursor: sqlite3.Cursor, jid_map: dict[int, str]) -> dict[int, dict]:
    """Build mapping from message row ID → poll data with options and votes."""
    # Get poll metadata
    cursor.execute("""
        SELECT
            message_row_id,
            selectable_options_count,
            poll_type
        FROM message_poll
    """)
    polls: dict[int, dict] = {}
    for msg_id, opt_count, poll_type in cursor.fetchall():
        polls[msg_id] = {
            "max_selectable": opt_count,
            "poll_type": poll_type,
            "options": [],
        }

    # Get poll options with vote totals
    cursor.execute("""
        SELECT
            message_row_id,
            _id,
            option_name,
            vote_total
        FROM message_poll_option
    """)
    option_id_to_msg: dict[int, int] = {}
    for msg_id, opt_id, opt_name, vote_total in cursor.fetchall():
        if msg_id in polls:
            polls[msg_id]["options"].append({
                "option_id": opt_id,
                "text": opt_name,
                "vote_count": vote_total if vote_total else 0,
                "voters": [],
            })
            option_id_to_msg[opt_id] = msg_id

    # Get who voted for what
    cursor.execute("""
        SELECT
            ao.parent_message_row_id,
            ao.sender_jid_row_id,
            pv.sender_timestamp,
            vso.message_poll_option_id
        FROM message_add_on ao
        JOIN message_add_on_poll_vote pv ON pv.message_add_on_row_id = ao._id
        JOIN message_add_on_poll_vote_selected_option vso ON vso.message_add_on_row_id = ao._id
        WHERE ao.message_add_on_type = 67
    """)
    votes_by_msg_option: dict[tuple[int, int], list[dict]] = {}
    for parent_msg_id, voter_jid_row_id, vote_ts, opt_id in cursor.fetchall():
        key = (parent_msg_id, opt_id)
        votes_by_msg_option.setdefault(key, []).append({
            "from": jid_map.get(voter_jid_row_id, ""),
            "timestamp": ts_to_iso(vote_ts),
        })

    # Attach voters to the correct option
    for (msg_id, opt_id), voters in votes_by_msg_option.items():
        if msg_id in polls:
            for option in polls[msg_id]["options"]:
                if option["option_id"] == opt_id:
                    option["voters"] = voters
                    break

    return polls


def build_messages(
    cursor: sqlite3.Cursor,
    jid_map: dict[int, str],
    reactions_map: dict[int, list[dict]],
    quoted_map: dict[int, dict],
    media_map: dict[int, dict],
    edit_history_map: dict[int, dict],
    polls_map: dict[int, dict],
    thumbnails_map: dict[int, str],
    contacts_mapping: dict[str, str] | None = None,
) -> dict[int, list[dict]]:
    """Load all messages, grouped by chat_row_id."""
    cursor.execute("""
        SELECT
            _id,
            chat_row_id,
            from_me,
            key_id,
            sender_jid_row_id,
            status,
            timestamp,
            received_timestamp,
            message_type,
            text_data,
            starred
        FROM message
        WHERE _id != 1
        ORDER BY timestamp ASC
    """)

    STATUS_MAP = {0: "received", 4: "sent", 5: "delivered", 6: "read", 13: "played"}
    if contacts_mapping is None:
        contacts_mapping = {}

    messages_by_chat: dict[int, list[dict]] = {}
    for row in cursor.fetchall():
        msg_id, chat_row_id, from_me, key_id, sender_jid_row_id, status, ts, recv_ts, msg_type, text, starred = row

        msg: dict = {
            "id": msg_id,
            "key_id": key_id,
            "from_me": bool(from_me),
            "timestamp": ts_to_iso(ts),
            "timestamp_ms": ts,
            "type": MESSAGE_TYPES.get(msg_type, f"unknown_{msg_type}"),
            "text": text,
            "status": STATUS_MAP.get(status, f"status_{status}"),
            "starred": bool(starred),
        }

        # Sender (relevant in groups)
        if sender_jid_row_id and sender_jid_row_id in jid_map:
            sender_jid = jid_map[sender_jid_row_id]
            msg["sender_jid"] = sender_jid
            # Add human-readable sender name if available
            sender_name, found_in_contacts = get_display_name(sender_jid, contacts_mapping)
            if found_in_contacts:  # Only add if we found it in contacts
                msg["sender_name"] = sender_name

        # Received timestamp
        if recv_ts and recv_ts > 0:
            msg["received_timestamp"] = ts_to_iso(recv_ts)

        # Reply / quote
        if msg_id in quoted_map:
            msg["reply_to"] = quoted_map[msg_id]

        # Reactions
        if msg_id in reactions_map:
            msg["reactions"] = reactions_map[msg_id]

        # Media
        if msg_id in media_map:
            msg["media"] = media_map[msg_id]

        # Edit history
        if msg_id in edit_history_map:
            msg["edited"] = edit_history_map[msg_id]

        # Poll data
        if msg_id in polls_map:
            msg["poll"] = polls_map[msg_id]

        # Thumbnail (base64-encoded preview image)
        if msg_id in thumbnails_map:
            msg["thumbnail"] = thumbnails_map[msg_id]

        messages_by_chat.setdefault(chat_row_id, []).append(msg)

    return messages_by_chat


def parse(db_path: str, contacts_mapping: dict[str, str] | None = None) -> dict:
    """Parse the WhatsApp database and return the full archive dict."""
    if contacts_mapping is None:
        contacts_mapping = {}

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print(f"  {len(contacts_mapping)} contacts loaded.")
    jid_map = build_jid_map(cursor)
    print(f"  {len(jid_map)} JIDs loaded.")

    print("Loading chats...")
    chats = build_chat_list(cursor, jid_map)
    print(f"  {len(chats)} chats loaded.")

    print("Loading group participants...")
    group_participants = build_group_participants(cursor)
    print(f"  {len(group_participants)} groups with participant data.")

    print("Loading reactions...")
    reactions_map = build_reactions_map(cursor, jid_map)
    total_reactions = sum(len(v) for v in reactions_map.values())
    print(f"  {total_reactions} reactions across {len(reactions_map)} messages.")

    print("Loading quoted messages (replies)...")
    quoted_map = build_quoted_map(cursor)
    print(f"  {len(quoted_map)} replies loaded.")

    print("Loading media metadata...")
    media_map = build_media_map(cursor)
    print(f"  {len(media_map)} media entries loaded.")

    print("Loading thumbnails...")
    thumbnails_map = build_thumbnails_map(cursor)
    print(f"  {len(thumbnails_map)} thumbnails loaded.")

    print("Loading call logs...")
    call_logs_map = build_call_logs_map(cursor, jid_map)
    total_calls = sum(len(v) for v in call_logs_map.values())
    print(f"  {total_calls} call log entries loaded.")

    print("Loading message edit history...")
    edit_history_map = build_edit_history_map(cursor)
    print(f"  {len(edit_history_map)} edited messages loaded.")

    print("Loading polls...")
    polls_map = build_polls_map(cursor, jid_map)
    total_poll_votes = sum(sum(len(opt["voters"]) for opt in p["options"]) for p in polls_map.values())
    print(f"  {len(polls_map)} polls loaded with {total_poll_votes} votes.")

    print("Loading messages...")
    messages_by_chat = build_messages(cursor, jid_map, reactions_map, quoted_map, media_map, edit_history_map, polls_map, thumbnails_map, contacts_mapping)
    total_messages = sum(len(v) for v in messages_by_chat.values())
    print(f"  {total_messages} messages loaded across {len(messages_by_chat)} chats.")

    # Attach messages, participants, and call logs to chats
    for chat in chats:
        chat_id = chat.pop("chat_row_id")
        chat["messages"] = messages_by_chat.get(chat_id, [])
        chat["message_count"] = len(chat["messages"])

        # Attach group participants if applicable
        if chat["is_group"] and chat["jid"] in group_participants:
            chat["participants"] = group_participants[chat["jid"]]

        # Attach call history
        jid_row_id = None
        for jid_id, jid_str in jid_map.items():
            if jid_str == chat["jid"]:
                jid_row_id = jid_id
                break
        if jid_row_id and jid_row_id in call_logs_map:
            chat["call_history"] = call_logs_map[jid_row_id]
            chat["total_calls"] = len(call_logs_map[jid_row_id])

    conn.close()

    return {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "source_db": os.path.basename(db_path),
        "total_chats": len(chats),
        "total_messages": total_messages,
        "contacts_count": len(contacts_mapping),
        "chats": chats,
    }


