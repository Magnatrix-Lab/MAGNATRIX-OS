
"""
youtube_transcript_native.py
MAGNATRIX-OS — YouTube Transcript Extractor

Extract YouTube video transcripts without API keys.
Inspired by Agent-Reach. Pure Python standard library.
"""

import urllib.request
import urllib.parse
import re
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class TranscriptSegment:
    text: str
    start: float
    duration: float


class YouTubeTranscriptExtractor:
    """Extract YouTube video transcripts without API fees."""

    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

    def extract_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from various YouTube URL formats."""
        patterns = [
            r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/|youtube\.com/v/)([a-zA-Z0-9_-]{11})",
            r"youtube\.com/shorts/([a-zA-Z0-9_-]{11})",
        ]
        for pat in patterns:
            m = re.search(pat, url)
            if m:
                return m.group(1)
        return None

    def _fetch_page(self, video_id: str) -> Optional[str]:
        url = f"https://www.youtube.com/watch?v={video_id}"
        try:
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                return resp.read().decode("utf-8", errors="ignore")
        except Exception:
            return None

    def _extract_transcript_url(self, html: str) -> Optional[str]:
        """Extract transcript API URL from YouTube page HTML."""
        # Look for ytInitialPlayerResponse
        match = re.search(r"ytInitialPlayerResponse\s*=\s*({.+?});", html, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
                captions = data.get("captions", {}).get("captionTracks", [])
                if captions:
                    # Prefer English, fallback to first available
                    for cap in captions:
                        if "en" in cap.get("languageCode", ""):
                            return cap["baseUrl"]
                    return captions[0]["baseUrl"]
            except Exception:
                pass
        return None

    def get_transcript(self, video_url_or_id: str) -> List[TranscriptSegment]:
        """Get transcript segments for a YouTube video."""
        video_id = video_url_or_id if len(video_url_or_id) == 11 else self.extract_video_id(video_url_or_id)
        if not video_id:
            return []
        html = self._fetch_page(video_id)
        if not html:
            return []
        transcript_url = self._extract_transcript_url(html)
        if not transcript_url:
            return []
        try:
            req = urllib.request.Request(transcript_url + "&fmt=json3", headers=self.headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8", errors="ignore"))
                segments = []
                for event in data.get("events", []):
                    text = " ".join(seg.get("utf8", "") for seg in event.get("segs", []))
                    if text.strip():
                        segments.append(TranscriptSegment(
                            text=text.strip(),
                            start=event.get("tStartMs", 0) / 1000.0,
                            duration=event.get("dDurationMs", 0) / 1000.0,
                        ))
                return segments
        except Exception:
            return []

    def get_full_text(self, video_url_or_id: str) -> str:
        """Get full transcript text as a single string."""
        segments = self.get_transcript(video_url_or_id)
        return " ".join(seg.text for seg in segments)

    def get_video_info(self, video_url_or_id: str) -> Dict[str, Any]:
        """Get basic video info."""
        video_id = video_url_or_id if len(video_url_or_id) == 11 else self.extract_video_id(video_url_or_id)
        if not video_id:
            return {}
        html = self._fetch_page(video_id)
        if not html:
            return {}
        match = re.search(r"ytInitialPlayerResponse\s*=\s*({.+?});", html, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
                vd = data.get("videoDetails", {})
                return {
                    "title": vd.get("title", ""),
                    "author": vd.get("author", ""),
                    "length_seconds": vd.get("lengthSeconds", 0),
                    "view_count": vd.get("viewCount", 0),
                    "video_id": video_id,
                }
            except Exception:
                pass
        return {}

    def to_dict(self) -> Dict[str, Any]:
        return {"description": "YouTube transcript extractor without API keys"}


__all__ = ["YouTubeTranscriptExtractor", "TranscriptSegment"]
