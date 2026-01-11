"""Storage utilities for runs, transcripts, and labels."""

import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
import subprocess

from sycop.config import RunConfig


def get_run_id(run_name: str) -> str:
    """Generate a timestamped run ID."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    # Sanitize run_name
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in run_name)
    return f"{timestamp}_{safe_name}"


def create_run_folder(base_path: Path, run_id: str) -> Path:
    """Create a run folder and return its path."""
    run_path = base_path / run_id
    run_path.mkdir(parents=True, exist_ok=True)
    return run_path


def save_config(run_path: Path, config: RunConfig) -> None:
    """Save run configuration to JSON."""
    config_path = run_path / "config.json"
    with open(config_path, "w") as f:
        json.dump(config.to_dict(), f, indent=2)


def load_config(run_path: Path) -> dict:
    """Load run configuration from JSON."""
    config_path = run_path / "config.json"
    with open(config_path, "r") as f:
        return json.load(f)


def write_transcript_jsonl(run_path: Path, transcript: dict) -> None:
    """Append a transcript record to JSONL file."""
    transcripts_path = run_path / "transcripts.jsonl"
    with open(transcripts_path, "a") as f:
        f.write(json.dumps(transcript) + "\n")


def read_transcripts(run_path: Path) -> list[dict]:
    """Read all transcripts from JSONL file."""
    transcripts_path = run_path / "transcripts.jsonl"
    if not transcripts_path.exists():
        return []
    
    transcripts = []
    with open(transcripts_path, "r") as f:
        for line in f:
            if line.strip():
                transcripts.append(json.loads(line))
    return transcripts


def write_labels_jsonl(run_path: Path, label: dict) -> None:
    """Append a label record to JSONL file."""
    labels_path = run_path / "labels.jsonl"
    with open(labels_path, "a") as f:
        f.write(json.dumps(label) + "\n")


def read_labels(run_path: Path) -> list[dict]:
    """Read all labels from JSONL file."""
    labels_path = run_path / "labels.jsonl"
    if not labels_path.exists():
        return []
    
    labels = []
    with open(labels_path, "r") as f:
        for line in f:
            if line.strip():
                labels.append(json.loads(line))
    return labels


def compute_file_hash(path: Path) -> str:
    """Compute SHA256 hash of a file."""
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def get_git_commit_hash() -> Optional[str]:
    """Get current git commit hash."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd=Path.cwd(),
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def get_python_env_info() -> dict:
    """Get Python environment information."""
    import sys
    import platform
    
    return {
        "python_version": sys.version,
        "platform": platform.platform(),
        "architecture": platform.machine(),
    }

