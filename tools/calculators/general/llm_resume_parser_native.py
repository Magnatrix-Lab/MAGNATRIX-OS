"""Native stdlib module: Resume Parser
Parses structured resume data into skills, experience, and education summaries.
"""
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum

class EducationLevel(Enum):
    HIGH_SCHOOL = "high_school"
    ASSOCIATE = "associate"
    BACHELOR = "bachelor"
    MASTER = "master"
    DOCTORATE = "doctorate"

@dataclass
class JobEntry:
    title: str
    company: str
    years: int
    skills: List[str] = field(default_factory=list)

@dataclass
class ResumeParser:
    candidate_name: str
    education: EducationLevel
    total_years_exp: int
    jobs: List[JobEntry] = field(default_factory=list)
    certifications: List[str] = field(default_factory=list)

    def all_skills(self) -> List[str]:
        skills = set()
        for job in self.jobs:
            skills.update(job.skills)
        skills.update(self.certifications)
        return sorted(skills)

    def avg_tenure_years(self) -> float:
        if not self.jobs:
            return 0.0
        return sum(j.years for j in self.jobs) / len(self.jobs)

    def skill_count(self) -> int:
        return len(self.all_skills())

    def stats(self) -> Dict:
        return {
            "candidate": self.candidate_name,
            "education": self.education.value,
            "total_years_exp": self.total_years_exp,
            "avg_tenure_years": round(self.avg_tenure_years(), 1),
            "skill_count": self.skill_count(),
            "all_skills": self.all_skills(),
        }

def run():
    rp = ResumeParser(
        candidate_name="Jane Doe",
        education=EducationLevel.MASTER,
        total_years_exp=8,
        jobs=[
            JobEntry("Data Scientist", "Acme Corp", 3, ["python", "ml", "sql"]),
            JobEntry("ML Engineer", "Beta Inc", 2, ["pytorch", "aws", "docker"]),
            JobEntry("Analyst", "Gamma LLC", 3, ["excel", "sql", "statistics"]),
        ],
        certifications=["AWS ML Specialty", "TensorFlow Developer"]
    )
    print(rp.stats())

if __name__ == "__main__":
    run()
