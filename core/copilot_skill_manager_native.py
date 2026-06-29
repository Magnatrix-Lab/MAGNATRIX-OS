"""
copilot_skill_manager_native.py
MAGNATRIX-OS — Copilot Skill Manager

Inspired by awesome-copilot skills:
Reusable markdown skills with usage tracking and rating for AI agents.
Pure Python standard library.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class CopilotSkill:
    skill_id: str
    name: str
    description: str
    content: str
    tags: List[str] = field(default_factory=list)
    format: str = "markdown"
    usage_count: int = 0
    rating: float = 0.0
    rating_count: int = 0
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class CopilotSkillManager:
    """Manage reusable markdown skills with usage tracking and rating."""

    SKILL_LIBRARY = {
        "code_review": {
            "name": "Code Review Skill",
            "description": "Systematic code review methodology",
            "content": "## Code Review Checklist\n\n1. Correctness - does it do what it claims?\n2. Readability - naming, comments, structure\n3. Performance - algorithmic complexity, bottlenecks\n4. Security - injection, XSS, auth, secrets\n5. Testing - coverage, edge cases, mocks\n6. Style - PEP8, conventions, consistency",
            "tags": ["review", "quality", "checklist"],
        },
        "commit_message": {
            "name": "Commit Message Skill",
            "description": "Write conventional commit messages",
            "content": "## Conventional Commits\n\nFormat: `<type>(<scope>): <description>`\n\nTypes: feat, fix, docs, style, refactor, test, chore\n\nRules:\n- Use imperative mood (\'Add\' not \'Added\')\n- Keep subject under 50 chars\n- Body under 72 chars per line\n- Reference issues: Fixes #123",
            "tags": ["git", "commit", "conventional"],
        },
        "pr_description": {
            "name": "PR Description Skill",
            "description": "Write clear pull request descriptions",
            "content": "## PR Template\n\n### What\n- Describe the change\n\n### Why\n- Motivation and context\n\n### How\n- Implementation approach\n\n### Testing\n- Steps to verify\n\n### Checklist\n- [ ] Tests pass\n- [ ] Docs updated\n- [ ] Self-reviewed",
            "tags": ["pr", "github", "template"],
        },
        "error_handling": {
            "name": "Error Handling Skill",
            "description": "Robust exception handling patterns",
            "content": "## Error Handling Patterns\n\n1. Catch specific exceptions, not bare `except:`\n2. Use `finally` for cleanup\n3. Log before re-raising\n4. Custom exceptions inherit from domain base\n5. Never swallow exceptions silently\n6. Use context managers for resource management",
            "tags": ["error", "exception", "robustness"],
        },
        "logging": {
            "name": "Logging Skill",
            "description": "Structured logging best practices",
            "content": "## Logging Guidelines\n\n- Use module-level logger: `logger = logging.getLogger(__name__)`\n- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL\n- Structured logging: `{\"event\": \"user_login\", \"user_id\": 123}`\n- Never log sensitive data (passwords, tokens)\n- Use rotation for production logs\n- Include correlation IDs for tracing",
            "tags": ["logging", "observability", "structured"],
        },
        "api_design": {
            "name": "API Design Skill",
            "description": "REST API design principles",
            "content": "## API Design Principles\n\n1. Use nouns for resources: `/users` not `/getUsers`\n2. Use HTTP methods: GET, POST, PUT, DELETE, PATCH\n3. Version in URL: `/v1/users`\n4. Use pagination: `?page=1&limit=20`\n5. Consistent error format: `{\"error\": \"...\", \"code\": 400}`\n6. HATEOAS links for discoverability",
            "tags": ["api", "rest", "design"],
        },
        "testing": {
            "name": "Testing Skill",
            "description": "Unit and integration testing patterns",
            "content": "## Testing Patterns\n\n- Arrange-Act-Assert structure\n- One assert per test (preferably)\n- Use fixtures for setup/teardown\n- Mock external dependencies\n- Parametrize for multiple inputs\n- Property-based testing with Hypothesis\n- Integration tests use test DB",
            "tags": ["testing", "pytest", "tdd"],
        },
        "docker": {
            "name": "Docker Skill",
            "description": "Container best practices",
            "content": "## Docker Best Practices\n\n- Use multi-stage builds\n- Pin base image versions: `python:3.11-slim`\n- Run as non-root user\n- Use .dockerignore\n- Health checks in Dockerfile\n- Minimize layers: combine RUN commands\n- Use BuildKit for cache mounts",
            "tags": ["docker", "container", "devops"],
        },
    }

    def __init__(self, skills_dir: str = "./copilot_skills"):
        self.skills_dir = Path(skills_dir)
        self.skills_dir.mkdir(exist_ok=True)
        self.skills: Dict[str, CopilotSkill] = {}
        self._load()

    def _load(self) -> None:
        file = self.skills_dir / "skills.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for sid, sd in data.items():
                        self.skills[sid] = CopilotSkill(**sd)
            except Exception:
                pass

    def _save(self) -> None:
        file = self.skills_dir / "skills.json"
        with open(file, "w", encoding="utf-8") as f:
            json.dump({sid: asdict(s) for sid, s in self.skills.items()}, f, indent=2)

    def add_from_library(self, skill_id: str, new_id: Optional[str] = None) -> Optional[CopilotSkill]:
        if skill_id not in self.SKILL_LIBRARY:
            return None
        info = self.SKILL_LIBRARY[skill_id]
        sid = new_id or skill_id
        skill = CopilotSkill(
            skill_id=sid, name=info["name"], description=info["description"],
            content=info["content"], tags=info.get("tags", []),
        )
        self.skills[sid] = skill
        self._save()
        return skill

    def add_custom(self, skill_id: str, name: str, description: str,
                   content: str, tags: Optional[List[str]] = None) -> CopilotSkill:
        skill = CopilotSkill(
            skill_id=skill_id, name=name, description=description,
            content=content, tags=tags or [],
        )
        self.skills[skill_id] = skill
        self._save()
        return skill

    def compose_skills(self, skill_ids: List[str]) -> str:
        parts = []
        for sid in skill_ids:
            skill = self.skills.get(sid)
            if skill:
                parts.append(f"# {skill.name}\n{skill.content}")
        return "\n\n---\n\n".join(parts)

    def use_skill(self, skill_id: str) -> Optional[str]:
        skill = self.skills.get(skill_id)
        if not skill:
            return None
        skill.usage_count += 1
        self._save()
        return skill.content

    def rate_skill(self, skill_id: str, rating: float) -> bool:
        skill = self.skills.get(skill_id)
        if not skill or not (0.0 <= rating <= 5.0):
            return False
        total = skill.rating * skill.rating_count + rating
        skill.rating_count += 1
        skill.rating = total / skill.rating_count
        self._save()
        return True

    def get_skill(self, skill_id: str) -> Optional[CopilotSkill]:
        return self.skills.get(skill_id)

    def list_skills(self) -> List[CopilotSkill]:
        return list(self.skills.values())

    def search_by_tag(self, tag: str) -> List[CopilotSkill]:
        return [s for s in self.skills.values() if tag in s.tags]

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.skills)
        total_usage = sum(s.usage_count for s in self.skills.values())
        avg_rating = sum(s.rating for s in self.skills.values() if s.rating > 0) / max(1, sum(1 for s in self.skills.values() if s.rating > 0))
        return {
            "total_skills": total, "library_size": len(self.SKILL_LIBRARY),
            "total_usage": total_usage, "avg_rating": round(avg_rating, 2),
        }

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["CopilotSkillManager", "CopilotSkill"]