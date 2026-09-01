"""
Domain Value Object: EmailAddress
Encapsulates RFC-compliant email validation and domain parsing.
"""
from dataclasses import dataclass
import re


EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


@dataclass(frozen=True)
class EmailAddress:
    """
    Immutable validated email value object.

    Time Complexity:
        Validation & Extraction: O(L) where L is email length.
    Space Complexity:
        O(1)
    """

    value: str

    def __post_init__(self) -> None:
        """Validate invariant format rules upon construction."""
        if not self.value or not isinstance(self.value, str):
            raise ValueError("Email address cannot be empty.")
        clean = self.value.strip().lower()
        if not EMAIL_REGEX.match(clean):
            raise ValueError(f"Invalid email address format: {self.value}")
        object.__setattr__(self, "value", clean)

    @property
    def domain(self) -> str:
        """Extract domain portion for MX routing & pattern mining."""
        return self.value.split("@")[-1]

    @property
    def local_part(self) -> str:
        """Extract local username portion."""
        return self.value.split("@")[0]

    def __str__(self) -> str:
        return self.value
