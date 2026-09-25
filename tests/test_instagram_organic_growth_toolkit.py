import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from instagram_organic_growth_toolkit import (
    AccountSnapshot,
    InstagramGrowthAnalyzer,
    InstagramGraphClient,
    InstagramToolkitError,
    PostMetrics,
    build_hashtag_candidates,
    load_metrics_file,
)


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, params, timeout):
        self.calls.append({"url": url, "params": params, "timeout": timeout})
        return self.responses.pop(0)


def make_post(media_id, timestamp, media_type="REELS", likes=20, reach=100):
    return PostMetrics(
        media_id=media_id,
        timestamp=datetime.fromisoformat(timestamp),
        media_type=media_type,
        likes=likes,
        comments=5,
        saves=3,
        shares=2,
        reach=reach,
    )


def test_report_uses_reach_before_follower_fallback():
    account = AccountSnapshot(username="creator", followers=1000)
    posts = [
        make_post("reach-post", "2026-09-14T17:00:00+00:00", likes=20, reach=100),
        make_post("fallback-post", "2026-09-15T17:00:00+00:00", likes=30, reach=0),
    ]

    report = InstagramGrowthAnalyzer(account, posts).build_report(
        niche="home fitness", keywords=["strength training"]
    )

    assert report["performance_summary"]["reach_available_for_posts"] == 1
    assert report["performance_summary"]["follower_fallback_posts"] == 1
    assert report["top_posts"][0]["media_id"] == "reach-post"
    assert report["top_posts"][0]["engagement_denominator"] == "reach"
    assert report["top_posts"][1]["engagement_denominator"] == "followers_fallback"


def test_posting_time_recommendation_is_sorted_by_engagement_rate():
    account = AccountSnapshot(followers=1000)
    posts = [
        make_post("a", "2026-09-14T17:00:00+00:00", likes=40, reach=100),
        make_post("b", "2026-09-15T09:00:00+00:00", likes=5, reach=100),
    ]

    best_time = InstagramGrowthAnalyzer(account, posts).build_report()["best_posting_times"][0]

    assert best_time["weekday"] == "Monday"
    assert best_time["hour_24"] == 17
    assert best_time["average_engagement_rate"] == 50.0


def test_hashtag_candidates_are_clean_and_do_not_claim_live_research():
    candidates = build_hashtag_candidates("Home Fitness!", ["Strength Training"])

    assert "#homefitness" in candidates["candidates"]
    assert "#strengthtraining" in candidates["candidates"]
    assert all(" " not in tag for tag in candidates["candidates"])
    assert any("do not represent" in note.lower() for note in candidates["usage_guidance"])


def test_load_metrics_json_export(tmp_path: Path):
    export = tmp_path / "metrics.json"
    export.write_text(
        json.dumps(
            {
                "account": {"username": "owner", "followers": 50},
                "posts": [
                    {
                        "media_id": "one",
                        "timestamp": "2026-09-01T12:00:00Z",
                        "likes": 4,
                        "reach": 20,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    account, posts = load_metrics_file(export)

    assert account.username == "owner"
    assert account.followers == 50
    assert len(posts) == 1
    assert posts[0].timestamp.tzinfo == timezone.utc


def test_graph_client_reads_only_expected_account_fields():
    session = FakeSession(
        [
            FakeResponse(
                {
                    "id": "1789",
                    "username": "owner",
                    "followers_count": 120,
                    "follows_count": 20,
                    "media_count": 5,
                }
            )
        ]
    )
    client = InstagramGraphClient(
        access_token="token",
        instagram_user_id="1789",
        session=session,
        min_request_interval=0,
    )

    account = client.get_account_snapshot()

    assert account.username == "owner"
    assert session.calls[0]["params"]["fields"] == "id,username,followers_count,follows_count,media_count"
    assert session.calls[0]["params"]["access_token"] == "token"


def test_graph_client_raises_sanitized_api_error():
    session = FakeSession(
        [FakeResponse({"error": {"message": "Permission denied", "code": 10}}, 400)]
    )
    client = InstagramGraphClient(
        access_token="token",
        instagram_user_id="1789",
        session=session,
        min_request_interval=0,
    )

    with pytest.raises(InstagramToolkitError, match="Instagram API error 10: Permission denied"):
        client.get_account_snapshot()
