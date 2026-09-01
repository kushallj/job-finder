"""
Domain Value Object: Compensation
Represents monetary salary compensation range and currency.
Follows Clean Architecture and Immutable Value Object principles.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Compensation:
    """
    Immutable value object representing compensation details.

    Attributes:
        min_salary: Lower bound of salary in local currency units.
        max_salary: Upper bound of salary in local currency units.
        currency: ISO 4217 currency symbol or code (e.g., 'INR', 'USD', '₹', '$').
        period: Pay frequency ('annual', 'monthly', 'hourly').

    Time Complexity:
        Initialization & Validation: O(1)
    Space Complexity:
        O(1)
    """

    min_salary: Optional[float] = None
    max_salary: Optional[float] = None
    currency: Optional[str] = "INR"
    period: str = "annual"

    def __post_init__(self) -> None:
        """Validate invariant rules for salary ranges."""
        if self.min_salary is not None and self.min_salary < 0:
            raise ValueError(f"min_salary cannot be negative: {self.min_salary}")
        if self.max_salary is not None and self.max_salary < 0:
            raise ValueError(f"max_salary cannot be negative: {self.max_salary}")
        if (
            self.min_salary is not None
            and self.max_salary is not None
            and self.min_salary > self.max_salary
        ):
            raise ValueError(
                f"min_salary ({self.min_salary}) cannot exceed max_salary ({self.max_salary})"
            )

    @property
    def has_range(self) -> bool:
        """Check if both bounds are defined."""
        return self.min_salary is not None and self.max_salary is not None

    @property
    def midpoint(self) -> Optional[float]:
        """Compute midpoint for ranking/simulation purposes."""
        if self.has_range and self.min_salary is not None and self.max_salary is not None:
            return (self.min_salary + self.max_salary) / 2.0
        return self.min_salary or self.max_salary

    def format_display(self) -> str:
        """Format human-readable compensation string."""
        curr = self.currency or "₹"
        if self.min_salary and self.max_salary:
            return f"{curr} {self.min_salary:,.0f} - {self.max_salary:,.0f}"
        if self.min_salary:
            return f"{curr} {self.min_salary:,.0f}+"
        if self.max_salary:
            return f"Up to {curr} {self.max_salary:,.0f}"
        return "Competitive"
