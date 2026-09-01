"""
Domain Value Object: TechStack
Represents standardized software engineering skills, frameworks, and tools.
"""
from dataclasses import dataclass
from typing import FrozenSet, Iterable, List


@dataclass(frozen=True)
class TechStack:
    """
    Immutable value object encapsulating a set of normalized technical skills.

    Time Complexity:
        Initialization & Lookup: O(N) where N is the number of skills.
    Space Complexity:
        O(N) storage in frozen set.
    """

    skills: FrozenSet[str]

    @classmethod
    def from_iterable(cls, items: Iterable[str]) -> "TechStack":
        """
        Factory method to construct normalized TechStack from strings or tags.

        Time Complexity: O(N * L) where L is average token length.
        Space Complexity: O(N)
        """
        cleaned = {
            item.strip().lower()
            for item in items
            if item and item.strip()
        }
        return cls(skills=frozenset(cleaned))

    def contains(self, skill: str) -> bool:
        """Check if skill exists in set in O(1) time."""
        return skill.strip().lower() in self.skills

    def overlap_score(self, target_skills: "TechStack") -> float:
        """
        Compute Jaccard similarity or overlap ratio between two tech stacks.

        Time Complexity: O(min(|A|, |B|)) set intersection.
        Space Complexity: O(min(|A|, |B|))
        """
        if not self.skills or not target_skills.skills:
            return 0.0
        common = self.skills.intersection(target_skills.skills)
        return len(common) / len(target_skills.skills)

    def to_list(self) -> List[str]:
        """Return sorted list of standardized tags."""
        return sorted(list(self.skills))
