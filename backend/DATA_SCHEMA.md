# SimPPL Dataset Schema Inference

This document was inferred from the actual JSONL file at `backend/data/data.jsonl`, not from assumptions.

## Dataset Shape

- File format: JSONL
- Row count: 8,799
- Root object shape: `{"kind": "t3", "data": {...}}`
- Observed root kinds: only `t3`
- Interpretation: every row is a Reddit submission/post object, not a mixed-platform or mixed-entity corpus
- Total distinct keys under `data`: 114
- Keys present on every row: 97

## 1. Field-By-Field Schema Summary

### Root-Level Fields

| Raw field | Presence | Type(s) | Notes |
|---|---:|---|---|
| `kind` | 8,799 / 8,799 | `str` | Always `t3`, meaning Reddit link/self post |
| `data` | 8,799 / 8,799 | `dict` | Full Reddit submission payload |

### Core Post Identity And Time

| Raw field | Presence | Type(s) | Notes |
|---|---:|---|---|
| `id` | 8,799 / 8,799 | `str` | Stable Reddit post id without `t3_` prefix |
| `name` | 8,799 / 8,799 | `str` | Full Reddit thing id, usually `t3_<id>` |
| `created` | 8,799 / 8,799 | `float` | Unix timestamp in seconds |
| `created_utc` | 8,799 / 8,799 | `float` | UTC Unix timestamp in seconds; best canonical time field |
| `edited` | 8,799 / 8,799 | `bool`, `float` | `false` when not edited; timestamp when edited |
| `permalink` | 8,799 / 8,799 | `str` | Relative Reddit path |
| `url` | 8,799 / 8,799 | `str` | External URL for link posts, Reddit URL for self posts |
| `domain` | 8,799 / 8,799 | `str` | Link domain; `self.<subreddit>` for self posts; 89 empty strings |

### Core Content Fields

| Raw field | Presence | Type(s) | Notes |
|---|---:|---|---|
| `title` | 8,799 / 8,799 | `str` | Always populated; primary text for all posts |
| `selftext` | 8,799 / 8,799 | `str` | Present but empty on 5,891 rows; non-empty on 2,903 rows |
| `selftext_html` | 8,799 / 8,799 | `str`, `None` | HTML rendering of `selftext`; non-null on 2,908 rows |
| `is_self` | 8,799 / 8,799 | `bool` | True on 2,059 rows; matches self-post behavior |
| `thumbnail` | 8,799 / 8,799 | `str` | Often sentinel values like `default`, `self`, `image`; 116 empty strings |
| `preview` | 6,239 / 8,799 | `dict` | Image preview metadata when available |
| `media` | 8,799 / 8,799 | `dict`, `None` | Non-null on 548 rows; embedded media such as YouTube |
| `secure_media` | 8,799 / 8,799 | `dict`, `None` | Secure version of media payload; same sparsity as `media` |
| `media_metadata` | 163 / 8,799 | `dict` | Gallery/media asset metadata |
| `gallery_data` | 147 / 8,799 | `dict` | Gallery item ordering and ids |

### Author And Community Fields

| Raw field | Presence | Type(s) | Notes |
|---|---:|---|---|
| `author` | 8,799 / 8,799 | `str` | Main visible username; 120 `[deleted]` values |
| `author_fullname` | 8,679 / 8,799 | `str`, missing | Stable Reddit user thing id when available |
| `subreddit` | 8,799 / 8,799 | `str` | Community name |
| `subreddit_id` | 8,799 / 8,799 | `str` | Stable Reddit subreddit id |
| `subreddit_name_prefixed` | 8,799 / 8,799 | `str` | Usually `r/<subreddit>` |
| `subreddit_type` | 8,799 / 8,799 | `str` | Community visibility/type |
| `author_flair_text` | 8,799 / 8,799 | `str`, `None` | Non-null on 2,753 rows; 30 empty strings |
| `author_flair_richtext` | 8,799 / 8,799 | `list` | Usually empty |
| `author_flair_text_color` | 8,799 / 8,799 | `str`, `None` | Optional flair metadata |
| `author_flair_background_color` | 8,799 / 8,799 | `str`, `None` | Optional flair metadata |
| `author_flair_template_id` | 8,799 / 8,799 | `str`, `None` | Optional flair metadata |
| `author_flair_type` | 8,799 / 8,799 | `str` | Flair rendering mode |
| `link_flair_text` | 8,799 / 8,799 | `str`, `None` | Non-null on 5,863 rows |
| `link_flair_richtext` | 8,799 / 8,799 | `list` | Usually empty |
| `link_flair_text_color` | 8,799 / 8,799 | `str`, `None` | Optional |
| `link_flair_background_color` | 8,799 / 8,799 | `str`, `None` | Optional |
| `link_flair_css_class` | 8,799 / 8,799 | `str`, `None` | Optional legacy flair field |
| `link_flair_type` | 8,799 / 8,799 | `str` | Flair rendering mode |

### Engagement And Ranking Fields

| Raw field | Presence | Type(s) | Notes |
|---|---:|---|---|
| `score` | 8,799 / 8,799 | `int` | Net score |
| `ups` | 8,799 / 8,799 | `int` | Upvotes snapshot |
| `downs` | 8,799 / 8,799 | `int` | Always present; not always meaningful on Reddit APIs |
| `upvote_ratio` | 8,799 / 8,799 | `float` | Ratio of positive votes |
| `num_comments` | 8,799 / 8,799 | `int` | Comment count |
| `total_awards_received` | 8,799 / 8,799 | `int` | Award count |
| `gilded` | 8,799 / 8,799 | `int` | Legacy gilding count |
| `gildings` | 8,799 / 8,799 | `dict` | Award details map |
| `all_awardings` | 8,799 / 8,799 | `list` | Award detail objects |
| `awarders` | 8,799 / 8,799 | `list` | Usually empty |

### Visibility, Moderation, And State Fields

| Raw field | Presence | Type(s) | Notes |
|---|---:|---|---|
| `saved` | 8,799 / 8,799 | `bool` | Viewer-specific state; not useful as dataset fact |
| `clicked` | 8,799 / 8,799 | `bool` | Viewer-specific state |
| `hidden` | 8,799 / 8,799 | `bool` | Viewer-specific state |
| `archived` | 8,799 / 8,799 | `bool` | Post state |
| `locked` | 8,799 / 8,799 | `bool` | Moderation state |
| `stickied` | 8,799 / 8,799 | `bool` | Moderator-pinned in subreddit listing |
| `pinned` | 8,799 / 8,799 | `bool` | Additional pinned flag |
| `spoiler` | 8,799 / 8,799 | `bool` | Content warning flag |
| `over_18` | 8,799 / 8,799 | `bool` | NSFW flag |
| `quarantine` | 8,799 / 8,799 | `bool` | Community quarantine flag at post snapshot time |
| `is_meta` | 8,799 / 8,799 | `bool` | Reddit metadata classification |
| `is_original_content` | 8,799 / 8,799 | `bool` | OC flag |
| `is_crosspostable` | 8,799 / 8,799 | `bool` | Crosspost policy |
| `can_mod_post` | 8,799 / 8,799 | `bool` | Viewer/mod capability flag |
| `is_created_from_ads_ui` | 8,799 / 8,799 | `bool` | Mostly irrelevant for analysis |
| `send_replies` | 8,799 / 8,799 | `bool` | User preference flag |
| `is_video` | 8,799 / 8,799 | `bool` | Video flag |
| `is_gallery` | 8,799 / 8,799 | `bool` | Gallery indicator |
| `is_reddit_media_domain` | 8,799 / 8,799 | `bool` | Helpful for distinguishing hosted media |
| `is_robot_indexable` | 8,799 / 8,799 | `bool` | Crawlability flag |
| `visited` | 8,799 / 8,799 | `bool` | Viewer-specific state |
| `no_follow` | 8,799 / 8,799 | `bool` | Link annotation |
| `hide_score` | 8,799 / 8,799 | `bool` | UI flag |

### Nested And Relationship Fields

| Raw field | Presence | Type(s) | Notes |
|---|---:|---|---|
| `crosspost_parent` | 238 / 8,799 | `str` | Parent Reddit thing id for crossposts |
| `crosspost_parent_list` | 238 / 8,799 | `list` | Embedded parent-post objects; one row had empty list |
| `media_embed` | 8,799 / 8,799 | `dict` | Usually empty dict |
| `secure_media_embed` | 8,799 / 8,799 | `dict` | Usually empty dict |
| `preview.images` | nested | `list` | Preview images with source and resolutions |
| `gallery_data.items` | nested | `list` | Gallery asset ordering |
| `media_metadata.*` | nested | `dict` | Media attributes keyed by asset id |

### Sparse Or Mostly-Irrelevant Reddit API Fields

These fields exist, but are implementation noise for this app unless a specific feature needs them:

- `approved_at_utc`
- `approved_by`
- `banned_at_utc`
- `banned_by`
- `category`
- `content_categories`
- `discussion_type`
- `likes`
- `mod_note`
- `mod_reason_by`
- `mod_reason_title`
- `num_reports`
- `removed_by`
- `report_reasons`
- `top_awarded_type`
- `view_count`
- `pwls`
- `treatment_tags`
- `user_reports`
- `mod_reports`
- `removal_reason`
- `allow_live_comments`
- `contest_mode`
- `wls`
- `whitelist_status`
- `parent_whitelist_status`
- `thumbnail_height`
- `thumbnail_width`
- `suggested_sort`
- `author_premium`
- `distinguished`
- `post_hint`
- `url_overridden_by_dest`

Several of these are always null; others are operational Reddit flags rather than meaningful investigative features.

## 2. Recommended Canonical Internal Model

The source file is a post-centric Reddit export. The cleanest app model is normalized around `Post`, with linked `Author`, `Community`, `Link`, `Entity`, and derived analysis metadata.

### Canonical `Post`

```text
Post
- post_id: str                      # from data.id
- platform: Literal["reddit"]
- platform_item_id: str             # from data.name (t3_xxx)
- source_kind: Literal["submission"]
- created_at: datetime              # from created_utc
- edited_at: datetime | None        # from edited if numeric
- title: str
- body_text: str | None             # normalized selftext
- full_text: str                    # title + "\n\n" + body_text when body exists
- permalink_url: str                # https://www.reddit.com + permalink
- canonical_url: str                # external url if link post else permalink_url
- domain: str | None
- is_self_post: bool
- language: str | None              # derived later if needed
- subreddit_id: str
- subreddit_name: str
- subreddit_label: str              # r/<name>
- author_id: str | None             # from author_fullname
- author_username: str
- score: int
- upvotes: int
- downvotes: int
- upvote_ratio: float | None
- comment_count: int
- award_count: int
- is_nsfw: bool
- is_spoiler: bool
- is_locked: bool
- is_stickied: bool
- is_pinned: bool
- is_archived: bool
- flair_text: str | None
- flair_type: str | None
- preview_image_url: str | None     # derived from preview/source
- media_type: str | None            # derived: image / video / youtube / gallery / link / self
- thumbnail_url: str | None         # only if thumbnail looks like real URL
- raw_json: dict                    # keep raw payload for debugging/edge features
```

### Canonical `Author`

```text
Author
- author_id: str | None             # author_fullname
- username: str                     # author
- platform: Literal["reddit"]
- flair_text: str | None
- flair_type: str | None
- flair_text_color: str | None
- flair_background_color: str | None
- is_deleted: bool                  # username == "[deleted]"
```

### Canonical `Community`

```text
Community
- community_id: str                 # subreddit_id
- platform: Literal["reddit"]
- name: str                         # subreddit
- label: str                        # subreddit_name_prefixed
- community_type: str | None        # subreddit_type
- is_quarantined_snapshot: bool | None
```

### Canonical `Link`

```text
Link
- link_id: str                      # derived, e.g. hash(canonical_url)
- post_id: str
- url: str
- domain: str | None
- url_type: str                     # external / reddit_permalink / reddit_media / youtube / image
- is_external: bool
```

### Canonical `Hashtag`

The dataset does not have a real hashtag field. Hashtags should be derived only.

```text
Hashtag
- tag: str
- normalized_tag: str
- source_post_id: str
- extraction_source: str            # text_regex
```

### Canonical `Entity`

Use a generic extracted-entity table rather than assuming platform-native entity fields exist.

```text
Entity
- entity_id: str                    # derived
- post_id: str
- entity_type: str                  # person / org / location / topic / url / subreddit / domain
- text: str
- normalized_text: str
- source: str                       # ner / regex / link_parser / subreddit_field
- confidence: float | None
```

### Canonical `PostMetadata`

```text
PostMetadata
- post_id: str
- raw_kind: str                     # t3
- crosspost_parent_id: str | None
- has_preview: bool
- has_media: bool
- has_gallery: bool
- has_external_url: bool
- raw_post_hint: str | None
- raw_flags: dict                   # optional bucket for less-used Reddit flags
```

## 3. Raw-To-Canonical Mapping

| Raw field(s) | Canonical field | Notes |
|---|---|---|
| `kind` | `PostMetadata.raw_kind` | Always `t3` in this dataset |
| `data.id` | `Post.post_id` | Best stable post key |
| `data.name` | `Post.platform_item_id` | Reddit thing id with prefix |
| `data.created_utc` | `Post.created_at` | Preferred canonical timestamp |
| `data.edited` | `Post.edited_at` | Use only when numeric; `false` means null |
| `data.title` | `Post.title` | Required |
| `data.selftext` | `Post.body_text` | Convert empty string to null |
| `data.title` + `data.selftext` | `Post.full_text` | Primary search/clustering text |
| `data.permalink` | `Post.permalink_url` | Prefix with `https://www.reddit.com` |
| `data.url` | `Post.canonical_url` | Use as external URL for link posts; for self posts may equal Reddit URL |
| `data.domain` | `Post.domain`, `Link.domain` | Normalize empty string to null |
| `data.is_self` | `Post.is_self_post` | Important for link-vs-text analysis |
| `data.subreddit_id` | `Community.community_id`, `Post.subreddit_id` | Stable community id |
| `data.subreddit` | `Community.name`, `Post.subreddit_name` | Human-readable community name |
| `data.subreddit_name_prefixed` | `Community.label`, `Post.subreddit_label` | Usually `r/<name>` |
| `data.subreddit_type` | `Community.community_type` | Optional categorical field |
| `data.quarantine` | `Community.is_quarantined_snapshot` | Snapshot-only |
| `data.author` | `Author.username`, `Post.author_username` | Required but may be `[deleted]` |
| `data.author_fullname` | `Author.author_id`, `Post.author_id` | Missing for some rows |
| `data.author_flair_text` | `Author.flair_text` | Optional |
| `data.author_flair_type` | `Author.flair_type` | Optional |
| `data.author_flair_text_color` | `Author.flair_text_color` | Optional |
| `data.author_flair_background_color` | `Author.flair_background_color` | Optional |
| `data.link_flair_text` | `Post.flair_text` | Optional post label |
| `data.link_flair_type` | `Post.flair_type` | Optional |
| `data.score` | `Post.score` | Snapshot metric |
| `data.ups` | `Post.upvotes` | Snapshot metric |
| `data.downs` | `Post.downvotes` | Keep optional; not always analytically meaningful |
| `data.upvote_ratio` | `Post.upvote_ratio` | Optional snapshot metric |
| `data.num_comments` | `Post.comment_count` | Useful for ranking and trend panels |
| `data.total_awards_received` | `Post.award_count` | Snapshot metric |
| `data.over_18` | `Post.is_nsfw` | Boolean |
| `data.spoiler` | `Post.is_spoiler` | Boolean |
| `data.locked` | `Post.is_locked` | Boolean |
| `data.stickied` | `Post.is_stickied` | Boolean |
| `data.pinned` | `Post.is_pinned` | Boolean |
| `data.archived` | `Post.is_archived` | Boolean |
| `data.preview` | `Post.preview_image_url`, `PostMetadata.has_preview` | Derive best source image URL |
| `data.media`, `data.secure_media` | `Post.media_type`, `PostMetadata.has_media` | Derive media class |
| `data.gallery_data`, `data.media_metadata` | `Post.media_type`, `PostMetadata.has_gallery` | Indicates gallery/media collections |
| `data.thumbnail` | `Post.thumbnail_url` | Use only if it is an actual URL |
| `data.crosspost_parent` | `PostMetadata.crosspost_parent_id` | Optional relationship |
| `data.crosspost_parent_list` | optional related-post edge | Preserve if crosspost analysis matters |
| `data.url` + `data.domain` + `data.is_self` | `Link.*` | Derived canonical link record |
| `data.title` + `data.selftext` | `Hashtag.*`, `Entity.*` | Derived via regex/NLP only |

## 4. Optional, Derived, And Ignored Fields

### Fields That Should Be Required

- `post_id`
- `platform`
- `source_kind`
- `created_at`
- `title`
- `full_text`
- `permalink_url`
- `subreddit_id`
- `subreddit_name`
- `subreddit_label`
- `author_username`
- `score`
- `comment_count`
- `is_self_post`

### Fields That Should Be Optional

- `body_text`
- `edited_at`
- `author_id`
- `domain`
- `upvote_ratio`
- `flair_text`
- `flair_type`
- `thumbnail_url`
- `preview_image_url`
- `media_type`
- `community_type`
- `crosspost_parent_id`
- all flair-style fields
- all media/gallery nested payloads

### Fields That Should Be Derived

- `full_text` from `title` + `selftext`
- `permalink_url` from `permalink`
- `canonical_url` from `url` and `is_self`
- `has_external_url` from `url`, `permalink`, `domain`, `is_self`
- `preview_image_url` from nested `preview`
- `media_type` from `is_self`, `is_video`, `domain`, `preview`, `media`, `gallery_data`
- `hashtags` from regex over `title` and `selftext`
- `entities` from NLP/regex/link parsing, not from raw source columns
- `language` from text detection if needed

### Fields That Should Usually Be Ignored In Core App Models

- Viewer-specific flags: `saved`, `clicked`, `visited`, `hidden`, `send_replies`
- Moderation/admin noise: `approved_*`, `banned_*`, `mod_*`, `removed_by`, `num_reports`, `report_reasons`
- UI/runtime flags: `hide_score`, `allow_live_comments`, `contest_mode`, `treatment_tags`
- Legacy or low-value Reddit internals: `pwls`, `wls`, `whitelist_status`, `parent_whitelist_status`
- Empty or nearly-empty fields: `category`, `content_categories`, `discussion_type`, `likes`, `top_awarded_type`, `view_count`

## 5. Dataset Risks And Quirks For Analytics Features

### Search

- The corpus is Reddit submissions only, so any “platform” abstraction should currently resolve to Reddit communities, not multiple social networks.
- `full_text` must use `title + selftext`; relying on `selftext` alone would discard most rows because 5,891 posts have empty bodies.
- Hashtags are not a native source field. Any hashtag search/filter is derived and will be sparse; only 177 posts contained regex-detectable hashtags in title/body.
- Many self posts have Reddit permalink-style `url` values, so URL-based filtering must distinguish external URLs from Reddit internal links.

### Clustering / Embeddings

- Titles dominate many rows because body text is frequently empty. Topic clusters may therefore skew toward headline phrasing rather than long-form argumentation.
- Crossposts and repeated news-link titles can create near-duplicate semantic clusters.
- Flair fields are tempting topical features, but they are community-specific and noisy; use them as auxiliary labels, not primary semantic content.
- Media-heavy posts may contain little textual evidence even when analytically important.

### Time-Series

- `created_utc` is the correct time field; `created` appears redundant and should not be treated as a separate timeline.
- Engagement metrics are snapshot values, not event histories. `score`, `ups`, and `num_comments` reflect crawl-time state, not longitudinal evolution.
- Stickied/pinned posts can distort activity summaries if treated the same as ordinary posts.

### Network Analysis

- There is no native mention/reply graph in the submission data. Author networks, hashtag networks, and link co-occurrence networks must be inferred.
- `crosspost_parent` and `crosspost_parent_list` provide a real relationship signal, but only for 238 rows.
- Author identity is imperfect because `author_fullname` is missing on some rows and `author` includes `[deleted]` accounts.
- Domain networks are likely stronger than hashtag networks because outbound URLs are common while hashtags are rare.

### General Data-Model Risks

- The dataset is strongly Reddit-specific, so any canonical model should preserve platform-specific raw payloads instead of over-normalizing into a fake universal schema.
- Several fields are operational Reddit API metadata rather than stable content facts. Pulling too many of them into search or clustering will add noise.
- `edited` is mixed-type (`false` or timestamp), so strict typing must normalize it before validation.
- `thumbnail` is not a reliable image URL field because Reddit uses sentinel strings such as `self`, `default`, and `image`.

## Recommended Implementation Direction

For this app, the most practical ingestion pipeline is:

1. Flatten each JSONL row to the `data` object.
2. Normalize into canonical `Post`, `Author`, `Community`, `Link`, and `PostMetadata` records.
3. Derive `full_text`, `hashtags`, `entities`, `media_type`, and `preview_image_url`.
4. Keep the original Reddit payload in `raw_json` for edge cases and future features.
5. Treat search, clustering, time-series, and network views as analysis layers built on top of the canonical post table, not on raw Reddit fields directly.
