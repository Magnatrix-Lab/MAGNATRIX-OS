"""Native stdlib module: Photo Caption Manager
Manages photo captions, credits, and alt text for editorial content.
"""
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class PhotoEntry:
    photo_id: str
    caption: str
    credit: str
    alt_text: str
    keywords: List[str] = field(default_factory=list)

@dataclass
class PhotoCaptionManager:
    story_name: str
    photos: List[PhotoEntry] = field(default_factory=list)

    def photo_count(self) -> int:
        return len(self.photos)

    def avg_caption_length(self) -> float:
        if not self.photos:
            return 0.0
        return sum(len(p.caption) for p in self.photos) / len(self.photos)

    def missing_alt_text(self) -> List[str]:
        return [p.photo_id for p in self.photos if not p.alt_text]

    def all_keywords(self) -> List[str]:
        keywords = set()
        for p in self.photos:
            keywords.update(p.keywords)
        return sorted(keywords)

    def stats(self) -> Dict:
        return {
            "story": self.story_name,
            "photo_count": self.photo_count(),
            "avg_caption_length": round(self.avg_caption_length(), 1),
            "missing_alt_text": self.missing_alt_text(),
            "all_keywords": self.all_keywords(),
        }

def run():
    pcm = PhotoCaptionManager(
        story_name="City Marathon",
        photos=[
            PhotoEntry("P001", "Runners at the starting line", "Photo by John Smith", "Runners prepare at the starting line of the marathon", ["marathon", "running", "sports"]),
            PhotoEntry("P002", "Winner crossing finish line", "Photo by Jane Doe", "", ["winner", "finish line", "victory"]),
            PhotoEntry("P003", "Crowd cheering", "Photo by Bob Lee", "Spectators cheering along the race route", ["crowd", "cheering", "spectators"]),
        ]
    )
    print(pcm.stats())

if __name__ == "__main__":
    run()
