"""Instagram organic-growth analysis using official Meta APIs only.

This module deliberately does *not* automate likes, follows, comments, direct
messages, publishing, or any other account action. It reads permitted data from
the Instagram API, analyzes historical performance, and produces planning
recommendations that an account owner can review and execute manually.

Supported data sources:
- Official Instagram API / Graph API for a connected professional account
- A locally exported JSON or CSV metrics file for offline analysis

See docs/INSTAGRAM_ORGANIC_GROWTH_TOOLKIT.md for setup, permissions, and usage.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import re
import time
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import requests

LOGGER = logging.getLogger(__name__)
DEFAULT_API_BASE_URL = "https://graph.instagram.com"
DEFAULT_API_VERSION = "v24.0"


class InstagramToolkitError(Exception):
    """Base exception for toolkit failures."""


class InstagramConfigurationError(InstagramToolkitError):
    """Raised when required local configuration is missing."""


class InstagramAPIError(InstagramToolkitError):
    """Raised when the official Instagram API returns an error."""


@dataclass
class AccountSnapshot:
    """A minimal, non-sensitive view of the connected professional account."""

    account_id: str = ""
    username: str = ""
    followers: int = 0
    following: int = 0
    media_count: int = 0

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "AccountSnapshot":
        return cls(
            account_id=str(data.get("id") or data.get("account_id") or ""),
            username=str(data.get("username") or ""),
            followers=_as_int(data.get("followers_count", data.get("followers", 0))),
            following=_as_int(data.get("follows_count", data.get("following", 0))),
            media_count=_as_int(data.get("media_count", 0)),
        )


@dataclass
class PostMetrics:
    """Normalized media metrics used for analysis.

    ``reach`` is preferred as the engagement-rate denominator. When it is not
    available, account followers are used as a clearly labelled fallback.
    """

    media_id: str
    timestamp: datetime
    media_type: str = "UNKNOWN"
    caption: str = ""
    likes: int = 0
    comments: int = 0
    saves: int = 0
    shares: int = 0
    reach: int = 0
    views: int = 0
    permalink: str = ""

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "PostMetrics":
        timestamp = _parse_timestamp(data.get("timestamp") or data.get("created_at"))
        if timestamp is None:
            raise ValueError("Each post requires an ISO-8601 timestamp or created_at value.")

        return cls(
            media_id=str(data.get("id") or data.get("media_id") or "unknown"),
            timestamp=timestamp,
            media_type=str(
                data.get("media_product_type") or data.get("media_type") or "UNKNOWN"
            ).upper(),
            caption=str(data.get("caption") or ""),
            likes=_as_int(data.get("like_count", data.get("likes", 0))),
            comments=_as_int(data.get("comments_count", data.get("comments", 0))),
            saves=_as_int(data.get("saved", data.get("saves", 0))),
            shares=_as_int(data.get("shares", 0)),
            reach=_as_int(data.get("reach", 0)),
            views=_as_int(data.get("views", 0)),
            permalink=str(data.get("permalink") or ""),
        )

    @property
    def interactions(self) -> int:
        return self.likes + self.comments + self.saves + self.shares


class InstagramGraphClient:
    """Small, rate-conscious client for the official Instagram API.

    The base URL and API version are configurable because Meta supports
    different login configurations and deprecates API versions over time. The
    caller must use an access token that was granted for the connected account.
    """

    def __init__(
        self,
        access_token: str,
        instagram_user_id: str,
        base_url: str = DEFAULT_API_BASE_URL,
        api_version: str = DEFAULT_API_VERSION,
        timeout_seconds: int = 20,
        min_request_interval: float = 0.4,
        session: Optional[requests.Session] = None,
    ) -> None:
        if not access_token:
            raise InstagramConfigurationError("INSTAGRAM_ACCESS_TOKEN is required.")
        if not instagram_user_id:
            raise InstagramConfigurationError("INSTAGRAM_USER_ID is required.")

        self.access_token = access_token
        self.instagram_user_id = instagram_user_id
        self.base_url = base_url.rstrip("/")
        self.api_version = api_version.strip("/")
        self.timeout_seconds = timeout_seconds
        self.min_request_interval = max(0.0, min_request_interval)
        self.session = session or requests.Session()
        self._last_request_at = 0.0

    @classmethod
    def from_env(cls) -> "InstagramGraphClient":
        """Create a client from local environment variables without logging secrets."""
        return cls(
            access_token=os.environ.get("INSTAGRAM_ACCESS_TOKEN", ""),
            instagram_user_id=os.environ.get("INSTAGRAM_USER_ID", ""),
            base_url=os.environ.get("INSTAGRAM_GRAPH_BASE_URL", DEFAULT_API_BASE_URL),
            api_version=os.environ.get("INSTAGRAM_GRAPH_API_VERSION", DEFAULT_API_VERSION),
            timeout_seconds=_as_int(os.environ.get("INSTAGRAM_TIMEOUT_SECONDS", 20)),
            min_request_interval=float(os.environ.get("INSTAGRAM_MIN_REQUEST_INTERVAL", "0.4")),
        )

    def get_account_snapshot(self) -> AccountSnapshot:
        """Retrieve permitted profile-level fields for the connected account."""
        payload = self._get(
            self.instagram_user_id,
            {
                "fields": "id,username,followers_count,follows_count,media_count",
            },
        )
        return AccountSnapshot.from_mapping(payload)

    def get_recent_media(
        self,
        limit: int = 25,
        include_insights: bool = True,
    ) -> List[PostMetrics]:
        """Retrieve recent media and permitted insights for the connected account.

        Insight availability depends on media type, account type, permissions,
        and the Meta API version. A missing insight never prevents basic media
        analysis; it is omitted and captured by the report's data-quality note.
        """
        safe_limit = max(1, min(int(limit), 50))
        payload = self._get(
            "%s/media" % self.instagram_user_id,
            {
                "fields": "id,caption,media_type,media_product_type,timestamp,"
                "like_count,comments_count,permalink",
                "limit": safe_limit,
            },
        )

        posts: List[PostMetrics] = []
        for media in payload.get("data", []):
            merged: Dict[str, Any] = dict(media)
            if include_insights:
                merged.update(self.get_media_insights(str(media.get("id", ""))))
            try:
                posts.append(PostMetrics.from_mapping(merged))
            except ValueError as error:
                LOGGER.warning("Skipping media with invalid metrics: %s", error)
        return posts

    def get_media_insights(self, media_id: str) -> Dict[str, int]:
        """Fetch optional media insights without making account changes.

        The metric set is intentionally compact. If a metric is not supported
        for a media type, Meta may reject the full request; in that case this
        method returns an empty mapping and leaves the post usable.
        """
        if not media_id:
            return {}
        try:
            payload = self._get(
                "%s/insights" % media_id,
                {"metric": "reach,saved,shares,views"},
            )
        except InstagramAPIError as error:
            LOGGER.info("Insights unavailable for media %s: %s", media_id, error)
            return {}

        values: Dict[str, int] = {}
        for metric in payload.get("data", []):
            name = str(metric.get("name", ""))
            metric_values = metric.get("values", [])
            if name and metric_values:
                values[name] = _as_int(metric_values[0].get("value", 0))
        return values

    def _get(self, path: str, params: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
        self._wait_for_rate_limit()
        request_params: Dict[str, Any] = dict(params or {})
        request_params["access_token"] = self.access_token
        url = "%s/%s/%s" % (self.base_url, self.api_version, path.lstrip("/"))

        try:
            response = self.session.get(
                url,
                params=request_params,
                timeout=self.timeout_seconds,
            )
        except requests.RequestException as error:
            raise InstagramAPIError("Instagram API request failed: %s" % error) from error

        try:
            payload = response.json()
        except ValueError:
            payload = {}

        if response.status_code >= 400 or payload.get("error"):
            error_details = payload.get("error", {}) if isinstance(payload, dict) else {}
            message = error_details.get("message") or "Unknown API error"
            code = error_details.get("code") or response.status_code
            raise InstagramAPIError("Instagram API error %s: %s" % (code, message))
        if not isinstance(payload, dict):
            raise InstagramAPIError("Instagram API returned an unexpected response format.")
        return payload

    def _wait_for_rate_limit(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        remaining = self.min_request_interval - elapsed
        if remaining > 0:
            time.sleep(remaining)
        self._last_request_at = time.monotonic()


class InstagramGrowthAnalyzer:
    """Creates transparent, human-reviewable organic-growth recommendations."""

    def __init__(self, account: AccountSnapshot, posts: Sequence[PostMetrics]) -> None:
        self.account = account
        self.posts = list(posts)

    def build_report(
        self,
        niche: str = "",
        keywords: Optional[Sequence[str]] = None,
    ) -> Dict[str, Any]:
        """Build a serializable strategy report using only supplied metrics."""
        scored_posts = [self._score_post(post) for post in self.posts]
        valid_rates = [row["engagement_rate"] for row in scored_posts if row["engagement_rate"] is not None]
        total_interactions = sum(post.interactions for post in self.posts)
        reached_posts = sum(1 for post in self.posts if post.reach > 0)

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "scope": {
                "source": "official_api_or_owner_export",
                "automation": "analysis_and_planning_only",
                "account": asdict(self.account),
                "posts_analyzed": len(self.posts),
            },
            "performance_summary": {
                "total_interactions": total_interactions,
                "average_engagement_rate": _round_or_none(_mean(valid_rates)),
                "engagement_rate_definition": (
                    "(likes + comments + saves + shares) / reach * 100; "
                    "uses followers only when reach is unavailable"
                ),
                "reach_available_for_posts": reached_posts,
                "follower_fallback_posts": sum(
                    1 for post in self.posts if post.reach <= 0 and self.account.followers > 0
                ),
            },
            "best_posting_times": self._best_posting_times(scored_posts),
            "content_type_performance": self._content_type_performance(scored_posts),
            "top_posts": self._top_posts(scored_posts),
            "content_plan": self._content_plan(niche),
            "hashtag_candidates": build_hashtag_candidates(niche, keywords or []),
            "engagement_strategy": engagement_strategy(),
            "data_quality_notes": self._data_quality_notes(reached_posts),
        }

    def _score_post(self, post: PostMetrics) -> Dict[str, Any]:
        rate, denominator = self._engagement_rate(post)
        return {
            "media_id": post.media_id,
            "timestamp": post.timestamp.isoformat(),
            "media_type": post.media_type,
            "interactions": post.interactions,
            "reach": post.reach,
            "views": post.views,
            "engagement_rate": _round_or_none(rate),
            "engagement_denominator": denominator,
            "permalink": post.permalink,
        }

    def _engagement_rate(self, post: PostMetrics) -> Tuple[Optional[float], str]:
        if post.reach > 0:
            return (post.interactions / float(post.reach)) * 100, "reach"
        if self.account.followers > 0:
            return (post.interactions / float(self.account.followers)) * 100, "followers_fallback"
        return None, "unavailable"

    def _best_posting_times(self, scored_posts: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
        buckets: Dict[Tuple[int, int], List[float]] = defaultdict(list)
        for score in scored_posts:
            rate = score.get("engagement_rate")
            timestamp = _parse_timestamp(score.get("timestamp"))
            if rate is not None and timestamp is not None:
                buckets[(timestamp.weekday(), timestamp.hour)].append(float(rate))

        recommendations = []
        for (weekday, hour), rates in buckets.items():
            recommendations.append(
                {
                    "weekday": _weekday_name(weekday),
                    "hour_24": hour,
                    "sample_size": len(rates),
                    "average_engagement_rate": _round_or_none(_mean(rates)),
                    "confidence_note": (
                        "Directional only; validate with more posts."
                        if len(rates) < 3
                        else "Based on historical post performance."
                    ),
                }
            )
        return sorted(
            recommendations,
            key=lambda item: (item["average_engagement_rate"] or 0, item["sample_size"]),
            reverse=True,
        )[:5]

    def _content_type_performance(self, scored_posts: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
        groups: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
        for score in scored_posts:
            groups[str(score["media_type"])].append(score)

        summary = []
        for media_type, rows in groups.items():
            rates = [float(row["engagement_rate"]) for row in rows if row["engagement_rate"] is not None]
            summary.append(
                {
                    "media_type": media_type,
                    "posts": len(rows),
                    "average_interactions": _round_or_none(
                        _mean([float(row["interactions"]) for row in rows])
                    ),
                    "average_engagement_rate": _round_or_none(_mean(rates)),
                }
            )
        return sorted(
            summary,
            key=lambda item: item["average_engagement_rate"] or 0,
            reverse=True,
        )

    def _top_posts(self, scored_posts: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
        ranked = sorted(
            scored_posts,
            key=lambda item: item["engagement_rate"] if item["engagement_rate"] is not None else -1,
            reverse=True,
        )
        return list(ranked[:5])

    @staticmethod
    def _content_plan(niche: str) -> Dict[str, Any]:
        niche_label = niche.strip() or "your niche"
        return {
            "cadence": "Plan 3-5 quality feed posts or Reels per week, then refine against results.",
            "recommended_mix": [
                "Education: a practical tip, framework, or before/after for %s." % niche_label,
                "Proof: a customer story, result, or behind-the-scenes process with consent.",
                "Conversation: a clear question that helps the audience share a relevant experience.",
                "Community: a credited user-generated post or collaborator feature, where permitted.",
            ],
            "caption_checklist": [
                "Open with a specific, audience-relevant hook.",
                "Deliver the promised value before the call to action.",
                "Ask one focused question instead of using generic engagement bait.",
                "Use only hashtags that accurately describe the post and audience.",
            ],
        }

    def _data_quality_notes(self, reached_posts: int) -> List[str]:
        notes = [
            "Recommendations are descriptive, not causal; test changes one at a time.",
            "Posting-time results use the timestamp timezone supplied by the API or export.",
            "This toolkit performs no automated engagement, follows, comments, messaging, or publishing.",
        ]
        if not self.posts:
            notes.append("No posts were supplied. Add an owner export or connect the official API.")
        if self.posts and reached_posts == 0:
            notes.append(
                "Reach was unavailable, so engagement rates use follower count when available; "
                "treat comparisons as directional."
            )
        return notes


def build_hashtag_candidates(niche: str, keywords: Sequence[str]) -> Dict[str, Any]:
    """Create a candidate set for human review; it does not claim trend data.

    Hashtag popularity and eligibility change frequently. The returned labels are
    a starting point only and must be checked in Instagram before publishing.
    """
    seeds = [niche] + list(keywords)
    normalized = [_hashtag_slug(seed) for seed in seeds if _hashtag_slug(seed)]
    candidates: List[str] = []
    for seed in normalized:
        candidates.extend([seed, "%stips" % seed, "%sideas" % seed, "%scommunity" % seed])

    candidates.extend(
        [
            "contentcreator",
            "instagramreels",
            "socialmediatips",
            "communitybuilding",
            "behindthescenes",
            "smallbusiness",
            "creatoreconomy",
            "educationalcontent",
            "shareyourstory",
            "brandstorytelling",
        ]
    )
    unique = _unique(candidates)
    return {
        "candidates": ["#%s" % candidate for candidate in unique[:25]],
        "usage_guidance": [
            "Select only relevant tags; do not add irrelevant tags to chase reach.",
            "Use a mix of precise niche, audience, format, and brand/community tags.",
            "Review each tag in Instagram before posting for relevance and current usage.",
            "Do not represent this candidate list as live trend or volume research.",
        ],
    }


def engagement_strategy() -> Dict[str, List[str]]:
    """Return manual, relationship-first actions from the supplied guide."""
    return {
        "daily": [
            "Review genuine comments and respond thoughtfully, aiming for a two-hour response window when practical.",
            "Spend a focused block engaging with relevant community posts; write specific, non-generic comments.",
            "Capture recurring audience questions for future posts, Stories, or FAQs.",
        ],
        "weekly": [
            "Review top posts, saves, shares, comments, reach, and posting times before changing the plan.",
            "Plan 3-5 quality posts or Reels and map each to one content pillar.",
            "Identify one authentic collaborator, customer story, or user-generated-content opportunity and obtain permission.",
        ],
        "guardrails": [
            "Do not buy followers or use bots, follow/unfollow tactics, generic comment spam, or irrelevant hashtags.",
            "Do not scrape Instagram data without permission; use the official API or owner-provided exports.",
            "Respect platform terms, user privacy, and applicable disclosure requirements.",
        ],
    }


def load_metrics_file(path: Path) -> Tuple[AccountSnapshot, List[PostMetrics]]:
    """Load owner-provided metric exports from JSON or CSV without network access."""
    if not path.exists():
        raise FileNotFoundError("Metrics file not found: %s" % path)

    if path.suffix.lower() == ".json":
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if isinstance(payload, list):
            return AccountSnapshot(), [PostMetrics.from_mapping(row) for row in payload]
        if not isinstance(payload, dict):
            raise ValueError("JSON export must be an object or list of posts.")
        posts = payload.get("posts", payload.get("data", []))
        if not isinstance(posts, list):
            raise ValueError("JSON 'posts' or 'data' field must be a list.")
        return AccountSnapshot.from_mapping(payload.get("account", {})), [
            PostMetrics.from_mapping(row) for row in posts
        ]

    if path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        return AccountSnapshot(), [PostMetrics.from_mapping(row) for row in rows]

    raise ValueError("Use a .json or .csv metrics export.")


def _as_int(value: Any) -> int:
    try:
        return int(float(value or 0))
    except (TypeError, ValueError):
        return 0


def _parse_timestamp(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _mean(values: Iterable[float]) -> Optional[float]:
    values_list = list(values)
    return sum(values_list) / len(values_list) if values_list else None


def _round_or_none(value: Optional[float]) -> Optional[float]:
    return round(value, 2) if value is not None else None


def _weekday_name(index: int) -> str:
    return ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][index]


def _hashtag_slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())[:50]


def _unique(values: Iterable[str]) -> List[str]:
    output: List[str] = []
    seen = set()
    for value in values:
        if value and value not in seen:
            output.append(value)
            seen.add(value)
    return output


def _parse_keywords(value: str) -> List[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Analyze Instagram performance without engagement automation."
    )
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--input", type=Path, help="Owner-provided JSON or CSV metrics export.")
    source_group.add_argument(
        "--from-api",
        action="store_true",
        help="Read the connected professional account through the official API.",
    )
    parser.add_argument("--niche", default="", help="Niche used only for planning suggestions.")
    parser.add_argument(
        "--keywords",
        default="",
        help="Comma-separated audience or topic keywords for human-reviewed hashtag candidates.",
    )
    parser.add_argument("--limit", type=int, default=25, help="Maximum recent posts to fetch from the API.")
    parser.add_argument(
        "--skip-insights",
        action="store_true",
        help="Skip optional per-media insight requests when using --from-api.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("instagram_growth_report.json"),
        help="Output JSON report path.",
    )
    args = parser.parse_args(argv)

    try:
        if args.from_api:
            client = InstagramGraphClient.from_env()
            account = client.get_account_snapshot()
            posts = client.get_recent_media(args.limit, include_insights=not args.skip_insights)
        else:
            account, posts = load_metrics_file(args.input)

        report = InstagramGrowthAnalyzer(account, posts).build_report(
            niche=args.niche,
            keywords=_parse_keywords(args.keywords),
        )
        args.report.parent.mkdir(parents=True, exist_ok=True)
        with args.report.open("w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2)
        print("Wrote compliant Instagram growth report: %s" % args.report)
        return 0
    except (InstagramToolkitError, OSError, ValueError, requests.RequestException) as error:
        LOGGER.error("Unable to build Instagram growth report: %s", error)
        return 1


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    raise SystemExit(main())
