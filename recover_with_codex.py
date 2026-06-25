#!/usr/bin/env python3
"""Ask the locally authenticated Codex CLI to reconstruct Python source."""

from __future__ import annotations

import subprocess
from pathlib import Path


root = Path(__file__).parent
disassembly = (root / "portable_motor_gui.dis").read_text(encoding="utf-8")
skeleton = (root / "portable_motor_gui.skeleton.py").read_text(encoding="utf-8")
prompt = f"""Reconstruct a complete, editable Python 3.14 module from its CPython bytecode disassembly.
Output only valid Python source: no Markdown and no explanation.
Preserve every import, global, function/class signature and entry point in the skeleton.
Replace every `pass  # pychd: unrecovered body` with behaviorally equivalent code inferred from the authoritative disassembly.
Do not retain `__classcell__ = ...`; that is decompiler noise. Do not invent credentials or external endpoints absent from the disassembly.

SKELETON:
```python
{skeleton}
```

AUTHORITATIVE DISASSEMBLY:
```
{disassembly}
```
"""
output = root / "portable_motor_gui.recovered.py"
subprocess.run(
    [
        "codex", "exec", "--ephemeral", "--skip-git-repo-check",
        "--sandbox", "read-only", "-m", "gpt-5.5", "-o", str(output), "-",
    ],
    input=prompt,
    text=True,
    check=True,
)
