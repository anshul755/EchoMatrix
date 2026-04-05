from fastapi import APIRouter
from ..services.data_loader import load_data

router = APIRouter()


@router.get("/stats")
async def get_stats():
    df = load_data()
    if df.empty:
        return {
            "total_posts": 0,
            "total_authors": 0,
            "date_range": None,
            "top_hashtags": [],
            "platforms": [],
            "top_authors": [],
        }

    all_tags = []
    for tags in df["hashtags"].dropna():
        if isinstance(tags, list):
            all_tags.extend(tags)

    from collections import Counter
    tag_counts = Counter(all_tags)
    top_tags = [tag for tag, _ in tag_counts.most_common(20)]

    valid_dates = df["date"].dropna()
    date_range = None
    if len(valid_dates) > 0:
        date_range = {
            "start": str(valid_dates.min().date()),
            "end": str(valid_dates.max().date()),
        }

    platforms = []
    if df["platform"].notna().any():
        platforms = df["platform"].value_counts().head(10).to_dict()
        platforms = [{"name": k, "count": int(v)} for k, v in platforms.items()]

    top_authors = []
    if df["author"].notna().any():
        author_counts = (
            df.loc[df["author"].astype(str).str.strip().ne(""), "author"]
            .value_counts()
            .head(10)
            .to_dict()
        )
        top_authors = [{"name": k, "count": int(v)} for k, v in author_counts.items()]

    return {
        "total_posts": len(df),
        "total_authors": int(df["author"].nunique()),
        "date_range": date_range,
        "top_hashtags": top_tags,
        "platforms": platforms,
        "top_authors": top_authors,
    }
