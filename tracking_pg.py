import os
from datetime import datetime
from typing import Optional, Dict, Any
from dotenv import load_dotenv
import psycopg2

# Load environment variables from .env file
load_dotenv()

# Database connection parameters loaded from environment variables
PG_CONN = {
    "host":     os.getenv("DB_HOST"),
    "port":     int(os.getenv("DB_PORT", "5432")),
    "dbname":   os.getenv("DB_NAME"),
    "user":     os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
}

# SQL statement for inserting a new repost record
INSERT_SQL = """
INSERT INTO reposted_video_tracking (
  original_video_id, original_channel_id, original_channel_name,
  original_title, original_description, original_posted_at,
  original_views, original_revenue,
  reposted_video_id, reposted_channel_id, reposted_channel_name,
  reposted_title, reposted_description, reposted_at,
  repost_number, video_url, status,
  total_reposts_for_video,
  reposted_post_id
)
VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s);
"""

# SQL statement for updating the status and related fields of a repost record
UPDATE_STATUS_SQL = """
UPDATE reposted_video_tracking
SET status = %s,
    reposted_video_id = COALESCE(%s, reposted_video_id),
    reposted_at       = COALESCE(%s, reposted_at),
    repost_number     = repost_number + 1,
    last_checked_at   = NOW()
WHERE original_video_id = %s
  AND reposted_channel_id = %s;
"""

def get_conn():
    """
    Establish and return a new database connection using the loaded environment variables.
    """
    return psycopg2.connect(**PG_CONN)

def insert_repost(cur, data: Dict[str, Any], status: str = "queued"):
    """
    Insert a new repost record into the reposted_video_tracking table.
    """
    # Step 1: Get the current number of reposts for this video
    cur.execute(
        "SELECT COUNT(*) FROM reposted_video_tracking WHERE original_video_id = %s",
        (data["original_video_id"],)
    )
    repost_number_for_this_entry = cur.fetchone()[0] + 1  # repost_number is count + 1

    # Step 2: Extract the short post_id if it comes as "PAGEID_POSTID"
    reposted_post_id_full = data.get("reposted_post_id")
    reposted_post_id_short = None
    if reposted_post_id_full and '_' in reposted_post_id_full:
        reposted_post_id_short = reposted_post_id_full.split('_')[-1]
    elif reposted_post_id_full:
        reposted_post_id_short = reposted_post_id_full

    # Step 3: Insert the new repost record with the correct repost_number
    cur.execute(INSERT_SQL, (
        data["original_video_id"], data["original_channel_id"], data.get("original_channel_name"),
        data.get("original_title"), data.get("original_description"), data["original_posted_at"],
        data.get("original_views"), data.get("original_revenue"),
        data.get("reposted_video_id"), data["reposted_channel_id"], data.get("reposted_channel_name"),
        data.get("reposted_title"), data.get("reposted_description"), data.get("reposted_at"),
        repost_number_for_this_entry,  # This is the current repost number (1, 2, 3, ...)
        data.get("video_url"), status,
        repost_number_for_this_entry,  # Initial value for total_reposts_for_video, will be updated below
        reposted_post_id_short
    ))

    # Step 4: Calculate the new total number of reposts after the insert
    cur.execute(
        "SELECT COUNT(*) FROM reposted_video_tracking WHERE original_video_id = %s",
        (data["original_video_id"],)
    )
    final_total_reposts = cur.fetchone()[0]

    # Step 5: Update the total_reposts_for_video column for all records with this original_video_id
    cur.execute("""
        UPDATE reposted_video_tracking
        SET total_reposts_for_video = %s
        WHERE original_video_id = %s;
    """, (final_total_reposts, data["original_video_id"]))

def update_status(
    cur,
    original_video_id: str,
    channel_id: str,
    status: str,
    reposted_video_id: Optional[str] = None,
    reposted_at: Optional[datetime] = None
):
    """
    Update the status, reposted_video_id, reposted_at, and repost_number for a given video/channel pair.
    """
    cur.execute(UPDATE_STATUS_SQL, (
        status, reposted_video_id, reposted_at,
        original_video_id, channel_id
    ))

# SQL statement for updating the reposted_post_id and marking the repost as posted
UPDATE_POST_ID_SQL = """
UPDATE reposted_video_tracking
SET reposted_post_id = %s,
    reposted_at       = NOW(),
    status            = 'posted'
WHERE original_video_id       = %s
  AND reposted_channel_id     = %s;
"""

def update_post_id(cur, original_video_id: str, reposted_channel_id: str, new_post_id: str):
    """
    Update the reposted_post_id for a given original_video_id and reposted_channel_id.
    If the new_post_id is in the format "PAGEID_POSTID", only the POST_ID part is stored.
    Also sets reposted_at to NOW() and status to 'posted'.
    """
    # Extract the short post_id as before
    reposted_post_id_short = None
    if new_post_id and '_' in new_post_id:
        reposted_post_id_short = new_post_id.split('_')[-1]
    elif new_post_id:
        reposted_post_id_short = new_post_id

    cur.execute(UPDATE_POST_ID_SQL, (
        reposted_post_id_short,
        original_video_id,
        reposted_channel_id
    ))
