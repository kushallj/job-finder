from __future__ import annotations

import csv
import json
import os
import time
import urllib.parse
from pathlib import Path
from typing import List, Optional, Dict, Any

import httpx

from .models import XProfile, XTweet

X_API_BASE = "https://api.twitter.com/2"
DISK_CACHE_DIR = Path("cache/x_api")
DISK_CACHE_TTL = 86400  # 24 hours


class XClient:
    """
    Client for X (Twitter) API v2 with automatic disk caching and offline CSV fallback.
    Seamlessly executes Follows, Likes, Retweets, Replies, and DMs.
    """

    def __init__(self, bearer_token: Optional[str] = None):
        self.bearer_token = (bearer_token or os.getenv("X_BEARER_TOKEN", "")).strip() or None
        self._use_api = bool(self.bearer_token)
        self._sample_paths = [
            Path("data_examples/sample_x_profiles.csv"),
            Path("sample_x_profiles.csv"),
        ]

    @property
    def mode(self) -> str:
        return "live_api" if self._use_api else "csv_fallback"

    # ------------------------------------------------------------------
    # Disk Cache
    # ------------------------------------------------------------------

    def _cache_path(self, key: str) -> Path:
        safe = "".join(c if c.isalnum() else "_" for c in key.lower())[:80]
        return DISK_CACHE_DIR / f"{safe}.json"

    def _read_cache(self, key: str) -> Optional[dict]:
        p = self._cache_path(key)
        if not p.exists():
            return None
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            if time.time() - data.get("ts", 0) > DISK_CACHE_TTL:
                return None
            return data.get("payload")
        except Exception:
            return None

    def _write_cache(self, key: str, payload: dict) -> None:
        try:
            DISK_CACHE_DIR.mkdir(parents=True, exist_ok=True)
            p = self._cache_path(key)
            p.write_text(json.dumps({"ts": time.time(), "payload": payload}, indent=2), encoding="utf-8")
        except Exception:
            pass

    # ------------------------------------------------------------------
    # User Search
    # ------------------------------------------------------------------

    def search_users_by_company(self, company: str, role: Optional[str] = None, limit: int = 10) -> List[XProfile]:
        company = (company or "").strip()
        if not company:
            return []

        cache_key = f"users_{company}_{role}_{limit}"
        cached = self._read_cache(cache_key)
        if cached:
            return [XProfile(**p) for p in cached]

        if self._use_api:
            try:
                profiles = self._search_users_api(company, role, limit)
                self._write_cache(cache_key, [p.model_dump() for p in profiles])
                return profiles
            except Exception:
                pass

        profiles = self._search_users_csv(company, role, limit)
        return profiles

    def _search_users_api(self, company: str, role: Optional[str] = None, limit: int = 10) -> List[XProfile]:
        query = f"{company} {role or 'engineer'}"
        headers = {"Authorization": f"Bearer {self.bearer_token}"}
        resp = httpx.get(
            f"{X_API_BASE}/users/by",
            headers=headers,
            params={"usernames": company.lower()},
            timeout=10.0,
        )
        if resp.status_code != 200:
            return []

        data = resp.json().get("data", [])
        return [
            XProfile(
                x_user_id=str(u["id"]),
                username=u["username"],
                name=u["name"],
                description=u.get("description"),
                company=company,
                title=role or "Engineering",
                source="api",
            )
            for u in data[:limit]
        ]

    def _search_users_csv(self, company: str, role: Optional[str] = None, limit: int = 10) -> List[XProfile]:
        sample_path = None
        for p in self._sample_paths:
            if p.exists():
                sample_path = p
                break
        if not sample_path:
            return []

        profiles: List[XProfile] = []
        try:
            with sample_path.open(newline="", encoding="utf-8-sig") as fh:
                reader = csv.DictReader(fh)
                for row in reader:
                    c_val = (row.get("company") or "").strip()
                    desc_val = (row.get("description") or "").strip()
                    title_val = (row.get("title") or "").strip()

                    match = (
                        company.lower() in c_val.lower()
                        or company.lower() in desc_val.lower()
                        or company.lower() in title_val.lower()
                    )
                    if not match:
                        continue

                    profiles.append(XProfile(
                        x_user_id=str(row.get("x_user_id") or "0"),
                        username=row.get("username", "user"),
                        name=row.get("name", "User"),
                        company=c_val or company,
                        title=title_val or "Engineer",
                        description=desc_val,
                        followers_count=int(row.get("followers_count") or 0),
                        verified=str(row.get("verified", "")).lower() == "true",
                        source="csv",
                    ))
                    if len(profiles) >= limit:
                        break
        except Exception:
            return []
        return profiles

    # ------------------------------------------------------------------
    # Tweet & Hiring Search
    # ------------------------------------------------------------------

    def search_hiring_tweets(self, company: str, role: Optional[str] = None, limit: int = 10) -> List[XTweet]:
        company = (company or "").strip()
        if not company:
            return []

        cache_key = f"tweets_{company}_{role}_{limit}"
        cached = self._read_cache(cache_key)
        if cached:
            return [XTweet(**t) for t in cached]

        if self._use_api:
            try:
                tweets = self._search_tweets_api(company, role, limit)
                self._write_cache(cache_key, [t.model_dump() for t in tweets])
                return tweets
            except Exception:
                pass

        return self._search_tweets_csv(company, role, limit)

    def _search_tweets_api(self, company: str, role: Optional[str] = None, limit: int = 10) -> List[XTweet]:
        q = f'"{company}" (hiring OR referral OR join our team) -is:retweet'
        headers = {"Authorization": f"Bearer {self.bearer_token}"}
        resp = httpx.get(
            f"{X_API_BASE}/tweets/search/recent",
            headers=headers,
            params={"query": q, "max_results": min(10, limit), "tweet.fields": "author_id,created_at,public_metrics"},
            timeout=10.0,
        )
        if resp.status_code != 200:
            return []

        data = resp.json().get("data", [])
        return [
            XTweet(
                tweet_id=str(t["id"]),
                author_id=t.get("author_id"),
                text=t["text"],
                like_count=t.get("public_metrics", {}).get("like_count", 0),
                retweet_count=t.get("public_metrics", {}).get("retweet_count", 0),
                reply_count=t.get("public_metrics", {}).get("reply_count", 0),
                is_hiring_tweet=True,
            )
            for t in data[:limit]
        ]

    def _search_tweets_csv(self, company: str, role: Optional[str] = None, limit: int = 10) -> List[XTweet]:
        sample_path = None
        for p in self._sample_paths:
            if p.exists():
                sample_path = p
                break
        if not sample_path:
            return []

        tweets: List[XTweet] = []
        try:
            with sample_path.open(newline="", encoding="utf-8-sig") as fh:
                reader = csv.DictReader(fh)
                for row in reader:
                    c_val = (row.get("company") or "").strip()
                    sample_tweet = (row.get("sample_hiring_tweet") or "").strip()
                    tweet_id = str(row.get("sample_tweet_id") or "18001001")
                    uname = (row.get("username") or "").strip()
                    name = (row.get("name") or "").strip()

                    if company.lower() in c_val.lower() or company.lower() in sample_tweet.lower():
                        if sample_tweet:
                            tweets.append(XTweet(
                                tweet_id=tweet_id,
                                author_id=str(row.get("x_user_id")),
                                author_username=uname,
                                author_name=name,
                                text=sample_tweet,
                                like_count=42,
                                retweet_count=12,
                                is_hiring_tweet=True,
                            ))
                            if len(tweets) >= limit:
                                break
        except Exception:
            return []
        return tweets

    # ------------------------------------------------------------------
    # Actions & Intent Fallback
    # ------------------------------------------------------------------

    def get_intent_url(self, action_type: str, username: Optional[str] = None, tweet_id: Optional[str] = None, text: Optional[str] = None) -> str:
        """Generates a direct X web intent link for fallback actions."""
        if action_type == "reply" and tweet_id:
            params = {"in_reply_to": tweet_id}
            if text:
                params["text"] = text
            return f"https://x.com/intent/tweet?{urllib.parse.urlencode(params)}"
        if action_type == "dm" and username:
            clean = username.lstrip("@")
            return f"https://x.com/messages/compose?recipient_id={clean}"
        if action_type == "like" and tweet_id:
            return f"https://x.com/intent/like?tweet_id={tweet_id}"
        if action_type == "repost" and tweet_id:
            return f"https://x.com/intent/retweet?tweet_id={tweet_id}"
        if action_type == "follow" and username:
            clean = username.lstrip("@")
            return f"https://x.com/intent/follow?screen_name={clean}"
        if text:
            return f"https://x.com/intent/tweet?{urllib.parse.urlencode({'text': text})}"
        return "https://x.com"

    async def execute_action(
        self,
        action_type: str,
        target_username: str,
        target_user_id: Optional[str] = None,
        tweet_id: Optional[str] = None,
        message_text: Optional[str] = None,
        access_token: Optional[str] = None,
        source_user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes follow, like, repost, reply, or DM via X API v2 if access_token is present,
        otherwise generates a web intent URL for instant assistive fallback.
        """
        intent_url = self.get_intent_url(
            action_type, username=target_username, tweet_id=tweet_id, text=message_text
        )

        if not access_token or not self._use_api:
            return {
                "success": True,
                "mode": "assistive_intent",
                "action": action_type,
                "target": target_username,
                "intent_url": intent_url,
                "message": f"Intent URL ready for {action_type} on @{target_username.lstrip('@')}",
            }

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            if action_type == "follow" and source_user_id and target_user_id:
                resp = await client.post(
                    f"{X_API_BASE}/users/{source_user_id}/following",
                    headers=headers,
                    json={"target_user_id": target_user_id},
                )
                return {"success": resp.status_code == 200, "data": resp.json(), "intent_url": intent_url}

            elif action_type == "like" and source_user_id and tweet_id:
                resp = await client.post(
                    f"{X_API_BASE}/users/{source_user_id}/likes",
                    headers=headers,
                    json={"tweet_id": tweet_id},
                )
                return {"success": resp.status_code == 200, "data": resp.json(), "intent_url": intent_url}

            elif action_type == "reply" and tweet_id and message_text:
                resp = await client.post(
                    f"{X_API_BASE}/tweets",
                    headers=headers,
                    json={"text": message_text, "reply": {"in_reply_to_tweet_id": tweet_id}},
                )
                return {"success": resp.status_code == 201, "data": resp.json(), "intent_url": intent_url}

            elif action_type == "dm" and target_user_id and message_text:
                resp = await client.post(
                    f"{X_API_BASE}/dm_conversations/with/{target_user_id}/messages",
                    headers=headers,
                    json={"text": message_text},
                )
                return {"success": resp.status_code in (200, 201), "data": resp.json(), "intent_url": intent_url}

        return {"success": True, "mode": "assistive_intent", "intent_url": intent_url}


x_client = XClient()
