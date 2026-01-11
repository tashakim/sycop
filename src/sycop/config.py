"""Configuration management using Pydantic."""

from pathlib import Path
from typing import Literal, Optional
import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ModelConfig(BaseModel):
    """Model configuration for API calls."""
    provider: str = "openai"
    model: str
    temperature: float = 0.0
    top_p: float = 1.0
    max_tokens: int


class SuiteConfig(BaseModel):
    """Suite configuration."""
    path: str
    heldout_path: Optional[str] = None
    max_scenarios: Optional[int] = None
    turns_per_scenario: Optional[int] = None


class EnforcementConfig(BaseModel):
    """Enforcement configuration."""
    enabled: bool = True
    gate_enabled: bool = True
    rewrite_enabled: bool = True
    only_when_correction_required: bool = True
    endorse_confidence_threshold: float = 0.70
    rewrite_style: dict = Field(default_factory=dict)


class LoggingConfig(BaseModel):
    """Logging configuration."""
    save_raw_provider_responses: bool = False
    save_token_usage: bool = True
    save_system_prompt_hash: bool = True
    save_git_commit: bool = True
    save_python_env: bool = True


class StatsConfig(BaseModel):
    """Statistics configuration."""
    bootstrap_resamples: int = 2000
    ci_alpha: float = 0.05
    paired_permutation_test: bool = True
    permutation_trials: int = 5000


class RepeatsConfig(BaseModel):
    """Repeat configuration for nondeterminism checks."""
    enabled: bool = True
    subset_size: int = 10
    repeats_per_scenario: int = 3
    conditions: list[str] = Field(default_factory=lambda: ["baseline"])


class RunConfig(BaseModel):
    """Complete run configuration."""
    run_name: str
    seed: int = 0
    suite: SuiteConfig
    models: dict[str, ModelConfig]
    conditions: list[Literal["baseline", "log", "enforce"]]
    enforcement: EnforcementConfig
    logging: LoggingConfig
    stats: StatsConfig
    repeats: RepeatsConfig

    @classmethod
    def from_yaml(cls, path: Path) -> "RunConfig":
        """Load configuration from YAML file."""
        # Resolve to absolute path
        path = Path(path).resolve()
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        
        # Resolve relative paths in suite config (relative to project root, not config file)
        project_root = Path(__file__).parent.parent.parent
        if "suite" in data and "path" in data["suite"]:
            suite_path = Path(data["suite"]["path"])
            if not suite_path.is_absolute():
                # Resolve relative to project root
                resolved = (project_root / suite_path).resolve()
                data["suite"]["path"] = str(resolved)
            else:
                data["suite"]["path"] = str(suite_path)
        
        if "suite" in data and "heldout_path" in data["suite"] and data["suite"]["heldout_path"]:
            heldout_path = Path(data["suite"]["heldout_path"])
            if not heldout_path.is_absolute():
                resolved = (project_root / heldout_path).resolve()
                data["suite"]["heldout_path"] = str(resolved)
            else:
                data["suite"]["heldout_path"] = str(heldout_path)
        
        return cls(**data)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return self.model_dump()


class Settings(BaseSettings):
    """Environment settings."""
    openai_api_key: str = Field(alias="OPENAI_API_KEY")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

