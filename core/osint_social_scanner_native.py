"""OSINT Social Scanner — Social media presence detection."""
from dataclasses import dataclass
from pathlib import Path
import json

@dataclass
class SocialProfile:
    platform: str = ""
    username: str = ""
    url: str = ""
    found: bool = False
    bio: str = ""
    followers: int = 0

class OsintSocialScanner:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._profiles: list[SocialProfile] = []
        self._platforms = ["twitter", "github", "linkedin", "instagram", "facebook", "reddit", "tiktok", "youtube"]
        self._persist_path = self.root / "osint_social.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._profiles = [SocialProfile(**p) for p in data.get("profiles", [])]

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "profiles": [p.__dict__ for p in self._profiles]
        }, indent=2))

    def scan_username(self, username: str) -> list[SocialProfile]:
        results = []
        for platform in self._platforms:
            url = f"https://{platform}.com/{username}"
            # Simulate detection (presence check)
            profile = SocialProfile(
                platform=platform,
                username=username,
                url=url,
                found=True,  # Simulated
                bio=f"Bio for {username} on {platform}",
                followers=0
            )
            self._profiles.append(profile)
            results.append(profile)
        self._save()
        return results

    def search_by_name(self, name: str) -> list[SocialProfile]:
        return [p for p in self._profiles if name.lower() in p.username.lower() or name.lower() in p.bio.lower()]

    def get_platforms(self) -> list[str]:
        return self._platforms

    def add_platform(self, platform: str, url_template: str) -> None:
        if platform not in self._platforms:
            self._platforms.append(platform)

    def to_dict(self) -> dict:
        return {"profile_count": len(self._profiles), "platforms": len(self._platforms)}

    def get_stats(self) -> dict:
        found = sum(1 for p in self._profiles if p.found)
        by_platform = {}
        for p in self._profiles:
            by_platform[p.platform] = by_platform.get(p.platform, 0) + 1
        return {"profiles": len(self._profiles), "found": found, "by_platform": by_platform}

__all__ = ["OsintSocialScanner", "SocialProfile"]
