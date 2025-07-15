#!/usr/bin/env python3
"""
Local test – uploads/schedules to Facebook and writes tracking to Postgres.
Run: python repost_pg.py  (reads first row from video_to_be_posted_3)
"""

import os, sys, time, logging
from datetime import datetime, timezone
from typing import Dict, Any
import requests, psycopg2
from dotenv import load_dotenv

import tracking_pg         # local tracker

load_dotenv()
FB_TOKEN  = os.getenv("FB_ACCESS_TOKEN","DUMMY")
FB_PAGEID = os.getenv("FB_PAGE_ID","TEST")
DRY_RUN   = os.getenv("DRY_RUN","1") == "1"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("repost_pg")

PG = dict(
    host=os.getenv("DB_HOST","localhost"),
    port=int(os.getenv("DB_PORT","5432")),
    dbname=os.getenv("DB_NAME","db"),
    user=os.getenv("DB_USER","postgres"),
    password=os.getenv("DB_PASSWORD","postgres"),
)

# ----------------------------- helpers -----------------------------
def upload(tmp, title, desc, ts) -> str:
    if DRY_RUN:
        fake = f"DRV_{int(time.time())}"
        log.info("[DRY] upload %s to %s at %d", tmp, FB_PAGEID, ts)
        return fake
    r = requests.post(
        f"https://graph.facebook.com/v23.0/{FB_PAGEID}/videos",
        files={"source":open(tmp,"rb")},
        data={"access_token":FB_TOKEN,"title":title,"description":desc,
              "published":"false","scheduled_publish_time":str(ts)},
        timeout=60)
    r.raise_for_status()
    return r.json()["id"]

# ----------------------------- main -----------------------------
def get_queue_row()->Dict[str,Any]:
    with psycopg2.connect(**PG) as pg: #type: ignore
        cur=pg.cursor()
        cur.execute("SELECT * FROM video_to_be_posted_3 LIMIT 1")
        row=cur.fetchone()
        if not row:
            log.error("Queue is empty"); sys.exit(1)
        return dict(zip([d[0] for d in cur.description], row))

def main():
    row=get_queue_row()
    title=row.get("title") or row.get("message") or ""
    desc =row.get("description") or ""
    sched=row.get("schedule_post") or row.get("schedule_dt")
    sched_dt=(datetime.fromisoformat(sched).astimezone(timezone.utc)
              if sched else datetime.now(timezone.utc))
    fb_id=upload(row["video_url"],title,desc,int(sched_dt.timestamp()))

    with tracking_pg.get_conn() as pg:
        cur=pg.cursor()
        tracking_pg.insert_repost(cur,{
            "original_video_id":row["video_id"],
            "original_channel_id":row["channel_id"],
            "original_posted_at":datetime.now(timezone.utc),
            "reposted_channel_id":row["channel_id"],
            "reposted_video_id":fb_id,
            "reposted_title":title,
            "reposted_description":desc,
            "video_url":row["video_url"],
        },"scheduled" if sched_dt>datetime.now(timezone.utc) else "posted")
        pg.commit()
    log.info("Done. Facebook video ID=%s",fb_id)
    print(fb_id)

if __name__=="__main__":
    main()
