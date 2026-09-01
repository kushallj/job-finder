"""
Application Service: TaxonomyClassifier
Categorizes job postings into tech stacks, seniority tiers, and work modes.
"""
import re
from typing import List, Tuple
from src.domain.value_objects.tech_stack import TechStack
from src.domain.value_objects.experience_level import ExperienceLevel

TECH_PATTERNS = {
    "Python": re.compile(r"\b(python|django|fastapi|flask|pandas|numpy|pytorch)\b", re.I),
    "Go / Golang": re.compile(r"\b(golang|go\s*developer|goroutine|gin|grpc)\b", re.I),
    "Rust": re.compile(r"\b(rust|tokio|actix|cargo|systems\s*programming)\b", re.I),
    "Java": re.compile(r"\b(java|spring\s*boot|hibernate|jvm|kotlin)\b", re.I),
    "C++": re.compile(r"\b(c\+\+|cpp|clang|multithreading|low\s*latency)\b", re.I),
    "React / Next.js": re.compile(r"\b(react|next\.js|redux|typescript|javascript)\b", re.I),
    "AWS / Cloud": re.compile(r"\b(aws|cloud|ec2|s3|lambda|dynamodb|azure|gcp)\b", re.I),
    "Kubernetes / Docker": re.compile(r"\b(kubernetes|k8s|docker|helm|terraform)\b", re.I),
    "Kafka / Event-Driven": re.compile(r"\b(kafka|rabbitmq|event\s*driven|eventbridge)\b", re.I),
    "GenAI & LLMs": re.compile(r"\b(llm|rag|langchain|llamaindex|generative\s*ai|openai|claude)\b", re.I),
    "Mobile (iOS / Android)": re.compile(r"\b(ios|android|swift|flutter|react\s*native)\b", re.I),
    "Security / Infosec": re.compile(r"\b(security|infosec|soc2|pci|owasp|cryptography)\b", re.I),
    "FinTech": re.compile(r"\b(fintech|payments|upi|banking|trading|crypto|ledger)\b", re.I),
}


class TaxonomyClassifier:
    """
    Classifies raw text into standardized tech stack and leveling value objects.

    Time Complexity:
        classify(): O(T * L) where T is pattern count and L is text length.
    Space Complexity:
        O(M) for matched tag collection.
    """

    @staticmethod
    def classify(title: str, description: str = "") -> Tuple[TechStack, ExperienceLevel, bool, str]:
        """Extract tech stack, level, remote status, and work mode from job content."""
        combined = f"{title} {description}".lower()

        # 1. Tech Stack
        matched_tags: List[str] = []
        for stack_name, pattern in TECH_PATTERNS.items():
            if pattern.search(combined):
                matched_tags.append(stack_name)

        # 2. Seniority Level
        exp_level = ExperienceLevel.from_text(title)
        matched_tags.append(exp_level.tier.value)

        # 3. Remote / Work Mode
        is_remote = any(k in combined for k in ("remote", "work from home", "wfh", "anywhere"))
        work_mode = "remote" if is_remote else ("hybrid" if "hybrid" in combined else "onsite")

        return TechStack.from_iterable(matched_tags), exp_level, is_remote, work_mode
