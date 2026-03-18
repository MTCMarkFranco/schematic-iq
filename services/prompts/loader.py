"""
Prompt loader — loads versioned prompt sets by stage and version.

Prompt structure:
  prompts/
    _shared/         — shared rules (included in all stages)
    stage2/v1/       — Stage 2 discovery prompts (version 1)
    stage3/v1/       — Stage 3 extraction prompts (version 1)
    rules/           — Domain rule files (uploaded to Code Interpreter)
"""

import os
from pathlib import Path


_PROMPTS_ROOT = Path(__file__).parent.parent.parent / "prompts"


def load_prompt(stage: str, version: str, filename: str) -> str:
    """Load a single prompt file.

    Args:
        stage: Stage identifier (e.g., "stage2", "stage3")
        version: Version string (e.g., "v1")
        filename: File name within the version directory (e.g., "system.md")

    Returns:
        The prompt text content.
    """
    path = _PROMPTS_ROOT / stage / version / filename
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


def load_shared(filename: str) -> str:
    """Load a shared prompt file from prompts/_shared/."""
    path = _PROMPTS_ROOT / "_shared" / filename
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


def load_stage2_prompts(version: str = "v1") -> dict[str, str]:
    """Load the complete Stage 2 prompt set.

    Returns dict with keys: 'system', 'user_template', 'json_rules'
    """
    prompts = {}
    prompts["system"] = load_prompt("stage2", version, "system.md")
    user_template_path = _PROMPTS_ROOT / "stage2" / version / "user_template.md"
    if user_template_path.exists():
        prompts["user_template"] = load_prompt("stage2", version, "user_template.md")
    prompts["json_rules"] = load_shared("json_rules.md")
    return prompts


def load_stage3_prompts(version: str = "v1") -> dict[str, str]:
    """Load the complete Stage 3 prompt set.

    Returns dict with keys: 'system', 'policy_pack', 'json_rules'
    """
    prompts = {}
    prompts["system"] = load_prompt("stage3", version, "system.md")
    policy_path = _PROMPTS_ROOT / "stage3" / version / "policy_pack.md"
    if policy_path.exists():
        prompts["policy_pack"] = load_prompt("stage3", version, "policy_pack.md")
    prompts["json_rules"] = load_shared("json_rules.md")
    return prompts


def load_rule_files() -> list[tuple[str, str]]:
    """Load all domain rule files from prompts/rules/.

    Returns list of (filename, content) tuples.
    """
    rules_dir = _PROMPTS_ROOT / "rules"
    if not rules_dir.exists():
        return []
    rules = []
    for path in sorted(rules_dir.iterdir()):
        if path.suffix == ".md":
            with open(path, "r", encoding="utf-8") as f:
                rules.append((path.name, f.read().strip()))
    return rules


def list_versions(stage: str) -> list[str]:
    """List available versions for a stage."""
    stage_dir = _PROMPTS_ROOT / stage
    if not stage_dir.exists():
        return []
    return sorted(
        d.name for d in stage_dir.iterdir() if d.is_dir() and d.name.startswith("v")
    )


# Legacy compatibility — load prompts from original locations
def load_discovery_prompt() -> str:
    """Load the Stage 2 discovery system prompt (legacy path).

    First tries the versioned path, falls back to the original file.
    """
    versioned_path = _PROMPTS_ROOT / "stage2" / "v1" / "system.md"
    if versioned_path.exists():
        with open(versioned_path, "r", encoding="utf-8") as f:
            return f.read().strip()
    # Fallback to original
    legacy_path = _PROMPTS_ROOT / "system-prompt-discovery.md"
    with open(legacy_path, "r", encoding="utf-8") as f:
        return f.read().strip()


def load_agent_instructions() -> str:
    """Load the Stage 3 agent instructions (legacy path).

    First tries the versioned path, falls back to the original file.
    """
    versioned_path = _PROMPTS_ROOT / "stage3" / "v1" / "system.md"
    if versioned_path.exists():
        with open(versioned_path, "r", encoding="utf-8") as f:
            return f.read().strip()
    # Fallback to original
    legacy_path = _PROMPTS_ROOT / "agent-instructions-extraction.md"
    with open(legacy_path, "r", encoding="utf-8") as f:
        return f.read().strip()
