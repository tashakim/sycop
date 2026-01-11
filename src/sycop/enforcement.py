"""Runtime enforcement: gate + rewrite logic."""

from pathlib import Path
from typing import Optional
import json

from sycop.config import EnforcementConfig, ModelConfig
from sycop.config import Settings
from sycop.models import ModelClient
from sycop.suite import Scenario


def load_prompt_template(name: str) -> str:
    """Load a prompt template from prompts directory."""
    prompt_path = Path(__file__).parent / "prompts" / f"{name}.txt"
    with open(prompt_path, "r") as f:
        return f.read()


class Enforcement:
    """Enforcement logic: gate detection + rewrite."""

    def __init__(
        self,
        config: EnforcementConfig,
        gate_model_config: ModelConfig,
        rewrite_model_config: ModelConfig,
        settings: Optional[Settings] = None,
    ):
        self.config = config
        self.gate_client = ModelClient(gate_model_config, settings)
        self.rewrite_client = ModelClient(rewrite_model_config, settings)
        self.gate_prompt_template = load_prompt_template("gate_prompt")
        self.rewrite_prompt_template = load_prompt_template("rewrite_prompt")

    def should_enforce(self, scenario: Scenario) -> bool:
        """Check if enforcement should be applied to this scenario."""
        if not self.config.enabled:
            return False
        if self.config.only_when_correction_required:
            return scenario.normative_expectation.correction_required
        return True

    def gate(self, premise: str, reply: str) -> dict:
        """Gate: detect if reply endorses premise."""
        prompt = self.gate_prompt_template.replace("{{PREMISE}}", premise).replace("{{REPLY}}", reply)
        
        messages = [{"role": "user", "content": prompt}]
        
        try:
            result, meta = self.gate_client.generate_json(messages)
            return {
                "endorses_premise": result.get("endorses_premise", False),
                "confidence": float(result.get("confidence", 0.0)),
                "evidence": result.get("evidence", ""),
                "gate_meta": meta.model_dump(),
            }
        except Exception as e:
            # Fallback: assume no endorsement on error
            return {
                "endorses_premise": False,
                "confidence": 0.0,
                "evidence": f"Error: {str(e)}",
                "gate_meta": None,
            }

    def rewrite(
        self,
        user_turn: str,
        premise: str,
        draft_reply: str,
    ) -> tuple[str, dict]:
        """Rewrite draft reply to avoid endorsement."""
        prompt = (
            self.rewrite_prompt_template
            .replace("{{USER_TURN}}", user_turn)
            .replace("{{PREMISE}}", premise)
            .replace("{{DRAFT}}", draft_reply)
        )
        
        messages = [{"role": "user", "content": prompt}]
        
        try:
            final_reply, meta = self.rewrite_client.generate(messages)
            return final_reply.strip(), {
                "rewrite_meta": meta.model_dump(),
            }
        except Exception as e:
            # Fallback: return draft on error
            return draft_reply, {
                "rewrite_meta": None,
                "error": str(e),
            }

    def enforce(
        self,
        scenario: Scenario,
        user_turn: str,
        draft_reply: str,
    ) -> tuple[str, dict]:
        """Full enforcement pipeline: gate + conditional rewrite."""
        if not self.should_enforce(scenario):
            return draft_reply, {"enforced": False, "reason": "not_required"}

        if not self.config.gate_enabled:
            # Skip gate, always rewrite (not recommended but supported)
            final_reply, rewrite_info = self.rewrite(
                user_turn,
                scenario.contested_premise,
                draft_reply,
            )
            return final_reply, {
                "enforced": True,
                "rewritten": True,
                "gate_skipped": True,
                **rewrite_info,
            }

        # Gate first
        gate_result = self.gate(scenario.contested_premise, draft_reply)
        
        should_rewrite = (
            gate_result["endorses_premise"]
            and gate_result["confidence"] >= self.config.endorse_confidence_threshold
        )

        if not should_rewrite or not self.config.rewrite_enabled:
            return draft_reply, {
                "enforced": True,
                "rewritten": False,
                "gate_result": gate_result,
            }

        # Rewrite
        final_reply, rewrite_info = self.rewrite(
            user_turn,
            scenario.contested_premise,
            draft_reply,
        )

        return final_reply, {
            "enforced": True,
            "rewritten": True,
            "gate_result": gate_result,
            **rewrite_info,
        }

