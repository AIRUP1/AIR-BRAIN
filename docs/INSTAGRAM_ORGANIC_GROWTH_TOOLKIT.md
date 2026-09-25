# Instagram Organic Growth Toolkit

A **read-only analytics and planning utility** for organic Instagram growth. It implements the supplied growth guide with a strict compliance boundary:

- reads the connected owner account through Meta's official Instagram API, or analyzes an owner-provided JSON/CSV export;
- calculates historic performance, post-time patterns, content-type performance, and human-reviewed hashtag candidates;
- generates a practical content and community-engagement plan;
- **never** automates follows, likes, comments, DMs, publishing, bot activity, or account actions;
- **never** scrapes Instagram profiles.

> The results are recommendations for a human account owner, not a promise of reach or follower growth. Test one change at a time and keep what the account's own data supports.

## What was applied from the guide

| Guide principle | Implementation |
| --- | --- |
| Use Instagram's official API | `InstagramGraphClient` is read-only and uses the configured official API endpoint. |
| Analyze account performance | Account snapshot, interactions, reach, views, and engagement-rate summary. |
| Identify best posting times | Ranks weekday/hour buckets by historic engagement rate, with an explicit sample-size note. |
| Generate content ideas | Recommends a repeatable 3–5 posts/Reels weekly mix: education, proof, conversation, and community. |
| Research hashtags responsibly | Produces labelled **candidates** only; it does not represent them as live trend or volume research. |
| Encourage authentic engagement | Daily/weekly manual routines, including thoughtful replies and community participation. |
| Avoid bots, spam, follower purchases, and scraping | Hard implementation boundary and deprecation of the legacy browser-based Instagram path. |

## Prerequisites

1. Use an Instagram professional account (Business or Creator) that you are authorized to access.
2. Create and configure a Meta app using the current Instagram API setup appropriate for that account.
3. Obtain an authorized user access token and connected Instagram user ID. Exact permissions, account linking, access-token lifetime, and available insight metrics are determined by Meta's current configuration and app review requirements.
4. Do **not** place credentials in source control. The repository ignores `.env` files.

Meta references:

- [Instagram Platform overview](https://developers.facebook.com/documentation/instagram-platform/overview)
- [Instagram Platform insights](https://developers.facebook.com/documentation/instagram-platform/insights)
- [Graph API rate limiting](https://developers.facebook.com/docs/graph-api/overview/rate-limiting/)

## Configure a local environment

Create a local `.env` file or set variables in your shell. Do not commit this file.

```env
# Required for --from-api
INSTAGRAM_ACCESS_TOKEN=replace_with_authorized_user_token
INSTAGRAM_USER_ID=replace_with_connected_instagram_user_id

# Optional operational settings
INSTAGRAM_GRAPH_BASE_URL=https://graph.instagram.com
INSTAGRAM_GRAPH_API_VERSION=v24.0
INSTAGRAM_TIMEOUT_SECONDS=20
INSTAGRAM_MIN_REQUEST_INTERVAL=0.4
```

The module uses a conservative, configurable pause between requests. Meta enforces the authoritative rate limits; the client does not attempt to evade them.

## Run with a metrics export (no API access needed)

This is the safest way to validate the workflow before connecting an account. An example export is included at `examples/instagram_metrics.example.json`.

```bash
python instagram_organic_growth_toolkit.py \
  --input examples/instagram_metrics.example.json \
  --niche "home fitness" \
  --keywords "strength training,workout routine,healthy habits" \
  --report reports/instagram_growth_report.json
```

### JSON format

```json
{
  "account": {
    "username": "example_creator",
    "followers": 2400,
    "following": 310,
    "media_count": 82
  },
  "posts": [
    {
      "media_id": "post-001",
      "timestamp": "2026-09-14T17:30:00-05:00",
      "media_type": "REELS",
      "likes": 245,
      "comments": 28,
      "saves": 44,
      "shares": 19,
      "reach": 4120,
      "views": 5890,
      "permalink": "https://www.instagram.com/p/example-001/"
    }
  ]
}
```

A CSV may contain the same post fields as column names. CSV input cannot include account-level follower data, so rates can use reach only unless the export itself carries a usable denominator.

## Run with the official API

After completing Meta's setup and loading the environment variables:

```bash
python instagram_organic_growth_toolkit.py \
  --from-api \
  --niche "your niche" \
  --keywords "audience keyword,topic keyword" \
  --limit 25 \
  --report reports/instagram_growth_report.json
```

Use `--skip-insights` when validating basic media access. Insight availability can vary by media type, account type, app permissions, and API version; the report records missing reach data rather than inventing a value.

## Report interpretation

- **Engagement rate:** `(likes + comments + saves + shares) / reach × 100`. If reach is unavailable, the report explicitly labels a follower-count fallback. If neither is available, the rate is `null`.
- **Best posting times:** Historic weekday/hour patterns, not a universal schedule. A bucket with fewer than three posts is clearly marked as directional.
- **Content type performance:** Compare Reels, images, and carousel posts only after enough similar posts exist.
- **Hashtag candidates:** Starting points for manual review inside Instagram; not a live hashtag popularity feed.
- **Top posts:** Inputs for qualitative review. Look at the hook, topic, format, audience intent, and call to action—not only the rate.

## Operating rhythm

| Cadence | Human action |
| --- | --- |
| Per post | Publish a high-quality image, carousel, or Reel with an accurate caption and a focused question. |
| Daily | Review and respond to genuine comments; participate substantively in relevant community conversations. |
| Weekly | Review the report, plan 3–5 quality posts/Reels, and identify one authentic collaborator or consented user-generated-content opportunity. |
| Monthly | Compare experiments by content pillar, format, post time, reach, saves, shares, comments, and follower growth. Retire weak assumptions. |

## Compliance guardrails

- Do not buy followers, automate engagement, mass-follow/unfollow, send unsolicited automated messages, or write generic comments.
- Do not scrape Instagram data; use the connected account's official API or owner-provided exports.
- Do not use irrelevant hashtags to obtain reach.
- Keep access tokens secret, minimize collected data, and retain exported data only as long as needed.
- Respect Instagram terms, Meta platform policies, privacy obligations, copyright, and collaboration/endorsement disclosure requirements.

## Testing

```bash
python -m pytest -q tests/test_instagram_organic_growth_toolkit.py
```

The test suite is fully offline: it uses an in-memory fake HTTP session and makes no Instagram API calls.
