create table if not exists public.reposted_video_tracking
(
    id                      serial
        primary key,
    original_video_id       text      not null,
    original_channel_id     text      not null,
    original_channel_name   text,
    original_title          text,
    original_description    text,
    original_posted_at      timestamp not null,
    original_views          integer,
    original_revenue        numeric(12, 2),
    reposted_video_id       text,
    reposted_channel_id     text      not null,
    reposted_channel_name   text,
    reposted_title          text,
    reposted_description    text,
    reposted_at             timestamp,
    reposted_views          integer,
    reposted_revenue        numeric(12, 2),
    repost_number           integer     default 1,
    last_checked_at         timestamp,
    status                  varchar(20) default 'queued'::character varying,
    video_url               text,
    total_reposts_for_video integer     default 1,
    reposted_post_id        text
);


