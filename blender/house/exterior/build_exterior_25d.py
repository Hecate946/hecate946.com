"""
Compatibility entry point for the professional exterior builder.

Why this wrapper uses runpy instead of a normal sibling import
---------------------------------------------------------------
When Blender executes a script with:

    blender --background --python path/to/script.py

the script's directory is not guaranteed to be present on sys.path in the same
way as a normal Python CLI invocation. Therefore:

    from build_exterior_pro import main

can fail even though build_exterior_pro.py is sitting beside this file.

Resolve and execute the sibling script by absolute path instead. This makes the
entry point independent of Blender's import-path behavior.
"""

from __future__ import annotations

import runpy
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PRO_BUILDER = SCRIPT_DIR / "build_exterior_pro.py"

if not PRO_BUILDER.exists():
    raise FileNotFoundError(
        f"Professional exterior builder not found: {PRO_BUILDER}"
    )

runpy.run_path(str(PRO_BUILDER), run_name="__main__")
