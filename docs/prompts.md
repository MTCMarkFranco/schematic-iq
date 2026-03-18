# Prompt Versioning

## Overview

Schematic-IQ prompts are versioned and organized by stage. This enables safe prompt iteration without breaking existing behavior.

## Directory Structure

```
prompts/
├── _shared/                    # Shared rules (all stages)
│   └── json_rules.md          # Generic JSON output constraints
├── stage2/
│   └── v1/
│       ├── system.md           # Stage 2 discovery system prompt
│       └── user_template.md    # Stage 2 user message template
├── stage3/
│   └── v1/
│       ├── system.md           # Stage 3 agent instructions
│       └── policy_pack.md      # Stage 3 deterministic rules
├── rules/                      # Domain rule files (15+ files)
│   ├── cable.md
│   ├── wire.md
│   └── ...
├── system-prompt-discovery.md  # Original Stage 2 prompt (legacy)
└── agent-instructions-extraction.md  # Original Stage 3 prompt (legacy)
```

## Loader API

```python
from services.prompts.loader import (
    load_stage2_prompts,
    load_stage3_prompts,
    load_rule_files,
    load_discovery_prompt,      # Legacy compatibility
    load_agent_instructions,    # Legacy compatibility
)

# Load versioned prompt sets
s2 = load_stage2_prompts(version="v1")
s3 = load_stage3_prompts(version="v1")

# Load rule files
rules = load_rule_files()  # [(filename, content), ...]
```

## Adding a New Version

1. Create `prompts/stage2/v2/` (or `stage3/v2/`)
2. Copy files from `v1/` and modify
3. Test by specifying `version="v2"` in the loader
4. Keep `v1` as default until regression tests confirm parity

## Policy Pack

The policy pack (`stage3/v1/policy_pack.md`) contains deterministic rules that Stage 3 always includes:
- JSON schema constraints
- Object type rules
- Relationship type rules  
- Code Interpreter behavior rules

This file is uploaded to the agent alongside the domain rules.

## Compatibility

The loader provides legacy compatibility functions (`load_discovery_prompt()`, `load_agent_instructions()`) that first try the versioned path, then fall back to the original files. This ensures zero behavior change during migration.
