"""Runner: replay trajectories and generate transcripts."""

import random
from pathlib import Path
from typing import Optional

from sycop.config import RunConfig, Settings
from sycop.suite import Suite, Scenario
from sycop.models import ModelClient
from sycop.enforcement import Enforcement
from sycop.storage import (
    create_run_folder,
    save_config,
    write_transcript_jsonl,
    get_run_id,
    compute_file_hash,
    get_git_commit_hash,
    get_python_env_info,
)


def load_system_prompt() -> str:
    """Load system prompt from data directory."""
    prompt_path = Path(__file__).parent.parent.parent / "data" / "system_prompt.txt"
    with open(prompt_path, "r") as f:
        return f.read()


class Runner:
    """Main runner for executing scenarios."""

    def __init__(self, config: RunConfig, settings: Optional[Settings] = None):
        self.config = config
        self.settings = settings or Settings()
        
        # Initialize model clients
        model_settings = Settings()
        self.generation_client = ModelClient(config.models["generation"], model_settings)
        
        # Initialize enforcement if needed
        if "enforce" in config.conditions:
            self.enforcement = Enforcement(
                config.enforcement,
                config.models["gate"],
                config.models["rewrite"],
                model_settings,
            )
        else:
            self.enforcement = None
        
        # Load system prompt
        self.system_prompt = load_system_prompt()
        
        # Set seed for reproducibility
        random.seed(config.seed)

    def run_scenario(
        self,
        scenario: Scenario,
        condition: str,
        run_id: str,
        run_path: Path,
    ) -> None:
        """Run a single scenario under a condition."""
        messages = []
        
        for turn_idx, user_turn in enumerate(scenario.turns):
            # Add user turn
            messages.append({"role": "user", "content": user_turn})
            
            # Generate draft reply
            draft_reply, gen_meta = self.generation_client.generate(
                messages,
                self.system_prompt,
            )
            
            # Apply enforcement if needed
            if condition == "enforce" and self.enforcement:
                final_reply, enforcement_info = self.enforcement.enforce(
                    scenario,
                    user_turn,
                    draft_reply,
                )
            else:
                final_reply = draft_reply
                enforcement_info = {"enforced": False}
            
            # Add assistant reply to conversation
            messages.append({"role": "assistant", "content": final_reply})
            
            # Build transcript record
            transcript = {
                "run_id": run_id,
                "condition": condition,
                "scenario_id": scenario.id,
                "category": scenario.category,
                "turn_idx": turn_idx,
                "user": user_turn,
                "assistant": final_reply,
                "meta": {
                    "model": gen_meta.model,
                    "temperature": gen_meta.temperature,
                    "max_tokens": gen_meta.max_tokens,
                    "token_usage": gen_meta.token_usage,
                    "correction_required": scenario.normative_expectation.correction_required,
                    "contested_premise": scenario.contested_premise,
                },
            }
            
            # Add enforcement info if present
            if enforcement_info.get("enforced"):
                transcript["meta"]["enforcement"] = enforcement_info
                if enforcement_info.get("rewritten"):
                    transcript["meta"]["draft_reply"] = draft_reply
            
            # Write transcript
            write_transcript_jsonl(run_path, transcript)

    def run(
        self,
        suite: Suite,
        base_path: Path = Path("runs"),
    ) -> Path:
        """Run all scenarios under all conditions."""
        # Create run folder
        run_id = get_run_id(self.config.run_name)
        run_path = create_run_folder(base_path, run_id)
        
        # Save config with metadata
        config_dict = self.config.to_dict()
        metadata = {
            "run_id": run_id,
            "suite_hash": compute_file_hash(Path(self.config.suite.path)),
            "git_commit": get_git_commit_hash(),
            "python_env": get_python_env_info(),
            "system_prompt_hash": compute_file_hash(
                Path(__file__).parent.parent.parent / "data" / "system_prompt.txt"
            ),
        }
        # Save metadata separately (can't modify RunConfig easily)
        import json
        with open(run_path / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)
        save_config(run_path, self.config)
        
        # Run scenarios
        for condition in self.config.conditions:
            for scenario in suite.scenarios:
                self.run_scenario(scenario, condition, run_id, run_path)
        
        return run_path

