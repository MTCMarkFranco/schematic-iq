# Plugins

## Overview

The plugin system allows optional enrichments to the pipeline without
altering the core extraction stages.  Plugins are **off by default** and
must be explicitly enabled.

## Available Plugins

### Template Symbol Detector

Uses OpenCV template matching to locate known symbol templates in the
schematic image.

| Setting | Default | Description |
|---|---|---|
| `SIQ_PLUGIN_TEMPLATE_SYMBOLS` | `0` (off) | Set to `1` to enable |
| Template directory | `templates/symbols/` | PNG files, stem = symbol name |
| Confidence threshold | 0.75 | Minimum NCC score |
| NMS overlap | 0.3 | IoU threshold for suppression |

#### Enabling

```bash
# Via environment variable
SIQ_PLUGIN_TEMPLATE_SYMBOLS=1 python main.py image.png
```

#### Adding Templates

Place grayscale PNG files in `templates/symbols/`:

```
templates/symbols/
├── fuse.png
├── relay.png
└── ground.png
```

File stems become symbol names in the output.

#### Output

When enabled, the plugin adds `template_symbol_candidates` to Stage 2 output:

```json
{
  "template_symbol_candidates": [
    {
      "template_name": "fuse",
      "bbox": {"x": 120, "y": 340, "w": 32, "h": 32},
      "confidence": 0.8723,
      "metadata": {}
    }
  ]
}
```

#### Programmatic Usage

```python
from services.plugins.template_symbols import TemplateSymbolDetector

detector = TemplateSymbolDetector(
    template_dir="templates/symbols",
    confidence_threshold=0.80,
)
candidates = detector.detect("schematic.png")
for c in candidates:
    print(f"{c.template_name} at ({c.x},{c.y}) conf={c.confidence:.3f}")
```

## Writing a New Plugin

1. Create `services/plugins/my_plugin.py`
2. Implement `is_enabled()` (check env/config)
3. Implement a detection/enrichment method
4. Export from `services/plugins/__init__.py`
5. Add documentation entry here
