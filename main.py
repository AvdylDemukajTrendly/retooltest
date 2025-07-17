from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import tracking_pg
import os

# === CORS Middleware to allow Retool/Frontend ===
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Allow all origins for testing, restrict in production!
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === MODELS ===
class PostRequest(BaseModel):
    video_id: str
    channel_id: str
    target_channel_id: str                     
    original_channel_name: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    video_url: Optional[str] = None
    schedule_post: Optional[datetime] = None
    target_channel_name: Optional[str] = None

class PostResponse(BaseModel):
    status: str
    fb_video_id: Optional[str] = None
    fb_post_id: Optional[str] = None
    message: Optional[str] = None

# === ENDPOINT for posting to Facebook (simulation) ===
@app.post("/post-to-facebook", response_model=PostResponse)
def post_to_facebook(req: PostRequest):
    fb_video_id = None
    fb_post_id = None

    # Simulate Facebook API logic
    if req.schedule_post:
        fb_video_id = f"FAKE_VIDEO_ID_SCHEDULED_{req.video_id}"
        fb_post_id = None
    else:
        fb_video_id = f"FAKE_VIDEO_ID_IMMEDIATE_{req.video_id}"
        fb_post_id = f"FAKE_PAGE_ID_FAKE_POST_ID_{req.video_id}"

    try:
        # Save tracking in DB via tracking_pg.py
        with tracking_pg.get_conn() as pg:
            cur = pg.cursor()
            tracking_pg.insert_repost(cur, {
                "original_video_id":      req.video_id,
                "original_channel_id":    req.channel_id,
                "original_channel_name":  req.original_channel_name,
                "original_title":         req.title,
                "original_description":   req.description,
                "original_posted_at":     datetime.now(),
                "original_views":         None,
                "original_revenue":       None,
                "reposted_video_id":      fb_video_id,
                "reposted_channel_id":    req.target_channel_id,   
                "reposted_channel_name":  req.target_channel_name,
                "reposted_title":         req.title,
                "reposted_description":   req.description,
                "reposted_at":            req.schedule_post or datetime.now(),
                "repost_number":          1,
                "video_url":              req.video_url,
                "reposted_post_id":       fb_post_id, # Added this line
            }, status="posted" if not req.schedule_post else "scheduled")
            pg.commit()

        return PostResponse(status="success", fb_video_id=fb_video_id, fb_post_id=fb_post_id)
    except Exception as e:
        # Log error
        print(f"[ERROR] Processing and tracking failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Processing and tracking failed: {str(e)}")


class UpdatePostIdRequest(BaseModel):
    new_fb_post_id: str

@app.patch("/videos/{video_id}/{reposted_channel_id}/update-post-id")
def update_scheduled_video_post_id(
    video_id: str,
    reposted_channel_id: str,
    req: UpdatePostIdRequest
):
    try:
        with tracking_pg.get_conn() as pg:
            cur = pg.cursor()
            tracking_pg.update_post_id(
                cur,
                original_video_id=video_id,
                reposted_channel_id=reposted_channel_id,
                new_post_id=req.new_fb_post_id
            )
            pg.commit()
        return {
            "status": "success",
            "message": f"Post ID updated for video {video_id} on channel {reposted_channel_id}"
        }
    except Exception as e:
        print(f"[ERROR] Failed to update post ID: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update post ID: {str(e)}")