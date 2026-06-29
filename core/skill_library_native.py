"""
skill_library_native.py
MAGNATRIX-OS — Skill Library

Inspired by telagod/code-abyss 30 domain skills:
Composable skill library with context-aware loading and domain expertise. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class Skill:
    skill_id: str
    name: str
    domain: str
    description: str
    content: str
    tags: List[str] = field(default_factory=list)
    usage_count: int = 0


class SkillLibrary:
    """Composable skill library with 30+ domain skills."""

    SKILL_LIBRARY = {
        "defending-applications": Skill(
            skill_id="defending-applications", name="Defending Applications",
            domain="security", description="Web/API/GraphQL hardening, OAuth/OIDC/JWT/Session, LLM AppSec",
            content="Application security hardening patterns. Covers input validation, auth flows, session management, prompt injection defense, RAG poisoning mitigation.",
            tags=["security", "web", "api", "llm"],
        ),
        "securing-cloud": Skill(
            skill_id="securing-cloud", name="Securing Cloud and Supply Chain",
            domain="security", description="Container escape, K8s RBAC/PSS, Service Mesh, SLSA/Sigstore/SBOM",
            content="Cloud security and supply chain hardening. Container security, Kubernetes policies, service mesh configs, SBOM generation, SLSA compliance.",
            tags=["security", "cloud", "kubernetes", "devops"],
        ),
        "detecting-responding": Skill(
            skill_id="detecting-responding", name="Detecting and Responding",
            domain="security", description="Sigma/YARA rule writing, EDR primitives, NIST 800-61 IR, forensics",
            content="Detection engineering and incident response. Write Sigma/YARA rules, EDR telemetry analysis, forensic artifact collection, hypothesis-driven threat hunting.",
            tags=["security", "detection", "forensics", "ir"],
        ),
        "architecting-security": Skill(
            skill_id="architecting-security", name="Architecting Security",
            domain="security", description="STRIDE/PASTA/LINDDUN threat modeling, zero-trust identity, compliance",
            content="Security architecture and threat modeling. STRIDE/PASTA/LINDDUN methodologies, zero-trust identity (WebAuthn/Kerberos/PAM JIT), SOC2/PCI/HIPAA/GDPR evidence chains.",
            tags=["security", "architecture", "compliance", "threat_modeling"],
        ),
        "single-agent-dev": Skill(
            skill_id="single-agent-dev", name="Single Agent Development",
            domain="ai", description="ReAct/Plan-Execute patterns, single-agent design",
            content="Single AI agent development patterns. ReAct loop, Plan-Execute architecture, tool use, memory management, reasoning traces.",
            tags=["ai", "agent", "react"],
        ),
        "multi-agent-orchestration": Skill(
            skill_id="multi-agent-orchestration", name="Multi-Agent Orchestration",
            domain="ai", description="Multi-agent coordination, delegation, consensus",
            content="Multi-agent system design. Agent roles, delegation protocols, consensus mechanisms, conflict resolution, swarm patterns.",
            tags=["ai", "multi_agent", "orchestration"],
        ),
        "rag-design": Skill(
            skill_id="rag-design", name="RAG System Design",
            domain="ai", description="Retrieval-Augmented Generation pipeline design",
            content="RAG pipeline architecture. Chunking strategies, embedding models, vector stores, reranking, hybrid search, query transformation.",
            tags=["ai", "rag", "llm"],
        ),
        "prompt-engineering": Skill(
            skill_id="prompt-engineering", name="Prompt Engineering",
            domain="ai", description="Advanced prompting techniques and patterns",
            content="Prompt engineering patterns. Few-shot, chain-of-thought, self-consistency, tree-of-thoughts, prompt chaining, structured output.",
            tags=["ai", "prompting", "llm"],
        ),
        "api-design": Skill(
            skill_id="api-design", name="API Design",
            domain="architecture", description="RESTful and GraphQL API design principles",
            content="API design best practices. REST conventions, GraphQL schema design, versioning, pagination, rate limiting, error handling, OpenAPI specs.",
            tags=["architecture", "api", "rest"],
        ),
        "cloud-native": Skill(
            skill_id="cloud-native", name="Cloud Native Patterns",
            domain="architecture", description="Microservices, containers, service mesh, observability",
            content="Cloud-native architecture patterns. 12-factor apps, microservices decomposition, containerization, service mesh, observability pillars.",
            tags=["architecture", "cloud", "microservices"],
        ),
        "messaging-patterns": Skill(
            skill_id="messaging-patterns", name="Messaging Patterns",
            domain="architecture", description="Message queues, event-driven, saga pattern",
            content="Messaging and event-driven architecture. Message queues, pub/sub, event sourcing, CQRS, saga pattern, outbox pattern.",
            tags=["architecture", "messaging", "events"],
        ),
        "caching-strategies": Skill(
            skill_id="caching-strategies", name="Caching Strategies",
            domain="architecture", description="Cache patterns, invalidation, CDN",
            content="Caching strategies and patterns. Cache-aside, write-through, write-behind, cache invalidation, CDN edge caching, distributed cache consistency.",
            tags=["architecture", "caching", "performance"],
        ),
        "data-security": Skill(
            skill_id="data-security", name="Data Security",
            domain="architecture", description="Encryption, tokenization, data classification",
            content="Data security patterns. At-rest and in-transit encryption, tokenization, data masking, classification, DLP, key management.",
            tags=["architecture", "security", "data"],
        ),
        "python-dev": Skill(
            skill_id="python-dev", name="Python Development",
            domain="development", description="Python best practices, patterns, tooling",
            content="Python development patterns. Type hints, dataclasses, async/await, testing with pytest, packaging, virtual environments, performance profiling.",
            tags=["development", "python"],
        ),
        "typescript-dev": Skill(
            skill_id="typescript-dev", name="TypeScript Development",
            domain="development", description="TypeScript patterns, type system, tooling",
            content="TypeScript development patterns. Advanced types, generics, decorators, strict mode, monorepo tooling, testing with vitest/jest.",
            tags=["development", "typescript"],
        ),
        "go-dev": Skill(
            skill_id="go-dev", name="Go Development",
            domain="development", description="Go idioms, concurrency, testing",
            content="Go development patterns. Goroutines, channels, interfaces, error handling, testing, benchmarking, module management.",
            tags=["development", "go"],
        ),
        "rust-dev": Skill(
            skill_id="rust-dev", name="Rust Development",
            domain="development", description="Rust ownership, lifetimes, async",
            content="Rust development patterns. Ownership, borrowing, lifetimes, traits, async/await, error handling with Result, testing.",
            tags=["development", "rust"],
        ),
        "git-workflow": Skill(
            skill_id="git-workflow", name="Git Workflow",
            domain="devops", description="Git branching, merging, CI/CD integration",
            content="Git workflow patterns. Feature branches, trunk-based development, conventional commits, semantic versioning, release management, GitOps.",
            tags=["devops", "git", "cicd"],
        ),
        "testing-strategies": Skill(
            skill_id="testing-strategies", name="Testing Strategies",
            domain="devops", description="Unit, integration, e2e, property-based testing",
            content="Testing strategies. TDD, BDD, mutation testing, contract testing, chaos testing, test pyramid, coverage analysis.",
            tags=["devops", "testing", "quality"],
        ),
        "database-ops": Skill(
            skill_id="database-ops", name="Database Operations",
            domain="devops", description="DB design, optimization, migrations",
            content="Database operations. Schema design, indexing, query optimization, migration strategies, replication, sharding, backup/recovery.",
            tags=["devops", "database", "operations"],
        ),
        "observability": Skill(
            skill_id="observability", name="Observability",
            domain="devops", description="Metrics, logs, traces, alerting",
            content="Observability engineering. Three pillars (metrics, logs, traces), SLO/SLI, alerting thresholds, incident response, distributed tracing.",
            tags=["devops", "observability", "monitoring"],
        ),
        "performance-tuning": Skill(
            skill_id="performance-tuning", name="Performance Tuning",
            domain="devops", description="Profiling, optimization, bottleneck analysis",
            content="Performance engineering. CPU profiling, memory profiling, flame graphs, latency analysis, bottleneck identification, capacity planning.",
            tags=["devops", "performance", "optimization"],
        ),
        "finops": Skill(
            skill_id="finops", name="FinOps",
            domain="devops", description="Cloud cost optimization, resource management",
            content="FinOps practices. Cloud cost visibility, rightsizing, reserved instances, spot instances, chargeback, budget alerts, waste elimination.",
            tags=["devops", "cost", "cloud"],
        ),
        "design-systems": Skill(
            skill_id="design-systems", name="Design Systems",
            domain="frontend", description="Glassmorphism, Neubrutalism, Claymorphism, Liquid Glass",
            content="Frontend design systems. Component libraries, design tokens, theming, accessibility, Glassmorphism/Neubrutalism/Claymorphism/Liquid Glass patterns.",
            tags=["frontend", "design", "ui"],
        ),
        "kubernetes": Skill(
            skill_id="kubernetes", name="Kubernetes Operations",
            domain="infra", description="K8s deployment, scaling, networking, GitOps",
            content="Kubernetes operations. Pod design, deployments, services, ingress, networking, storage, RBAC, Helm, GitOps with ArgoCD/Flux.",
            tags=["infra", "kubernetes", "devops"],
        ),
        "gitops-iac": Skill(
            skill_id="gitops-iac", name="GitOps and IaC",
            domain="infra", description="Terraform, Pulumi, Ansible, infrastructure as code",
            content="GitOps and IaC patterns. Terraform modules, Pulumi programs, Ansible playbooks, state management, drift detection, policy as code.",
            tags=["infra", "gitops", "iac"],
        ),
        "data-pipelines": Skill(
            skill_id="data-pipelines", name="Data Pipelines",
            domain="data", description="ETL, streaming, data quality, lineage",
            content="Data engineering pipelines. ETL/ELT patterns, stream processing, data quality checks, lineage tracking, schema evolution, data contracts.",
            tags=["data", "pipeline", "etl"],
        ),
        "cultivating-skills": Skill(
            skill_id="cultivating-skills", name="Cultivating Skills",
            domain="self-evolution", description="Distill repeated workflows into reusable skills",
            content="Self-evolution skill cultivation. Pattern extraction from repeated workflows, safety scanning, three-tier publish funnel (local → project → community).",
            tags=["self-evolution", "automation", "meta"],
        ),
        "cultivating-personas": Skill(
            skill_id="cultivating-personas", name="Cultivating Personas",
            domain="self-evolution", description="Distill voice into Tech Persona Card",
            content="Persona cultivation. Voice extraction from interaction patterns, Tech Persona Card generation, validation, versioning, community sharing.",
            tags=["self-evolution", "persona", "meta"],
        ),
        "indexing-code": Skill(
            skill_id="indexing-code", name="Indexing Code",
            domain="code-intelligence", description="Call graph, impact analysis, temporal analysis",
            content="Code intelligence indexing. Call graph construction, reference resolution, impact analysis, hotspot detection, change coupling, evolution tracing.",
            tags=["code-intelligence", "analysis", "graph"],
        ),
    }

    def __init__(self, data_dir: str = "./skills"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.custom_skills: Dict[str, Skill] = {}
        self._load()

    def _load(self) -> None:
        file = self.data_dir / "custom_skills.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for sid, sd in data.items():
                        self.custom_skills[sid] = Skill(**sd)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.data_dir / "custom_skills.json", "w", encoding="utf-8") as f:
            json.dump({k: asdict(v) for k, v in self.custom_skills.items()}, f, indent=2)

    def get_skill(self, skill_id: str) -> Optional[Skill]:
        return self.SKILL_LIBRARY.get(skill_id) or self.custom_skills.get(skill_id)

    def list_skills(self, domain: Optional[str] = None) -> List[str]:
        all_skills = {**self.SKILL_LIBRARY, **self.custom_skills}
        if domain:
            return [s.skill_id for s in all_skills.values() if s.domain == domain]
        return list(all_skills.keys())

    def create_skill(self, skill_id: str, name: str, domain: str, description: str,
                     content: str, tags: List[str]) -> Skill:
        skill = Skill(skill_id=skill_id, name=name, domain=domain, description=description,
                      content=content, tags=tags)
        self.custom_skills[skill_id] = skill
        self._save()
        return skill

    def use_skill(self, skill_id: str) -> Optional[Skill]:
        skill = self.get_skill(skill_id)
        if skill:
            skill.usage_count += 1
            self._save()
        return skill

    def get_stats(self) -> Dict[str, Any]:
        domains = {}
        for s in {**self.SKILL_LIBRARY, **self.custom_skills}.values():
            domains[s.domain] = domains.get(s.domain, 0) + 1
        return {"total_skills": len(self.SKILL_LIBRARY) + len(self.custom_skills), "domains": domains}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["SkillLibrary", "Skill"]