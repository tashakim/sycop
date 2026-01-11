"""Load and validate prompt suite YAML files."""

from pathlib import Path
from typing import Literal, Optional
import yaml
from pydantic import BaseModel, Field, field_validator


class NormativeExpectation(BaseModel):
    """Normative expectation for a scenario."""
    correction_required: bool
    should_not_validate: bool


class Scenario(BaseModel):
    """A single scenario from the suite."""
    id: str
    category: Literal["false_premise", "authority", "moral_framing", "identity_belonging"]
    contested_premise: str
    normative_expectation: NormativeExpectation
    turns: list[str] = Field(min_length=4, max_length=10)
    notes: Optional[dict] = None

    @field_validator("turns")
    @classmethod
    def validate_turns(cls, v: list[str]) -> list[str]:
        """Ensure turns are non-empty strings."""
        if not all(isinstance(t, str) and len(t.strip()) > 0 for t in v):
            raise ValueError("All turns must be non-empty strings")
        return v


class Suite(BaseModel):
    """A complete prompt suite."""
    scenarios: list[Scenario]

    @classmethod
    def from_yaml(cls, path: Path) -> "Suite":
        """Load suite from YAML file."""
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        
        if not isinstance(data, list):
            raise ValueError("Suite YAML must be a list of scenarios")
        
        scenarios = [Scenario(**item) for item in data]
        return cls(scenarios=scenarios)

    def filter_by_correction_required(self) -> "Suite":
        """Return only scenarios where correction is required."""
        filtered = [
            s for s in self.scenarios
            if s.normative_expectation.correction_required
        ]
        return Suite(scenarios=filtered)

    def limit(self, max_scenarios: Optional[int] = None) -> "Suite":
        """Limit number of scenarios."""
        if max_scenarios is None:
            return self
        return Suite(scenarios=self.scenarios[:max_scenarios])

